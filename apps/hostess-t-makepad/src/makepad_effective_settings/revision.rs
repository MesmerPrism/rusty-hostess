use serde_json::Value;
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;

pub(super) const EFFECTIVE_SETTINGS_REVISION_FILE_NAME: &str =
    "makepad-effective-settings.revision.json";
pub(super) const EFFECTIVE_SETTINGS_REVISION_SCHEMA: &str =
    "rusty.gui.makepad.effective_settings_revision.v1";
pub(super) const EFFECTIVE_SETTINGS_RUNTIME_SCOPES: &[&str] = &[
    "mesh_replay",
    "camera_projection",
    "stimulus",
    "remote_camera",
    "matter_surface",
    "particles",
];
const EFFECTIVE_SETTINGS_GPU_PROOF_SCOPES: &[&str] = &["gpu_proof"];

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub(crate) struct MakepadEffectiveSettingsIdentity {
    pub(crate) source_effective_settings_path: Option<String>,
    pub(crate) source_modified_ns: Option<u128>,
    pub(crate) source_revision_key: Option<String>,
    pub(crate) scope_revision_keys: BTreeMap<String, String>,
    pub(crate) source_revision_manifest_path: Option<String>,
    pub(crate) source_revision_manifest_modified_ns: Option<u128>,
}

impl MakepadEffectiveSettingsIdentity {
    pub(crate) fn runtime_settings_revision_key(&self) -> Option<String> {
        self.scoped_revision_key(EFFECTIVE_SETTINGS_RUNTIME_SCOPES)
    }

    pub(crate) fn gpu_proof_settings_revision_key(&self) -> Option<String> {
        self.scoped_revision_key(EFFECTIVE_SETTINGS_GPU_PROOF_SCOPES)
    }

    pub(crate) fn gpu_proof_settings_changed_from(
        &self,
        previous_path: Option<&str>,
        previous_gpu_proof_revision_key: Option<&str>,
    ) -> bool {
        if self.source_effective_settings_path.as_deref() != previous_path {
            return false;
        }
        if let Some(gpu_proof_revision_key) =
            self.scoped_revision_key(EFFECTIVE_SETTINGS_GPU_PROOF_SCOPES)
        {
            return Some(gpu_proof_revision_key.as_str()) != previous_gpu_proof_revision_key;
        }
        false
    }

    pub(crate) fn runtime_settings_changed_from(
        &self,
        previous_path: Option<&str>,
        previous_modified_ns: Option<u128>,
        previous_runtime_revision_key: Option<&str>,
    ) -> bool {
        self.changed_from_scopes(
            previous_path,
            previous_modified_ns,
            previous_runtime_revision_key,
            EFFECTIVE_SETTINGS_RUNTIME_SCOPES,
        )
    }

    pub(crate) fn changed_from_scopes(
        &self,
        previous_path: Option<&str>,
        previous_modified_ns: Option<u128>,
        previous_scoped_revision_key: Option<&str>,
        scopes: &[&str],
    ) -> bool {
        if self.source_effective_settings_path.as_deref() != previous_path {
            return true;
        }
        if let Some(scoped_revision_key) = self.scoped_revision_key(scopes) {
            return Some(scoped_revision_key.as_str()) != previous_scoped_revision_key;
        }
        self.source_modified_ns != previous_modified_ns
    }

    pub(crate) fn scoped_revision_key(&self, scopes: &[&str]) -> Option<String> {
        let mut parts = Vec::new();
        for scope in scopes {
            if let Some(scope_revision_key) = self.scope_revision_keys.get(*scope) {
                parts.push(format!("{scope}={scope_revision_key}"));
            }
        }
        if parts.is_empty() {
            None
        } else {
            Some(parts.join("|"))
        }
    }
}

pub(crate) fn makepad_effective_settings_identity_from_path(
    path: &Path,
) -> MakepadEffectiveSettingsIdentity {
    let revision_identity = effective_settings_revision_identity_from_path(path);
    MakepadEffectiveSettingsIdentity {
        source_effective_settings_path: Some(path.display().to_string()),
        source_modified_ns: file_modified_ns(path),
        source_revision_key: revision_identity
            .as_ref()
            .map(|identity| identity.revision_key.clone()),
        scope_revision_keys: revision_identity
            .as_ref()
            .map(|identity| identity.scope_revision_keys.clone())
            .unwrap_or_default(),
        source_revision_manifest_path: revision_identity
            .as_ref()
            .map(|identity| identity.manifest_path.display().to_string()),
        source_revision_manifest_modified_ns: revision_identity
            .as_ref()
            .and_then(|identity| identity.manifest_modified_ns),
    }
}

pub(super) fn file_modified_ns(path: &Path) -> Option<u128> {
    std::fs::metadata(path)
        .ok()
        .and_then(|metadata| metadata.modified().ok())
        .and_then(|modified| modified.duration_since(UNIX_EPOCH).ok())
        .map(|duration| duration.as_nanos())
}

#[derive(Debug)]
struct EffectiveSettingsRevisionIdentity {
    revision_key: String,
    scope_revision_keys: BTreeMap<String, String>,
    manifest_path: PathBuf,
    manifest_modified_ns: Option<u128>,
}

fn effective_settings_revision_identity_from_path(
    effective_settings_path: &Path,
) -> Option<EffectiveSettingsRevisionIdentity> {
    let manifest_path =
        effective_settings_path.with_file_name(EFFECTIVE_SETTINGS_REVISION_FILE_NAME);
    let text = std::fs::read_to_string(&manifest_path).ok()?;
    let value = serde_json::from_str::<Value>(text.trim_start_matches('\u{feff}')).ok()?;
    if value.get("schema").and_then(Value::as_str) != Some(EFFECTIVE_SETTINGS_REVISION_SCHEMA) {
        return None;
    }

    let mut parts = Vec::new();
    if let Some(source_sha) = value.get("source_sha256").and_then(Value::as_str) {
        parts.push(format!("source_sha256={source_sha}"));
    }
    if let Some(source_revision) = json_scalar_token(value.get("source_revision")) {
        parts.push(format!("source_revision={source_revision}"));
    }
    if let Some(scopes) = value.get("scopes").and_then(Value::as_object) {
        for scope in EFFECTIVE_SETTINGS_RUNTIME_SCOPES {
            if let Some(scope_hash) = scopes
                .get(*scope)
                .and_then(|scope_value| scope_value.get("revision_hash_sha256"))
                .and_then(Value::as_str)
            {
                parts.push(format!("{scope}={scope_hash}"));
            }
        }
    }
    let scope_revision_keys = value
        .get("scopes")
        .and_then(Value::as_object)
        .map(|scopes| {
            scopes
                .iter()
                .filter_map(|(scope, scope_value)| {
                    scope_value
                        .get("revision_hash_sha256")
                        .and_then(Value::as_str)
                        .map(|scope_hash| (scope.clone(), scope_hash.to_string()))
                })
                .collect::<BTreeMap<_, _>>()
        })
        .unwrap_or_default();
    if parts.is_empty() {
        return None;
    }

    Some(EffectiveSettingsRevisionIdentity {
        revision_key: parts.join("|"),
        scope_revision_keys,
        manifest_modified_ns: file_modified_ns(&manifest_path),
        manifest_path,
    })
}

fn json_scalar_token(value: Option<&Value>) -> Option<String> {
    match value? {
        Value::String(value) => Some(value.clone()),
        Value::Number(value) => Some(value.to_string()),
        Value::Bool(value) => Some(value.to_string()),
        _ => None,
    }
}
