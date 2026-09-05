mod commands;
#[cfg(test)]
mod commands_tests;
mod config;
mod db;
mod security;
use config::Config;
use rusqlite::Connection;
use security::{Grant, Session};
use std::{collections::HashMap, sync::Mutex};
use tauri::Manager;
pub struct Inner {
    pub db: Connection,
    pub config: Config,
    pub technician: Option<Session>,
    pub admin: Option<Session>,
    pub grants: HashMap<String, Grant>,
    pub failures: HashMap<String, (u32, i64)>,
}
pub struct AppState(pub Mutex<Inner>);
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let mut config =
                Config::load(app.path().app_data_dir()?).map_err(std::io::Error::other)?;
            if config.mode == "mock"
                && std::env::var("ALICE_DATABASE_PATH")
                    .unwrap_or_default()
                    .is_empty()
            {
                config.database.set_file_name("console-mock.sqlite3");
            }
            let db = db::open(&config).map_err(std::io::Error::other)?;
            if config.model.is_empty() {
                config.model = db
                    .query_row(
                        "SELECT value FROM settings WHERE key='llm_model'",
                        [],
                        |r| r.get(0),
                    )
                    .unwrap_or_default();
            }
            app.manage(AppState(Mutex::new(Inner {
                db,
                config,
                technician: None,
                admin: None,
                grants: HashMap::new(),
                failures: HashMap::new(),
            })));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::runtime_config,
            commands::demo_session,
            commands::admin_login,
            commands::admin_logout,
            commands::logout,
            commands::list_technicians,
            commands::save_technician,
            commands::set_technician_enabled,
            commands::remove_enrollment,
            commands::enroll_technician,
            commands::technician_login,
            commands::cache_decision,
            commands::cache_annotation,
            commands::reset_mock_scenario,
            commands::append_audit,
            commands::read_console_history,
            commands::mock_verify,
            commands::verify_face,
            commands::submit_action,
            commands::llm_health,
            commands::configure_llm,
            commands::llm_generate,
            commands::biometric_health
        ])
        .run(tauri::generate_context!())
        .expect("ALICE application failed to start");
}
