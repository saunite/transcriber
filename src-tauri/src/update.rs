//! Manual "Check for updates" (openspec/changes/add-manual-update-check).
//!
//! The only network request the app makes, and only when the user clicks the
//! button: one GET to GitHub's latest published release. The comparison is
//! a pure function so every outcome is testable without a network.

use serde::Serialize;
use std::time::Duration;
use tauri::AppHandle;
use tauri_plugin_opener::OpenerExt;

const REPO: &str = "saunite/transcriber";

/// What a check found, sent to the page as `{ "state": ..., "version": ... }`.
#[derive(Debug, PartialEq, Serialize)]
#[serde(tag = "state", content = "version", rename_all = "snake_case")]
pub enum UpdateStatus {
    UpToDate(String),
    Available(String),
    NoRelease,
    Unavailable,
}

/// Maps GitHub's answer to a verdict. Anything unexpected is `Unavailable`
/// rather than a guess: a wrong "up to date" would be worse than "couldn't check".
pub fn classify(current: &semver::Version, status: u16, body: &str) -> UpdateStatus {
    match status {
        200 => {}
        404 => return UpdateStatus::NoRelease,
        _ => return UpdateStatus::Unavailable,
    }
    let latest = serde_json::from_str::<serde_json::Value>(body)
        .ok()
        .and_then(|release| release.get("tag_name")?.as_str().map(str::to_owned))
        .and_then(|tag| semver::Version::parse(tag.strip_prefix('v').unwrap_or(&tag)).ok());
    match latest {
        Some(latest) if latest > *current => UpdateStatus::Available(latest.to_string()),
        Some(_) => UpdateStatus::UpToDate(current.to_string()),
        None => UpdateStatus::Unavailable,
    }
}

/// One GET to GitHub, returning the status and body whatever the status is.
fn fetch_latest(current: &semver::Version) -> Result<(u16, String), ureq::Error> {
    let agent: ureq::Agent = ureq::Agent::config_builder()
        .timeout_global(Some(Duration::from_secs(10)))
        .http_status_as_error(false)
        // The OS trust store, so a corporate proxy's installed CA is honoured
        // without ever disabling verification.
        .tls_config(
            ureq::tls::TlsConfig::builder()
                .root_certs(ureq::tls::RootCerts::PlatformVerifier)
                .build(),
        )
        .build()
        .into();
    let mut response = agent
        .get(&format!("https://api.github.com/repos/{REPO}/releases/latest"))
        .header("User-Agent", &format!("Transcriber/{current}"))
        .header("Accept", "application/vnd.github+json")
        .call()?;
    let status = response.status().as_u16();
    Ok((status, response.body_mut().read_to_string()?))
}

#[tauri::command]
pub async fn check_for_update(app: AppHandle) -> UpdateStatus {
    let current = app.package_info().version.clone();
    // Blocking I/O off the main thread, so the window never freezes on a slow network.
    tauri::async_runtime::spawn_blocking(move || match fetch_latest(&current) {
        Ok((status, body)) => classify(&current, status, &body),
        Err(_) => UpdateStatus::Unavailable,
    })
    .await
    .unwrap_or(UpdateStatus::Unavailable)
}

/// Opens the project's own releases page -- a fixed URL, never one taken from
/// the network or the page.
#[tauri::command]
pub fn open_releases_page(app: AppHandle) -> Result<(), String> {
    app.opener()
        .open_url(format!("https://github.com/{REPO}/releases/latest"), None::<&str>)
        .map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::{classify, UpdateStatus};

    /// A real GitHub `releases/latest` response's fields, with `tag_name` set to
    /// this project's `v<version>` form.
    const RELEASE: &str = include_str!("testdata/github-latest-release.json");

    fn v(s: &str) -> semver::Version {
        semver::Version::parse(s).unwrap()
    }

    fn with_tag(tag: &str) -> String {
        RELEASE.replace("\"v0.2.0\"", &format!("\"{tag}\""))
    }

    #[test]
    fn newer_release_is_available() {
        assert_eq!(classify(&v("0.1.0"), 200, RELEASE), UpdateStatus::Available("0.2.0".into()));
    }

    #[test]
    fn same_or_older_release_is_up_to_date() {
        assert_eq!(classify(&v("0.2.0"), 200, RELEASE), UpdateStatus::UpToDate("0.2.0".into()));
        assert_eq!(classify(&v("0.3.0"), 200, RELEASE), UpdateStatus::UpToDate("0.3.0".into()));
    }

    #[test]
    fn tag_without_v_prefix_still_parses() {
        assert_eq!(
            classify(&v("0.1.0"), 200, &with_tag("0.2.0")),
            UpdateStatus::Available("0.2.0".into())
        );
    }

    #[test]
    fn no_published_release_is_404() {
        let body = r#"{"message":"Not Found","status":"404"}"#;
        assert_eq!(classify(&v("0.1.0"), 404, body), UpdateStatus::NoRelease);
    }

    #[test]
    fn other_statuses_are_unavailable() {
        assert_eq!(classify(&v("0.1.0"), 403, "{}"), UpdateStatus::Unavailable);
        assert_eq!(classify(&v("0.1.0"), 500, ""), UpdateStatus::Unavailable);
    }

    #[test]
    fn unusable_bodies_are_unavailable() {
        assert_eq!(classify(&v("0.1.0"), 200, r#"{"name":"x"}"#), UpdateStatus::Unavailable);
        assert_eq!(classify(&v("0.1.0"), 200, &with_tag("nightly")), UpdateStatus::Unavailable);
        assert_eq!(classify(&v("0.1.0"), 200, "not json"), UpdateStatus::Unavailable);
    }

    /// The only test that touches the network, so it never runs by default:
    /// `cargo test -- --ignored live_github`. Proves TLS through the OS trust
    /// store and GitHub's API answer end to end.
    #[test]
    #[ignore]
    fn live_github_request_completes() {
        let (status, body) = super::fetch_latest(&v("0.1.0")).expect("transport or TLS failure");
        assert!(status == 200 || status == 404, "unexpected status {status}: {body}");
        assert_ne!(classify(&v("0.1.0"), status, &body), UpdateStatus::Unavailable, "{status}: {body}");
    }

    #[test]
    fn serializes_for_the_page() {
        let json = serde_json::to_string(&UpdateStatus::Available("0.2.0".into())).unwrap();
        assert_eq!(json, r#"{"state":"available","version":"0.2.0"}"#);
        assert_eq!(serde_json::to_string(&UpdateStatus::NoRelease).unwrap(), r#"{"state":"no_release"}"#);
    }
}
