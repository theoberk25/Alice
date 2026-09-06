use super::*;
use crate::{
    biometric_sessions::{Control, Outcome, Purpose, REQUIRED},
    security::Session,
};
use ring::signature::{KeyPair, UnparsedPublicKey, ED25519};
use tauri::Manager;

fn key() -> Ed25519KeyPair {
    let pkcs8 = Ed25519KeyPair::generate_pkcs8(&ring::rand::SystemRandom::new()).unwrap();
    Ed25519KeyPair::from_pkcs8(pkcs8.as_ref()).unwrap()
}
fn snapshot() -> Snapshot {
    let request = json!({"schema_version":"1.0","request_id":"REQ-1","agent_id":"AGENT-1","action":"set_light_state","target":"ESP-LIGHT-01","parameters":{"state":"on"},"issued_at":"2026-09-06T00:00:00Z"});
    Snapshot {
        schema_version: "alice-runtime-review-v1".into(),
        request_id: "REQ-1".into(),
        request_sha256: digest(&canonical(&request).unwrap()),
        decision_event_id: "REQ-1.decision".into(),
        decision_event_hash: "a".repeat(64),
        release_sha256: "b".repeat(64),
        authority_interval_ref: Some("AUTH-1".into()),
        runtime_epoch: "EPOCH-1".into(),
        review_nonce: "NONCE-1".into(),
        request: Some(request),
        decision: "CHALLENGE".into(),
        decision_reason_codes: Some(vec!["PERMISSION_REVIEW_REQUIRED".into()]),
        assessment: None,
        review_state: "PENDING".into(),
        eligible: true,
        reason: "READY".into(),
        execution_status: "NOT_EXECUTED".into(),
        accepted_action_id: None,
        accepted_action: None,
    }
}
fn authorize(s: &mut Inner, intent: &str) -> String {
    s.config.mode = "remote".into();
    s.config.biometric_mode = "arcface".into();
    s.db.execute(
        "INSERT INTO technicians VALUES('TECH-1','tech','Technician','technician',1)",
        [],
    )
    .unwrap();
    s.db.execute("INSERT INTO face_enrollments(technician_id,updated_at,provider,format,generation) VALUES('TECH-1','2026-09-06','arcface','MULTI_POSE_V2','generation-1')",[]).unwrap();
    s.technician = Some(Session {
        id: "TECH-1".into(),
        expires_at: Utc::now().timestamp() + 3600,
    });
    s.runtime_review.snapshot = Some(Cache {
        view: snapshot(),
        fetched: Instant::now(),
        technician: "TECH-1".into(),
        epoch: s.biometrics.authority_epoch.clone(),
    });
    s.runtime_review.signer = Some(Signer {
        console: "CONSOLE-1".into(),
        key: key(),
    });
    let scope = scope(s, "REQ-1", "REQ-1.decision", intent).unwrap();
    s.biometrics
        .begin(
            Purpose::Approval,
            "TECH-1".into(),
            "generation-1".into(),
            Some(scope.clone()),
        )
        .unwrap();
    let grant = grant(s, &scope).unwrap();
    let id = grant.verification_id.clone();
    let a = s.biometrics.current.as_mut().unwrap();
    a.view.verification = Some(grant);
    a.view.state = "SUCCEEDED".into();
    a.view.controls = REQUIRED
        .into_iter()
        .map(|name| {
            (
                name.into(),
                Control {
                    result: Outcome::Pass,
                    model: "test-observation".into(),
                    reason: "test-only".into(),
                    score: Some(0.9),
                },
            )
        })
        .collect();
    id
}
#[test]
fn bounded_json_rejects_ambiguous_numbers_duplicates_and_limits() {
    for raw in [
        r#"{"a":1,"a":2}"#,
        r#"{"x":{"a":1,"a":2}}"#,
        r#"{"a":1.0}"#,
        r#"{"a":1e1}"#,
        r#"{"a":9223372036854775808}"#,
        r#"{"a":"\ud800"}"#,
        r#"{"é":1}"#,
        r#"{"":1}"#,
    ] {
        assert!(parse(raw.as_bytes()).is_err(), "{raw}");
    }
    assert!(parse(&vec![b' '; MAX_BYTES + 1]).is_err());
    assert!(parse(format!("{}0{}", "[".repeat(17), "]".repeat(17)).as_bytes()).is_err());
    assert!(parse(serde_json::to_string(&vec![0; 65]).unwrap().as_bytes()).is_err());
    assert!(parse(format!("{{\"a\":\"{}\"}}", "x".repeat(4097)).as_bytes()).is_err());
    assert_eq!(
        canonical(&parse(br#"{ "z": -9223372036854775808, "a": 9223372036854775807 }"#).unwrap())
            .unwrap(),
        br#"{"a":9223372036854775807,"z":-9223372036854775808}"#
    );
}
#[test]
fn request_hash_schema_and_resolved_bindings_are_always_checked() {
    let mut v = snapshot();
    v.validate("REQ-1").unwrap();
    v.eligible = false;
    v.request.as_mut().unwrap()["parameters"]["state"] = json!("off");
    assert!(v.validate("REQ-1").is_err());
    v = snapshot();
    v.request.as_mut().unwrap()["parameters"]["voltage"] = json!(12);
    v.request_sha256 = digest(&canonical(v.request.as_ref().unwrap()).unwrap());
    assert!(v.validate("REQ-1").is_err());
    v = snapshot();
    v.authority_interval_ref = None;
    assert!(v.validate("REQ-1").is_err());
    v.eligible = false;
    v.validate("REQ-1").unwrap();
    v.review_state = "APPROVED".into();
    assert!(v.validate("REQ-1").is_err());
    v.accepted_action_id = Some("ACT-1".into());
    v.accepted_action = Some("APPROVE_ONCE".into());
    v.validate("REQ-1").unwrap();
}
#[test]
fn consumption_is_one_use_and_keeps_valid_success_evidence_and_original_expiry() {
    let (app, _dir) = crate::commands_tests::app();
    let state = app.state::<AppState>();
    let mut s = lock(&state).unwrap();
    let id = authorize(&mut s, "APPROVE_ONCE");
    let original = Utc::now() - chrono::Duration::seconds(35);
    let a = s.biometrics.current.as_mut().unwrap();
    let g = a.view.verification.as_mut().unwrap();
    g.timestamp = original.to_rfc3339();
    g.expires_at = (original + chrono::Duration::seconds(60)).to_rfc3339();
    let (envelope, submission) = consume(&mut s, &id).unwrap();
    assert_eq!(envelope["proof"]["issued_at"], original.timestamp());
    assert_eq!(envelope["proof"]["expires_at"], original.timestamp() + 60);
    let attempt = s.biometrics.current.as_ref().unwrap();
    assert!(attempt.authority_consumed);
    assert_eq!(attempt.view.state, "SUCCEEDED");
    assert!(attempt.view.verification.is_some());
    assert_eq!(
        read_submission(&s, "REQ-1").unwrap().unwrap().action_id,
        submission.action_id
    );
    assert!(consume(&mut s, &id).is_err());
    assert!(scope(&s, "REQ-1", "REQ-1.decision", "REJECT").is_err());
}
#[test]
fn cancelled_after_success_cannot_sign_and_terminal_view_is_valid() {
    let (app, _dir) = crate::commands_tests::app();
    let state = app.state::<AppState>();
    let (id, session_id) = {
        let mut s = lock(&state).unwrap();
        let id = authorize(&mut s, "REJECT");
        let local = s
            .biometrics
            .current
            .as_ref()
            .unwrap()
            .view
            .verification
            .clone()
            .unwrap();
        s.grants.insert(id.clone(), local);
        (
            id,
            s.biometrics
                .current
                .as_ref()
                .unwrap()
                .view
                .session_id
                .clone(),
        )
    };
    crate::biometric_commands::cancel_biometric_session(state.clone(), session_id).unwrap();
    let mut s = lock(&state).unwrap();
    assert!(consume(&mut s, &id).is_err());
    assert!(!s.grants.contains_key(&id));
    let a = s.biometrics.current.as_ref().unwrap();
    assert!(a.authority_revoked);
    assert_eq!(a.view.state, "CANCELLED");
    assert!(a.view.verification.is_none());
    assert!(read_submission(&s, "REQ-1").unwrap().is_none());
}
#[test]
fn changed_snapshot_expired_cache_and_intent_cannot_sign() {
    for kind in [
        "snapshot",
        "lease",
        "intent",
        "epoch",
        "grant-expired",
        "grant-binding",
        "control",
    ] {
        let (app, _dir) = crate::commands_tests::app();
        let state = app.state::<AppState>();
        let mut s = lock(&state).unwrap();
        let id = authorize(&mut s, "APPROVE_ONCE");
        match kind {
            "snapshot" => {
                s.runtime_review
                    .snapshot
                    .as_mut()
                    .unwrap()
                    .view
                    .review_nonce = "NEW-NONCE".into()
            }
            "lease" => {
                s.runtime_review.snapshot.as_mut().unwrap().fetched =
                    Instant::now() - Duration::from_secs(61)
            }
            "intent" => {
                s.biometrics
                    .current
                    .as_mut()
                    .unwrap()
                    .scope
                    .as_mut()
                    .unwrap()["action"] = json!("UNKNOWN")
            }
            "epoch" => s.biometrics.authority_epoch = "RELOGIN".into(),
            "grant-expired" => {
                s.biometrics
                    .current
                    .as_mut()
                    .unwrap()
                    .view
                    .verification
                    .as_mut()
                    .unwrap()
                    .expires_at = (Utc::now() - chrono::Duration::seconds(1)).to_rfc3339()
            }
            "grant-binding" => {
                s.biometrics
                    .current
                    .as_mut()
                    .unwrap()
                    .view
                    .verification
                    .as_mut()
                    .unwrap()
                    .request_id = "REQ-OTHER".into()
            }
            "control" => {
                s.biometrics
                    .current
                    .as_mut()
                    .unwrap()
                    .view
                    .controls
                    .get_mut("pad")
                    .unwrap()
                    .result = Outcome::Fail
            }
            _ => unreachable!(),
        }
        assert!(consume(&mut s, &id).is_err(), "{kind}");
        assert!(read_submission(&s, "REQ-1").unwrap().is_none());
    }
}
#[test]
fn logout_disable_generation_and_pending_activation_revoke_authority() {
    for kind in ["logout", "disable", "generation", "activation"] {
        let (app, _dir) = crate::commands_tests::app();
        let state = app.state::<AppState>();
        let mut s = lock(&state).unwrap();
        let id = authorize(&mut s, "REJECT");
        match kind {
            "logout" => {
                s.biometrics.revoke("LOGOUT");
                s.technician = None;
            }
            "disable" => {
                s.db.execute("UPDATE technicians SET enabled=0", [])
                    .unwrap();
            }
            "generation" => {
                s.db.execute("UPDATE face_enrollments SET generation='new'", [])
                    .unwrap();
            }
            "activation" => {
                s.db.execute("INSERT INTO face_activation_intents VALUES('TECH-1','new','generation-1','now')",[]).unwrap();
            }
            _ => unreachable!(),
        }
        assert!(consume(&mut s, &id).is_err(), "{kind}");
    }
}
#[test]
fn submission_failure_cannot_consume_or_send_and_restart_preserves_identity() {
    let (app, _dir) = crate::commands_tests::app();
    let state = app.state::<AppState>();
    let mut s = lock(&state).unwrap();
    let id = authorize(&mut s, "REJECT");
    s.db.execute_batch("CREATE TRIGGER reject_submission BEFORE INSERT ON runtime_review_submissions BEGIN SELECT RAISE(ABORT,'test disk failure'); END;").unwrap();
    assert!(consume(&mut s, &id).is_err());
    assert!(!s.biometrics.current.as_ref().unwrap().authority_consumed);
    s.db.execute_batch("DROP TRIGGER reject_submission;")
        .unwrap();
    let (_, submission) = consume(&mut s, &id).unwrap();
    s.db = crate::db::open(&s.config).unwrap();
    s.biometrics = crate::biometric_sessions::Book::default();
    assert_eq!(
        read_submission(&s, "REQ-1").unwrap().unwrap().action_id,
        submission.action_id
    );
    assert!(consume(&mut s, &id).is_err());
}
#[test]
fn receipt_conflicts_and_rejection_execution_are_rejected() {
    let mut r = Receipt {
        schema_version: "alice-review-receipt-v1".into(),
        action_id: "ACT-1".into(),
        request_id: "REQ-1".into(),
        status: "ACCEPTED".into(),
        review_state: "REJECTED".into(),
        execution_status: "NOT_EXECUTED".into(),
        idempotent_replay: false,
    };
    r.validate("REQ-1", "ACT-1", "REJECT").unwrap();
    assert!(r.validate("REQ-1", "ACT-2", "REJECT").is_err());
    assert!(r.validate("REQ-2", "ACT-1", "REJECT").is_err());
    assert!(r.validate("REQ-1", "ACT-1", "APPROVE_ONCE").is_err());
    r.execution_status = "COMPLETED".into();
    assert!(r.validate("REQ-1", "ACT-1", "REJECT").is_err());
}
fn golden() -> Value {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../tests/fixtures/runtime-review/golden.json");
    serde_json::from_slice(&std::fs::read(path).expect("shared public cross-language fixture"))
        .unwrap()
}
fn unhex(s: &str) -> Vec<u8> {
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
        .collect()
}
#[test]
fn python_signature_and_canonical_json_verify_in_native() {
    let v = golden();
    let bytes = canonical(&v["proof"]).unwrap();
    assert_eq!(bytes, v["proof_canonical"].as_str().unwrap().as_bytes());
    assert_eq!(
        canonical(&v["request"]).unwrap(),
        v["request_canonical"].as_str().unwrap().as_bytes()
    );
    assert_eq!(
        digest(&canonical(&v["request"]).unwrap()),
        v["request_sha256"].as_str().unwrap()
    );
    let mut message = DOMAIN.to_vec();
    message.extend(bytes);
    let signature = base64::engine::general_purpose::STANDARD
        .decode(v["signature"].as_str().unwrap())
        .unwrap();
    UnparsedPublicKey::new(&ED25519, unhex(v["public_key"].as_str().unwrap()))
        .verify(&message, &signature)
        .unwrap();
    for case in v["canonical_cases"].as_array().unwrap() {
        assert_eq!(
            canonical(&case["value"]).unwrap(),
            case["canonical"].as_str().unwrap().as_bytes()
        );
    }
}
#[test]
fn native_ephemeral_signature_verifies_and_exports_public_vector_when_requested() {
    let v = golden();
    let key = key();
    let envelope = signed_envelope(v["proof"].clone(), &key).unwrap();
    let mut message = DOMAIN.to_vec();
    message.extend(canonical(&envelope["proof"]).unwrap());
    let signature = base64::engine::general_purpose::STANDARD
        .decode(envelope["signature"].as_str().unwrap())
        .unwrap();
    UnparsedPublicKey::new(&ED25519, key.public_key())
        .verify(&message, &signature)
        .unwrap();
    if let Ok(path) = std::env::var("ALICE_REVIEW_VECTOR_OUT") {
        let path = std::path::Path::new(&path);
        assert!(path.is_absolute());
        let mut out = envelope;
        out["public_key"] = json!(key
            .public_key()
            .as_ref()
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect::<String>());
        std::fs::write(path, serde_json::to_vec(&out).unwrap()).unwrap();
    }
}

#[test]
fn delayed_failures_and_reconciliation_cannot_downgrade_accepted_execution() {
    let (app, _dir) = crate::commands_tests::app();
    let state = app.state::<AppState>();
    let mut s = lock(&state).unwrap();
    let id = authorize(&mut s, "APPROVE_ONCE");
    let (_, mut saved) = consume(&mut s, &id).unwrap();
    let mut delayed = saved.clone();
    saved.state = "ACCEPTED".into();
    saved.receipt = Some(Receipt {
        schema_version: "alice-review-receipt-v1".into(),
        action_id: id.clone(),
        request_id: "REQ-1".into(),
        status: "ACCEPTED".into(),
        review_state: "APPROVED".into(),
        execution_status: "COMPLETED".into(),
        idempotent_replay: false,
    });
    save_submission(&s, &mut saved).unwrap();
    delayed.state = "UNCERTAIN".into();
    delayed.error = Some("delayed failure".into());
    save_submission(&s, &mut delayed).unwrap();
    assert_eq!(delayed.state, "ACCEPTED");
    assert_eq!(
        delayed.receipt.as_ref().unwrap().execution_status,
        "COMPLETED"
    );
    delayed.receipt.as_mut().unwrap().execution_status = "UNKNOWN".into();
    save_submission(&s, &mut delayed).unwrap();
    assert_eq!(delayed.receipt.unwrap().execution_status, "COMPLETED");
    let session_id = s
        .biometrics
        .current
        .as_ref()
        .unwrap()
        .view
        .session_id
        .clone();
    drop(s);
    assert_eq!(
        crate::biometric_commands::cancel_biometric_session(state, session_id).unwrap_err(),
        "REVIEW_ALREADY_SUBMITTED_RECONCILE_LEDGER"
    );
}

static TRANSPORT_ENV: std::sync::Mutex<()> = std::sync::Mutex::new(());
struct FeedEnvironment {
    prior: Vec<(&'static str, Option<std::ffi::OsString>)>,
}
impl FeedEnvironment {
    fn set(port: u16) -> Self {
        let prior = ["ALICE_FEED_URL", "ALICE_FEED_TOKEN"]
            .into_iter()
            .map(|k| (k, std::env::var_os(k)))
            .collect();
        std::env::set_var("ALICE_FEED_URL", format!("http://127.0.0.1:{port}"));
        std::env::set_var(
            "ALICE_FEED_TOKEN",
            "test-only-loopback-transport-token-00000000",
        );
        Self { prior }
    }
}
impl Drop for FeedEnvironment {
    fn drop(&mut self) {
        for (k, v) in &self.prior {
            match v {
                Some(v) => std::env::set_var(k, v),
                None => std::env::remove_var(k),
            }
        }
    }
}
fn incoming(stream: &mut std::net::TcpStream) -> (String, Value) {
    stream
        .set_read_timeout(Some(Duration::from_secs(5)))
        .unwrap();
    let mut bytes = Vec::new();
    let mut byte = [0];
    while !bytes.ends_with(b"\r\n\r\n") {
        stream.read_exact(&mut byte).unwrap();
        bytes.push(byte[0]);
        assert!(bytes.len() < 8192);
    }
    let head = String::from_utf8(bytes).unwrap();
    assert!(head
        .to_ascii_lowercase()
        .contains("authorization: bearer test-only-loopback-transport-token-00000000"));
    let length = head
        .lines()
        .find_map(|line| {
            line.to_ascii_lowercase()
                .strip_prefix("content-length: ")
                .map(|v| v.trim().parse::<usize>().unwrap())
        })
        .unwrap_or(0);
    assert!(length <= MAX_BYTES);
    let mut body = vec![0; length];
    stream.read_exact(&mut body).unwrap();
    (
        head.lines().next().unwrap().into(),
        if body.is_empty() {
            Value::Null
        } else {
            parse(&body).unwrap()
        },
    )
}
fn respond(stream: &mut std::net::TcpStream, body: &[u8]) {
    use std::io::Write;
    write!(stream,"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",body.len()).unwrap();
    stream.write_all(body).unwrap();
}
#[test]
fn native_http_lost_ack_reconciles_exact_action_after_restart_without_second_post() {
    let _serial = TRANSPORT_ENV.lock().unwrap();
    let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
    let _env = FeedEnvironment::set(listener.local_addr().unwrap().port());
    let server = std::thread::spawn(move || {
        let (mut first, _) = listener.accept().unwrap();
        let (line, envelope) = incoming(&mut first);
        assert_eq!(line, "POST /review HTTP/1.1");
        drop(first);
        let (mut second, _) = listener.accept().unwrap();
        let (line, body) = incoming(&mut second);
        assert_eq!(line, "GET /review/REQ-1 HTTP/1.1");
        assert!(body.is_null());
        let mut view = snapshot();
        view.eligible = false;
        view.review_state = "APPROVED".into();
        view.execution_status = "COMPLETED".into();
        view.accepted_action_id = Some(envelope["proof"]["action_id"].as_str().unwrap().into());
        view.accepted_action = Some("APPROVE_ONCE".into());
        respond(&mut second, &serde_json::to_vec(&view).unwrap());
    });
    let (app, _dir) = crate::commands_tests::app();
    let state = app.state::<AppState>();
    let id = authorize(&mut lock(&state).unwrap(), "APPROVE_ONCE");
    assert!(
        tauri::async_runtime::block_on(submit_runtime_review(state.clone(), id.clone())).is_err()
    );
    assert_eq!(
        read_submission(&lock(&state).unwrap(), "REQ-1")
            .unwrap()
            .unwrap()
            .state,
        "UNCERTAIN"
    );
    {
        let mut s = lock(&state).unwrap();
        s.db = crate::db::open(&s.config).unwrap();
        s.biometrics = crate::biometric_sessions::Book::default();
    }
    let reconciled =
        tauri::async_runtime::block_on(reconcile_runtime_submission(state.clone(), "REQ-1".into()))
            .unwrap();
    assert_eq!(reconciled.state, "ACCEPTED");
    assert_eq!(reconciled.action_id, id);
    assert_eq!(reconciled.receipt.unwrap().execution_status, "COMPLETED");
    assert!(tauri::async_runtime::block_on(submit_runtime_review(state, id)).is_err());
    server.join().unwrap();
}
#[test]
fn malformed_http_snapshot_invalidates_cache_and_native_feed_requires_login() {
    let _serial = TRANSPORT_ENV.lock().unwrap();
    let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
    let _env = FeedEnvironment::set(listener.local_addr().unwrap().port());
    let server = std::thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        assert_eq!(incoming(&mut stream).0, "GET /review/REQ-1 HTTP/1.1");
        respond(&mut stream, br#"{"eligible":true,"eligible":false}"#);
    });
    let (app, _dir) = crate::commands_tests::app();
    let state = app.state::<AppState>();
    authorize(&mut lock(&state).unwrap(), "REJECT");
    assert!(
        tauri::async_runtime::block_on(read_runtime_review(state.clone(), "REQ-1".into())).is_err()
    );
    assert!(lock(&state).unwrap().runtime_review.snapshot.is_none());
    crate::commands::logout(state.clone()).unwrap();
    assert_eq!(
        tauri::async_runtime::block_on(crate::commands::read_runtime_events(state, 0)).unwrap_err(),
        "Technician authentication required"
    );
    server.join().unwrap();
}
#[test]
fn successful_http_read_cannot_cross_logout_and_relogin_boundary() {
    let _serial = TRANSPORT_ENV.lock().unwrap();
    let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
    let _env = FeedEnvironment::set(listener.local_addr().unwrap().port());
    let (app, _dir) = crate::commands_tests::app();
    let state = app.state::<AppState>();
    authorize(&mut lock(&state).unwrap(), "REJECT");
    let app_handle = app.handle().clone();
    let server = std::thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        incoming(&mut stream);
        let state = app_handle.state::<AppState>();
        let mut s = lock(&state).unwrap();
        s.biometrics.revoke("LOGOUT");
        s.technician = Some(Session {
            id: "TECH-1".into(),
            expires_at: Utc::now().timestamp() + 3600,
        });
        drop(s);
        respond(&mut stream, &serde_json::to_vec(&snapshot()).unwrap());
    });
    assert_eq!(
        tauri::async_runtime::block_on(read_runtime_review(state, "REQ-1".into())).unwrap_err(),
        "TECHNICIAN_SESSION_CHANGED"
    );
    server.join().unwrap();
}

#[test]
#[ignore = "requires explicitly started local Python rehearsal; synthetic biometric evidence, no camera"]
fn native_to_python_local_rehearsal_approves_rejects_and_replays_once() {
    let _serial = TRANSPORT_ENV.lock().unwrap();
    let path = std::path::PathBuf::from(
        std::env::var("ALICE_REVIEW_INTEGRATION_SESSION")
            .expect("explicit local rehearsal session file"),
    );
    assert!(path.is_absolute());
    let descriptor: Value = serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
    assert_eq!(
        descriptor["source"],
        "LOCAL REHEARSAL / SIGNED FIXTURE RELEASE / FIXTURE ASSESSMENT / MOCK ESP"
    );
    let mut restore = FeedEnvironment { prior: Vec::new() };
    for name in [
        "ALICE_FEED_URL",
        "ALICE_FEED_TOKEN",
        "ALICE_CONSOLE_ID",
        "ALICE_REVIEW_KEY_FILE",
    ] {
        restore.prior.push((name, std::env::var_os(name)));
        std::env::set_var(name, descriptor["environment"][name].as_str().unwrap());
    }
    let (app, _dir) = crate::commands_tests::app();
    let state = app.state::<AppState>();
    {
        let mut s = lock(&state).unwrap();
        s.config.mode = "remote".into();
        s.config.biometric_mode = "arcface".into();
        s.db.execute("INSERT INTO technicians VALUES('TECH-001','test-native','Synthetic test technician','technician',1)",[]).unwrap();
        s.db.execute("INSERT INTO face_enrollments(technician_id,updated_at,provider,format,generation) VALUES('TECH-001','2026-09-06','arcface','MULTI_POSE_V2','synthetic-test-generation')",[]).unwrap();
        s.technician = Some(Session {
            id: "TECH-001".into(),
            expires_at: Utc::now().timestamp() + 3600,
        });
    }
    for (request, intent, expected_execution) in [
        ("native-test-approve", "APPROVE_ONCE", "COMPLETED"),
        ("native-test-reject", "REJECT", "NOT_EXECUTED"),
    ] {
        let view =
            tauri::async_runtime::block_on(read_runtime_review(state.clone(), request.into()))
                .unwrap();
        assert!(view.eligible);
        let verification_id = {
            let mut s = lock(&state).unwrap();
            let signer = prepare_signer(&s).unwrap();
            let bound = scope(&s, request, &view.decision_event_id, intent).unwrap();
            s.biometrics
                .begin(
                    Purpose::Approval,
                    "TECH-001".into(),
                    "synthetic-test-generation".into(),
                    Some(bound.clone()),
                )
                .unwrap();
            s.runtime_review.bind_signer(signer);
            let g = grant(&s, &bound).unwrap();
            let verification_id = g.verification_id.clone();
            let a = s.biometrics.current.as_mut().unwrap();
            a.view.verification = Some(g);
            a.view.state = "SUCCEEDED".into();
            a.view.controls = REQUIRED
                .into_iter()
                .map(|name| {
                    (
                        name.into(),
                        Control {
                            result: Outcome::Pass,
                            model: "SYNTHETIC_UNIT_TEST_ONLY".into(),
                            reason: "No camera acceptance claimed".into(),
                            score: Some(0.9),
                        },
                    )
                })
                .collect();
            verification_id
        };
        let receipt = tauri::async_runtime::block_on(submit_runtime_review(
            state.clone(),
            verification_id.clone(),
        ))
        .unwrap();
        assert_eq!(receipt.execution_status, expected_execution);
        assert!(!receipt.idempotent_replay);
        let envelope = {
            let s = lock(&state).unwrap();
            let raw: String =
                s.db.query_row(
                    "SELECT envelope FROM runtime_review_submissions WHERE action_id=?1",
                    [&verification_id],
                    |r| r.get(0),
                )
                .unwrap();
            parse(raw.as_bytes()).unwrap()
        };
        let replay: Receipt = serde_json::from_value(
            tauri::async_runtime::block_on(exchange("/review", Some(envelope))).unwrap(),
        )
        .unwrap();
        replay.validate(request, &verification_id, intent).unwrap();
        assert!(replay.idempotent_replay);
        assert_eq!(replay.execution_status, expected_execution);
        assert!(tauri::async_runtime::block_on(submit_runtime_review(
            state.clone(),
            verification_id
        ))
        .is_err());
        let reconciled = tauri::async_runtime::block_on(reconcile_runtime_submission(
            state.clone(),
            request.into(),
        ))
        .unwrap();
        assert_eq!(reconciled.state, "ACCEPTED");
    }
    let events =
        tauri::async_runtime::block_on(crate::commands::read_runtime_events(state, 0)).unwrap();
    assert!(events["events"].as_array().is_some_and(|v| !v.is_empty()));
}

#[test]
fn native_signer_rejects_exposed_keys_symlinks_and_invalid_identity() {
    use ring::rand::SecureRandom;
    use std::os::unix::fs::{symlink, PermissionsExt};
    let _serial = TRANSPORT_ENV.lock().unwrap();
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("console.seed");
    let restore = FeedEnvironment {
        prior: ["ALICE_REVIEW_KEY_FILE", "ALICE_CONSOLE_ID"]
            .into_iter()
            .map(|k| (k, std::env::var_os(k)))
            .collect(),
    };
    let mut seed = [0; 32];
    ring::rand::SystemRandom::new().fill(&mut seed).unwrap();
    std::fs::write(&path, seed).unwrap();
    seed.fill(0);
    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600)).unwrap();
    std::env::set_var("ALICE_REVIEW_KEY_FILE", &path);
    std::env::set_var("ALICE_CONSOLE_ID", "native-test-console");
    load_signer().unwrap();
    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o644)).unwrap();
    assert!(load_signer().is_err());
    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600)).unwrap();
    let linked = dir.path().join("linked.seed");
    symlink(&path, &linked).unwrap();
    std::env::set_var("ALICE_REVIEW_KEY_FILE", linked);
    assert!(load_signer().is_err());
    std::env::set_var("ALICE_REVIEW_KEY_FILE", &path);
    std::env::set_var("ALICE_CONSOLE_ID", ".invalid");
    assert!(load_signer().is_err());
    std::env::set_var("ALICE_CONSOLE_ID", "native-test-console");
    std::fs::write(&path, b"invalid length").unwrap();
    assert!(load_signer().is_err());
    drop(restore);
}

#[test]
fn reused_request_id_cannot_inherit_acknowledgment_from_another_runtime_or_decision() {
    let (app, _dir) = crate::commands_tests::app();
    let state = app.state::<AppState>();
    let mut s = lock(&state).unwrap();
    let id = authorize(&mut s, "APPROVE_ONCE");
    let (_, mut saved) = consume(&mut s, &id).unwrap();
    let original = snapshot();
    submission_binding(&s, &saved, &original).unwrap();
    for field in [
        "request_sha256",
        "decision_event_id",
        "decision_event_hash",
        "release_sha256",
        "authority_interval_ref",
    ] {
        let mut changed = serde_json::to_value(&original).unwrap();
        changed[field] = json!(if field.contains("sha256") || field.ends_with("hash") {
            "c".repeat(64)
        } else {
            "CHANGED".into()
        });
        let changed: Snapshot = serde_json::from_value(changed).unwrap();
        assert!(submission_binding(&s, &saved, &changed).is_err(), "{field}");
    }
    saved.state = "ACCEPTED".into();
    saved.receipt = Some(Receipt {
        schema_version: "alice-review-receipt-v1".into(),
        action_id: id.clone(),
        request_id: "REQ-1".into(),
        status: "ACCEPTED".into(),
        review_state: "APPROVED".into(),
        execution_status: "COMPLETED".into(),
        idempotent_replay: false,
    });
    assert!(submission_binding(&s, &saved, &original).is_err());
    let mut confirmed = original;
    confirmed.accepted_action_id = Some(id);
    confirmed.accepted_action = Some("APPROVE_ONCE".into());
    confirmed.review_state = "APPROVED".into();
    confirmed.eligible = false;
    confirmed.runtime_epoch = "restarted".into();
    confirmed.review_nonce = "new-nonce".into();
    confirmed.release_sha256 = "d".repeat(64);
    confirmed.authority_interval_ref = Some("later-authority".into());
    submission_binding(&s, &saved, &confirmed).unwrap();
    confirmed.decision_event_hash = "e".repeat(64);
    assert!(submission_binding(&s, &saved, &confirmed).is_err());
    save_submission(&s, &mut saved).unwrap();
    let invalidated = unconfirmed(saved, "REVIEW_SUBMISSION_BINDING_CONFLICT");
    assert_eq!(invalidated.state, "UNCERTAIN");
    assert!(invalidated.receipt.is_none());
    assert!(read_submission(&s, "REQ-1")
        .unwrap()
        .unwrap()
        .receipt
        .is_some());
}

#[test]
fn demo_fan_request_is_exact_and_cannot_become_a_physical_action() {
    let mut view = snapshot();
    let rid = "c".repeat(64);
    let request = json!({"schema_version":"alice-demo-fan-v1","request_id":rid,
        "client_request_id":"fan-1","run_id":"a".repeat(32),"expected_revision":0,
        "agent_id":"cooling-agent-01","action":"set_demo_fan_pct","target":"DEMO-SERVER-01",
        "parameters":{"fan_basis_points":8500}});
    view.request_id = rid.clone();
    view.request = Some(request.clone());
    view.request_sha256 = digest(&canonical(&request).unwrap());
    assert!(view.validate(&rid).is_ok());
    for (field, bad) in [("target", json!("ESP-LIGHT-01")),
                          ("action", json!("set_light_state")),
                          ("expected_revision", json!(-1)),
                          ("parameters", json!({"fan_basis_points":10001})),
                          ("parameters", json!({"fan_pct":85})),
                          ("run_id", json!("old-run"))] {
        let mut changed = request.clone();
        changed[field] = bad;
        view.request_sha256 = digest(&canonical(&changed).unwrap());
        view.request = Some(changed);
        assert!(view.validate(&rid).is_err());
    }
}
