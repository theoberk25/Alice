use crate::config::Config;
use argon2::{
    password_hash::{PasswordHasher, SaltString},
    Argon2,
};
use rand_core::OsRng;
use rusqlite::{params, Connection};
use std::{fs, os::unix::fs::PermissionsExt};
pub fn open(config: &Config) -> Result<Connection, String> {
    if let Some(parent) = config.database.parent() {
        let existed = parent.exists();
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        if !existed {
            fs::set_permissions(parent, fs::Permissions::from_mode(0o700))
                .map_err(|e| e.to_string())?;
        }
    }
    let conn = Connection::open(&config.database).map_err(|e| e.to_string())?;
    fs::set_permissions(&config.database, fs::Permissions::from_mode(0o600))
        .map_err(|e| e.to_string())?;
    conn.execute_batch("PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL;
      CREATE TABLE IF NOT EXISTS admin_accounts(username TEXT PRIMARY KEY,password_hash TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS technicians(technician_id TEXT PRIMARY KEY,username TEXT UNIQUE NOT NULL,display_name TEXT NOT NULL,role TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 1);
      CREATE TABLE IF NOT EXISTS face_enrollments(technician_id TEXT PRIMARY KEY REFERENCES technicians(technician_id),updated_at TEXT NOT NULL,provider TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS decision_cache(decision_id TEXT PRIMARY KEY,request_id TEXT NOT NULL,payload TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS decision_annotations(event_key TEXT PRIMARY KEY,payload TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS technician_actions(action_id TEXT PRIMARY KEY,decision_id TEXT NOT NULL,payload TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS local_audit_events(id TEXT PRIMARY KEY,timestamp TEXT NOT NULL,event_type TEXT NOT NULL,payload TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);").map_err(|e|e.to_string())?;
    let count: i64 = conn
        .query_row("SELECT COUNT(*) FROM admin_accounts", [], |r| r.get(0))
        .map_err(|e| e.to_string())?;
    if count == 0 {
        if let (Ok(username), Ok(password)) = (
            std::env::var("ALICE_ADMIN_USERNAME"),
            std::env::var("ALICE_ADMIN_PASSWORD"),
        ) {
            if !username.is_empty() && !password.is_empty() {
                if password.len() < 12 {
                    return Err(
                        "Bootstrap admin password must contain at least 12 characters".into(),
                    );
                }
                let hash = Argon2::default()
                    .hash_password(password.as_bytes(), &SaltString::generate(&mut OsRng))
                    .map_err(|e| e.to_string())?
                    .to_string();
                conn.execute(
                    "INSERT INTO admin_accounts(username,password_hash) VALUES(?1,?2)",
                    params![username, hash],
                )
                .map_err(|e| e.to_string())?;
            }
        }
    }
    // Avoid retaining bootstrap credentials in the running process environment.
    std::env::remove_var("ALICE_ADMIN_PASSWORD");
    Ok(conn)
}
pub fn audit(
    conn: &Connection,
    event_type: &str,
    payload: &serde_json::Value,
) -> Result<(), String> {
    conn.execute(
        "INSERT INTO local_audit_events(id,timestamp,event_type,payload) VALUES(?1,?2,?3,?4)",
        params![
            uuid::Uuid::new_v4().to_string(),
            chrono::Utc::now().to_rfc3339(),
            event_type,
            payload.to_string()
        ],
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}
