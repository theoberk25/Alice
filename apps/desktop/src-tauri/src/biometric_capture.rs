//! Parent-owned, bounded camera pipe. Renderer IPC cannot select a helper or feed pixels.
use serde::Serialize;
use serde_json::Value;
use std::{
    io::{BufRead, BufReader, Read},
    process::{Child, Command, Stdio},
    sync::{
        atomic::{AtomicBool, Ordering},
        mpsc::{sync_channel, Receiver, TrySendError},
        Arc, Mutex,
    },
    time::{Duration, Instant},
};

#[derive(Clone, Serialize)]
pub struct Preview {
    pub session_id: String,
    pub sequence: u64,
    pub jpeg: String,
}

#[derive(Default)]
pub struct PreviewSlot {
    pub latest: Option<(Preview, Instant)>,
}
impl PreviewSlot {
    fn accept(&mut self, packet: &Value, session_id: &str) -> Result<(), String> {
        let sequence = packet["sequence"]
            .as_u64()
            .filter(|s| (1..=3000).contains(s))
            .ok_or("INVALID_PREVIEW_SEQUENCE")?;
        let jpeg = packet["jpeg"]
            .as_str()
            .filter(|s| !s.is_empty() && s.len() <= 700_000)
            .ok_or("INVALID_PREVIEW_FRAME")?;
        if packet["session_id"] != session_id
            || self
                .latest
                .as_ref()
                .is_some_and(|(p, _)| p.sequence >= sequence)
        {
            return Err("INVALID_PREVIEW_BINDING".into());
        }
        self.latest = Some((
            Preview {
                session_id: session_id.into(),
                sequence,
                jpeg: jpeg.into(),
            },
            Instant::now(),
        ));
        Ok(())
    }
    pub fn read(&self) -> Option<Preview> {
        self.latest
            .as_ref()
            .filter(|(_, at)| at.elapsed() <= Duration::from_millis(500))
            .map(|(frame, _)| frame.clone())
    }
}

pub struct Capture {
    child: Arc<Mutex<Child>>,
    _directory: tempfile::TempDir,
    pub frames: Receiver<Result<Value, String>>,
    pub preview: Arc<Mutex<PreviewSlot>>,
    pub failure: Arc<Mutex<Option<String>>>,
    stopping: Arc<AtomicBool>,
}

fn record_failure(latch: &Mutex<Option<String>>, reason: String) {
    if let Ok(mut first) = latch.lock() {
        if first.is_none() {
            *first = Some(reason);
        }
    }
}

fn record_eof(latch: &Mutex<Option<String>>, stopping: &AtomicBool) {
    // Dropping a capture after an inference error intentionally kills its helper.
    // That cleanup EOF must not replace the original error in the session view.
    // A disconnect observed before shutdown remains latched and cannot be erased.
    if !stopping.load(Ordering::SeqCst) {
        record_failure(latch, "CAMERA_DISCONNECTED".into());
    }
}

impl Capture {
    #[cfg(target_os = "macos")]
    pub fn start(session_id: &str, seconds: u64) -> Result<Self, String> {
        use std::os::unix::fs::PermissionsExt;
        if uuid::Uuid::parse_str(session_id).is_err() || !(1..=90).contains(&seconds) {
            return Err("INVALID_CAPTURE_SESSION".into());
        }
        let directory = tempfile::Builder::new()
            .prefix("alice-camera-")
            .tempdir()
            .map_err(|e| e.to_string())?;
        std::fs::set_permissions(directory.path(), std::fs::Permissions::from_mode(0o700))
            .map_err(|e| e.to_string())?;
        let path = directory.path().join("camera");
        std::fs::write(
            &path,
            include_bytes!(concat!(env!("OUT_DIR"), "/alice-biometric-camera")),
        )
        .map_err(|e| e.to_string())?;
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o500))
            .map_err(|e| e.to_string())?;
        let mut child = Command::new(&path)
            .args([session_id, &seconds.to_string()])
            .env_clear()
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|_| "NATIVE_CAMERA_START_FAILED")?;
        let output = child.stdout.take().ok_or("CAMERA_PIPE_MISSING")?;
        let (sender, frames) = sync_channel(1);
        let preview = Arc::new(Mutex::new(PreviewSlot::default()));
        let reader_preview = preview.clone();
        let failure = Arc::new(Mutex::new(None));
        let reader_failure = failure.clone();
        let stopping = Arc::new(AtomicBool::new(false));
        let reader_stopping = stopping.clone();
        let binding = session_id.to_owned();
        std::thread::spawn(move || {
            let mut reader = BufReader::new(output);
            loop {
                let mut line = Vec::new();
                let read = reader.by_ref().take(700_001).read_until(b'\n', &mut line);
                let packet: Result<Value, String> = match read {
                    Ok(0) => {
                        record_eof(&reader_failure, &reader_stopping);
                        let _ = sender.try_send(Err("CAMERA_DISCONNECTED".into()));
                        break;
                    }
                    Ok(_) if line.len() <= 700_000 => serde_json::from_slice::<Value>(&line)
                        .map_err(|_| "INVALID_CAMERA_PACKET".into()),
                    _ => {
                        record_failure(&reader_failure, "CAMERA_PACKET_LIMIT".into());
                        let _ = sender.try_send(Err("CAMERA_PACKET_LIMIT".into()));
                        break;
                    }
                };
                if let Err(ref reason) = packet {
                    record_failure(&reader_failure, reason.clone());
                    break;
                }
                if let Ok(ref value) = packet {
                    if value["kind"] == "stopped" {
                        record_failure(
                            &reader_failure,
                            value["reason"]
                                .as_str()
                                .filter(|s| s.len() <= 200)
                                .unwrap_or("CAMERA_STOPPED")
                                .into(),
                        );
                        break;
                    }
                    if value["kind"] == "preview" {
                        let valid = reader_preview
                            .lock()
                            .map_err(|_| "PREVIEW_LOCK_FAILED".to_owned())
                            .and_then(|mut slot| slot.accept(value, &binding));
                        if let Err(reason) = valid {
                            record_failure(&reader_failure, reason.clone());
                            let _ = sender.try_send(Err(reason));
                            break;
                        }
                        continue;
                    }
                }
                match sender.try_send(packet) {
                    Ok(_) | Err(TrySendError::Full(_)) => {} // One pending frame; drop excess.
                    Err(TrySendError::Disconnected(_)) => break,
                }
            }
            if let Ok(mut slot) = reader_preview.lock() {
                slot.latest = None;
            }
        });
        Ok(Self {
            child: Arc::new(Mutex::new(child)),
            _directory: directory,
            frames,
            preview,
            failure,
            stopping,
        })
    }

    #[cfg(not(target_os = "macos"))]
    pub fn start(_: &str, _: u64) -> Result<Self, String> {
        Err("NATIVE_CAMERA_MACOS_REQUIRED".into())
    }

    pub fn stop_handle(&self) -> Arc<Mutex<Child>> {
        self.child.clone()
    }

    pub fn next(&self) -> Result<Option<Value>, String> {
        self.check_health()?;
        match self.frames.recv_timeout(Duration::from_millis(100)) {
            Ok(result) => result.map(Some),
            Err(std::sync::mpsc::RecvTimeoutError::Timeout) => Ok(None),
            Err(_) => Err("CAMERA_DISCONNECTED".into()),
        }
    }

    pub fn check_health(&self) -> Result<(), String> {
        if let Some(reason) = self
            .failure
            .lock()
            .map_err(|_| "CAMERA_STATE_UNAVAILABLE")?
            .clone()
        {
            return Err(reason);
        }
        if self
            .child
            .lock()
            .map_err(|_| "CAMERA_STATE_UNAVAILABLE")?
            .try_wait()
            .map_err(|_| "CAMERA_STATE_UNAVAILABLE")?
            .is_some()
        {
            return Err("CAMERA_DISCONNECTED".into());
        }
        Ok(())
    }
}

impl Drop for Capture {
    fn drop(&mut self) {
        self.stopping.store(true, Ordering::SeqCst);
        if let Ok(mut child) = self.child.lock() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    #[test]
    fn intentional_cleanup_keeps_inference_error_but_real_disconnect_still_fails() {
        use crate::biometric_sessions::{Book, Purpose};
        let failure = Arc::new(Mutex::new(None));
        let stopping = AtomicBool::new(false);
        let mut book = Book::default();
        book.begin(Purpose::Enrollment, "T1".into(), "none".into(), None)
            .unwrap();
        let id = book.current.as_ref().unwrap().view.session_id.clone();
        book.current.as_mut().unwrap().capture_failure = Some(failure.clone());
        // Simulate a rejected inference unwinding Capture before its caller
        // records the service error, while a UI poll/watchdog reads the session.
        stopping.store(true, Ordering::SeqCst);
        record_eof(&failure, &stopping);
        let attempt = book.get(&id).unwrap();
        assert!(!attempt.terminal());
        attempt.finish("FAILED", "PAD_INVALID_BOUNDS");
        assert_eq!(attempt.view.reason, "PAD_INVALID_BOUNDS");

        let failure = Mutex::new(None);
        let stopping = AtomicBool::new(false);
        record_eof(&failure, &stopping);
        stopping.store(true, Ordering::SeqCst);
        record_eof(&failure, &stopping);
        assert_eq!(
            failure.lock().unwrap().as_deref(),
            Some("CAMERA_DISCONNECTED")
        );
    }
    #[test]
    fn camera_failure_survives_a_full_evidence_queue() {
        let (sender, receiver) = sync_channel(1);
        sender
            .try_send(Ok::<_, String>(json!({"kind":"frame"})))
            .unwrap();
        let failure = Mutex::new(None);
        record_failure(&failure, "CAMERA_DISCONNECTED".into());
        assert!(sender.try_send(Err("CAMERA_DISCONNECTED".into())).is_err());
        record_failure(&failure, "LATER_FAILURE".into());
        assert_eq!(
            failure.lock().unwrap().as_deref(),
            Some("CAMERA_DISCONNECTED")
        );
        assert!(receiver.try_recv().unwrap().is_ok());
    }
    #[test]
    fn preview_keeps_only_newest_bound_frame_and_expires() {
        let mut slot = PreviewSlot::default();
        for sequence in 1..=100 {
            slot.accept(
                &json!({"session_id":"s1","sequence":sequence,"jpeg":"YQ=="}),
                "s1",
            )
            .unwrap();
        }
        assert_eq!(slot.read().unwrap().sequence, 100);
        assert!(slot
            .accept(
                &json!({"session_id":"s1","sequence":99,"jpeg":"YQ=="}),
                "s1"
            )
            .is_err());
        assert!(slot
            .accept(
                &json!({"session_id":"s2","sequence":101,"jpeg":"YQ=="}),
                "s1"
            )
            .is_err());
        slot.latest.as_mut().unwrap().1 = Instant::now() - Duration::from_secs(1);
        assert!(slot.read().is_none());
    }
}
