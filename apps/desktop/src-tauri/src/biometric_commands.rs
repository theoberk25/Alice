//! Facial-operation integration; existing decision and action authority stays in commands/security.
use crate::{
    biometric_capture::Capture,
    biometric_sessions::*,
    commands::*,
    config::Config,
    db,
    security::{require_admin, require_technician, Session},
    AppState, Inner,
};
use chrono::Utc;
use rusqlite::{params, OptionalExtension};
use serde::Deserialize;
use serde_json::{json, Value};
use std::{
    collections::BTreeMap,
    io::Read,
    time::{Duration, Instant},
};
use tauri::{AppHandle, Manager, State};

fn generation(s: &Inner, id: &str) -> Result<String, String> {
    require_no_removal(&s.db, id)?;
    let pending: bool =
        s.db.query_row(
            "SELECT EXISTS(SELECT 1 FROM face_activation_intents WHERE technician_id=?1)",
            [id],
            |r| r.get(0),
        )
        .map_err(|e| e.to_string())?;
    if pending {
        return Err("ENROLLMENT_ACTIVATION_RECOVERY_REQUIRED".into());
    }
    active_generation(s, id)
}

fn active_generation(s: &Inner, id: &str) -> Result<String, String> {
    Ok(s.db
        .query_row(
            "SELECT generation FROM face_enrollments WHERE technician_id=?1",
            [id],
            |r| r.get(0),
        )
        .optional()
        .map_err(|e| e.to_string())?
        .unwrap_or_else(|| "none".into()))
}

fn eligible(s: &Inner, attempt: &Attempt) -> Result<(), String> {
    require_no_removal(&s.db, &attempt.technician_id)?;
    let tech = technician(s, &attempt.technician_id)?;
    let pending: Option<(String, String)> = s.db.query_row(
        "SELECT generation,previous_generation FROM face_activation_intents WHERE technician_id=?1",
        [&tech.technician_id],
        |r| Ok((r.get(0)?, r.get(1)?)),
    ).optional().map_err(|e| e.to_string())?;
    if pending.is_some_and(|(generation, previous)| {
        // Polling must not cancel the enrollment that owns the in-flight
        // activation. Every other session still requires explicit recovery.
        attempt.view.purpose != Purpose::Enrollment
            || attempt.view.state != "EVALUATING"
            || generation != attempt.view.session_id
            || previous != attempt.generation
    }) {
        return Err("ENROLLMENT_ACTIVATION_RECOVERY_REQUIRED".into());
    }
    if !tech.enabled || active_generation(s, &tech.technician_id)? != attempt.generation {
        return Err("TECHNICIAN_OR_ENROLLMENT_CHANGED".into());
    }
    if attempt.view.purpose != Purpose::Enrollment
        && tech.enrollment_version.as_deref() != Some("MULTI_POSE_V2")
    {
        return Err("MULTI_POSE_V2_REQUIRED".into());
    }
    match attempt.view.purpose {
        Purpose::Enrollment => require_admin(s),
        Purpose::Login => {
            if tech.enrolled {
                Ok(())
            } else {
                Err("IDENTITY_NOT_ENROLLED".into())
            }
        }
        Purpose::Approval => {
            if require_technician(s)? != attempt.technician_id {
                return Err("TECHNICIAN_SESSION_CHANGED".into());
            }
            let scope = attempt.scope.as_ref().ok_or("MISSING_APPROVAL_SCOPE")?;
            let id = scope["decision_id"].as_str().ok_or("MISSING_DECISION")?;
            let current = load_decision(s, id)?;
            require_current_assessment(s, &current)?;
            if &current != scope
                || current["decision"]["result"] != "HOLD"
                || current["policy"]["result"] == "DENY"
                || !current["technician_actions"]["available"]
                    .as_array()
                    .is_some_and(|v| v.iter().any(|a| a == "APPROVE"))
            {
                return Err("APPROVAL_SCOPE_NO_LONGER_ELIGIBLE".into());
            }
            Ok(())
        }
    }
}

fn current(s: &mut Inner, id: &str) -> Result<(), String> {
    if s.biometrics.get(id)?.terminal() {
        return Err("BIOMETRIC_SESSION_TERMINAL".into());
    }
    let valid = eligible(s, s.biometrics.current.as_ref().ok_or("SESSION_MISSING")?);
    if let Err(ref reason) = valid {
        s.biometrics.get(id)?.finish("CANCELLED", reason);
    }
    valid
}

fn watch_session(state: &AppState, id: &str, stopped: std::sync::mpsc::Receiver<()>) {
    while matches!(
        stopped.recv_timeout(Duration::from_millis(100)),
        Err(std::sync::mpsc::RecvTimeoutError::Timeout)
    ) {
        // A stalled HTTP request must not extend the camera lease or authority.
        // This watcher owns no renderer input and cannot complete an operation.
        let Ok(mut s) = lock(state) else { return };
        if current(&mut s, id).is_err() {
            return;
        }
    }
}

#[tauri::command]
pub fn begin_biometric_session(
    app: AppHandle,
    state: State<AppState>,
    intent: Intent,
) -> Result<View, String> {
    let view = {
        let mut s = lock(&state)?;
        if s.config.biometric_mode != "arcface" {
            return Err("LIVE_CAPTURE_REQUIRES_REAL_BIOMETRIC_MODE".into());
        }
        let (id, scope) = match intent.purpose {
            Purpose::Enrollment => {
                require_admin(&s)?;
                if intent.username.is_some()
                    || intent.decision_id.is_some()
                    || intent.request_id.is_some()
                {
                    return Err("INVALID_ENROLLMENT_INTENT".into());
                }
                (intent.technician_id.ok_or("TECHNICIAN_REQUIRED")?, None)
            }
            Purpose::Login => {
                if intent.technician_id.is_some()
                    || intent.decision_id.is_some()
                    || intent.request_id.is_some()
                {
                    return Err("INVALID_LOGIN_INTENT".into());
                }
                let username = intent.username.ok_or("USERNAME_REQUIRED")?;
                if username.is_empty() || username.len() > 100 {
                    return Err("INVALID_USERNAME".into());
                }
                throttled(&s, &format!("login:{username}"))?;
                let id: String =
                    s.db.query_row(
                        "SELECT technician_id FROM technicians WHERE username=?1",
                        [username],
                        |r| r.get(0),
                    )
                    .map_err(|_| "IDENTITY_NOT_AVAILABLE")?;
                (id, None)
            }
            Purpose::Approval => {
                if intent.username.is_some() {
                    return Err("INVALID_APPROVAL_INTENT".into());
                }
                let id = require_technician(&s)?;
                if intent.technician_id.as_ref() != Some(&id) {
                    return Err("TECHNICIAN_MISMATCH".into());
                }
                let decision = load_decision(&s, &intent.decision_id.ok_or("DECISION_REQUIRED")?)?;
                if decision["request"]["request_id"].as_str() != intent.request_id.as_deref() {
                    return Err("REQUEST_MISMATCH".into());
                }
                throttled(&s, &id)?;
                (id, Some(decision))
            }
        };
        let tech = technician(&s, &id)?;
        if !tech.enabled {
            return Err("TECHNICIAN_DISABLED".into());
        }
        let generation = generation(&s, &id)?;
        if intent.purpose != Purpose::Enrollment
            && (generation == "legacy-v1"
                || generation == "none"
                || tech.enrollment_version.as_deref() != Some("MULTI_POSE_V2"))
        {
            return Err("MULTI_POSE_V2_REQUIRED: ask an administrator to re-enroll; prior enrollment is preserved".into());
        }
        let view = s.biometrics.begin(intent.purpose, id, generation, scope)?;
        current(&mut s, &view.session_id)?;
        view
    };
    let id = view.session_id.clone();
    tauri::async_runtime::spawn_blocking(move || {
        let state = app.state::<AppState>();
        let result = std::thread::scope(|scope| {
            let (stop, stopped) = std::sync::mpsc::channel();
            let worker_state = &*state;
            let session_id = id.as_str();
            scope.spawn(move || watch_session(worker_state, session_id, stopped));
            let result = run(&app, &id);
            drop(stop);
            result
        });
        if let Ok(mut s) = lock(&state) {
            if let Err(reason) = result {
                let failure = s
                    .biometrics
                    .get(&id)
                    .ok()
                    .filter(|a| !a.terminal())
                    .map(|a| {
                        let actor = (a.technician_id.clone(), a.view.purpose.clone());
                        a.finish("FAILED", &reason);
                        actor
                    });
                if let Some((tech, purpose)) = failure {
                    let key = if purpose == Purpose::Login {
                        format!(
                            "login:{}",
                            technician(&s, &tech)
                                .map(|t| t.username)
                                .unwrap_or_default()
                        )
                    } else {
                        tech.clone()
                    };
                    failed(&mut s, &key);
                    let _ = db::audit(
                        &s.db,
                        "LIVE_BIOMETRIC_FAILED",
                        &json!({"technician_id":tech,"purpose":purpose,"policy":POLICY}),
                    );
                }
            }
        };
    });
    Ok(view)
}

#[tauri::command]
pub fn read_biometric_session(state: State<AppState>, session_id: String) -> Result<View, String> {
    let mut s = lock(&state)?;
    if !s.biometrics.get(&session_id)?.terminal() {
        let _ = current(&mut s, &session_id);
    }
    let a = s.biometrics.get(&session_id)?;
    a.last_poll = Instant::now();
    Ok(a.view.clone())
}

#[tauri::command]
pub fn read_biometric_preview(
    state: State<AppState>,
    session_id: String,
) -> Result<Option<crate::biometric_capture::Preview>, String> {
    let mut s = lock(&state)?;
    if s.biometrics.get(&session_id)?.terminal() {
        return Ok(None);
    }
    current(&mut s, &session_id)?;
    let a = s.biometrics.get(&session_id)?;
    // Reading display pixels does not renew the session's presentation lease
    // or provide authentication evidence. Only the native capture owns this slot.
    Ok(a.preview
        .as_ref()
        .and_then(|slot| slot.lock().ok().and_then(|p| p.read())))
}

#[tauri::command]
pub fn cancel_biometric_session(state: State<AppState>, session_id: String) -> Result<(), String> {
    lock(&state)?
        .biometrics
        .get(&session_id)?
        .finish("CANCELLED", "OPERATOR_OR_NAVIGATION_CANCELLED");
    Ok(())
}

fn service(
    client: &reqwest::blocking::Client,
    config: &Config,
    path: &str,
    payload: Option<&Value>,
) -> Result<Value, String> {
    if config.biometric_token.len() < 32 {
        return Err("BIOMETRIC_SERVICE_TOKEN_NOT_CONFIGURED".into());
    }
    let url = format!("{}{path}", config.biometric_url);
    let request = if let Some(v) = payload {
        client.post(url).json(v)
    } else {
        client.get(url)
    };
    let response = request
        .bearer_auth(&config.biometric_token)
        .send()
        .map_err(|_| "BIOMETRIC_SERVICE_UNAVAILABLE")?;
    let status = response.status();
    let mut bytes = Vec::new();
    response
        .take(1_000_001)
        .read_to_end(&mut bytes)
        .map_err(|_| "BIOMETRIC_RESPONSE_READ_FAILED")?;
    if bytes.len() > 1_000_000 {
        return Err("BIOMETRIC_RESPONSE_TOO_LARGE".into());
    }
    let value: Value = serde_json::from_slice(&bytes).map_err(|_| "INVALID_BIOMETRIC_RESPONSE")?;
    if !status.is_success() {
        return Err(value["detail"]
            .as_str()
            .filter(|s| s.len() <= 200)
            .unwrap_or("BIOMETRIC_SERVICE_REJECTED")
            .into());
    }
    Ok(value)
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Evidence {
    schema_version: String,
    session_id: String,
    nonce: String,
    service_epoch: String,
    sequence: u64,
    purpose: Purpose,
    generation: String,
    boot_epoch: String,
    helper_epoch: String,
    policy: String,
    models: Value,
    controls: BTreeMap<String, Control>,
    accepted_samples: u32,
    coverage: BTreeMap<String, u32>,
    prompt: String,
    complete: bool,
}

fn run(app: &AppHandle, id: &str) -> Result<(), String> {
    let state = app.state::<AppState>();
    let (config, payload) = {
        let mut s = lock(&state)?;
        current(&mut s, id)?;
        (
            s.config.clone(),
            request(
                s.biometrics.current.as_ref().unwrap(),
                &s.biometrics.boot_epoch,
            ),
        )
    };
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(5))
        .redirect(reqwest::redirect::Policy::none())
        .build()
        .map_err(|e| e.to_string())?;
    let ready = service(&client, &config, "/live/readiness", None)?;
    if ready["schema_version"] != "2.0"
        || ready["policy"] != POLICY
        || ready["service_epoch"].as_str().is_none()
    {
        return Err("INVALID_LIVE_SERVICE_CONTRACT".into());
    }
    {
        let mut s = lock(&state)?;
        current(&mut s, id)?;
        let a = s.biometrics.get(id)?;
        for name in ["identity", "pose", "pad"] {
            let result = serde_json::from_value::<Outcome>(ready[name].clone())
                .map_err(|_| "INVALID_READINESS_OUTCOME")?;
            a.view.controls.insert(
                name.into(),
                Control {
                    // Availability is not observed biometric evidence.
                    result: if result == Outcome::Pass {
                        Outcome::Inconclusive
                    } else {
                        result
                    },
                    model: ready["models"][name].as_str().unwrap_or("UNKNOWN").into(),
                    reason: "MODEL_READINESS_ONLY".into(),
                    score: None,
                },
            );
        }
    }
    // Pin the required pose/PAD assets before camera acquisition.
    validate_model_configuration(&ready["models"])?;
    with_service_session(&client, &config, &payload, &ready, || {
        let seconds = if payload["purpose"] == "ENROLLMENT" {
            90
        } else {
            45
        };
        // Authority may have changed while the service handled begin. Avoid
        // opening the camera for a session that has already been cancelled.
        current(&mut *lock(&state)?, id)?;
        let capture = Capture::start(id, seconds)?;
        let capture_started = Instant::now();
        {
            let mut s = lock(&state)?;
            current(&mut s, id)?;
            let a = s.biometrics.get(id)?;
            a.camera = Some(capture.stop_handle());
            a.preview = Some(capture.preview.clone());
            a.capture_failure = Some(capture.failure.clone());
            a.view.state = "CAPTURING".into();
        }
        let mut last_sequence = 0;
        let mut last_elapsed = 0;
        let mut source_confirmed = false;
        loop {
            {
                let mut s = lock(&state)?;
                current(&mut s, id)?;
            }
            let Some(packet) = capture.next()? else {
                continue;
            };
            if packet["session_id"] != id {
                return Err("WRONG_CAPTURE_SESSION".into());
            }
            match packet["kind"].as_str() {
                Some("ready") => {
                    if packet["source"] != "AVFOUNDATION_BUILT_IN"
                        || packet["mirrored"] != false
                        || packet["width"] != 640
                        || !matches!(packet["height"].as_u64(), Some(360 | 480))
                    {
                        return Err("UNSUPPORTED_CAPTURE_SOURCE".into());
                    }
                    source_confirmed = true;
                    continue;
                }
                Some("frame") => {}
                _ => return Err(packet["reason"].as_str().unwrap_or("CAMERA_FAILED").into()),
            }
            let sequence = packet["sequence"]
                .as_u64()
                .ok_or("MISSING_SAMPLE_SEQUENCE")?;
            if !source_confirmed {
                return Err("CAPTURE_SOURCE_NOT_CONFIRMED".into());
            }
            let elapsed = packet["elapsed_ms"]
                .as_u64()
                .ok_or("MISSING_CAPTURE_TIME")?;
            let jpeg = packet["jpeg"]
                .as_str()
                .filter(|f| f.len() <= 700_000)
                .ok_or("INVALID_CAPTURE_FRAME")?;
            if sequence <= last_sequence
                || sequence > 360
                || elapsed <= last_elapsed
                || elapsed > 90_000
                || capture_started
                    .elapsed()
                    .as_millis()
                    .abs_diff(elapsed as u128)
                    > 1500
            {
                return Err("STALE_OR_REPLAYED_CAPTURE".into());
            }
            last_sequence = sequence;
            last_elapsed = elapsed;
            let observed = service(
                &client,
                &config,
                "/live/observe",
                Some(
                    &json!({"session_id":id,"nonce":payload["nonce"],"service_epoch":ready["service_epoch"],"sequence":sequence,"elapsed_ms":elapsed,"jpeg":jpeg}),
                ),
            )?;
            let e: Evidence =
                serde_json::from_value(observed).map_err(|_| "INVALID_EVIDENCE_CONTRACT")?;
            capture.check_health()?;
            if serde_json::to_value(&e.purpose).map_err(|_| "INVALID_PURPOSE")?
                != payload["purpose"]
                || e.generation != payload["generation"].as_str().unwrap_or("")
                || e.boot_epoch != payload["boot_epoch"].as_str().unwrap_or("")
                || e.helper_epoch != payload["helper_epoch"].as_str().unwrap_or("")
            {
                return Err("EVIDENCE_PURPOSE_OR_EPOCH_MISMATCH".into());
            }
            if e.schema_version != "2.0"
                || e.session_id != id
                || e.nonce != payload["nonce"].as_str().unwrap_or("")
                || e.service_epoch != ready["service_epoch"].as_str().unwrap_or("")
                || e.sequence != sequence
                || e.policy != POLICY
                || e.models != ready["models"]
                || e.accepted_samples > 360
                || e.coverage
                    .iter()
                    .any(|(k, v)| !REQUIRED_POSES.contains(&k.as_str()) || *v > 2)
            {
                return Err("EVIDENCE_BINDING_REJECTED".into());
            }
            let mut s = lock(&state)?;
            current(&mut s, id)?;
            let a = s.biometrics.get(id)?;
            // Preview has a separate bounded path and never waits on inference.
            a.view.preview = None;
            a.view.coverage = e.coverage;
            a.view.accepted_samples = e.accepted_samples;
            a.view.controls = e.controls;
            a.view.prompt = e.prompt;
            a.view.controls.insert(
                "capture_integrity".into(),
                Control {
                    result: Outcome::Pass,
                    model: "AVFOUNDATION_BUILT_IN".into(),
                    reason: "NATIVE_PIPE_AND_FRESHNESS_VALIDATED".into(),
                    score: None,
                },
            );
            if e.complete {
                validate_controls(&a.view.controls)?;
                let minimum_samples = if a.view.purpose == Purpose::Enrollment {
                    14
                } else {
                    3
                };
                if a.view.accepted_samples < minimum_samples
                    || (a.view.purpose == Purpose::Enrollment
                        && REQUIRED_POSES
                            .iter()
                            .any(|p| a.view.coverage.get(*p) != Some(&2)))
                {
                    return Err("INSUFFICIENT_EVIDENCE".into());
                }
                a.view.state = "EVALUATING".into();
                a.view.preview = None;
                break;
            }
        }
        capture.check_health()?;
        // Detach only after a healthy final observation. The following shutdown
        // is intentional; its EOF must not revoke the already completed capture.
        {
            let mut s = lock(&state)?;
            current(&mut s, id)?;
            s.biometrics.get(id)?.capture_failure = None;
        }
        drop(capture); // Release camera before authentication or persistent activation.
        lock(&state)?.biometrics.get(id)?.camera = None;
        complete(&state, id, &client, &config)
    })
}

fn with_service_session(
    client: &reqwest::blocking::Client,
    config: &Config,
    payload: &Value,
    ready: &Value,
    operation: impl FnOnce() -> Result<(), String>,
) -> Result<(), String> {
    let result = (|| {
        let opened = service(client, config, "/live/begin", Some(payload))?;
        if opened["session_id"] != payload["session_id"]
            || opened["service_epoch"] != ready["service_epoch"]
        {
            return Err("INFERENCE_RESTARTED".into());
        }
        operation()
    })();
    // Begin may have succeeded remotely even when its acknowledgment was lost.
    // Always release that exact binding, including camera-start failures.
    let _ = service(
        client,
        config,
        "/live/cancel",
        Some(
            &json!({"session_id":payload["session_id"],"nonce":payload["nonce"],"service_epoch":ready["service_epoch"]}),
        ),
    );
    result
}

fn complete(
    state: &AppState,
    id: &str,
    client: &reqwest::blocking::Client,
    config: &Config,
) -> Result<(), String> {
    let mut s = lock(state)?;
    current(&mut s, id)?;
    let a = s.biometrics.current.as_ref().unwrap();
    validate_controls(&a.view.controls)?;
    let purpose = a.view.purpose.clone();
    let tech = a.technician_id.clone();
    let previous = a.generation.clone();
    match purpose {
        Purpose::Enrollment => {
            s.db.execute(
                "INSERT INTO face_activation_intents VALUES(?1,?2,?3,?4)",
                params![tech, id, previous, Utc::now().to_rfc3339()],
            )
            .map_err(|e| e.to_string())?;
            let epoch = s.biometrics.authority_epoch.clone();
            drop(s);
            let ack = service(
                client,
                config,
                "/generation/activate",
                Some(&json!({"technician_id":tech,"generation":id,"previous_generation":previous})),
            )
            .map_err(|_| "ENROLLMENT_ACTIVATION_RECOVERY_REQUIRED")?;
            s = lock(state)?;
            if s.biometrics.authority_epoch != epoch || ack["generation"] != id {
                return Err("ACTIVATION_RECOVERY_REQUIRED".into());
            }
            current(&mut s, id).map_err(|_| "ENROLLMENT_ACTIVATION_RECOVERY_REQUIRED")?;
            commit_metadata(&mut s, &tech, id)
                .map_err(|_| "ENROLLMENT_ACTIVATION_RECOVERY_REQUIRED")?;
        }
        Purpose::Login => {
            let t = technician(&s, &tech)?;
            db::audit(
                &s.db,
                "TECHNICIAN_LOGIN_SUCCESS",
                &json!({"technician_id":tech,"policy":POLICY}),
            )?;
            s.failures.remove(&format!("login:{}", t.username));
            s.grants.clear();
            s.technician = Some(Session {
                id: tech.clone(),
                expires_at: Utc::now().timestamp() + 28_800,
            });
            s.biometrics.get(id)?.view.technician = Some(t);
        }
        Purpose::Approval => {
            let scope = s
                .biometrics
                .current
                .as_ref()
                .unwrap()
                .scope
                .clone()
                .ok_or("MISSING_SCOPE")?;
            let grant = issue_grant(
                &mut s,
                scope["decision_id"].as_str().ok_or("DECISION_MISSING")?,
                scope["request"]["request_id"]
                    .as_str()
                    .ok_or("REQUEST_MISSING")?,
                "PASS",
                "arcface",
            )?;
            s.failures.remove(&tech);
            s.biometrics.get(id)?.view.verification = Some(grant);
        }
    }
    s.biometrics
        .get(id)?
        .finish("SUCCEEDED", "ALL_REQUIRED_CONTROLS_PASSED");
    Ok(())
}

fn commit_metadata(s: &mut Inner, tech: &str, generation: &str) -> Result<(), String> {
    let tx = s.db.transaction().map_err(|e| e.to_string())?;
    require_no_removal(&tx, tech)?;
    let (pending, previous): (String, String) = tx
        .query_row(
            "SELECT generation,previous_generation FROM face_activation_intents WHERE technician_id=?1",
            [tech],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .map_err(|_| "NO_PENDING_ACTIVATION")?;
    if pending != generation {
        return Err("ACTIVATION_GENERATION_CHANGED".into());
    }
    let active: String = tx
        .query_row(
            "SELECT generation FROM face_enrollments WHERE technician_id=?1",
            [tech],
            |r| r.get(0),
        )
        .optional()
        .map_err(|e| e.to_string())?
        .unwrap_or_else(|| "none".into());
    if active != previous {
        return Err("ACTIVATION_PREVIOUS_GENERATION_CHANGED".into());
    }
    tx.execute("INSERT INTO face_enrollments(technician_id,updated_at,provider,format,generation) VALUES(?1,?2,'arcface','MULTI_POSE_V2',?3) ON CONFLICT(technician_id) DO UPDATE SET updated_at=excluded.updated_at,provider=excluded.provider,format=excluded.format,generation=excluded.generation",params![tech,Utc::now().to_rfc3339(),generation]).map_err(|e|e.to_string())?;
    tx.execute(
        "DELETE FROM face_activation_intents WHERE technician_id=?1",
        [tech],
    )
    .map_err(|e| e.to_string())?;
    db::audit(
        &tx,
        "FACE_ENROLLMENT_UPDATED",
        &json!({
            "technician_id": tech, "format": "MULTI_POSE_V2", "policy": POLICY
        }),
    )?;
    tx.commit().map_err(|e| e.to_string())?;
    s.grants.retain(|_, g| g.technician_id != tech);
    if s.technician.as_ref().is_some_and(|t| t.id == tech) {
        s.technician = None;
    }
    Ok(())
}

#[tauri::command]
pub async fn recover_face_enrollment(
    state: State<'_, AppState>,
    technician_id: String,
) -> Result<(), String> {
    let (config, generation, previous, epoch) = {
        let s = lock(&state)?;
        require_admin(&s)?;
        require_no_removal(&s.db, &technician_id)?;
        if !technician(&s, &technician_id)?.enabled {
            return Err("TECHNICIAN_DISABLED".into());
        }
        let (g,p):(String,String)=s.db.query_row("SELECT generation,previous_generation FROM face_activation_intents WHERE technician_id=?1",[&technician_id],|r|Ok((r.get(0)?,r.get(1)?))).map_err(|_|"NO_PENDING_ACTIVATION")?;
        (s.config.clone(), g, p, s.biometrics.authority_epoch.clone())
    };
    let id = technician_id.clone();
    let new_generation = generation.clone();
    let ack=tauri::async_runtime::spawn_blocking(move|| {
        let c=reqwest::blocking::Client::builder().timeout(Duration::from_secs(5)).build().map_err(|e|e.to_string())?;
        service(&c,&config,"/generation/activate",Some(&json!({"technician_id":id,"generation":new_generation,"previous_generation":previous})))
    }).await.map_err(|_|"RECOVERY_HELPER_FAILED")??;
    let mut s = lock(&state)?;
    require_admin(&s)?;
    require_no_removal(&s.db, &technician_id)?;
    if s.biometrics.authority_epoch != epoch || ack["generation"] != generation {
        return Err("RECOVERY_AUTHORITY_CHANGED".into());
    }
    commit_metadata(&mut s, &technician_id, &generation)?;
    s.biometrics.revoke("ENROLLMENT_RECOVERED");
    Ok(())
}

fn require_no_removal(db: &rusqlite::Connection, technician_id: &str) -> Result<(), String> {
    let pending: bool = db
        .query_row(
            "SELECT EXISTS(SELECT 1 FROM face_removal_intents WHERE technician_id=?1)",
            [technician_id],
            |r| r.get(0),
        )
        .map_err(|e| e.to_string())?;
    if pending {
        Err("ENROLLMENT_REMOVAL_RECOVERY_REQUIRED: retry Remove face or Discard pending enrollment as administrator".into())
    } else {
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq)]
struct RemovalIntent {
    removal_id: String,
    active_generation: String,
    pending_generation: Option<String>,
    pending_previous_generation: Option<String>,
}

fn removal_intent(db: &rusqlite::Connection, id: &str) -> Result<Option<RemovalIntent>, String> {
    db.query_row(
        "SELECT removal_id,active_generation,pending_generation,pending_previous_generation FROM face_removal_intents WHERE technician_id=?1",
        [id], |r| Ok(RemovalIntent {
            removal_id: r.get(0)?, active_generation: r.get(1)?,
            pending_generation: r.get(2)?, pending_previous_generation: r.get(3)?,
        }),
    ).optional().map_err(|e| e.to_string())
}

fn enrollment_snapshot(
    db: &rusqlite::Connection,
    id: &str,
    removal_id: String,
) -> Result<RemovalIntent, String> {
    let active_generation = db
        .query_row(
            "SELECT generation FROM face_enrollments WHERE technician_id=?1",
            [id],
            |r| r.get(0),
        )
        .optional()
        .map_err(|e| e.to_string())?
        .unwrap_or_else(|| "none".into());
    let pending: Option<(String, String)> = db.query_row(
        "SELECT generation,previous_generation FROM face_activation_intents WHERE technician_id=?1",
        [id], |r| Ok((r.get(0)?, r.get(1)?)),
    ).optional().map_err(|e| e.to_string())?;
    let (pending_generation, pending_previous_generation) =
        pending.map(|(g, p)| (Some(g), Some(p))).unwrap_or_default();
    Ok(RemovalIntent {
        removal_id,
        active_generation,
        pending_generation,
        pending_previous_generation,
    })
}

fn prepare_removal(s: &mut Inner, technician_id: &str) -> Result<RemovalIntent, String> {
    require_admin(s)?;
    technician(s, technician_id)?;
    let tx = s.db.transaction().map_err(|e| e.to_string())?;
    let intent = if let Some(intent) = removal_intent(&tx, technician_id)? {
        if enrollment_snapshot(&tx, technician_id, intent.removal_id.clone())? != intent {
            return Err("ENROLLMENT_REMOVAL_SNAPSHOT_CHANGED".into());
        }
        intent
    } else {
        let intent = enrollment_snapshot(&tx, technician_id, uuid::Uuid::new_v4().to_string())?;
        tx.execute(
            "INSERT INTO face_removal_intents VALUES(?1,?2,?3,?4,?5,?6)",
            params![
                technician_id,
                intent.removal_id,
                intent.active_generation,
                intent.pending_generation,
                intent.pending_previous_generation,
                Utc::now().to_rfc3339()
            ],
        )
        .map_err(|e| e.to_string())?;
        db::audit(
            &tx,
            "FACE_ENROLLMENT_REMOVAL_STARTED",
            &json!({"technician_id":technician_id,"removal_id":intent.removal_id}),
        )?;
        intent
    };
    tx.commit().map_err(|e| e.to_string())?;
    s.biometrics.revoke("ENROLLMENT_REMOVAL_STARTED");
    s.grants.retain(|_, g| g.technician_id != technician_id);
    if s.technician.as_ref().is_some_and(|t| t.id == technician_id) {
        s.technician = None;
    }
    Ok(intent)
}

fn commit_removal(
    s: &mut Inner,
    technician_id: &str,
    intent: &RemovalIntent,
) -> Result<(), String> {
    let tx = s.db.transaction().map_err(|e| e.to_string())?;
    if removal_intent(&tx, technician_id)?.as_ref() != Some(intent)
        || enrollment_snapshot(&tx, technician_id, intent.removal_id.clone())? != *intent
    {
        return Err("ENROLLMENT_REMOVAL_SNAPSHOT_CHANGED".into());
    }
    for table in [
        "face_enrollments",
        "face_activation_intents",
        "face_removal_intents",
    ] {
        tx.execute(
            &format!("DELETE FROM {table} WHERE technician_id=?1"),
            [technician_id],
        )
        .map_err(|e| e.to_string())?;
    }
    db::audit(
        &tx,
        "FACE_ENROLLMENT_REMOVED",
        &json!({"technician_id":technician_id,"removal_id":intent.removal_id}),
    )?;
    tx.commit().map_err(|e| e.to_string())?;
    s.biometrics.revoke("TECHNICIAN_OR_ENROLLMENT_CHANGED");
    s.grants.retain(|_, g| g.technician_id != technician_id);
    if s.technician.as_ref().is_some_and(|t| t.id == technician_id) {
        s.technician = None;
    }
    Ok(())
}

pub(crate) async fn remove_face_enrollment(
    state: State<'_, AppState>,
    technician_id: String,
) -> Result<(), String> {
    let (config, intent, epoch) = {
        let mut s = lock(&state)?;
        let intent = prepare_removal(&mut s, &technician_id)?;
        (
            s.config.clone(),
            intent,
            s.biometrics.authority_epoch.clone(),
        )
    };
    let mut expected_generations = vec![intent.active_generation.clone()];
    if let Some(pending) = &intent.pending_generation {
        if !expected_generations.contains(pending) {
            expected_generations.push(pending.clone());
        }
    }
    let payload = json!({"technician_id":technician_id,"removal_id":intent.removal_id,"expected_generations":expected_generations});
    let ack = tauri::async_runtime::spawn_blocking(move || {
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(5))
            .redirect(reqwest::redirect::Policy::none())
            .build()
            .map_err(|e| e.to_string())?;
        service(&client, &config, "/generation/remove", Some(&payload))
    })
    .await
    .map_err(|_| "REMOVAL_HELPER_FAILED")?
    .map_err(|_| {
        "ENROLLMENT_REMOVAL_RECOVERY_REQUIRED: retry Remove face or Discard pending enrollment as administrator"
    })?;
    let mut s = lock(&state)?;
    require_admin(&s)?;
    if s.biometrics.authority_epoch != epoch
        || ack["status"] != "REMOVED"
        || ack["technician_id"] != technician_id
        || ack["removal_id"] != intent.removal_id
    {
        return Err(
            "ENROLLMENT_REMOVAL_RECOVERY_REQUIRED: authority or acknowledgment changed".into(),
        );
    }
    commit_removal(&mut s, &technician_id, &intent)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::commands_tests::{app, fixture, reassessment};

    fn passed_controls() -> BTreeMap<String, Control> {
        // This only exercises native authority; it never qualifies a model.
        REQUIRED
            .into_iter()
            .map(|name| {
                (
                    name.into(),
                    Control {
                        result: Outcome::Pass,
                        model: "test".into(),
                        reason: "TEST_ONLY".into(),
                        score: None,
                    },
                )
            })
            .collect()
    }

    fn read_http_request(socket: &mut std::net::TcpStream) -> String {
        socket
            .set_read_timeout(Some(Duration::from_secs(5)))
            .unwrap();
        let mut request = Vec::new();
        loop {
            let mut byte = [0];
            assert_eq!(socket.read(&mut byte).unwrap(), 1);
            request.push(byte[0]);
            if request.ends_with(b"\r\n\r\n") {
                break;
            }
        }
        let headers = String::from_utf8(request.clone()).unwrap();
        let length: usize = headers
            .lines()
            .find_map(|line| {
                let (name, value) = line.split_once(':')?;
                name.eq_ignore_ascii_case("content-length")
                    .then(|| value.trim().parse().unwrap())
            })
            .unwrap_or(0);
        let mut body = vec![0; length];
        socket.read_exact(&mut body).unwrap();
        request.extend(body);
        String::from_utf8(request).unwrap()
    }

    fn http_json(socket: &mut std::net::TcpStream, body: &Value) {
        use std::io::Write;
        let body = body.to_string();
        write!(socket, "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}", body.len(), body).unwrap();
    }

    fn setup() -> (
        tauri::App<tauri::test::MockRuntime>,
        tempfile::TempDir,
        String,
    ) {
        let (app, dir) = app();
        let state = app.state::<AppState>();
        admin_login(
            state.clone(),
            "test-admin".into(),
            "test-only-password".into(),
        )
        .unwrap();
        save_technician(
            state.clone(),
            crate::security::Technician {
                technician_id: "T1".into(),
                username: "tech".into(),
                display_name: "Test".into(),
                role: "Technician".into(),
                enabled: true,
                enrolled: false,
                enrollment_version: None,
            },
        )
        .unwrap();
        cache_decision(state.clone(), fixture()).unwrap();
        let id = {
            let mut s = lock(&state).unwrap();
            s.db.execute(
                "INSERT INTO face_enrollments VALUES('T1','test','arcface','MULTI_POSE_V2','g1')",
                [],
            )
            .unwrap();
            s.technician = Some(Session {
                id: "T1".into(),
                expires_at: Utc::now().timestamp() + 60,
            });
            s.biometrics
                .begin(Purpose::Approval, "T1".into(), "g1".into(), Some(fixture()))
                .unwrap()
                .session_id
        };
        (app, dir, id)
    }
    #[test]
    fn reassessment_while_scanning_invalidates_exact_scope() {
        let (app, _dir, id) = setup();
        let state = app.state::<AppState>();
        assert!(current(&mut lock(&state).unwrap(), &id).is_ok());
        cache_decision(state.clone(), reassessment()).unwrap();
        assert!(current(&mut lock(&state).unwrap(), &id).is_err());
    }
    #[test]
    fn changed_request_hard_deny_and_generation_cannot_complete_old_evidence() {
        for change in ["request", "deny", "generation"] {
            let (app, _dir, id) = setup();
            let state = app.state::<AppState>();
            let mut s = lock(&state).unwrap();
            if change == "generation" {
                s.db.execute("UPDATE face_enrollments SET generation='g2'", [])
                    .unwrap();
            } else {
                let mut d = fixture();
                if change == "deny" {
                    d["policy"]["result"] = json!("DENY");
                } else {
                    d["request"]["target"] = json!("changed target");
                }
                s.db.execute("UPDATE decision_cache SET payload=?1", [d.to_string()])
                    .unwrap();
            }
            assert!(current(&mut s, &id).is_err());
            assert!(s.grants.is_empty());
        }
    }
    #[test]
    fn disabled_account_immediately_revokes_scan() {
        let (app, _dir, id) = setup();
        let state = app.state::<AppState>();
        set_technician_enabled(state.clone(), "T1".into(), false).unwrap();
        assert!(current(&mut lock(&state).unwrap(), &id).is_err());
    }

    #[test]
    fn watchdog_releases_capture_without_renderer_or_inference_polling() {
        for expired in ["deadline", "lease", "technician_session"] {
            let (app, _dir, id) = setup();
            let state = app.state::<AppState>();
            let child = std::process::Command::new("/bin/sleep")
                .arg("30")
                .spawn()
                .unwrap();
            let handle = std::sync::Arc::new(std::sync::Mutex::new(child));
            {
                let mut s = lock(&state).unwrap();
                let a = s.biometrics.get(&id).unwrap();
                a.camera = Some(handle.clone());
                a.view.preview = Some("test-only-preview".into());
                match expired {
                    "deadline" => a.deadline = Instant::now(),
                    "lease" => a.last_poll = Instant::now() - Duration::from_secs(4),
                    _ => s.technician.as_mut().unwrap().expires_at = 0,
                }
            }
            let started = Instant::now();
            let (_stop, stopped) = std::sync::mpsc::channel();
            watch_session(&state, &id, stopped);
            assert!(!handle.lock().unwrap().wait().unwrap().success());
            assert!(started.elapsed() < Duration::from_secs(1));
            let mut s = lock(&state).unwrap();
            let a = s.biometrics.get(&id).unwrap();
            assert!(a.terminal());
            assert!(a.view.preview.is_none());
            assert!(s.grants.is_empty());
        }
    }

    #[test]
    fn stale_watchdog_cannot_cancel_a_replacement_session() {
        let (app, _dir, old_id) = setup();
        let state = app.state::<AppState>();
        let next = {
            let mut s = lock(&state).unwrap();
            s.biometrics
                .get(&old_id)
                .unwrap()
                .finish("CANCELLED", "TEST");
            s.biometrics
                .begin(Purpose::Login, "T1".into(), "g1".into(), None)
                .unwrap()
                .session_id
        };
        let (_stop, stopped) = std::sync::mpsc::channel();
        watch_session(&state, &old_id, stopped);
        assert!(!lock(&state)
            .unwrap()
            .biometrics
            .get(&next)
            .unwrap()
            .terminal());
    }
    #[test]
    fn pending_activation_blocks_both_stores_until_recovery() {
        let (app, _dir, _id) = setup();
        let state = app.state::<AppState>();
        let s = lock(&state).unwrap();
        s.db.execute(
            "INSERT INTO face_activation_intents VALUES('T1','g2','g1','test')",
            [],
        )
        .unwrap();
        assert!(generation(&s, "T1").is_err());
        assert_eq!(
            s.db.query_row(
                "SELECT generation FROM face_enrollments WHERE technician_id='T1'",
                [],
                |r| r.get::<_, String>(0)
            )
            .unwrap(),
            "g1"
        );
    }

    #[test]
    fn enrollment_polling_during_activation_preserves_only_its_own_intent() {
        for change in [
            "poll",
            "admin_logout",
            "admin_expiry",
            "disable",
            "other_intent",
            "previous_generation",
        ] {
            let (app, _dir, old_id) = setup();
            let state = app.state::<AppState>();
            let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
            let (id, config) = {
                let mut s = lock(&state).unwrap();
                s.biometrics
                    .get(&old_id)
                    .unwrap()
                    .finish("CANCELLED", "TEST");
                s.config.biometric_url = format!("http://{}", listener.local_addr().unwrap());
                s.config.biometric_token = "test-only-bearer-token-32-characters".into();
                let id = s
                    .biometrics
                    .begin(Purpose::Enrollment, "T1".into(), "g1".into(), None)
                    .unwrap()
                    .session_id;
                let a = s.biometrics.get(&id).unwrap();
                a.view.state = "EVALUATING".into();
                a.view.controls = passed_controls();
                (id, s.config.clone())
            };
            let handle = app.handle().clone();
            let requested = id.clone();
            let server = std::thread::spawn(move || {
                let (mut socket, _) = listener.accept().unwrap();
                assert!(read_http_request(&mut socket).starts_with("POST /generation/activate "));
                let state = handle.state::<AppState>();
                match change {
                    "admin_logout" => admin_logout(state.clone()).unwrap(),
                    "disable" => set_technician_enabled(state.clone(), "T1".into(), false).unwrap(),
                    "admin_expiry" => lock(&state).unwrap().admin.as_mut().unwrap().expires_at = 0,
                    "other_intent" => {
                        lock(&state)
                            .unwrap()
                            .db
                            .execute("UPDATE face_activation_intents SET generation='other'", [])
                            .unwrap();
                    }
                    "previous_generation" => {
                        lock(&state)
                            .unwrap()
                            .db
                            .execute("UPDATE face_enrollments SET generation='changed'", [])
                            .unwrap();
                    }
                    _ => {}
                }
                let view = read_biometric_session(state, requested.clone()).unwrap();
                assert_eq!(
                    view.state,
                    if change == "poll" {
                        "EVALUATING"
                    } else {
                        "CANCELLED"
                    }
                );
                http_json(&mut socket, &json!({"generation":requested}));
            });
            let outcome = complete(&state, &id, &reqwest::blocking::Client::new(), &config);
            server.join().unwrap();
            assert_eq!(outcome.is_ok(), change == "poll", "{change}: {outcome:?}");
            let mut s = lock(&state).unwrap();
            assert!(s.grants.is_empty());
            if change == "poll" {
                assert_eq!(generation(&s, "T1").unwrap(), id);
                assert_eq!(s.biometrics.get(&id).unwrap().view.state, "SUCCEEDED");
            } else {
                assert!(generation(&s, "T1").is_err());
                assert_ne!(active_generation(&s, "T1").unwrap(), id);
            }
        }
    }

    #[test]
    fn opened_service_session_is_cancelled_on_early_failures_and_lost_ack() {
        for failure in ["camera_start", "begin_ack", "service_restart"] {
            let (app, _dir, id) = setup();
            let state = app.state::<AppState>();
            let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
            let mut config = lock(&state).unwrap().config.clone();
            config.biometric_url = format!("http://{}", listener.local_addr().unwrap());
            config.biometric_token = "test-only-bearer-token-32-characters".into();
            let payload = json!({"session_id":id,"nonce":"nonce"});
            let ready = json!({"service_epoch":"original"});
            let expected_binding =
                json!({"session_id":id,"nonce":"nonce","service_epoch":"original"});
            let server = std::thread::spawn(move || {
                let (mut socket, _) = listener.accept().unwrap();
                assert!(read_http_request(&mut socket).starts_with("POST /live/begin "));
                if failure != "begin_ack" {
                    http_json(
                        &mut socket,
                        &json!({"session_id":id,"service_epoch": if failure == "service_restart" {"new"} else {"original"}}),
                    );
                }
                drop(socket);
                let (mut socket, _) = listener.accept().unwrap();
                let request = read_http_request(&mut socket);
                assert!(request.starts_with("POST /live/cancel "));
                let (_, body) = request.split_once("\r\n\r\n").unwrap();
                assert_eq!(
                    serde_json::from_str::<Value>(body).unwrap(),
                    expected_binding
                );
                http_json(&mut socket, &json!({"cancelled":true}));
            });
            let result = with_service_session(
                &reqwest::blocking::Client::new(),
                &config,
                &payload,
                &ready,
                || {
                    assert_eq!(failure, "camera_start");
                    Err("NATIVE_CAMERA_START_FAILED".into())
                },
            );
            assert!(result.is_err());
            server.join().unwrap();
        }
    }
    #[test]
    fn activation_metadata_rolls_back_and_rejects_stale_recovery() {
        let (app, _dir, _) = setup();
        let state = app.state::<AppState>();
        let mut s = lock(&state).unwrap();
        s.db.execute(
            "INSERT INTO face_activation_intents VALUES('T1','g2','g1','test')",
            [],
        )
        .unwrap();
        assert!(commit_metadata(&mut s, "T1", "stale").is_err());
        s.db.execute("UPDATE face_enrollments SET generation='changed'", [])
            .unwrap();
        assert_eq!(
            commit_metadata(&mut s, "T1", "g2").unwrap_err(),
            "ACTIVATION_PREVIOUS_GENERATION_CHANGED"
        );
        s.db.execute("UPDATE face_enrollments SET generation='g1'", [])
            .unwrap();
        s.db.execute_batch("CREATE TRIGGER reject_activation BEFORE UPDATE ON face_enrollments BEGIN SELECT RAISE(ABORT,'test failure'); END;").unwrap();
        assert!(commit_metadata(&mut s, "T1", "g2").is_err());
        assert!(generation(&s, "T1").is_err());
        let old: String =
            s.db.query_row(
                "SELECT generation FROM face_enrollments WHERE technician_id='T1'",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(old, "g1");
        s.db.execute_batch("DROP TRIGGER reject_activation")
            .unwrap();
        commit_metadata(&mut s, "T1", "g2").unwrap();
        assert_eq!(generation(&s, "T1").unwrap(), "g2");
        assert!(s.technician.is_none());
        assert!(commit_metadata(&mut s, "T1", "g2").is_err());
    }
    #[test]
    fn recovery_retries_after_lost_http_acknowledgment() {
        use std::io::{Read, Write};
        let (app, _dir, _) = setup();
        let state = app.state::<AppState>();
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        {
            let mut s = lock(&state).unwrap();
            s.config.biometric_url = format!("http://{}", listener.local_addr().unwrap());
            s.config.biometric_token = "test-only-bearer-token-32-characters".into();
            s.db.execute(
                "INSERT INTO face_activation_intents VALUES('T1','g2','g1','test')",
                [],
            )
            .unwrap();
        }
        let server = std::thread::spawn(move || {
            for send_ack in [false, true] {
                let (mut socket, _) = listener.accept().unwrap();
                socket
                    .set_read_timeout(Some(Duration::from_secs(5)))
                    .unwrap();
                let mut request = Vec::new();
                loop {
                    let mut chunk = [0; 2048];
                    let count = socket.read(&mut chunk).unwrap();
                    assert!(count > 0);
                    request.extend_from_slice(&chunk[..count]);
                    if request.windows(4).any(|w| w == b"\r\n\r\n") {
                        break;
                    }
                }
                assert!(String::from_utf8_lossy(&request).starts_with("POST /generation/activate "));
                if send_ack {
                    let body = r#"{"generation":"g2"}"#;
                    write!(socket, "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}", body.len(), body).unwrap();
                }
            }
        });
        assert!(tauri::async_runtime::block_on(recover_face_enrollment(
            state.clone(),
            "T1".into()
        ))
        .is_err());
        assert!(generation(&lock(&state).unwrap(), "T1").is_err());
        tauri::async_runtime::block_on(recover_face_enrollment(state.clone(), "T1".into()))
            .unwrap();
        server.join().unwrap();
        assert_eq!(generation(&lock(&state).unwrap(), "T1").unwrap(), "g2");
    }

    #[test]
    fn removal_preserves_pending_activation_on_lost_ack_and_retries_after_restart() {
        let (app, _dir, old_id) = setup();
        let state = app.state::<AppState>();
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        {
            let mut s = lock(&state).unwrap();
            s.config.biometric_url = format!("http://{}", listener.local_addr().unwrap());
            s.config.biometric_token = "test-only-bearer-token-32-characters".into();
            s.db.execute(
                "INSERT INTO face_activation_intents VALUES('T1','g2','g1','test')",
                [],
            )
            .unwrap();
        }
        let server = std::thread::spawn(move || {
            let mut original = None;
            for send_ack in [false, true] {
                let (mut socket, _) = listener.accept().unwrap();
                let request = read_http_request(&mut socket);
                assert!(request.starts_with("POST /generation/remove "));
                let payload: Value =
                    serde_json::from_str(request.split_once("\r\n\r\n").unwrap().1).unwrap();
                assert_eq!(payload["technician_id"], "T1");
                assert_eq!(payload["expected_generations"], json!(["g1", "g2"]));
                assert!(uuid::Uuid::parse_str(payload["removal_id"].as_str().unwrap()).is_ok());
                if let Some(prior) = &original {
                    assert_eq!(&payload, prior);
                }
                original = Some(payload.clone());
                if send_ack {
                    http_json(
                        &mut socket,
                        &json!({"status":"REMOVED","technician_id":"T1","removal_id":payload["removal_id"]}),
                    );
                }
            }
        });
        assert!(
            tauri::async_runtime::block_on(remove_enrollment(state.clone(), "T1".into())).is_err()
        );
        {
            let mut s = lock(&state).unwrap();
            assert!(s.biometrics.get(&old_id).unwrap().terminal());
            assert!(s.grants.is_empty());
            assert!(s.technician.is_none());
            assert_eq!(active_generation(&s, "T1").unwrap(), "g1");
            assert!(generation(&s, "T1").is_err());
            assert!(commit_metadata(&mut s, "T1", "g2").is_err());
            let blocked = s
                .biometrics
                .begin(Purpose::Enrollment, "T1".into(), "g1".into(), None)
                .unwrap()
                .session_id;
            assert!(current(&mut s, &blocked).is_err());
            let original = removal_intent(&s.db, "T1").unwrap().unwrap();
            // Reopening SQLite and discarding ephemeral authority simulates the
            // persistent boundary; no request or private enrollment is reset.
            s.db = db::open(&s.config).unwrap();
            s.admin = None;
            s.biometrics = Book::default();
            assert_eq!(removal_intent(&s.db, "T1").unwrap(), Some(original));
        }
        assert!(tauri::async_runtime::block_on(recover_face_enrollment(
            state.clone(),
            "T1".into()
        ))
        .is_err());
        admin_login(
            state.clone(),
            "test-admin".into(),
            "test-only-password".into(),
        )
        .unwrap();
        assert!(tauri::async_runtime::block_on(recover_face_enrollment(
            state.clone(),
            "T1".into()
        ))
        .unwrap_err()
        .starts_with("ENROLLMENT_REMOVAL_RECOVERY_REQUIRED"));
        tauri::async_runtime::block_on(remove_enrollment(state.clone(), "T1".into())).unwrap();
        server.join().unwrap();
        let s = lock(&state).unwrap();
        assert_eq!(generation(&s, "T1").unwrap(), "none");
        assert!(removal_intent(&s.db, "T1").unwrap().is_none());
        assert!(!technician(&s, "T1").unwrap().enrolled);
        assert!(s.grants.is_empty());
    }

    #[test]
    fn removal_ack_rechecks_admin_token_and_enrollment_snapshot() {
        for change in [
            "admin_logout",
            "admin_expiry",
            "wrong_ack",
            "new_generation",
            "new_intent",
        ] {
            let (app, _dir, _) = setup();
            let state = app.state::<AppState>();
            let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
            {
                let mut s = lock(&state).unwrap();
                s.config.biometric_url = format!("http://{}", listener.local_addr().unwrap());
                s.config.biometric_token = "test-only-bearer-token-32-characters".into();
            }
            let handle = app.handle().clone();
            let server = std::thread::spawn(move || {
                let (mut socket, _) = listener.accept().unwrap();
                let request = read_http_request(&mut socket);
                let payload: Value =
                    serde_json::from_str(request.split_once("\r\n\r\n").unwrap().1).unwrap();
                let state = handle.state::<AppState>();
                match change {
                    "admin_logout" => admin_logout(state.clone()).unwrap(),
                    "admin_expiry" => lock(&state).unwrap().admin.as_mut().unwrap().expires_at = 0,
                    "new_generation" => {
                        lock(&state)
                            .unwrap()
                            .db
                            .execute("UPDATE face_enrollments SET generation='new'", [])
                            .unwrap();
                    }
                    "new_intent" => {
                        lock(&state)
                            .unwrap()
                            .db
                            .execute("UPDATE face_removal_intents SET removal_id='new-token'", [])
                            .unwrap();
                    }
                    _ => {}
                }
                let token = if change == "wrong_ack" {
                    json!("wrong-token")
                } else {
                    payload["removal_id"].clone()
                };
                http_json(
                    &mut socket,
                    &json!({"status":"REMOVED","technician_id":"T1","removal_id":token}),
                );
            });
            assert!(
                tauri::async_runtime::block_on(remove_enrollment(state.clone(), "T1".into()))
                    .is_err(),
                "{change}"
            );
            server.join().unwrap();
            let s = lock(&state).unwrap();
            assert!(removal_intent(&s.db, "T1").unwrap().is_some());
            assert!(generation(&s, "T1").is_err());
            assert!(technician(&s, "T1").unwrap().enrolled);
            assert_eq!(s.db.query_row("SELECT COUNT(*) FROM local_audit_events WHERE event_type='FACE_ENROLLMENT_REMOVED'", [], |r| r.get::<_, u32>(0)).unwrap(), 0);
        }
    }

    #[test]
    fn removal_metadata_and_audit_rollback_together() {
        let (app, _dir, _) = setup();
        let state = app.state::<AppState>();
        let mut s = lock(&state).unwrap();
        s.db.execute(
            "INSERT INTO face_activation_intents VALUES('T1','g2','g1','test')",
            [],
        )
        .unwrap();
        let intent = prepare_removal(&mut s, "T1").unwrap();
        assert_eq!(prepare_removal(&mut s, "T1").unwrap(), intent);
        s.db.execute_batch("CREATE TRIGGER reject_removal_audit BEFORE INSERT ON local_audit_events WHEN NEW.event_type='FACE_ENROLLMENT_REMOVED' BEGIN SELECT RAISE(ABORT,'test audit failure'); END;").unwrap();
        assert!(commit_removal(&mut s, "T1", &intent).is_err());
        assert_eq!(active_generation(&s, "T1").unwrap(), "g1");
        assert_eq!(removal_intent(&s.db, "T1").unwrap().as_ref(), Some(&intent));
        assert_eq!(
            enrollment_snapshot(&s.db, "T1", intent.removal_id.clone()).unwrap(),
            intent
        );
        s.db.execute_batch("DROP TRIGGER reject_removal_audit")
            .unwrap();
        commit_removal(&mut s, "T1", &intent).unwrap();
        assert_eq!(generation(&s, "T1").unwrap(), "none");
        assert!(removal_intent(&s.db, "T1").unwrap().is_none());
        assert!(s.grants.is_empty());
    }
    #[test]
    fn completion_preserves_login_and_approval_throttling() {
        let (app, _dir, old_id) = setup();
        let state = app.state::<AppState>();
        let (id, config) = {
            let mut s = lock(&state).unwrap();
            s.biometrics
                .get(&old_id)
                .unwrap()
                .finish("CANCELLED", "TEST");
            failed(&mut s, "login:tech");
            let id = s
                .biometrics
                .begin(Purpose::Login, "T1".into(), "g1".into(), None)
                .unwrap()
                .session_id;
            let a = s.biometrics.get(&id).unwrap();
            // Test-only evidence setup exercises completion, never camera/model qualification.
            for name in ["identity", "quality", "capture_integrity", "pose", "pad"] {
                a.view.controls.insert(
                    name.into(),
                    Control {
                        result: Outcome::Pass,
                        model: "test".into(),
                        reason: "TEST_ONLY".into(),
                        score: None,
                    },
                );
            }
            (id, s.config.clone())
        };
        complete(&state, &id, &reqwest::blocking::Client::new(), &config).unwrap();
        let mut s = lock(&state).unwrap();
        assert!(!s.failures.contains_key("login:tech"));
        assert!(s.grants.is_empty());
        assert_eq!(require_technician(&s).unwrap(), "T1");
        assert_eq!(s.biometrics.get(&id).unwrap().view.state, "SUCCEEDED");
        let controls = s.biometrics.get(&id).unwrap().view.controls.clone();
        let approval = s
            .biometrics
            .begin(Purpose::Approval, "T1".into(), "g1".into(), Some(fixture()))
            .unwrap()
            .session_id;
        s.biometrics.get(&approval).unwrap().view.controls = controls;
        failed(&mut s, "T1");
        drop(s);
        complete(
            &state,
            &approval,
            &reqwest::blocking::Client::new(),
            &config,
        )
        .unwrap();
        let s = lock(&state).unwrap();
        assert!(!s.failures.contains_key("T1"));
        assert_eq!(s.grants.len(), 1);
    }
    #[test]
    fn cancellation_kills_the_owned_capture_process() {
        let mut b = Book::default();
        let view = b
            .begin(Purpose::Enrollment, "T1".into(), "none".into(), None)
            .unwrap();
        let child = std::process::Command::new("/bin/sleep")
            .arg("30")
            .spawn()
            .unwrap();
        let handle = std::sync::Arc::new(std::sync::Mutex::new(child));
        b.get(&view.session_id).unwrap().camera = Some(handle.clone());
        b.revoke("NAVIGATION");
        assert!(!handle.lock().unwrap().wait().unwrap().success());
    }
    #[test]
    fn metadata_migration_preserves_legacy_and_recovers_partial_columns() {
        let (_app, dir) = app();
        let mut config = crate::config::Config::load(dir.path().to_owned()).unwrap();
        config.database = dir.path().join("legacy.sqlite3");
        {
            let c = rusqlite::Connection::open(&config.database).unwrap();
            c.execute_batch("CREATE TABLE face_enrollments(technician_id TEXT PRIMARY KEY,updated_at TEXT,provider TEXT,format TEXT DEFAULT 'IDENTITY_ONLY_V1');INSERT INTO face_enrollments VALUES('T1','old-date','arcface','IDENTITY_ONLY_V1');").unwrap();
        }
        let c = db::open(&config).unwrap();
        assert_eq!(
            c.query_row(
                "SELECT updated_at,format,generation FROM face_enrollments",
                [],
                |r| Ok((
                    r.get::<_, String>(0)?,
                    r.get::<_, String>(1)?,
                    r.get::<_, String>(2)?
                ))
            )
            .unwrap(),
            (
                "old-date".into(),
                "IDENTITY_ONLY_V1".into(),
                "legacy-v1".into()
            )
        );
    }
}
