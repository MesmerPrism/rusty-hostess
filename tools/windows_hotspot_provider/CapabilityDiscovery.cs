using System.Reflection;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace RustyHostess.WindowsHotspot;

internal static class CapabilityDiscovery
{
    internal const string Schema =
        "rusty.quest.workflow.provider_capability_discovery.v1";
    internal const string ProviderId =
        "rusty.hostess.windows-hotspot-provider";
    internal const string CapabilityId =
        "rusty.hostess.windows-hotspot";
    internal const string EffectOwner =
        "rusty.hostess.windows-hotspot-provider";
    internal const int MaximumAgeSeconds = 300;

    private static readonly IReadOnlyDictionary<string, ActionMetadata>
        ActionRegistry =
            new Dictionary<string, ActionMetadata>(StringComparer.Ordinal)
            {
                ["status"] = new(
                    "observe",
                    ["process-access-control", "caller-authority-external"]),
                ["start"] = new(
                    "effect",
                    [
                        "process-access-control",
                        "caller-authority-external",
                        "effect-owner-profile"
                    ]),
                ["ensure"] = new(
                    "effect",
                    [
                        "process-access-control",
                        "caller-authority-external",
                        "effect-owner-profile"
                    ]),
                ["stop"] = new(
                    "effect",
                    [
                        "process-access-control",
                        "caller-authority-external",
                        "effect-owner-profile",
                        "ownership-generation"
                    ])
            };

    internal static DiscoveryDescriptor Create(
        DateTimeOffset observedAtUtc,
        string providerVersion)
    {
        var observed = observedAtUtc.ToUniversalTime();
        var actions = CreateActions();
        return new DiscoveryDescriptor
        {
            Provider = new DiscoveryProvider
            {
                Id = ProviderId,
                Version = providerVersion
            },
            Availability = new DiscoveryAvailability
            {
                ObservedAtUtc = observed.ToString("O"),
                ExpiresAtUtc = observed
                    .AddSeconds(MaximumAgeSeconds)
                    .ToString("O")
            },
            Capabilities =
            [
                new DiscoveryCapability
                {
                    Id = CapabilityId,
                    ContractVersions = [Protocol.RequestSchema],
                    Actions = actions,
                    EffectOwner = EffectOwner,
                    ReceiptSchema = Protocol.ReceiptSchema,
                    Exclusions =
                    [
                        "no-fleet-policy",
                        "no-hotspot-configuration",
                        "no-owner-state",
                        "no-release-eligibility"
                    ]
                }
            ]
        };
    }

    internal static string Serialize(
        DateTimeOffset observedAtUtc,
        string providerVersion) =>
        JsonSerializer.Serialize(Create(observedAtUtc, providerVersion));

    private static List<DiscoveryAction> CreateActions()
    {
        if (ActionRegistry.Count != Protocol.Actions.Count ||
            ActionRegistry.Keys.Any(action => !Protocol.Actions.Contains(action)) ||
            Protocol.Actions.Any(action => !ActionRegistry.ContainsKey(action)))
        {
            throw new InvalidOperationException(
                "Discovery action metadata does not match Protocol.Actions.");
        }

        return Protocol.Actions
            .OrderBy(action => action, StringComparer.Ordinal)
            .Select(action =>
            {
                var metadata = ActionRegistry[action];
                return new DiscoveryAction
                {
                    Id = action,
                    Kind = metadata.Kind,
                    AuthenticationRequirements =
                        [.. metadata.AuthenticationRequirements]
                };
            })
            .ToList();
    }

    private sealed record ActionMetadata(
        string Kind,
        IReadOnlyList<string> AuthenticationRequirements);
}

internal static partial class ProviderAssemblyVersion
{
    [GeneratedRegex(
        "^(?<version>[0-9]+\\.[0-9]+\\.[0-9]+(?:-[a-z0-9.-]+)?)(?:\\+[0-9A-Za-z.-]+)?$",
        RegexOptions.CultureInvariant)]
    private static partial Regex SemVerPattern();

    internal static string Read()
    {
        var informationalVersion = typeof(ProviderAssemblyVersion)
            .Assembly
            .GetCustomAttribute<AssemblyInformationalVersionAttribute>()
            ?.InformationalVersion;
        if (informationalVersion is not null)
            return ParseInformationalVersion(informationalVersion);

        var version = typeof(ProviderAssemblyVersion).Assembly.GetName().Version
            ?? throw new InvalidOperationException(
                "Provider assembly version is unavailable.");
        if (version.Major < 0 || version.Minor < 0 || version.Build < 0)
            throw new InvalidOperationException(
                "Provider assembly version is not SemVer-compatible.");
        return $"{version.Major}.{version.Minor}.{version.Build}";
    }

    internal static string ParseInformationalVersion(
        string informationalVersion)
    {
        var match = SemVerPattern().Match(informationalVersion);
        if (!match.Success)
        {
            throw new InvalidOperationException(
                "Provider informational version is not compatible with " +
                "the discovery SemVer contract.");
        }
        return match.Groups["version"].Value;
    }
}

internal sealed record DiscoveryDescriptor
{
    [JsonPropertyName("schema")]
    public string Schema { get; init; } = CapabilityDiscovery.Schema;

    [JsonPropertyName("provider")]
    public required DiscoveryProvider Provider { get; init; }

    [JsonPropertyName("placement")]
    public string Placement { get; init; } = "windows-host-process";

    [JsonPropertyName("availability")]
    public required DiscoveryAvailability Availability { get; init; }

    [JsonPropertyName("description_authentication")]
    public string DescriptionAuthentication { get; init; } = "none";

    [JsonPropertyName("authorizes_execution")]
    public bool AuthorizesExecution { get; init; }

    [JsonPropertyName("target_specific")]
    public bool TargetSpecific { get; init; }

    [JsonPropertyName("capabilities")]
    public required List<DiscoveryCapability> Capabilities { get; init; }

    [JsonPropertyName("exclusions")]
    public List<string> Exclusions { get; init; } =
    [
        "no-credentials",
        "no-endpoints",
        "no-execution-grant",
        "no-owner-state",
        "no-profile-data",
        "no-target-resolution"
    ];
}

internal sealed record DiscoveryProvider
{
    [JsonPropertyName("id")]
    public required string Id { get; init; }

    [JsonPropertyName("version")]
    public required string Version { get; init; }
}

internal sealed record DiscoveryAvailability
{
    [JsonPropertyName("status")]
    public string Status { get; init; } = "descriptor-available";

    [JsonPropertyName("observed_at_utc")]
    public required string ObservedAtUtc { get; init; }

    [JsonPropertyName("expires_at_utc")]
    public required string ExpiresAtUtc { get; init; }

    [JsonPropertyName("maximum_age_seconds")]
    public int MaximumAgeSeconds { get; init; } =
        CapabilityDiscovery.MaximumAgeSeconds;
}

internal sealed record DiscoveryCapability
{
    [JsonPropertyName("id")]
    public required string Id { get; init; }

    [JsonPropertyName("contract_versions")]
    public required List<string> ContractVersions { get; init; }

    [JsonPropertyName("actions")]
    public required List<DiscoveryAction> Actions { get; init; }

    [JsonPropertyName("effect_owner")]
    public required string EffectOwner { get; init; }

    [JsonPropertyName("receipt_schema")]
    public required string ReceiptSchema { get; init; }

    [JsonPropertyName("exclusions")]
    public required List<string> Exclusions { get; init; }
}

internal sealed record DiscoveryAction
{
    [JsonPropertyName("id")]
    public required string Id { get; init; }

    [JsonPropertyName("kind")]
    public required string Kind { get; init; }

    [JsonPropertyName("authentication_requirements")]
    public required List<string> AuthenticationRequirements { get; init; }
}
