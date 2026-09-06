use crate::{
    commands,
    config::Config,
    db,
    security::{Action, Technician},
    AppState, Inner,
};
use argon2::{
    password_hash::{PasswordHasher, SaltString},
    Argon2,
};
use rand_core::OsRng;
use serde_json::{json, Value};
use std::{collections::HashMap, sync::Mutex};
use tauri::Manager;

pub(crate) fn fixture() -> Value {
    let mut value: Value =
        serde_json::from_str(include_str!("../../../../fixtures/legacy/decision.json")).unwrap();
    value["event_type"] = json!("alice.decision");
    value["system"]
        .as_object_mut()
        .unwrap()
        .remove("dcamr_node");
    value["system"]["node"] = json!("ALICE-PI-01");
    value
}
pub(crate) fn app() -> (tauri::App<tauri::test::MockRuntime>, tempfile::TempDir) {
    let dir = tempfile::tempdir().unwrap();
    let config = Config {
        mode: "mock".into(),
        biometric_mode: "mock".into(),
        model: String::new(),
        ollama_url: "http://127.0.0.1:11434".into(),
        biometric_url: "http://127.0.0.1:8765".into(),
        biometric_token: String::new(),
        database: dir.path().join("test.sqlite3"),
    };
    let db = db::open(&config).unwrap();
    let password = Argon2::default()
        .hash_password(b"test-only-password", &SaltString::generate(&mut OsRng))
        .unwrap()
        .to_string();
    assert!(password.starts_with("$argon2id$"));
    db.execute(
        "INSERT INTO admin_accounts VALUES('test-admin',?1)",
        [password],
    )
    .unwrap();
    let app = tauri::test::mock_builder()
        .manage(AppState(Mutex::new(Inner {
            db,
            config,
            technician: None,
            admin: None,
            grants: HashMap::new(),
            failures: HashMap::new(),
            biometrics: crate::biometric_sessions::Book::default(),
        })))
        .build(tauri::test::mock_context(tauri::test::noop_assets()))
        .unwrap();
    (app, dir)
}
fn action(proof: Option<String>) -> Action {
    Action {
        schema_version: "1.0".into(),
        event_type: "alice.technician_action".into(),
        action_id: "ACTION-TEST-1".into(),
        timestamp: chrono::Utc::now().to_rfc3339(),
        decision_id: "DEC-20260905-000184".into(),
        request_id: "REQ-88291".into(),
        technician_id: "TECH-DEMO".into(),
        action: "APPROVE_ONCE".into(),
        biometric_verification_id: proof,
        note: String::new(),
        mode: "mock".into(),
    }
}
pub(crate) fn reassessment() -> Value {
    let mut d = fixture();
    d["decision_id"] = json!("DEC-20260905-000185");
    d["reassessment"] = json!({"previous_decision_id":"DEC-20260905-000184","root_decision_id":"DEC-20260905-000184","sequence":1,"trigger":"AGENT_CONTEXT_RESPONSE"});
    d["anomaly"]["risk_score"] = json!(62);
    d["context_challenge"]["required"] = json!(false);
    d
}
#[test]
fn native_reassessment_revokes_previous_grants_and_preserves_immutable_history() {
    let (app, _dir) = app();
    let s = app.state::<AppState>();
    let original = fixture();
    commands::cache_decision(s.clone(), original.clone()).unwrap();
    commands::demo_session(s.clone()).unwrap();
    let old_grant = commands::mock_verify(
        s.clone(),
        "TECH-DEMO".into(),
        "DEC-20260905-000184".into(),
        "REQ-88291".into(),
        "PASS".into(),
    )
    .unwrap();
    commands::cache_decision(s.clone(), reassessment()).unwrap();
    assert!(s.0.lock().unwrap().grants.is_empty());
    let mut stale = action(Some(old_grant.verification_id));
    stale.decision_id = "DEC-20260905-000185".into();
    assert!(commands::submit_action(s.clone(), stale).is_err());
    for kind in ["APPROVE_ONCE", "HOLD", "RESEARCH", "REJECT"] {
        let mut old = action(None);
        old.action = kind.into();
        assert!(commands::submit_action(s.clone(), old).is_err());
    }
    assert!(commands::mock_verify(
        s.clone(),
        "TECH-DEMO".into(),
        "DEC-20260905-000184".into(),
        "REQ-88291".into(),
        "PASS".into()
    )
    .is_err());
    let fresh = commands::mock_verify(
        s.clone(),
        "TECH-DEMO".into(),
        "DEC-20260905-000185".into(),
        "REQ-88291".into(),
        "PASS".into(),
    )
    .unwrap();
    let mut approval = action(Some(fresh.verification_id));
    approval.decision_id = "DEC-20260905-000185".into();
    let receipt = commands::submit_action(s.clone(), approval).unwrap();
    assert_eq!(receipt["execution_status"], "NOT_EXECUTED");
    let history = commands::read_console_history(s.clone()).unwrap();
    assert_eq!(history["decisions"][0], original);
    assert_eq!(history["decisions"][1], reassessment());
    assert_eq!(history["actions"][0]["decision_id"], "DEC-20260905-000185");
    for kind in [
        "REASSESSMENT_RECEIVED",
        "DECISION_SUPERSEDED",
        "CURRENT_ASSESSMENT_UPDATED",
    ] {
        assert!(history["audit"]
            .as_array()
            .unwrap()
            .iter()
            .any(|e| e["type"] == kind && e["request_id"] == "REQ-88291"));
    }
    // Reopening SQLite retains the full lineage; grants never survive a restart.
    let config = s.0.lock().unwrap().config.clone();
    let reopened = db::open(&config).unwrap();
    let raw: String = reopened
        .query_row(
            "SELECT payload FROM decision_cache WHERE decision_id='DEC-20260905-000185'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(serde_json::from_str::<Value>(&raw).unwrap(), reassessment());
}
#[test]
fn native_cache_rejects_broken_lineage_and_conflicting_duplicates() {
    let (app, _dir) = app();
    let s = app.state::<AppState>();
    assert!(commands::cache_decision(s.clone(), reassessment()).is_err());
    commands::cache_decision(s.clone(), fixture()).unwrap();
    for field in ["request_id", "agent_id", "mission_id", "action", "target"] {
        let mut wrong = reassessment();
        wrong["request"][field] = json!("OTHER");
        assert!(commands::cache_decision(s.clone(), wrong).is_err());
    }
    for (field, value) in [
        ("previous_decision_id", json!("MISSING")),
        ("root_decision_id", json!("MISSING")),
        ("sequence", json!(2)),
        ("trigger", json!("LLM")),
    ] {
        let mut wrong = reassessment();
        wrong["reassessment"][field] = value;
        assert!(commands::cache_decision(s.clone(), wrong).is_err());
    }
    commands::cache_decision(s.clone(), reassessment()).unwrap();
    commands::cache_decision(s.clone(), reassessment()).unwrap();
    let mut conflict = reassessment();
    conflict["anomaly"]["risk_score"] = json!(10);
    assert!(commands::cache_decision(s.clone(), conflict).is_err());
    let mut branch = reassessment();
    branch["decision_id"] = json!("BRANCH");
    assert!(commands::cache_decision(s.clone(), branch).is_err());
    let mut unlinked = fixture();
    unlinked["decision_id"] = json!("UNLINKED");
    assert!(commands::cache_decision(s.clone(), unlinked).is_err());
    let mut next = reassessment();
    next["decision_id"] = json!("DEC-186");
    next["reassessment"]["previous_decision_id"] = json!("DEC-20260905-000185");
    next["reassessment"]["sequence"] = json!(2);
    commands::cache_decision(s.clone(), next).unwrap();
}
#[test]
fn native_mock_slice_is_bound_and_replay_safe() {
    let (app, _dir) = app();
    let s = app.state::<AppState>();
    commands::cache_decision(s.clone(), fixture()).unwrap();
    commands::demo_session(s.clone()).unwrap();
    assert!(commands::submit_action(s.clone(), action(None)).is_err());
    let grant = commands::mock_verify(
        s.clone(),
        "TECH-DEMO".into(),
        "DEC-20260905-000184".into(),
        "REQ-88291".into(),
        "PASS".into(),
    )
    .unwrap();
    let a = action(Some(grant.verification_id.clone()));
    let serialized = serde_json::to_value(&a).unwrap();
    let receipt = commands::submit_action(s.clone(), a).unwrap();
    assert_eq!(receipt["execution_status"], "NOT_EXECUTED");
    assert!(s.0.lock().unwrap().grants.is_empty());
    assert!(
        commands::submit_action(s.clone(), serde_json::from_value(serialized).unwrap()).is_ok()
    );
    let mut replay = action(Some(grant.verification_id));
    replay.action_id = "REPLAY".into();
    assert!(commands::submit_action(s.clone(), replay).is_err());
    let history = commands::read_console_history(s.clone()).unwrap();
    assert_eq!(history["actions"].as_array().unwrap().len(), 1);
    assert_eq!(history["decisions"][0]["decision"]["result"], "HOLD");
}
#[test]
fn native_admin_gate_and_password_hash_work() {
    let (app, _dir) = app();
    let s = app.state::<AppState>();
    assert!(commands::list_technicians(s.clone()).is_err());
    assert!(commands::admin_login(s.clone(), "test-admin".into(), "wrong".into()).is_err());
    commands::admin_login(s.clone(), "test-admin".into(), "test-only-password".into()).unwrap();
    let t = Technician {
        technician_id: "T1".into(),
        username: "test-tech".into(),
        display_name: "Test Technician".into(),
        role: "Technician".into(),
        enabled: true,
        enrolled: false,
        enrollment_version: None,
    };
    commands::save_technician(s.clone(), t).unwrap();
    commands::set_technician_enabled(s.clone(), "T1".into(), false).unwrap();
    assert!(!commands::list_technicians(s.clone()).unwrap()[0].enabled);
    commands::admin_logout(s.clone()).unwrap();
    assert!(commands::list_technicians(s.clone()).is_err());
}
#[test]
fn native_remote_refuses_mock_grants_and_renderer_cache() {
    let (app, _dir) = app();
    let s = app.state::<AppState>();
    s.0.lock().unwrap().config.mode = "remote".into();
    assert!(commands::demo_session(s.clone()).is_err());
    assert!(commands::cache_decision(s.clone(), fixture()).is_err());
    assert!(commands::reset_mock_scenario(s.clone()).is_err());
}

#[test]
fn real_identity_cannot_use_the_simulated_session_shortcut() {
    let (app, _dir) = app();
    let s = app.state::<AppState>();
    commands::demo_session(s.clone()).unwrap();
    s.0.lock().unwrap().config.biometric_mode = "arcface".into();
    assert!(commands::read_console_history(s.clone()).is_err());
    assert!(commands::demo_session(s.clone()).is_err());
    assert!(commands::mock_verify(
        s.clone(),
        "TECH-DEMO".into(),
        "DEC-20260905-000184".into(),
        "REQ-88291".into(),
        "PASS".into()
    )
    .is_err());
}
#[test]
#[ignore = "requires a configured, running local Ollama model"]
fn ollama_live_gateway_returns_only_structured_operational_content() {
    let (app, _dir) = app();
    let s = app.state::<AppState>();
    let model = std::env::var("ALICE_TEST_OLLAMA_MODEL")
        .expect("Set ALICE_TEST_OLLAMA_MODEL to an installed model");
    s.0.lock().unwrap().config.model = model;
    commands::demo_session(s.clone()).unwrap();
    let health = tauri::async_runtime::block_on(commands::llm_health(s.clone())).unwrap();
    assert_eq!(health["status"], "READY");
    let schema = json!({"type":"object","properties":{"summary":{"type":"string","minLength":1,"maxLength":3000},"evidence_ids":{"type":"array","items":{"type":"string","minLength":1,"maxLength":200}}},"required":["summary","evidence_ids"],"additionalProperties":false});
    let result = tauri::async_runtime::block_on(commands::llm_generate(
        s.clone(),
        "Explain why this upstream request is held in two sentences. Do not authorize it.".into(),
        fixture(),
        schema,
    ))
    .unwrap();
    assert!(!result["summary"].as_str().unwrap().is_empty());
    assert!(result.get("thinking").is_none());
    assert!(result.get("action").is_none());
    assert!(result["evidence_ids"].as_array().unwrap().iter().all(|e| [
        "PROC-8821",
        "EDR-9921",
        "NETFLOW-8177"
    ]
    .iter()
    .any(|id| e == id)));
    println!("Local Ollama structured explanation validated; no authorization emitted.");
}

#[test]
fn ollama_grammar_preserves_shape_without_large_string_repetitions() {
    let schema = json!({"type":"object","additionalProperties":false,"required":["summary"],"properties":{"summary":{"type":"string","minLength":1,"maxLength":3000},"ids":{"type":"array","items":{"type":"string","maxLength":200}},"intent":{"type":"string","enum":["UNKNOWN","RESEARCH"]}}});
    let safe = commands::ollama_sampling_schema(schema);
    assert!(safe["properties"]["summary"].get("maxLength").is_none());
    assert!(safe["properties"]["summary"].get("minLength").is_none());
    assert!(safe["properties"]["ids"]["items"]
        .get("maxLength")
        .is_none());
    assert_eq!(safe["properties"]["summary"]["type"], "string");
    assert_eq!(safe["additionalProperties"], false);
    assert_eq!(safe["required"], json!(["summary"]));
    assert_eq!(
        safe["properties"]["intent"]["enum"],
        json!(["UNKNOWN", "RESEARCH"])
    );
}

#[test]
fn retired_frame_ipc_never_mints_enrollment_login_or_approval() {
    let (app, _dir) = app();
    let state = app.state::<AppState>();
    commands::admin_login(
        state.clone(),
        "test-admin".into(),
        "test-only-password".into(),
    )
    .unwrap();
    state.0.lock().unwrap().config.biometric_mode = "arcface".into();
    for frames in [vec!["injected".into()], vec!["image".into(); 5], Vec::new()] {
        assert!(tauri::async_runtime::block_on(commands::enroll_technician(
            state.clone(),
            "T1".into(),
            frames.clone()
        ))
        .unwrap_err()
        .contains("RETIRED"));
        assert!(tauri::async_runtime::block_on(commands::technician_login(
            state.clone(),
            "tech".into(),
            frames.clone()
        ))
        .err()
        .unwrap()
        .contains("RETIRED"));
        assert!(tauri::async_runtime::block_on(commands::verify_face(
            state.clone(),
            "T1".into(),
            "D1".into(),
            "R1".into(),
            frames
        ))
        .err()
        .unwrap()
        .contains("RETIRED"));
    }
    assert!(commands::demo_session(state.clone()).is_err());
    let inner = state.0.lock().unwrap();
    assert!(inner.technician.is_none() && inner.grants.is_empty());
    assert_eq!(
        inner
            .db
            .query_row("SELECT COUNT(*) FROM face_enrollments", [], |r| r
                .get::<_, i64>(0))
            .unwrap(),
        0
    );
}

#[test]
fn logout_relogin_and_admin_lock_revoke_biometric_epochs() {
    use crate::biometric_sessions::Purpose;
    let (app, _dir) = app();
    let state = app.state::<AppState>();
    let id = {
        let mut s = state.0.lock().unwrap();
        s.biometrics
            .begin(Purpose::Login, "TECH-DEMO".into(), "V2".into(), None)
            .unwrap()
            .session_id
    };
    commands::logout(state.clone()).unwrap();
    commands::demo_session(state.clone()).unwrap();
    assert_eq!(
        state
            .0
            .lock()
            .unwrap()
            .biometrics
            .get(&id)
            .unwrap()
            .view
            .state,
        "CANCELLED"
    );
    let id = {
        let mut s = state.0.lock().unwrap();
        s.biometrics
            .begin(Purpose::Enrollment, "TECH-DEMO".into(), "V2".into(), None)
            .unwrap()
            .session_id
    };
    commands::admin_logout(state.clone()).unwrap();
    assert_eq!(
        state
            .0
            .lock()
            .unwrap()
            .biometrics
            .get(&id)
            .unwrap()
            .view
            .state,
        "CANCELLED"
    );
}
