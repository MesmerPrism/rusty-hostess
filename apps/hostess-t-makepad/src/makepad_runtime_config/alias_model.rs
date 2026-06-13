//! Runtime-key alias evidence model.
//!
//! Legacy and deprecated alias metadata lives here so the generic runtime-config
//! facade does not carry retired compatibility terms in its core type section.

use super::{RuntimeConfig, RuntimeConfigError, RuntimeKey, RuntimeValue};

/// Source spelling accepted for a runtime-key alias.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RuntimeKeyAliasSource {
    Canonical,
    LaunchExtra,
    AndroidProperty,
    EnvironmentVariable,
    LegacyRuntimeKey,
}

/// Compatibility status for a runtime-key alias.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RuntimeKeyAliasStatus {
    Canonical,
    Current,
    Legacy,
    Deprecated,
}

/// Value transformation needed when an alias has different historical
/// semantics than its canonical key.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RuntimeKeyAliasValueTransform {
    Identity,
    NegateNumber,
}

impl RuntimeKeyAliasValueTransform {
    pub(super) fn apply(
        self,
        alias: &str,
        raw_value: &str,
        value: RuntimeValue,
    ) -> Result<RuntimeValue, RuntimeConfigError> {
        match self {
            Self::Identity => Ok(value),
            Self::NegateNumber => match value {
                RuntimeValue::Integer(value) => value
                    .checked_neg()
                    .map(RuntimeValue::Integer)
                    .ok_or_else(|| RuntimeConfigError::InvalidAliasValue {
                        alias: alias.to_string(),
                        value: raw_value.to_string(),
                    }),
                RuntimeValue::Float(value) => Ok(RuntimeValue::Float(-value)),
                RuntimeValue::Bool(_) | RuntimeValue::Text(_) => {
                    Err(RuntimeConfigError::InvalidAliasValue {
                        alias: alias.to_string(),
                        value: raw_value.to_string(),
                    })
                }
            },
        }
    }
}

/// Exact alias accepted for a canonical runtime key.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RuntimeKeyAlias {
    pub alias: &'static str,
    pub canonical_key: &'static str,
    pub source: RuntimeKeyAliasSource,
    pub status: RuntimeKeyAliasStatus,
    pub value_transform: RuntimeKeyAliasValueTransform,
}

impl RuntimeKeyAlias {
    pub fn canonical_runtime_key(&self) -> RuntimeKey {
        RuntimeKey::new(self.canonical_key).expect("registered aliases should target valid keys")
    }
}

/// Alias evidence recorded when an input key is canonicalized.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RuntimeKeyAliasRecord {
    pub input_key: String,
    pub canonical_key: RuntimeKey,
    pub source: RuntimeKeyAliasSource,
    pub status: RuntimeKeyAliasStatus,
    pub value_transform: RuntimeKeyAliasValueTransform,
}

/// Parsed runtime config plus key-alias evidence.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq)]
pub struct RuntimeConfigAliasParse {
    pub config: RuntimeConfig,
    pub aliases: Vec<RuntimeKeyAliasRecord>,
}

impl RuntimeConfigAliasParse {
    pub fn into_config(self) -> RuntimeConfig {
        self.config
    }
}
