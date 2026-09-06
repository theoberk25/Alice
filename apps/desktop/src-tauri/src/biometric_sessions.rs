//! Native session and gate authority. No renderer frame/result submission API.
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    collections::BTreeMap,
    process::Child,
    sync::{Arc, Mutex},
    time::{Duration, Instant},
};
use uuid::Uuid;

pub const POLICY: &str = "alice.live-face.v3";
pub const REQUIRED: [&str; 5] = ["identity", "quality", "capture_integrity", "pose", "pad"];
pub const REQUIRED_POSES: [&str; 7] = [
    "CENTER", "LEFT", "RIGHT", "UP", "DOWN", "UP_LEFT", "UP_RIGHT",
];

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Purpose {
    Enrollment,
    Login,
    Approval,
}

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Intent {
    pub purpose: Purpose,
    pub username: Option<String>,
    pub technician_id: Option<String>,
    pub decision_id: Option<String>,
    pub request_id: Option<String>,
    pub runtime_action: Option<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Outcome {
    Pass,
    Fail,
    Inconclusive,
    Unavailable,
    NotConfigured,
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Control {
    pub result: Outcome,
    pub model: String,
    pub reason: String,
    pub score: Option<f64>,
}

#[derive(Clone, Serialize)]
pub struct View {
    pub schema_version: String,
    pub session_id: String,
    pub purpose: Purpose,
    pub state: String,
    pub policy: String,
    pub prompt: String,
    pub reason: String,
    pub coverage: BTreeMap<String, u32>,
    pub accepted_samples: u32,
    pub controls: BTreeMap<String, Control>,
    pub preview: Option<String>,
    pub technician: Option<crate::security::Technician>,
    pub verification: Option<crate::security::Grant>,
}

pub struct Attempt {
    pub view: View,
    pub nonce: String,
    pub helper_epoch: String,
    pub authority_epoch: String,
    pub technician_id: String,
    pub generation: String,
    pub scope: Option<Value>,
    pub started: Instant,
    pub deadline: Instant,
    pub camera: Option<Arc<Mutex<Child>>>,
    pub preview: Option<Arc<Mutex<crate::biometric_capture::PreviewSlot>>>,
    pub capture_failure: Option<Arc<Mutex<Option<String>>>>,
    pub last_poll: Instant,
    // Authority state is separate from the public terminal evidence. Consuming
    // a grant must not make a successful APPROVAL view schema-invalid.
    pub authority_consumed: bool,
    pub authority_revoked: bool,
}

impl Attempt {
    pub fn terminal(&self) -> bool {
        matches!(
            self.view.state.as_str(),
            "FAILED" | "CANCELLED" | "EXPIRED" | "SUCCEEDED"
        )
    }
    pub fn finish(&mut self, state: &str, reason: &str) {
        if self.terminal() {
            return;
        }
        if let Some(camera) = self.camera.take() {
            if let Ok(mut child) = camera.lock() {
                let _ = child.kill();
            }
        }
        self.view.preview = None;
        if let Some(preview) = self.preview.take() {
            if let Ok(mut slot) = preview.lock() {
                slot.latest = None;
            }
        }
        self.view.state = state.into();
        self.view.reason = reason.into();
    }
    pub fn revoke(&mut self, reason: &str) {
        self.authority_revoked = true;
        self.finish("CANCELLED", reason);
        if self.view.state == "SUCCEEDED" {
            self.view.state = "CANCELLED".into();
            self.view.reason = reason.into();
        }
        self.view.technician = None;
        self.view.verification = None;
    }
    pub fn valid(&mut self, epoch: &str, now: Instant) -> Result<(), String> {
        let failure = self
            .capture_failure
            .as_ref()
            .and_then(|latch| match latch.lock() {
                Ok(reason) => reason.clone(),
                Err(_) => Some("CAMERA_STATE_UNAVAILABLE".into()),
            });
        if !self.terminal() {
            if let Some(reason) = failure {
                self.finish("FAILED", &reason);
            }
        }
        if !self.terminal()
            && (now >= self.deadline || now.duration_since(self.last_poll) > Duration::from_secs(3))
        {
            self.finish("EXPIRED", "SESSION_OR_PRESENTATION_LEASE_EXPIRED");
        }
        if !self.terminal() && self.authority_epoch != epoch {
            self.finish("CANCELLED", "AUTHORITY_CHANGED");
        }
        if self.terminal() {
            Err(self.view.reason.clone())
        } else {
            Ok(())
        }
    }
}

impl Drop for Attempt {
    fn drop(&mut self) {
        self.finish("CANCELLED", "NATIVE_OWNER_DROPPED");
    }
}

pub struct Book {
    pub boot_epoch: String,
    pub authority_epoch: String,
    pub current: Option<Attempt>,
}
impl Default for Book {
    fn default() -> Self {
        Self {
            boot_epoch: Uuid::new_v4().to_string(),
            authority_epoch: Uuid::new_v4().to_string(),
            current: None,
        }
    }
}
impl Book {
    pub fn revoke(&mut self, reason: &str) {
        self.authority_epoch = Uuid::new_v4().to_string();
        if let Some(s) = self.current.as_mut() {
            s.revoke(reason);
        }
    }
    pub fn begin(
        &mut self,
        purpose: Purpose,
        technician_id: String,
        generation: String,
        scope: Option<Value>,
    ) -> Result<View, String> {
        if self.current.as_ref().is_some_and(|s| !s.terminal()) {
            return Err("BIOMETRIC_SESSION_BUSY".into());
        }
        let now = Instant::now();
        let seconds = if purpose == Purpose::Enrollment {
            90
        } else {
            45
        };
        let view = View {
            schema_version: "2.0".into(),
            session_id: Uuid::new_v4().to_string(),
            purpose,
            state: "CREATED".into(),
            policy: POLICY.into(),
            prompt: "CHECKING_REQUIRED_CONTROLS".into(),
            reason: String::new(),
            coverage: BTreeMap::new(),
            accepted_samples: 0,
            controls: BTreeMap::new(),
            preview: None,
            technician: None,
            verification: None,
        };
        self.current = Some(Attempt {
            view: view.clone(),
            nonce: Uuid::new_v4().to_string(),
            helper_epoch: Uuid::new_v4().to_string(),
            authority_epoch: self.authority_epoch.clone(),
            technician_id,
            generation,
            scope,
            started: now,
            deadline: now + Duration::from_secs(seconds),
            camera: None,
            preview: None,
            capture_failure: None,
            last_poll: now,
            authority_consumed: false,
            authority_revoked: false,
        });
        Ok(view)
    }
    pub fn get(&mut self, id: &str) -> Result<&mut Attempt, String> {
        let s = self
            .current
            .as_mut()
            .filter(|s| s.view.session_id == id)
            .ok_or("UNKNOWN_BIOMETRIC_SESSION")?;
        let _ = s.valid(&self.authority_epoch, Instant::now());
        Ok(s)
    }
}

pub fn validate_controls(controls: &BTreeMap<String, Control>) -> Result<(), String> {
    if controls.len() != REQUIRED.len() {
        return Err("MISSING_OR_UNKNOWN_CONTROL".into());
    }
    for key in REQUIRED {
        let c = controls.get(key).ok_or("MISSING_REQUIRED_CONTROL")?;
        if c.result != Outcome::Pass
            || c.model.is_empty()
            || c.reason.len() > 200
            || c.score
                .is_some_and(|v| !v.is_finite() || !(-1.0..=1.0).contains(&v))
        {
            return Err(format!("REQUIRED_CONTROL_NOT_PASSED:{key}"));
        }
    }
    Ok(())
}

pub fn validate_model_configuration(models: &Value) -> Result<(), String> {
    if models["pose"] != "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"
        || models["pad"] != "b32929adc2d9c34b9486f8c4c7bc97c1b69bc0ea9befefc380e4faae4e463907"
    {
        return Err("MODEL_CONFIGURATION_MISMATCH".into());
    }
    Ok(())
}

pub fn request(s: &Attempt, boot: &str) -> Value {
    json!({"schema_version":"2.0","session_id":s.view.session_id,"nonce":s.nonce,
        "boot_epoch":boot,"helper_epoch":s.helper_epoch,"policy":POLICY,"purpose":s.view.purpose,
        "technician_id":s.technician_id,"generation":s.generation})
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn gate_intersects_every_required_control() {
        let pass: BTreeMap<_, _> = REQUIRED
            .into_iter()
            .map(|k| {
                (
                    k.into(),
                    Control {
                        result: Outcome::Pass,
                        model: "test".into(),
                        reason: "test".into(),
                        score: Some(0.9),
                    },
                )
            })
            .collect();
        assert!(validate_controls(&pass).is_ok());
        for key in REQUIRED {
            for outcome in [
                Outcome::Fail,
                Outcome::Inconclusive,
                Outcome::Unavailable,
                Outcome::NotConfigured,
            ] {
                let mut values = pass.clone();
                values.get_mut(key).unwrap().result = outcome;
                assert!(validate_controls(&values).is_err());
            }
        }
        for key in REQUIRED {
            let mut values = pass.clone();
            values.remove(key);
            assert!(validate_controls(&values).is_err());
        }
        let mut values = pass;
        values.get_mut("pad").unwrap().score = Some(f64::NAN);
        assert!(validate_controls(&values).is_err());
    }
    #[test]
    fn cancellation_expiry_epoch_and_duplicate_terminal_are_final() {
        let mut b = Book::default();
        let v = b
            .begin(Purpose::Login, "T1".into(), "V2".into(), None)
            .unwrap();
        let preview = Arc::new(Mutex::new(crate::biometric_capture::PreviewSlot {
            latest: Some((
                crate::biometric_capture::Preview {
                    session_id: v.session_id.clone(),
                    sequence: 1,
                    jpeg: "YQ==".into(),
                },
                Instant::now(),
            )),
        }));
        b.current.as_mut().unwrap().preview = Some(preview.clone());
        b.revoke("LOGOUT");
        assert!(preview.lock().unwrap().read().is_none());
        let a = b.get(&v.session_id).unwrap();
        a.finish("SUCCEEDED", "late");
        assert_eq!(a.view.state, "CANCELLED");
        let next = b
            .begin(Purpose::Login, "T1".into(), "V2".into(), None)
            .unwrap();
        assert_ne!(v.session_id, next.session_id);
        assert!(b.get(&v.session_id).is_err());
        let epoch = b.authority_epoch.clone();
        let a = b.get(&next.session_id).unwrap();
        assert!(a.valid(&epoch, a.deadline).is_err());
        assert_eq!(a.view.state, "EXPIRED");
    }
    #[test]
    fn restart_and_new_attempt_have_fresh_bindings() {
        let mut a = Book::default();
        let b = Book::default();
        assert_ne!(a.boot_epoch, b.boot_epoch);
        a.begin(Purpose::Approval, "T1".into(), "V2".into(), None)
            .unwrap();
        let old = a.current.as_ref().unwrap().nonce.clone();
        a.revoke("POLICY_OR_HELPER_CHANGED");
        a.begin(Purpose::Approval, "T1".into(), "V2".into(), None)
            .unwrap();
        assert_ne!(old, a.current.as_ref().unwrap().nonce);
    }
    #[test]
    fn camera_failure_during_inference_cannot_become_success() {
        let mut book = Book::default();
        book.begin(Purpose::Login, "T1".into(), "g1".into(), None)
            .unwrap();
        let epoch = book.authority_epoch.clone();
        let attempt = book.current.as_mut().unwrap();
        attempt.view.state = "EVALUATING".into();
        attempt.capture_failure = Some(Arc::new(Mutex::new(Some("CAMERA_DISCONNECTED".into()))));
        assert_eq!(
            attempt.valid(&epoch, Instant::now()).unwrap_err(),
            "CAMERA_DISCONNECTED"
        );
        attempt.finish("SUCCEEDED", "late inference");
        assert_eq!(attempt.view.state, "FAILED");
    }
    #[test]
    fn renderer_cannot_add_frames_or_report_success() {
        assert!(
            serde_json::from_value::<Intent>(json!({"purpose":"LOGIN","frames":["image"]}))
                .is_err()
        );
        assert!(
            serde_json::from_value::<Intent>(json!({"purpose":"LOGIN","result":"PASS"})).is_err()
        );
        assert!(validate_model_configuration(&json!({"forged_media":"PASS"})).is_err());
    }
    #[test]
    fn no_operation_requests_head_movement_challenges() {
        for purpose in [Purpose::Enrollment, Purpose::Login, Purpose::Approval] {
            let mut book = Book::default();
            book.begin(purpose.clone(), "T1".into(), "g1".into(), None)
                .unwrap();
            let attempt = book.current.as_ref().unwrap();
            let payload = request(attempt, &book.boot_epoch);
            assert!(payload.get("challenge").is_none());
            if purpose == Purpose::Enrollment {
                assert_eq!(
                    attempt.deadline.duration_since(attempt.started).as_secs(),
                    90
                );
            } else {
                assert_eq!(
                    attempt.deadline.duration_since(attempt.started).as_secs(),
                    45
                );
            }
        }
    }
    #[test]
    fn live_face_requires_exact_pose_and_pad_without_a_forged_detector() {
        let models = json!({
            "pose":"64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff",
            "pad":"b32929adc2d9c34b9486f8c4c7bc97c1b69bc0ea9befefc380e4faae4e463907"
        });
        assert!(validate_model_configuration(&models).is_ok());
        for name in ["pose", "pad"] {
            let mut changed = models.clone();
            changed[name] = json!("unverified");
            assert!(validate_model_configuration(&changed).is_err());
        }
        let mut book = Book::default();
        book.begin(Purpose::Login, "T1".into(), "g1".into(), None)
            .unwrap();
        assert_eq!(
            request(book.current.as_ref().unwrap(), &book.boot_epoch)["policy"],
            "alice.live-face.v3"
        );
    }
}
