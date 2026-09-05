use crate::Inner;
use chrono::Utc;
use serde::{Deserialize, Serialize};
use serde_json::Value;
#[derive(Clone)]
pub struct Session {
    pub id: String,
    pub expires_at: i64,
}
#[derive(Clone, Serialize)]
pub struct Grant {
    pub verification_id: String,
    pub decision_id: String,
    pub request_id: String,
    pub technician_id: String,
    pub timestamp: String,
    pub expires_at: String,
    pub result: String,
    pub provider: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub similarity: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub threshold: Option<f64>,
}
#[derive(Serialize, Deserialize, Clone)]
pub struct Technician {
    pub technician_id: String,
    pub username: String,
    pub display_name: String,
    pub role: String,
    pub enabled: bool,
    pub enrolled: bool,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Action {
    pub schema_version: String,
    pub event_type: String,
    pub action_id: String,
    pub timestamp: String,
    pub decision_id: String,
    pub request_id: String,
    pub technician_id: String,
    pub action: String,
    pub biometric_verification_id: Option<String>,
    pub note: String,
    pub mode: String,
}
pub fn require_admin(s: &Inner) -> Result<(), String> {
    if s.admin
        .as_ref()
        .is_some_and(|a| a.expires_at > Utc::now().timestamp())
    {
        Ok(())
    } else {
        Err("Administrator authentication required".into())
    }
}
pub fn require_technician(s: &Inner) -> Result<String, String> {
    let session = s
        .technician
        .as_ref()
        .filter(|t| t.expires_at > Utc::now().timestamp())
        .ok_or("Technician authentication required")?;
    if s.config.mode == "mock" && s.config.biometric_mode == "mock" && session.id == "TECH-DEMO" {
        return Ok(session.id.clone());
    }
    let enabled =
        s.db.query_row(
            "SELECT enabled FROM technicians WHERE technician_id=?1",
            [&session.id],
            |r| r.get::<_, bool>(0),
        )
        .unwrap_or(false);
    if !enabled {
        return Err("Technician is disabled".into());
    }
    Ok(session.id.clone())
}
pub fn validate_action(
    d: &Value,
    a: &Action,
    technician: &str,
    grant: Option<&Grant>,
    mode: &str,
    now: i64,
) -> Result<(), String> {
    if a.schema_version != "1.0"
        || a.event_type != "alice.technician_action"
        || a.mode != mode
        || a.action_id.is_empty()
        || a.note.len() > 2000
    {
        return Err("Invalid technician action envelope".into());
    }
    if a.technician_id != technician {
        return Err("Technician identity mismatch".into());
    }
    if d["decision_id"].as_str() != Some(&a.decision_id)
        || d["request"]["request_id"].as_str() != Some(&a.request_id)
    {
        return Err("Action is bound to a different request".into());
    }
    if d["decision"]["result"] != "HOLD" || d["policy"]["result"] == "DENY" {
        return Err("Upstream policy cannot be overridden".into());
    }
    if !["APPROVE_ONCE", "HOLD", "RESEARCH", "REJECT"].contains(&a.action.as_str()) {
        return Err("Unsupported action".into());
    }
    let capability = if a.action == "APPROVE_ONCE" {
        "APPROVE"
    } else {
        &a.action
    };
    if !d["technician_actions"]["available"]
        .as_array()
        .is_some_and(|v| v.iter().any(|x| x == capability))
    {
        return Err("Action is not available in the upstream contract".into());
    }
    if a.action == "APPROVE_ONCE" && d["decision"]["biometric_required_for_approval"] != false {
        let g = grant.ok_or("Fresh backend-issued verification required")?;
        let issued = chrono::DateTime::parse_from_rfc3339(&g.timestamp)
            .map_err(|_| "Invalid verification timestamp")?
            .timestamp();
        let expiry = chrono::DateTime::parse_from_rfc3339(&g.expires_at)
            .map_err(|_| "Invalid verification expiry")?
            .timestamp();
        if g.result != "PASS"
            || g.decision_id != a.decision_id
            || g.request_id != a.request_id
            || g.technician_id != technician
            || issued > now
            || now - issued > 60
            || expiry <= now
            || (mode == "remote" && g.provider != "arcface")
        {
            return Err("Verification failed, expired, or does not belong to this request".into());
        }
    }
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    fn action() -> Action {
        Action {
            schema_version: "1.0".into(),
            event_type: "alice.technician_action".into(),
            action_id: "A1".into(),
            timestamp: Utc::now().to_rfc3339(),
            decision_id: "D1".into(),
            request_id: "R1".into(),
            technician_id: "T1".into(),
            action: "APPROVE_ONCE".into(),
            biometric_verification_id: None,
            note: String::new(),
            mode: "mock".into(),
        }
    }
    fn decision() -> Value {
        json!({"decision_id":"D1","request":{"request_id":"R1"},"decision":{"result":"HOLD","biometric_required_for_approval":true},"policy":{"result":"REVIEW"},"technician_actions":{"available":["APPROVE","HOLD","REJECT","RESEARCH"]}})
    }
    fn grant() -> Grant {
        Grant {
            verification_id: "V1".into(),
            decision_id: "D1".into(),
            request_id: "R1".into(),
            technician_id: "T1".into(),
            timestamp: Utc::now().to_rfc3339(),
            expires_at: (Utc::now() + chrono::Duration::seconds(60)).to_rfc3339(),
            result: "PASS".into(),
            provider: "mock".into(),
            similarity: None,
            threshold: None,
        }
    }
    #[test]
    fn missing_proof_fails() {
        assert!(validate_action(
            &decision(),
            &action(),
            "T1",
            None,
            "mock",
            Utc::now().timestamp()
        )
        .is_err());
    }
    #[test]
    fn policy_deny_never_overridden() {
        let mut d = decision();
        d["policy"]["result"] = json!("DENY");
        assert!(validate_action(
            &d,
            &action(),
            "T1",
            Some(&grant()),
            "mock",
            Utc::now().timestamp()
        )
        .is_err());
    }
    #[test]
    fn exact_fresh_proof_passes() {
        assert!(validate_action(
            &decision(),
            &action(),
            "T1",
            Some(&grant()),
            "mock",
            Utc::now().timestamp()
        )
        .is_ok());
    }
    #[test]
    fn cross_request_and_expired_proofs_fail() {
        let mut g = grant();
        g.request_id = "R2".into();
        assert!(validate_action(
            &decision(),
            &action(),
            "T1",
            Some(&g),
            "mock",
            Utc::now().timestamp()
        )
        .is_err());
        let g = grant();
        assert!(validate_action(
            &decision(),
            &action(),
            "T1",
            Some(&g),
            "mock",
            Utc::now().timestamp() + 61
        )
        .is_err());
    }
    #[test]
    fn mock_proof_cannot_reach_remote() {
        let mut a = action();
        a.mode = "remote".into();
        assert!(validate_action(
            &decision(),
            &a,
            "T1",
            Some(&grant()),
            "remote",
            Utc::now().timestamp()
        )
        .is_err());
    }
    #[test]
    fn face_login_is_not_step_up() {
        assert!(validate_action(
            &decision(),
            &action(),
            "T1",
            None,
            "mock",
            Utc::now().timestamp()
        )
        .is_err());
    }
    #[test]
    fn hold_does_not_require_face() {
        let mut a = action();
        a.action = "HOLD".into();
        assert!(
            validate_action(&decision(), &a, "T1", None, "mock", Utc::now().timestamp()).is_ok()
        );
    }
}
