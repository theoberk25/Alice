//! Native authority for the fixed Pi review endpoint. Renderer inputs are IDs
//! and intent only; the existing local DB holds submission identity, never an
//! alternate HOLD queue. Unknown delivery is reconciled by GET, never reexecuted.
use crate::{
    commands::lock,
    security::{require_technician, Grant},
    AppState, Inner,
};
use base64::Engine;
use chrono::Utc;
use ring::signature::Ed25519KeyPair;
use rusqlite::{params, OptionalExtension};
use serde::{
    de::{self, MapAccess, SeqAccess, Visitor},
    Deserialize, Deserializer, Serialize,
};
use serde_json::{json, Value};
use std::{
    fmt,
    io::Read,
    time::{Duration, Instant},
};
use tauri::State;

const MAX_BYTES: usize = 16 * 1024;
const SNAPSHOT_LEASE: Duration = Duration::from_secs(60);
const DOMAIN: &[u8] = b"alice-native-review-v1\0";

// Same alice-json-v1 canonicalization as dcamr.audit.event_contract. Deserialize
// through a visitor so duplicate keys cannot disappear before validation.
struct Unique(Value);
impl<'de> Deserialize<'de> for Unique {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        struct V;
        impl<'de> Visitor<'de> for V {
            type Value = Unique;
            fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
                f.write_str("bounded integer-only JSON")
            }
            fn visit_bool<E: de::Error>(self, v: bool) -> Result<Unique, E> {
                Ok(Unique(json!(v)))
            }
            fn visit_unit<E: de::Error>(self) -> Result<Unique, E> {
                Ok(Unique(Value::Null))
            }
            fn visit_i64<E: de::Error>(self, v: i64) -> Result<Unique, E> {
                Ok(Unique(json!(v)))
            }
            fn visit_u64<E: de::Error>(self, v: u64) -> Result<Unique, E> {
                i64::try_from(v)
                    .map(|n| Unique(json!(n)))
                    .map_err(|_| E::custom("integer range"))
            }
            fn visit_str<E: de::Error>(self, v: &str) -> Result<Unique, E> {
                Ok(Unique(json!(v)))
            }
            fn visit_seq<A: SeqAccess<'de>>(self, mut a: A) -> Result<Unique, A::Error> {
                let mut out = Vec::new();
                while let Some(Unique(v)) = a.next_element()? {
                    if out.len() >= 64 {
                        return Err(de::Error::custom("array limit"));
                    }
                    out.push(v);
                }
                Ok(Unique(Value::Array(out)))
            }
            fn visit_map<A: MapAccess<'de>>(self, mut a: A) -> Result<Unique, A::Error> {
                let mut out = serde_json::Map::new();
                while let Some((k, Unique(v))) = a.next_entry::<String, Unique>()? {
                    if out.len() >= 64 || out.contains_key(&k) {
                        return Err(de::Error::custom("duplicate key or object limit"));
                    }
                    out.insert(k, v);
                }
                Ok(Unique(Value::Object(out)))
            }
        }
        d.deserialize_any(V)
    }
}
fn canonical(value: &Value) -> Result<Vec<u8>, String> {
    fn tree(v: &Value, depth: usize, budget: &mut usize) -> Result<(), String> {
        *budget = budget.checked_sub(1).ok_or("INVALID_BOUNDED_JSON")?;
        if depth > 16 {
            return Err("INVALID_BOUNDED_JSON".into());
        }
        match v {
            Value::Object(m) => {
                if m.len() > 64 {
                    return Err("INVALID_BOUNDED_JSON".into());
                }
                for (k, v) in m {
                    if k.is_empty() || k.len() > 128 || !k.is_ascii() {
                        return Err("INVALID_BOUNDED_JSON".into());
                    }
                    *budget = budget
                        .checked_sub(k.len() + 3)
                        .ok_or("INVALID_BOUNDED_JSON")?;
                    tree(v, depth + 1, budget)?;
                }
            }
            Value::Array(a) => {
                if a.len() > 64 {
                    return Err("INVALID_BOUNDED_JSON".into());
                }
                for v in a {
                    tree(v, depth + 1, budget)?;
                }
            }
            Value::String(s) => {
                if s.chars().count() > 4096 {
                    return Err("INVALID_BOUNDED_JSON".into());
                }
                *budget = budget.checked_sub(s.len()).ok_or("INVALID_BOUNDED_JSON")?;
            }
            Value::Number(n) if n.as_i64().is_none() => return Err("INVALID_BOUNDED_JSON".into()),
            _ => (),
        }
        Ok(())
    }
    let mut budget = MAX_BYTES;
    tree(value, 0, &mut budget)?;
    let bytes = serde_json::to_vec(value).map_err(|_| "INVALID_BOUNDED_JSON")?;
    if bytes.len() > MAX_BYTES {
        return Err("INVALID_BOUNDED_JSON".into());
    }
    Ok(bytes)
}
fn parse(bytes: &[u8]) -> Result<Value, String> {
    if bytes.len() > MAX_BYTES {
        return Err("REVIEW_RESPONSE_TOO_LARGE".into());
    }
    let Unique(value) = serde_json::from_slice(bytes).map_err(|_| "INVALID_REVIEW_JSON")?;
    canonical(&value)?;
    Ok(value)
}
fn digest(bytes: &[u8]) -> String {
    ring::digest::digest(&ring::digest::SHA256, bytes)
        .as_ref()
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}
fn id(value: &str) -> bool {
    value
        .as_bytes()
        .first()
        .is_some_and(u8::is_ascii_alphanumeric)
        && value.len() <= 128
        && value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"_.:-".contains(&b))
}
fn hash(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
fn action(value: &str) -> bool {
    ["APPROVE_ONCE", "REJECT"].contains(&value)
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Snapshot {
    pub schema_version: String,
    pub request_id: String,
    pub request_sha256: String,
    pub decision_event_id: String,
    pub decision_event_hash: String,
    pub release_sha256: String,
    #[serde(deserialize_with = "required_nullable")]
    pub authority_interval_ref: Option<String>,
    pub runtime_epoch: String,
    pub review_nonce: String,
    #[serde(deserialize_with = "required_nullable")]
    pub request: Option<Value>,
    pub decision: String,
    #[serde(default)]
    pub decision_reason_codes: Vec<String>,
    #[serde(default)]
    pub assessment: Option<Value>,
    pub review_state: String,
    pub eligible: bool,
    pub reason: String,
    pub execution_status: String,
    #[serde(deserialize_with = "required_nullable")]
    pub accepted_action_id: Option<String>,
    #[serde(deserialize_with = "required_nullable")]
    pub accepted_action: Option<String>,
}
fn required_nullable<'de, D: Deserializer<'de>, T: Deserialize<'de>>(
    d: D,
) -> Result<Option<T>, D::Error> {
    Option::<T>::deserialize(d)
}
struct Cache {
    view: Snapshot,
    fetched: Instant,
    technician: String,
    epoch: String,
}
pub(crate) struct Signer {
    console: String,
    key: Ed25519KeyPair,
}
#[derive(Default)]
pub struct Book {
    snapshot: Option<Cache>,
    read_generation: u64,
    signer: Option<Signer>,
}
impl Book {
    pub fn invalidate(&mut self) {
        self.snapshot = None;
        self.signer = None;
        self.read_generation = self.read_generation.wrapping_add(1);
    }
    pub(crate) fn bind_signer(&mut self, signer: Signer) {
        self.signer = Some(signer);
    }
}
impl Snapshot {
    fn validate(&self, request_id: &str) -> Result<(), String> {
        if self.schema_version != "alice-runtime-review-v1"
            || self.request_id != request_id
            || ![
                &self.request_id,
                &self.decision_event_id,
                &self.runtime_epoch,
                &self.review_nonce,
            ]
            .into_iter()
            .all(|v| id(v))
            || self.authority_interval_ref.as_ref().is_some_and(|v| !id(v))
            || ![
                &self.request_sha256,
                &self.decision_event_hash,
                &self.release_sha256,
            ]
            .into_iter()
            .all(|v| hash(v))
            || !["ALLOW", "DENY", "CHALLENGE", "REJECTED"].contains(&self.decision.as_str())
            || !["PENDING", "APPROVED", "REJECTED"].contains(&self.review_state.as_str())
            || !["NOT_EXECUTED", "COMPLETED", "FAILED", "UNKNOWN"]
                .contains(&self.execution_status.as_str())
            || self.reason.len() > 200
            || self.decision_reason_codes.len() > 32
            || self.decision_reason_codes.iter().any(|v| !id(v))
        {
            return Err("INVALID_RUNTIME_REVIEW".into());
        }
        match (
            &self.accepted_action_id,
            &self.accepted_action,
            self.review_state.as_str(),
        ) {
            (None, None, "PENDING") => (),
            (Some(a), Some(intent), state)
                if id(a)
                    && action(intent)
                    && ((intent == "APPROVE_ONCE" && state == "APPROVED")
                        || (intent == "REJECT" && state == "REJECTED")) =>
            {
                ()
            }
            _ => return Err("INVALID_RUNTIME_REVIEW_ACTION".into()),
        }
        // Validate retained request evidence for all outcomes, not just eligible HOLDs.
        if let Some(request) = &self.request {
            let parsed: Request =
                serde_json::from_value(request.clone()).map_err(|_| "INVALID_REVIEW_REQUEST")?;
            if parsed.schema_version != "1.0"
                || parsed.request_id != request_id
                || parsed.request_id.len() > 64
                || parsed.agent_id.len() > 64
                || !id(&parsed.agent_id)
                || !parsed.valid_action()
                || !parsed.issued_at.ends_with('Z')
                || chrono::DateTime::parse_from_rfc3339(&parsed.issued_at).is_err()
                || digest(&canonical(request)?) != self.request_sha256
            {
                return Err("REVIEW_REQUEST_BINDING_INVALID".into());
            }
        }
        if self.eligible
            && (self.request.is_none()
                || self.authority_interval_ref.is_none()
                || self.decision != "CHALLENGE"
                || self.review_state != "PENDING"
                || self.execution_status != "NOT_EXECUTED")
        {
            return Err("REVIEW_REQUEST_BINDING_INVALID".into());
        }
        if self.review_state == "REJECTED" && self.execution_status != "NOT_EXECUTED" {
            return Err("INVALID_REJECTION_EXECUTION".into());
        }
        if let Some(value) = &self.assessment {
            let object = value.as_object().ok_or("INVALID_RUNTIME_ASSESSMENT")?;
            let expected = ["status", "result", "score_ppm", "raw_score_ppm", "model_id",
                            "model_fingerprint", "reason_codes"];
            if object.len() != expected.len() || expected.iter().any(|k| !object.contains_key(*k))
                || object.get("status").and_then(Value::as_str) != Some("OK")
                || !object.get("result").and_then(Value::as_str)
                    .is_some_and(|v| ["LOW", "ELEVATED", "HIGH"].contains(&v))
                || !object.get("score_ppm").and_then(Value::as_i64)
                    .is_some_and(|v| (0..=1_000_000).contains(&v))
                || object.get("raw_score_ppm").and_then(Value::as_i64).is_none()
                || !object.get("model_id").and_then(Value::as_str).is_some_and(id)
                || !object.get("model_fingerprint").and_then(Value::as_str)
                    .is_some_and(|v| {
                        v.len() == 64
                            && v.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f'))
                    })
                || !object.get("reason_codes").and_then(Value::as_array).is_some_and(|values| {
                    values.len() <= 32
                        && values.iter().all(|item| item.as_str().is_some_and(id))
                })
            {
                return Err("INVALID_RUNTIME_ASSESSMENT".into());
            }
        }
        Ok(())
    }
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    schema_version: String,
    request_id: String,
    agent_id: String,
    action: String,
    target: String,
    parameters: Parameters,
    issued_at: String,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Parameters {
    #[serde(default)]
    state: Option<String>,
    #[serde(default)]
    value: Option<i64>,
}
impl Request {
    fn valid_action(&self) -> bool {
        match self.action.as_str() {
            "set_light_state" => {
                (1..=8).any(|n| self.target == format!("ESP-LIGHT-0{n}"))
                    && self.parameters.value.is_none()
                    && self.parameters.state.as_deref().is_some_and(|v| ["on", "off"].contains(&v))
            }
            "set_fan_speed" => self.target == "SERVER-ROOM-FANS"
                && self.parameters.state.is_none()
                && self.parameters.value.is_some_and(|v| (0..=100).contains(&v)),
            _ => false,
        }
    }
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Receipt {
    schema_version: String,
    action_id: String,
    request_id: String,
    status: String,
    review_state: String,
    execution_status: String,
    idempotent_replay: bool,
}
impl Receipt {
    fn validate(&self, request: &str, action_id: &str, intent: &str) -> Result<(), String> {
        if self.schema_version != "alice-review-receipt-v1"
            || self.action_id != action_id
            || self.request_id != request
            || self.status != "ACCEPTED"
            || self.review_state
                != if intent == "APPROVE_ONCE" {
                    "APPROVED"
                } else {
                    "REJECTED"
                }
            || !["NOT_EXECUTED", "COMPLETED", "FAILED", "UNKNOWN"]
                .contains(&self.execution_status.as_str())
            || (intent == "REJECT" && self.execution_status != "NOT_EXECUTED")
        {
            return Err("REVIEW_RECEIPT_INVALID_REFRESH_LEDGER".into());
        }
        Ok(())
    }
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Submission {
    schema_version: String,
    request_id: String,
    action_id: String,
    action: String,
    state: String,
    created_at: String,
    receipt: Option<Receipt>,
    error: Option<String>,
}

async fn exchange(path: &str, body: Option<Value>) -> Result<Value, String> {
    let (base, token) = crate::config::feed_config(
        &std::env::var("ALICE_FEED_URL").unwrap_or_default(),
        &std::env::var("ALICE_FEED_TOKEN").unwrap_or_default(),
    )?;
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(12))
        .redirect(reqwest::redirect::Policy::none())
        .no_proxy()
        .build()
        .map_err(|_| "REVIEW_CLIENT_UNAVAILABLE")?;
    let request = if let Some(body) = body {
        client
            .post(format!("{base}{path}"))
            .body(canonical(&body)?)
            .header("Content-Type", "application/json")
    } else {
        client.get(format!("{base}{path}"))
    };
    let mut response = request
        .bearer_auth(token)
        .send()
        .await
        .map_err(|_| "REVIEW_DELIVERY_UNCERTAIN_REFRESH_LEDGER")?;
    let status = response.status();
    let mut bytes = Vec::new();
    while let Some(chunk) = response
        .chunk()
        .await
        .map_err(|_| "REVIEW_DELIVERY_UNCERTAIN_REFRESH_LEDGER")?
    {
        if bytes.len() + chunk.len() > MAX_BYTES {
            return Err("REVIEW_RESPONSE_TOO_LARGE".into());
        }
        bytes.extend_from_slice(&chunk);
    }
    if !status.is_success() {
        return Err(format!("REVIEW_HTTP_{}_REFRESH_LEDGER", status.as_u16()));
    }
    parse(&bytes)
}
fn require_remote(s: &Inner) -> Result<(), String> {
    if s.config.mode != "remote" || s.config.biometric_mode != "arcface" {
        return Err("NATIVE_LIVE_REVIEW_REQUIRED".into());
    }
    Ok(())
}
fn session(s: &Inner) -> Result<(String, String), String> {
    require_remote(s)?;
    Ok((require_technician(s)?, s.biometrics.authority_epoch.clone()))
}
fn check_session(s: &Inner, expected: &(String, String)) -> Result<(), String> {
    if session(s)? != *expected {
        return Err("TECHNICIAN_SESSION_CHANGED".into());
    }
    Ok(())
}
async fn fetch_snapshot(request: &str) -> Result<Snapshot, String> {
    let v: Snapshot = serde_json::from_value(exchange(&format!("/review/{request}"), None).await?)
        .map_err(|_| "INVALID_RUNTIME_REVIEW")?;
    v.validate(request)?;
    Ok(v)
}
#[tauri::command]
pub async fn read_runtime_review(
    state: State<'_, AppState>,
    request_id: String,
) -> Result<Snapshot, String> {
    if !id(&request_id) {
        return Err("INVALID_REQUEST_ID".into());
    }
    let (expected, generation) = {
        let mut s = lock(&state)?;
        let expected = session(&s)?;
        s.runtime_review.read_generation = s.runtime_review.read_generation.wrapping_add(1);
        (expected, s.runtime_review.read_generation)
    };
    let result = fetch_snapshot(&request_id).await;
    let mut s = lock(&state)?;
    check_session(&s, &expected)?;
    if s.runtime_review.read_generation != generation {
        return Err("SUPERSEDED_REVIEW_READ".into());
    }
    match result {
        Ok(value) => {
            s.runtime_review.snapshot = Some(Cache {
                view: value.clone(),
                fetched: Instant::now(),
                technician: expected.0,
                epoch: expected.1,
            });
            Ok(value)
        }
        Err(e) => {
            s.runtime_review.snapshot = None;
            Err(e)
        }
    }
}
#[tauri::command]
pub fn runtime_review_status(state: State<AppState>) -> Result<Value, String> {
    let s = lock(&state)?;
    session(&s)?;
    Ok(match configured_signer() {
        Ok(_) => json!({"ready":true,"reason":"READY"}),
        Err(e) => json!({"ready":false,"reason":e}),
    })
}
pub(crate) fn prepare_signer(s: &Inner) -> Result<Signer, String> {
    session(s)?;
    configured_signer()
}
fn configured_signer() -> Result<Signer, String> {
    crate::config::feed_config(
        &std::env::var("ALICE_FEED_URL").unwrap_or_default(),
        &std::env::var("ALICE_FEED_TOKEN").unwrap_or_default(),
    )?;
    load_signer()
}
pub fn scope(s: &Inner, request: &str, decision: &str, intent: &str) -> Result<Value, String> {
    let (tech, epoch) = session(s)?;
    let cache = s
        .runtime_review
        .snapshot
        .as_ref()
        .ok_or("LOAD_RUNTIME_REVIEW_FIRST")?;
    let view = &cache.view;
    if cache.fetched.elapsed() > SNAPSHOT_LEASE
        || cache.technician != tech
        || cache.epoch != epoch
        || !view.eligible
        || view.request_id != request
        || view.decision_event_id != decision
        || !action(intent)
    {
        return Err("RUNTIME_REVIEW_STALE_OR_INELIGIBLE".into());
    }
    if read_submission(s, request)?.is_some() {
        return Err("REVIEW_ALREADY_SUBMITTED_RECONCILE_LEDGER".into());
    }
    Ok(json!({"runtime_review":view,"action":intent}))
}
pub fn eligible(s: &Inner, value: &Value) -> Result<(), String> {
    let snapshot: Snapshot = serde_json::from_value(value["runtime_review"].clone())
        .map_err(|_| "INVALID_RUNTIME_SCOPE")?;
    if scope(
        s,
        &snapshot.request_id,
        &snapshot.decision_event_id,
        value["action"].as_str().unwrap_or(""),
    )? != *value
    {
        return Err("RUNTIME_REVIEW_CHANGED".into());
    }
    Ok(())
}
pub fn grant(s: &Inner, scope: &Value) -> Result<Grant, String> {
    eligible(s, scope)?;
    let now = Utc::now();
    Ok(Grant {
        verification_id: uuid::Uuid::new_v4().to_string(),
        decision_id: scope["runtime_review"]["decision_event_id"]
            .as_str()
            .ok_or("INVALID_SCOPE")?
            .into(),
        request_id: scope["runtime_review"]["request_id"]
            .as_str()
            .ok_or("INVALID_SCOPE")?
            .into(),
        technician_id: require_technician(s)?,
        timestamp: now.to_rfc3339(),
        expires_at: (now + chrono::Duration::seconds(60)).to_rfc3339(),
        result: "PASS".into(),
        provider: "arcface".into(),
        similarity: None,
        threshold: None,
    })
}
fn load_signer() -> Result<Signer, String> {
    let console = std::env::var("ALICE_CONSOLE_ID").unwrap_or_default();
    let path =
        std::env::var("ALICE_REVIEW_KEY_FILE").map_err(|_| "CONSOLE_REVIEW_KEY_NOT_CONFIGURED")?;
    if !id(&console) {
        return Err("CONSOLE_ID_NOT_CONFIGURED".into());
    }
    use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
    let mut file = std::fs::OpenOptions::new()
        .read(true)
        .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
        .open(path)
        .map_err(|_| "CONSOLE_REVIEW_KEY_UNAVAILABLE")?;
    let metadata = file
        .metadata()
        .map_err(|_| "CONSOLE_REVIEW_KEY_UNAVAILABLE")?;
    if !metadata.is_file() || metadata.len() != 32 {
        return Err("INVALID_CONSOLE_REVIEW_KEY".into());
    }
    if metadata.mode() & 0o077 != 0 || metadata.uid() != unsafe { libc::geteuid() } {
        return Err("CONSOLE_REVIEW_KEY_MUST_BE_PRIVATE".into());
    }
    let mut seed = [0u8; 32];
    file.read_exact(&mut seed)
        .map_err(|_| "CONSOLE_REVIEW_KEY_UNAVAILABLE")?;
    let key = Ed25519KeyPair::from_seed_unchecked(&seed).map_err(|_| "INVALID_CONSOLE_REVIEW_KEY");
    seed.fill(0);
    Ok(Signer { console, key: key? })
}
fn signed_envelope(proof: Value, key: &Ed25519KeyPair) -> Result<Value, String> {
    let mut bytes = DOMAIN.to_vec();
    bytes.extend(canonical(&proof)?);
    let signature = base64::engine::general_purpose::STANDARD.encode(key.sign(&bytes).as_ref());
    Ok(json!({"proof":proof,"signature":signature}))
}
fn consume(s: &mut Inner, verification_id: &str) -> Result<(Value, Submission), String> {
    session(s)?;
    let attempt = s
        .biometrics
        .current
        .as_ref()
        .ok_or("FRESH_FACE_VERIFICATION_REQUIRED")?;
    crate::biometric_commands::eligible(s, attempt)?;
    let g = attempt
        .view
        .verification
        .as_ref()
        .ok_or("FRESH_FACE_VERIFICATION_REQUIRED")?;
    let issued = chrono::DateTime::parse_from_rfc3339(&g.timestamp)
        .map_err(|_| "INVALID_GRANT")?
        .timestamp();
    let expires = chrono::DateTime::parse_from_rfc3339(&g.expires_at)
        .map_err(|_| "INVALID_GRANT")?
        .timestamp();
    let now = Utc::now().timestamp();
    if attempt.view.purpose != crate::biometric_sessions::Purpose::Approval
        || attempt.view.state != "SUCCEEDED"
        || attempt.authority_consumed
        || attempt.authority_revoked
        || g.verification_id != verification_id
        || g.provider != "arcface"
        || g.result != "PASS"
        || g.technician_id != attempt.technician_id
        || attempt.authority_epoch != s.biometrics.authority_epoch
        || issued > now
        || issued < now - 60
        || expires <= now
        || expires > issued + 60
    {
        return Err("FRESH_FACE_VERIFICATION_REQUIRED".into());
    }
    crate::biometric_sessions::validate_controls(&attempt.view.controls)?;
    let scope = attempt.scope.as_ref().ok_or("MISSING_SCOPE")?;
    eligible(s, scope)?;
    if g.decision_id != scope["runtime_review"]["decision_event_id"]
        || g.request_id != scope["runtime_review"]["request_id"]
    {
        return Err("GRANT_SCOPE_MISMATCH".into());
    }
    let signer = s
        .runtime_review
        .signer
        .as_ref()
        .ok_or("CONSOLE_REVIEW_KEY_NOT_CONFIGURED")?;
    let mut proof = json!({"schema_version":"alice-review-action-v1","console_id":signer.console,"technician_id":g.technician_id,"action_id":g.verification_id,"action":scope["action"],"biometric_session_id":attempt.view.session_id,"biometric_policy":crate::biometric_sessions::POLICY,"issued_at":issued,"expires_at":expires});
    for field in [
        "request_id",
        "request_sha256",
        "decision_event_id",
        "decision_event_hash",
        "release_sha256",
        "authority_interval_ref",
        "runtime_epoch",
        "review_nonce",
    ] {
        proof[field] = scope["runtime_review"][field].clone();
    }
    let envelope = signed_envelope(proof, &signer.key)?;
    let submission = Submission {
        schema_version: "alice-native-review-submission-v1".into(),
        request_id: g.request_id.clone(),
        action_id: g.verification_id.clone(),
        action: scope["action"].as_str().ok_or("INVALID_ACTION")?.into(),
        state: "PENDING".into(),
        created_at: Utc::now().to_rfc3339(),
        receipt: None,
        error: None,
    };
    // Durably save exact action identity before proof consumption or network I/O.
    s.db.execute("INSERT INTO runtime_review_submissions(action_id,request_id,technician_id,payload,envelope) VALUES(?1,?2,?3,?4,?5)",params![submission.action_id,submission.request_id,g.technician_id,serde_json::to_string(&submission).map_err(|_|"INVALID_SUBMISSION")?,envelope.to_string()]).map_err(|_|"REVIEW_SUBMISSION_PRESERVATION_FAILED")?;
    s.biometrics
        .current
        .as_mut()
        .ok_or("SESSION_MISSING")?
        .authority_consumed = true;
    Ok((envelope, submission))
}
fn read_submission(s: &Inner, request: &str) -> Result<Option<Submission>, String> {
    let raw: Option<String> =
        s.db.query_row(
            "SELECT payload FROM runtime_review_submissions WHERE request_id=?1",
            [request],
            |r| r.get(0),
        )
        .optional()
        .map_err(|_| "REVIEW_SUBMISSION_STORAGE_UNAVAILABLE")?;
    raw.map(|v| serde_json::from_str(&v).map_err(|_| "INVALID_SAVED_SUBMISSION".into()))
        .transpose()
}
fn submission_binding(s: &Inner, saved: &Submission, view: &Snapshot) -> Result<(), String> {
    let raw: String =
        s.db.query_row(
            "SELECT envelope FROM runtime_review_submissions WHERE action_id=?1 AND request_id=?2",
            params![saved.action_id, saved.request_id],
            |r| r.get(0),
        )
        .map_err(|_| "REVIEW_SUBMISSION_BINDING_CONFLICT")?;
    let envelope = parse(raw.as_bytes())?;
    let proof = &envelope["proof"];
    let expected = serde_json::to_value(view).map_err(|_| "INVALID_RUNTIME_REVIEW")?;
    // The event hash commits the original policy, permission release, authority,
    // and exact request. Runtime epoch/nonce intentionally change after restart.
    if [
        "request_id",
        "request_sha256",
        "decision_event_id",
        "decision_event_hash",
    ]
    .iter()
    .any(|field| proof[*field] != expected[*field])
        || proof["action_id"] != saved.action_id
        || proof["action"] != saved.action
    {
        return Err("REVIEW_SUBMISSION_BINDING_CONFLICT".into());
    }
    let confirmed = view.accepted_action_id.as_ref() == Some(&saved.action_id)
        && view.accepted_action.as_ref() == Some(&saved.action);
    if !confirmed
        && (["release_sha256", "authority_interval_ref"]
            .iter()
            .any(|field| proof[*field] != expected[*field])
            || (view.accepted_action_id.is_some()
                && view.accepted_action_id.as_ref() != Some(&saved.action_id)))
    {
        return Err("REVIEW_SUBMISSION_BINDING_CONFLICT".into());
    }
    if saved.receipt.is_some() && !confirmed {
        return Err("REVIEW_SUBMISSION_CURRENTNESS_UNCONFIRMED".into());
    }
    Ok(())
}
fn unconfirmed(mut saved: Submission, reason: &str) -> Submission {
    // Preserve the original durable record, but never attribute it to another
    // runtime's reused request ID or present a stale receipt as current evidence.
    saved.state = "UNCERTAIN".into();
    saved.receipt = None;
    saved.error = Some(reason.into());
    saved
}
fn save_submission(s: &Inner, v: &mut Submission) -> Result<(), String> {
    if let Some(saved) = read_submission(s, &v.request_id)? {
        if saved.action_id != v.action_id || saved.action != v.action {
            return Err("REVIEW_SUBMISSION_CONFLICT".into());
        }
        // Concurrent GET and POST responses may arrive out of order. Never
        // downgrade accepted or terminal execution evidence to uncertainty.
        let terminal = saved
            .receipt
            .as_ref()
            .is_some_and(|r| ["COMPLETED", "FAILED"].contains(&r.execution_status.as_str()));
        if saved.state == "ACCEPTED" && (v.state != "ACCEPTED" || terminal) {
            *v = saved;
        }
    }
    let changed =
        s.db.execute(
            "UPDATE runtime_review_submissions SET payload=?1 WHERE action_id=?2 AND request_id=?3",
            params![
                serde_json::to_string(v).map_err(|_| "INVALID_SUBMISSION")?,
                v.action_id,
                v.request_id
            ],
        )
        .map_err(|_| "REVIEW_RECEIPT_PRESERVATION_FAILED_REFRESH_LEDGER")?;
    if changed != 1 {
        return Err("REVIEW_SUBMISSION_MISSING".into());
    }
    Ok(())
}
#[tauri::command]
pub async fn read_runtime_submission(
    state: State<'_, AppState>,
    request_id: String,
) -> Result<Option<Submission>, String> {
    if !id(&request_id) {
        return Err("INVALID_REQUEST_ID".into());
    }
    let (saved, expected) = {
        let s = lock(&state)?;
        (read_submission(&s, &request_id)?, session(&s)?)
    };
    let Some(saved) = saved else { return Ok(None) };
    let result = fetch_snapshot(&request_id).await;
    let s = lock(&state)?;
    check_session(&s, &expected)?;
    Ok(Some(match result {
        Ok(view) => match submission_binding(&s, &saved, &view) {
            Ok(()) => saved,
            Err(reason) => unconfirmed(saved, &reason),
        },
        Err(_) => unconfirmed(saved, "REVIEW_SUBMISSION_CURRENTNESS_UNCONFIRMED"),
    }))
}
#[tauri::command]
pub async fn submit_runtime_review(
    state: State<'_, AppState>,
    verification_id: String,
) -> Result<Receipt, String> {
    let (envelope, mut submission, expected) = {
        let mut s = lock(&state)?;
        let expected = session(&s)?;
        let (e, v) = consume(&mut s, &verification_id)?;
        (e, v, expected)
    };
    let result = async {
        let receipt: Receipt = serde_json::from_value(exchange("/review", Some(envelope)).await?)
            .map_err(|_| "INVALID_REVIEW_RECEIPT")?;
        receipt.validate(
            &submission.request_id,
            &submission.action_id,
            &submission.action,
        )?;
        Ok::<_, String>(receipt)
    }
    .await;
    match &result {
        Ok(receipt) => {
            submission.state = "ACCEPTED".into();
            submission.receipt = Some(receipt.clone());
            submission.error = None;
        }
        Err(e) => {
            submission.state = "UNCERTAIN".into();
            submission.error = Some(e.clone());
        }
    }
    let s = lock(&state)?;
    // Preserve an acknowledgment even if logout/navigation happened in flight.
    save_submission(&s, &mut submission)?;
    check_session(&s, &expected)?;
    match submission.receipt {
        Some(receipt) => Ok(receipt),
        None => result,
    }
}
#[tauri::command]
pub async fn reconcile_runtime_submission(
    state: State<'_, AppState>,
    request_id: String,
) -> Result<Submission, String> {
    if !id(&request_id) {
        return Err("INVALID_REQUEST_ID".into());
    }
    let (mut submission, expected) = {
        let s = lock(&state)?;
        (
            read_submission(&s, &request_id)?.ok_or("NO_RUNTIME_SUBMISSION")?,
            session(&s)?,
        )
    };
    let result = fetch_snapshot(&request_id).await;
    let s = lock(&state)?;
    check_session(&s, &expected)?;
    match &result {
        Ok(view) => {
            if let Err(reason) = submission_binding(&s, &submission, view) {
                return Ok(unconfirmed(submission, &reason));
            }
        }
        Err(_) => {
            return Ok(unconfirmed(
                submission,
                "REVIEW_SUBMISSION_CURRENTNESS_UNCONFIRMED",
            ))
        }
    }
    match result {
        Ok(v)
            if v.accepted_action_id.as_ref() == Some(&submission.action_id)
                && v.accepted_action.as_ref() == Some(&submission.action) =>
        {
            let receipt = Receipt {
                schema_version: "alice-review-receipt-v1".into(),
                action_id: submission.action_id.clone(),
                request_id: submission.request_id.clone(),
                status: "ACCEPTED".into(),
                review_state: v.review_state,
                execution_status: v.execution_status,
                idempotent_replay: true,
            };
            receipt.validate(
                &submission.request_id,
                &submission.action_id,
                &submission.action,
            )?;
            submission.state = "ACCEPTED".into();
            submission.receipt = Some(receipt);
            submission.error = None;
        }
        Ok(_) => {
            if submission.state != "ACCEPTED" {
                submission.state = "UNCERTAIN".into();
                submission.error = Some("ACTION_NOT_CONFIRMED_NO_AUTOMATIC_RETRY".into());
            }
        }
        Err(e) => {
            if submission.state != "ACCEPTED" {
                submission.state = "UNCERTAIN".into();
                submission.error = Some(e);
            }
        }
    }
    // A parallel POST may have received acceptance while this GET was in flight.
    if let Some(saved) = read_submission(&s, &request_id)? {
        if saved.state == "ACCEPTED" && submission.state != "ACCEPTED" {
            return Ok(saved);
        }
    }
    save_submission(&s, &mut submission)?;
    Ok(submission)
}

#[cfg(test)]
mod tests;
