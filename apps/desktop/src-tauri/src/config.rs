use serde::Serialize;
use std::{env, path::PathBuf};
#[derive(Clone)]
pub struct Config {
    pub mode: String,
    pub biometric_mode: String,
    pub model: String,
    pub ollama_url: String,
    pub biometric_url: String,
    pub biometric_token: String,
    pub database: PathBuf,
}
#[derive(Serialize)]
pub struct PublicConfig {
    pub transport_mode: String,
    pub biometric_mode: String,
    pub llm_model: String,
    pub ollama_url: String,
    pub biometric_url: String,
    pub admin_configured: bool,
}
pub fn loopback_url(value: &str) -> Result<String, String> {
    let u = url::Url::parse(value).map_err(|_| "Invalid local service URL")?;
    if u.scheme() != "http"
        || !matches!(
            u.host_str(),
            Some("127.0.0.1") | Some("localhost") | Some("[::1]")
        )
        || !u.username().is_empty()
        || u.password().is_some()
    {
        return Err("Local service URLs must use HTTP on loopback without credentials".into());
    }
    Ok(value.trim_end_matches('/').to_owned())
}
impl Config {
    pub fn load(data_dir: PathBuf) -> Result<Self, String> {
        let mode = env::var("ALICE_TRANSPORT_MODE").unwrap_or_else(|_| "remote".into());
        if !["mock", "remote"].contains(&mode.as_str()) {
            return Err("ALICE_TRANSPORT_MODE must be mock or remote".into());
        }
        let biometric_mode = env::var("ALICE_BIOMETRIC_MODE").unwrap_or_else(|_| {
            if mode == "mock" {
                "mock".into()
            } else {
                "arcface".into()
            }
        });
        if !["mock", "arcface"].contains(&biometric_mode.as_str())
            || (mode == "remote" && biometric_mode == "mock")
        {
            return Err("Biometric mode must be arcface for remote transport".into());
        }
        Ok(Self {
            mode,
            biometric_mode,
            model: env::var("ALICE_LLM_MODEL").unwrap_or_default(),
            ollama_url: loopback_url(
                &env::var("OLLAMA_BASE_URL").unwrap_or_else(|_| "http://127.0.0.1:11434".into()),
            )?,
            biometric_url: loopback_url(
                &env::var("ALICE_BIOMETRIC_SERVICE_URL")
                    .unwrap_or_else(|_| "http://127.0.0.1:8765".into()),
            )?,
            biometric_token: env::var("ALICE_BIOMETRIC_TOKEN").unwrap_or_default(),
            database: env::var("ALICE_DATABASE_PATH")
                .ok()
                .filter(|s| !s.is_empty())
                .map(PathBuf::from)
                .unwrap_or_else(|| data_dir.join("console.sqlite3")),
        })
    }
}

pub fn feed_config(url: &str, token: &str) -> Result<(String, String), String> {
    let base = loopback_url(url)?;
    let parsed = url::Url::parse(&base).map_err(|_| "Invalid feed URL")?;
    if parsed.path() != "/" || parsed.query().is_some() || parsed.fragment().is_some()
        || parsed.port().is_none() || parsed.host_str() == Some("localhost")
        || token.len() < 32 || !token.bytes().all(|b| b.is_ascii_graphic())
    {
        return Err("Configure an explicit loopback ALICE_FEED_URL and private ALICE_FEED_TOKEN".into());
    }
    Ok((base, token.to_owned()))
}

#[cfg(test)]
mod feed_tests {
    use super::feed_config;
    #[test]
    fn feed_boundary_rejects_remote_hosts_paths_and_weak_secrets() {
        for url in ["http://192.168.1.2:8787", "http://127.0.0.1:8787/request", "http://user@127.0.0.1:8787", "https://127.0.0.1:8787"] {
            assert!(feed_config(url, &"x".repeat(32)).is_err());
        }
        assert!(feed_config("http://127.0.0.1:8787", "").is_err());
        assert!(feed_config("http://127.0.0.1:8787", &"x".repeat(32)).is_ok());
    }
}
