//! Projection runtime manifest marker formatting.

use super::*;

pub fn projection_runtime_manifest_marker_lines(
    backend: &str,
    phase: &str,
    resolution: &RuntimeConfigResolution,
    aliases: &[RuntimeKeyAliasRecord],
) -> Vec<String> {
    const ALIASES_PER_LINE: usize = 8;
    const FIELDS_PER_LINE: usize = 4;
    let fields = resolution
        .iter()
        .filter(|setting| projection_runtime_key_definition(setting.key.as_str()).is_some())
        .map(projection_runtime_manifest_field_token)
        .collect::<Vec<_>>();
    let alias_tokens = projection_runtime_alias_tokens(aliases);
    let field_count = fields.len();
    let alias_part_count = alias_tokens.len().div_ceil(ALIASES_PER_LINE);
    let field_part_count = field_count.div_ceil(FIELDS_PER_LINE).max(1);
    let part_count = alias_part_count + field_part_count;
    let mut lines = Vec::new();
    let backend = sanitize_marker_token(backend);
    let phase = sanitize_marker_token(phase);

    for (index, chunk) in alias_tokens.chunks(ALIASES_PER_LINE).enumerate() {
        lines.push(format!(
            "RUSTY_MAKEPAD_PROJECTION_RUNTIME_MANIFEST schema=rusty.gui.makepad.projection_runtime_manifest.v1 backend={} phase={} part={}/{} section=aliases fieldCount={} aliasCount={} aliases={} fields=none",
            backend,
            phase,
            index + 1,
            part_count,
            field_count,
            aliases.len(),
            chunk.join("|")
        ));
    }

    if fields.is_empty() {
        lines.push(format!(
            "RUSTY_MAKEPAD_PROJECTION_RUNTIME_MANIFEST schema=rusty.gui.makepad.projection_runtime_manifest.v1 backend={} phase={} part={}/{} section=fields fieldCount=0 aliasCount={} aliases={} fields=none",
            backend,
            phase,
            alias_part_count + 1,
            part_count,
            aliases.len(),
            if aliases.is_empty() { "none" } else { "see-section-aliases" }
        ));
        return lines;
    }

    for (index, chunk) in fields.chunks(FIELDS_PER_LINE).enumerate() {
        lines.push(format!(
            "RUSTY_MAKEPAD_PROJECTION_RUNTIME_MANIFEST schema=rusty.gui.makepad.projection_runtime_manifest.v1 backend={} phase={} part={}/{} section=fields fieldCount={} aliasCount={} aliases={} fields={}",
            backend,
            phase,
            alias_part_count + index + 1,
            part_count,
            field_count,
            aliases.len(),
            if aliases.is_empty() { "none" } else { "see-section-aliases" },
            chunk.join(";")
        ));
    }

    lines
}

fn projection_runtime_manifest_field_token(setting: &RuntimeResolvedSetting) -> String {
    let default_value = setting
        .default_value
        .as_ref()
        .map(runtime_value_marker_token)
        .unwrap_or_else(|| "none".to_string());
    let candidates = setting
        .candidates
        .iter()
        .map(|candidate| {
            format!(
                "{}:{}:{}:{}",
                candidate.precedence,
                sanitize_marker_token(candidate.owner.as_str()),
                runtime_source_marker_token(&candidate.source),
                runtime_value_marker_token(&candidate.value)
            )
        })
        .collect::<Vec<_>>()
        .join("|");
    format!(
        "{}[owner={},resolved={},source={},default={},candidates={}]",
        setting.key.as_str(),
        sanitize_marker_token(setting.owner.as_str()),
        runtime_value_marker_token(&setting.value),
        runtime_source_marker_token(&setting.source),
        default_value,
        candidates
    )
}

fn projection_runtime_alias_tokens(aliases: &[RuntimeKeyAliasRecord]) -> Vec<String> {
    aliases
        .iter()
        .map(|alias| {
            format!(
                "{}>{}:{}:{}:{}",
                sanitize_marker_token(&alias.input_key),
                alias.canonical_key.as_str(),
                alias_source_marker_token(alias.source),
                alias_status_marker_token(alias.status),
                alias_transform_marker_token(alias.value_transform)
            )
        })
        .collect::<Vec<_>>()
}

fn runtime_value_marker_token(value: &RuntimeValue) -> String {
    match value {
        RuntimeValue::Bool(value) => format!("bool:{value}"),
        RuntimeValue::Integer(value) => format!("int:{value}"),
        RuntimeValue::Float(value) => format!("float:{value:.6}"),
        RuntimeValue::Text(value) => format!("text:{}", sanitize_marker_token(value)),
    }
}

fn runtime_source_marker_token(source: &RuntimeConfigSource) -> &'static str {
    match source {
        RuntimeConfigSource::Default => "default",
        RuntimeConfigSource::Environment => "environment",
        RuntimeConfigSource::AndroidProperty => "android-property",
        RuntimeConfigSource::File => "file",
        RuntimeConfigSource::CommandLine => "command-line",
        RuntimeConfigSource::Synthetic => "synthetic",
    }
}

fn alias_source_marker_token(source: RuntimeKeyAliasSource) -> &'static str {
    match source {
        RuntimeKeyAliasSource::Canonical => "canonical",
        RuntimeKeyAliasSource::LaunchExtra => "launch-extra",
        RuntimeKeyAliasSource::AndroidProperty => "android-property",
        RuntimeKeyAliasSource::EnvironmentVariable => "environment-variable",
        RuntimeKeyAliasSource::LegacyRuntimeKey => "legacy-runtime-key",
    }
}

fn alias_status_marker_token(status: RuntimeKeyAliasStatus) -> &'static str {
    match status {
        RuntimeKeyAliasStatus::Canonical => "canonical",
        RuntimeKeyAliasStatus::Current => "current",
        RuntimeKeyAliasStatus::Legacy => "legacy",
        RuntimeKeyAliasStatus::Deprecated => "deprecated",
    }
}

fn alias_transform_marker_token(transform: RuntimeKeyAliasValueTransform) -> &'static str {
    match transform {
        RuntimeKeyAliasValueTransform::Identity => "identity",
        RuntimeKeyAliasValueTransform::NegateNumber => "negate-number",
    }
}

fn sanitize_marker_token(value: &str) -> String {
    value
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() || matches!(ch, '-' | '_' | '.' | ':' | '/') {
                ch
            } else {
                '_'
            }
        })
        .collect()
}
