mod biometric_capture;
mod biometric_commands;
mod biometric_sessions;
mod commands;
#[cfg(test)]
mod commands_tests;
mod config;
mod db;
mod runtime_review;
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
    pub runtime_review: runtime_review::Book,
    pub biometrics: biometric_sessions::Book,
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
                runtime_review: runtime_review::Book::default(),
                biometrics: biometric_sessions::Book::default(),
            })));
            Ok(())
        })
        .on_window_event(|window, event| {
            if matches!(
                event,
                tauri::WindowEvent::Destroyed | tauri::WindowEvent::CloseRequested { .. }
            ) {
                if let Some(state) = window.try_state::<AppState>() {
                    if let Ok(mut s) = state.0.lock() {
                        s.biometrics.revoke("WINDOW_CLOSED");
                    }
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            biometric_commands::begin_biometric_session,
            biometric_commands::read_biometric_session,
            biometric_commands::read_biometric_preview,
            biometric_commands::cancel_biometric_session,
            biometric_commands::recover_face_enrollment,
            commands::runtime_config,
            commands::read_runtime_events,
            commands::read_runtime_plant,
            runtime_review::read_runtime_review,
            runtime_review::submit_runtime_review,
            runtime_review::read_runtime_submission,
            runtime_review::reconcile_runtime_submission,
            runtime_review::runtime_review_status,
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
