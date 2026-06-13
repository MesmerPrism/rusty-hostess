//! Makepad runtime configuration helpers.
//!
//! This crate models generic launch/runtime settings. Downstream apps can map
//! their private environment variables, Android properties, or config files
//! onto these public keys without publishing app-specific aliases.
//!
//! Enable the `serde` feature when runtime profiles or operator tools need to
//! serialize these public settings.
//!
//! ```
//! use makepad_runtime_config::{RuntimeConfig, RuntimeConfigSource, RuntimeValue};
//!
//! let mut config = RuntimeConfig::new();
//! config
//!     .set("render_scale", RuntimeValue::Float(0.8), RuntimeConfigSource::Synthetic)
//!     .expect("key should be public-safe");
//! assert_eq!(config.get("render_scale"), Some(&RuntimeValue::Float(0.8)));
//! ```

use std::{collections::BTreeMap, fmt, str::FromStr};

mod alias_model;
mod aliases;
mod manifest;
mod projection_keys;
mod retired_aliases;
#[cfg(test)]
mod tests;

pub use alias_model::{
    RuntimeConfigAliasParse, RuntimeKeyAlias, RuntimeKeyAliasRecord, RuntimeKeyAliasSource,
    RuntimeKeyAliasStatus, RuntimeKeyAliasValueTransform,
};
pub use aliases::{projection_runtime_key_alias, PROJECTION_RUNTIME_KEY_ALIASES};
pub use manifest::projection_runtime_manifest_marker_lines;
pub use projection_keys::*;
pub use retired_aliases::{
    retired_projection_runtime_key_alias, RetiredRuntimeKeyAlias,
    RETIRED_PROJECTION_RUNTIME_KEY_ALIASES,
};

/// Crate version exposed for lightweight smoke checks.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Stable runtime setting key.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct RuntimeKey(String);

impl RuntimeKey {
    pub fn new(value: impl Into<String>) -> Result<Self, RuntimeConfigError> {
        let value = value.into();
        validate_key(&value)?;
        Ok(Self(value))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }

    pub fn android_property(&self, prefix: &AndroidPropertyPrefix) -> String {
        let suffix = self.as_str().replace(['_', '-'], ".");
        format!("{}.{}", prefix.as_str(), suffix)
    }
}

impl fmt::Display for RuntimeKey {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

impl FromStr for RuntimeKey {
    type Err = RuntimeConfigError;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        Self::new(value)
    }
}

/// Broad area that owns a runtime key.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RuntimeKeyDomain {
    Projection,
}

/// Projection sub-contract that owns a runtime key.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ProjectionRuntimeKeyOwner {
    Geometry,
    ProjectionArea,
    TargetFootprint,
    SourceSampling,
    Alpha,
    RendererPolicy,
}

/// Expected value shape for a runtime key.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RuntimeValueKind {
    Bool,
    Integer,
    Float,
    Text,
}

/// Public runtime-key registry entry.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RuntimeKeyDefinition {
    pub key: &'static str,
    pub domain: RuntimeKeyDomain,
    pub owner: ProjectionRuntimeKeyOwner,
    pub value_kind: RuntimeValueKind,
    pub description: &'static str,
}

impl RuntimeKeyDefinition {
    pub fn runtime_key(&self) -> RuntimeKey {
        RuntimeKey::new(self.key).expect("registered runtime keys should be valid")
    }
}

/// Public Android property prefix. Keep app-specific prefixes in app repos.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AndroidPropertyPrefix(String);

impl AndroidPropertyPrefix {
    pub fn new(value: impl Into<String>) -> Result<Self, RuntimeConfigError> {
        let value = value.into();
        if value.is_empty()
            || !value
                .bytes()
                .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'.')
        {
            return Err(RuntimeConfigError::InvalidAndroidPropertyPrefix(value));
        }
        Ok(Self(value))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl Default for AndroidPropertyPrefix {
    fn default() -> Self {
        Self("debug.rusty".to_string())
    }
}

/// Public owner label for a runtime-config layer.
///
/// Owners describe where a group of settings came from, such as a launch
/// profile, Android property readback, file profile, or backend default table.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct RuntimeConfigOwner(String);

impl RuntimeConfigOwner {
    pub fn new(value: impl Into<String>) -> Result<Self, RuntimeConfigError> {
        let value = value.into();
        validate_owner(&value)?;
        Ok(Self(value))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for RuntimeConfigOwner {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

impl FromStr for RuntimeConfigOwner {
    type Err = RuntimeConfigError;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        Self::new(value)
    }
}

/// Generic runtime setting value.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq)]
pub enum RuntimeValue {
    Bool(bool),
    Integer(i64),
    Float(f64),
    Text(String),
}

impl RuntimeValue {
    pub fn parse_typed(raw: &str) -> Self {
        let trimmed = raw.trim();
        if let Some(value) = parse_bool(trimmed) {
            return Self::Bool(value);
        }
        if let Ok(value) = trimmed.parse::<i64>() {
            return Self::Integer(value);
        }
        if let Ok(value) = trimmed.parse::<f64>() {
            if value.is_finite() {
                return Self::Float(value);
            }
        }
        Self::Text(trimmed.to_string())
    }

    pub fn parse_for_kind(raw: &str, kind: RuntimeValueKind) -> Option<Self> {
        let trimmed = raw.trim();
        match kind {
            RuntimeValueKind::Bool => parse_bool(trimmed).map(Self::Bool),
            RuntimeValueKind::Integer => trimmed.parse::<i64>().ok().map(Self::Integer),
            RuntimeValueKind::Float => trimmed
                .parse::<f64>()
                .ok()
                .filter(|value| value.is_finite())
                .map(Self::Float),
            RuntimeValueKind::Text => Some(Self::Text(trimmed.to_string())),
        }
    }

    pub fn as_bool(&self) -> Option<bool> {
        match self {
            Self::Bool(value) => Some(*value),
            _ => None,
        }
    }

    pub fn as_integer(&self) -> Option<i64> {
        match self {
            Self::Integer(value) => Some(*value),
            _ => None,
        }
    }

    pub fn as_float(&self) -> Option<f64> {
        match self {
            Self::Float(value) => Some(*value),
            Self::Integer(value) => Some(*value as f64),
            _ => None,
        }
    }

    pub fn as_text(&self) -> Option<&str> {
        match self {
            Self::Text(value) => Some(value),
            _ => None,
        }
    }
}

/// One parsed runtime setting with source metadata.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq)]
pub struct RuntimeSetting {
    pub key: RuntimeKey,
    pub value: RuntimeValue,
    pub source: RuntimeConfigSource,
}

impl RuntimeSetting {
    pub fn new(key: RuntimeKey, value: RuntimeValue, source: RuntimeConfigSource) -> Self {
        Self { key, value, source }
    }
}

/// Source of a runtime setting.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum RuntimeConfigSource {
    Default,
    Environment,
    AndroidProperty,
    File,
    CommandLine,
    Synthetic,
}

/// Ordered map of runtime settings.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, Default, PartialEq)]
pub struct RuntimeConfig {
    settings: BTreeMap<RuntimeKey, RuntimeSetting>,
}

impl RuntimeConfig {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert(&mut self, setting: RuntimeSetting) -> Option<RuntimeSetting> {
        self.settings.insert(setting.key.clone(), setting)
    }

    pub fn set(
        &mut self,
        key: impl Into<String>,
        value: RuntimeValue,
        source: RuntimeConfigSource,
    ) -> Result<Option<RuntimeSetting>, RuntimeConfigError> {
        let key = RuntimeKey::new(key)?;
        Ok(self.insert(RuntimeSetting::new(key, value, source)))
    }

    pub fn get(&self, key: &str) -> Option<&RuntimeValue> {
        self.settings
            .get(&RuntimeKey::new(key).ok()?)
            .map(|setting| &setting.value)
    }

    pub fn parse_pairs<'a>(
        source: RuntimeConfigSource,
        pairs: impl IntoIterator<Item = (&'a str, &'a str)>,
    ) -> Result<Self, RuntimeConfigError> {
        let mut config = Self::new();
        for (key, raw_value) in pairs {
            config.set(key, RuntimeValue::parse_typed(raw_value), source.clone())?;
        }
        Ok(config)
    }

    pub fn iter(&self) -> impl Iterator<Item = &RuntimeSetting> {
        self.settings.values()
    }
}

pub fn resolve_projection_runtime_key(
    input: &str,
) -> Result<RuntimeKeyAliasRecord, RuntimeConfigError> {
    if projection_runtime_key_definition(input).is_some() {
        return Ok(RuntimeKeyAliasRecord {
            input_key: input.to_string(),
            canonical_key: RuntimeKey::new(input)?,
            source: RuntimeKeyAliasSource::Canonical,
            status: RuntimeKeyAliasStatus::Canonical,
            value_transform: RuntimeKeyAliasValueTransform::Identity,
        });
    }

    let alias = projection_runtime_key_alias(input)
        .ok_or_else(|| RuntimeConfigError::UnknownRuntimeKeyAlias(input.to_string()))?;
    Ok(RuntimeKeyAliasRecord {
        input_key: input.to_string(),
        canonical_key: alias.canonical_runtime_key(),
        source: alias.source,
        status: alias.status,
        value_transform: alias.value_transform,
    })
}

pub fn parse_projection_runtime_pairs<'a>(
    source: RuntimeConfigSource,
    pairs: impl IntoIterator<Item = (&'a str, &'a str)>,
) -> Result<RuntimeConfigAliasParse, RuntimeConfigError> {
    let mut config = RuntimeConfig::new();
    let mut aliases = Vec::new();
    for (input_key, raw_value) in pairs {
        let alias = resolve_projection_runtime_key(input_key)?;
        let definition = projection_runtime_key_definition(alias.canonical_key.as_str())
            .expect("resolved projection aliases should target registered keys");
        let value =
            RuntimeValue::parse_for_kind(raw_value, definition.value_kind).ok_or_else(|| {
                RuntimeConfigError::InvalidAliasValue {
                    alias: input_key.to_string(),
                    value: raw_value.to_string(),
                }
            })?;
        let value = alias.value_transform.apply(input_key, raw_value, value)?;
        config.insert(RuntimeSetting::new(
            alias.canonical_key.clone(),
            value,
            source.clone(),
        ));
        aliases.push(alias);
    }

    Ok(RuntimeConfigAliasParse { config, aliases })
}

/// One runtime-config layer with explicit precedence.
///
/// Higher precedence wins. If two layers use the same precedence for the same
/// key, the later layer wins so callers can keep deterministic local override
/// behavior.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq)]
pub struct RuntimeConfigLayer {
    pub owner: RuntimeConfigOwner,
    pub precedence: u32,
    pub config: RuntimeConfig,
}

impl RuntimeConfigLayer {
    pub fn new(
        owner: impl Into<String>,
        precedence: u32,
        config: RuntimeConfig,
    ) -> Result<Self, RuntimeConfigError> {
        Ok(Self {
            owner: RuntimeConfigOwner::new(owner)?,
            precedence,
            config,
        })
    }
}

/// Candidate value considered during resolution.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq)]
pub struct RuntimeConfigCandidate {
    pub key: RuntimeKey,
    pub value: RuntimeValue,
    pub source: RuntimeConfigSource,
    pub owner: RuntimeConfigOwner,
    pub precedence: u32,
}

impl RuntimeConfigCandidate {
    fn from_setting(setting: &RuntimeSetting, owner: &RuntimeConfigOwner, precedence: u32) -> Self {
        Self {
            key: setting.key.clone(),
            value: setting.value.clone(),
            source: setting.source.clone(),
            owner: owner.clone(),
            precedence,
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
struct OrderedRuntimeConfigCandidate {
    candidate: RuntimeConfigCandidate,
    layer_order: usize,
}

/// Resolved value for one key, including all candidate values.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq)]
pub struct RuntimeResolvedSetting {
    pub key: RuntimeKey,
    pub value: RuntimeValue,
    pub source: RuntimeConfigSource,
    pub owner: RuntimeConfigOwner,
    pub precedence: u32,
    pub default_value: Option<RuntimeValue>,
    pub candidates: Vec<RuntimeConfigCandidate>,
}

impl RuntimeResolvedSetting {
    pub fn overridden_candidates(&self) -> impl Iterator<Item = &RuntimeConfigCandidate> {
        self.candidates
            .iter()
            .filter(move |candidate| !candidate_matches_resolution(candidate, self))
    }
}

/// Full traced resolution for a set of runtime-config layers.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, Default, PartialEq)]
pub struct RuntimeConfigResolution {
    resolved: RuntimeConfig,
    settings: BTreeMap<RuntimeKey, RuntimeResolvedSetting>,
}

impl RuntimeConfigResolution {
    pub fn resolved(&self) -> &RuntimeConfig {
        &self.resolved
    }

    pub fn get(&self, key: &str) -> Option<&RuntimeResolvedSetting> {
        self.settings.get(&RuntimeKey::new(key).ok()?)
    }

    pub fn iter(&self) -> impl Iterator<Item = &RuntimeResolvedSetting> {
        self.settings.values()
    }
}

/// Projection-specific resolved runtime config plus alias evidence.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, Default, PartialEq)]
pub struct ProjectionRuntimeConfigResolution {
    pub resolution: RuntimeConfigResolution,
    pub aliases: Vec<RuntimeKeyAliasRecord>,
}

impl ProjectionRuntimeConfigResolution {
    pub fn manifest_marker_lines(&self, backend: &str, phase: &str) -> Vec<String> {
        projection_runtime_manifest_marker_lines(backend, phase, &self.resolution, &self.aliases)
    }
}

/// Builder for traced projection runtime config layers.
#[derive(Clone, Debug, Default)]
pub struct ProjectionRuntimeConfigBuilder {
    resolver: RuntimeConfigResolver,
    aliases: Vec<RuntimeKeyAliasRecord>,
}

impl ProjectionRuntimeConfigBuilder {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn push_layer(
        &mut self,
        owner: impl Into<String>,
        precedence: u32,
        config: RuntimeConfig,
    ) -> Result<&mut Self, RuntimeConfigError> {
        if config.iter().next().is_some() {
            self.resolver
                .push_layer(RuntimeConfigLayer::new(owner, precedence, config)?);
        }
        Ok(self)
    }

    pub fn with_layer(
        mut self,
        owner: impl Into<String>,
        precedence: u32,
        config: RuntimeConfig,
    ) -> Result<Self, RuntimeConfigError> {
        self.push_layer(owner, precedence, config)?;
        Ok(self)
    }

    pub fn push_aliases(
        &mut self,
        aliases: impl IntoIterator<Item = RuntimeKeyAliasRecord>,
    ) -> &mut Self {
        self.aliases.extend(aliases);
        self
    }

    pub fn with_aliases(
        mut self,
        aliases: impl IntoIterator<Item = RuntimeKeyAliasRecord>,
    ) -> Self {
        self.push_aliases(aliases);
        self
    }

    pub fn resolve(self) -> ProjectionRuntimeConfigResolution {
        ProjectionRuntimeConfigResolution {
            resolution: self.resolver.resolve(),
            aliases: self.aliases,
        }
    }
}

/// Incremental resolver for layered runtime configuration.
#[derive(Clone, Debug, Default)]
pub struct RuntimeConfigResolver {
    layers: Vec<RuntimeConfigLayer>,
}

impl RuntimeConfigResolver {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn push_layer(&mut self, layer: RuntimeConfigLayer) {
        self.layers.push(layer);
    }

    pub fn with_layer(mut self, layer: RuntimeConfigLayer) -> Self {
        self.push_layer(layer);
        self
    }

    pub fn resolve(&self) -> RuntimeConfigResolution {
        let mut by_key: BTreeMap<RuntimeKey, Vec<OrderedRuntimeConfigCandidate>> = BTreeMap::new();
        for (layer_order, layer) in self.layers.iter().enumerate() {
            for setting in layer.config.iter() {
                by_key.entry(setting.key.clone()).or_default().push(
                    OrderedRuntimeConfigCandidate {
                        candidate: RuntimeConfigCandidate::from_setting(
                            setting,
                            &layer.owner,
                            layer.precedence,
                        ),
                        layer_order,
                    },
                );
            }
        }

        let mut resolved = RuntimeConfig::new();
        let mut settings = BTreeMap::new();
        for (key, mut candidates) in by_key {
            candidates.sort_by(|left, right| {
                right
                    .candidate
                    .precedence
                    .cmp(&left.candidate.precedence)
                    .then_with(|| right.layer_order.cmp(&left.layer_order))
            });

            let winner = candidates
                .first()
                .expect("candidate vector should not be empty")
                .candidate
                .clone();
            let default_value = candidates
                .iter()
                .find(|candidate| candidate.candidate.source == RuntimeConfigSource::Default)
                .map(|candidate| candidate.candidate.value.clone());
            let public_candidates = candidates
                .into_iter()
                .map(|candidate| candidate.candidate)
                .collect::<Vec<_>>();
            let setting = RuntimeResolvedSetting {
                key: key.clone(),
                value: winner.value.clone(),
                source: winner.source.clone(),
                owner: winner.owner.clone(),
                precedence: winner.precedence,
                default_value,
                candidates: public_candidates,
            };

            resolved.insert(RuntimeSetting::new(
                key.clone(),
                winner.value,
                winner.source,
            ));
            settings.insert(key, setting);
        }

        RuntimeConfigResolution { resolved, settings }
    }
}

/// Runtime configuration parsing error.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum RuntimeConfigError {
    InvalidKey(String),
    InvalidOwner(String),
    InvalidAndroidPropertyPrefix(String),
    UnknownRuntimeKeyAlias(String),
    InvalidAliasValue { alias: String, value: String },
}

impl fmt::Display for RuntimeConfigError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidKey(value) => write!(f, "invalid runtime config key: {value}"),
            Self::InvalidOwner(value) => write!(f, "invalid runtime config owner: {value}"),
            Self::InvalidAndroidPropertyPrefix(value) => {
                write!(f, "invalid Android property prefix: {value}")
            }
            Self::UnknownRuntimeKeyAlias(value) => {
                write!(f, "unknown runtime config key alias: {value}")
            }
            Self::InvalidAliasValue { alias, value } => {
                write!(f, "invalid value for runtime config alias {alias}: {value}")
            }
        }
    }
}

impl std::error::Error for RuntimeConfigError {}

fn validate_key(value: &str) -> Result<(), RuntimeConfigError> {
    if value.is_empty() {
        return Err(RuntimeConfigError::InvalidKey(value.to_string()));
    }

    let mut previous_was_separator = false;
    for byte in value.bytes() {
        let is_valid =
            byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'_' || byte == b'-';
        if !is_valid {
            return Err(RuntimeConfigError::InvalidKey(value.to_string()));
        }
        let is_separator = byte == b'_' || byte == b'-';
        if is_separator && previous_was_separator {
            return Err(RuntimeConfigError::InvalidKey(value.to_string()));
        }
        previous_was_separator = is_separator;
    }

    Ok(())
}

fn validate_owner(value: &str) -> Result<(), RuntimeConfigError> {
    if value.is_empty() {
        return Err(RuntimeConfigError::InvalidOwner(value.to_string()));
    }

    for byte in value.bytes() {
        let is_valid = byte.is_ascii_lowercase()
            || byte.is_ascii_digit()
            || byte == b'_'
            || byte == b'-'
            || byte == b'.';
        if !is_valid {
            return Err(RuntimeConfigError::InvalidOwner(value.to_string()));
        }
    }

    Ok(())
}

fn candidate_matches_resolution(
    candidate: &RuntimeConfigCandidate,
    setting: &RuntimeResolvedSetting,
) -> bool {
    candidate.key == setting.key
        && candidate.value == setting.value
        && candidate.source == setting.source
        && candidate.owner == setting.owner
        && candidate.precedence == setting.precedence
}

fn parse_bool(value: &str) -> Option<bool> {
    match value.to_ascii_lowercase().as_str() {
        "1" | "true" | "yes" | "on" | "enabled" => Some(true),
        "0" | "false" | "no" | "off" | "disabled" => Some(false),
        _ => None,
    }
}
