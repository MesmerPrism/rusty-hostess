using System.Diagnostics;
using System.Globalization;
using System.Reflection;
using System.Text.RegularExpressions;
using System.Text.Json;
using HostessCompanion.Wpf.Models;
using HostessCompanion.Wpf.Services;
using HostessCompanion.Wpf.ViewModels;

static partial class WpfCompanionTests
{
    public static IEnumerable<string> HostessCliSegments(string cliRoute)
    {
        return cliRoute
            .Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Where(segment =>
                segment.Contains("python tools\\hostessctl\\hostessctl.py", StringComparison.Ordinal)
                || segment.Contains("python $HostessCtl", StringComparison.Ordinal));
    }
    

    public static string JsonString(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var value)
            ? value.GetString() ?? string.Empty
            : string.Empty;
    }
    

    public static bool JsonBool(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var value)
            && value.ValueKind == JsonValueKind.True;
    }
    

    public static ConnectivityProtocolEvidenceRow PromotedProtocolRow(
        string capabilityId,
        string probeId,
        string transportKind,
        string evidenceTier) =>
        new()
        {
            CapabilityId = capabilityId,
            ProbeId = probeId,
            TransportKind = transportKind,
            SemanticFamily = "generic_data_protocol",
            AuthorityOwner = evidenceTier == "quest_runtime"
                ? "rusty.quest.device_link"
                : "rusty.manifold.transport",
            RequiredForFoldIn = true,
            Status = "usable",
            PromotionState = "promoted",
            PromotionAllowed = true,
            EvidenceTier = evidenceTier,
            PromotionGate = "Quest-runtime or broker-owned evidence required",
            MissingGates = [],
            GateResults =
            [
                new ConnectivityProtocolEvidenceGate
                {
                    GateId = $"gate.{probeId.ToLowerInvariant().Replace("-", string.Empty)}.promotion_allowed",
                    Status = "satisfied",
                    Evidence = "promotion.allowed=True",
                },
            ],
            Measurements = JsonSerializer.SerializeToElement(new { packets = 16 }),
        };
    

    public static void AssertArgument(IReadOnlyList<string> arguments, string name, string value)
    {
        var index = arguments.ToList().IndexOf(name);
        Assert(index >= 0, $"missing argument {name}");
        Assert(index + 1 < arguments.Count, $"missing value for {name}");
        Assert(arguments[index + 1] == value, $"expected {name} {value}, got {arguments[index + 1]}");
    }
    

    public static void AssertPageProperty(string propertyName, Type expectedType)
    {
        var property = typeof(MainWindowViewModel).GetProperty(propertyName);
        Assert(property is not null, $"missing page property {propertyName}");
        Assert(property!.PropertyType == expectedType, $"{propertyName} must be {expectedType.Name}");
    }
    

    public static T ReadFixture<T>(string name)
    {
        var path = Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "Fixtures", name);
        using var stream = File.OpenRead(Path.GetFullPath(path));
        return JsonSerializer.Deserialize<T>(
                stream,
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true })
            ?? throw new InvalidOperationException($"fixture {name} was empty");
    }
    

    public static bool RustyQuestMediaStreamSessionPlanExists()
    {
        var repoRoot = LocateHostessRepoRoot();
        var planPath = Path.GetFullPath(Path.Combine(
            repoRoot.FullName,
            "..",
            "rusty-quest",
            "fixtures",
            "media-stream-sessions",
            "display-composite-mediaprojection-h264.plan.json"));
        return File.Exists(planPath);
    }
    

    public static bool ManifoldWebSocketStreamEvidenceExists()
    {
        var repoRoot = LocateHostessRepoRoot();
        var routePath = Path.GetFullPath(Path.Combine(
            repoRoot.FullName,
            "..",
            "rusty-manifold",
            "fixtures",
            "bridge-route",
            "stream-websocket-ordered-route.json"));
        var evidencePath = Path.GetFullPath(Path.Combine(
            repoRoot.FullName,
            "..",
            "rusty-manifold",
            "fixtures",
            "bridge-route",
            "stream-websocket-ordered-evidence.json"));
        return File.Exists(routePath) && File.Exists(evidencePath);
    }
    

    public static DirectoryInfo LocateHostessRepoRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            if (File.Exists(Path.Combine(current.FullName, "tools", "hostessctl", "hostessctl.py")))
            {
                return current;
            }
            current = current.Parent;
        }
        throw new InvalidOperationException("Could not locate rusty-hostess repository root.");
    }
    

    public static void Assert(bool condition, string message)
    {
        if (!condition)
        {
            throw new InvalidOperationException(message);
        }
    }

}
