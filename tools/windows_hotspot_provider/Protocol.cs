using System.Text.Json;

namespace RustyHostess.WindowsHotspot;

internal static class Protocol
{
    internal const string RequestSchema = "rusty.hostess.windows_hotspot.provider_request.v1";
    internal const string ReceiptSchema = "rusty.hostess.windows_hotspot.provider_receipt.v1";
    internal static readonly HashSet<string> Actions = new(StringComparer.Ordinal)
        { "status", "start", "ensure", "stop" };
    private static readonly HashSet<string> Fields = new(StringComparer.Ordinal)
        { "schema", "request_id", "operation_id", "action", "expires_at_utc", "timeout_ms", "ownership_generation" };

    internal static Request ParseRequest(string input, DateTimeOffset now)
    {
        if (string.IsNullOrWhiteSpace(input)) throw new RejectedException("request.empty");
        JsonDocument doc;
        try { doc = JsonDocument.Parse(input, new JsonDocumentOptions { AllowTrailingCommas = false, CommentHandling = JsonCommentHandling.Disallow }); }
        catch (JsonException) { throw new RejectedException("request.invalid_json"); }
        using (doc)
        {
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object) throw new RejectedException("request.not_object");
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var property in root.EnumerateObject())
            {
                if (!Fields.Contains(property.Name) || !seen.Add(property.Name))
                    throw new RejectedException("request.unknown_or_duplicate_field");
            }
            string RequiredString(string name)
            {
                if (!root.TryGetProperty(name, out var value) || value.ValueKind != JsonValueKind.String)
                    throw new RejectedException($"request.{name}_required");
                var text = value.GetString()!;
                if (string.IsNullOrWhiteSpace(text) || text.Length > 128) throw new RejectedException($"request.{name}_invalid");
                return text;
            }
            var schema = RequiredString("schema");
            if (schema != RequestSchema) throw new RejectedException("request.schema_unsupported");
            var requestId = RequiredString("request_id");
            var operationId = RequiredString("operation_id");
            var action = RequiredString("action");
            if (!Actions.Contains(action)) throw new RejectedException("request.action_invalid");
            var expiryText = RequiredString("expires_at_utc");
            if (!DateTimeOffset.TryParseExact(expiryText, "O", null, System.Globalization.DateTimeStyles.RoundtripKind, out var expiry))
                throw new RejectedException("request.expires_at_utc_invalid");
            if (expiry <= now || expiry > now.AddMinutes(10)) throw new RejectedException("request.expired_or_unbounded");
            if (!root.TryGetProperty("timeout_ms", out var timeoutValue) || !timeoutValue.TryGetInt32(out var timeoutMs) || timeoutMs is < 100 or > 120_000)
                throw new RejectedException("request.timeout_ms_invalid");
            string? generation = null;
            if (root.TryGetProperty("ownership_generation", out var generationValue))
            {
                if (generationValue.ValueKind != JsonValueKind.String || string.IsNullOrWhiteSpace(generationValue.GetString()) || generationValue.GetString()!.Length > 128)
                    throw new RejectedException("request.ownership_generation_invalid");
                generation = generationValue.GetString();
            }
            if (action == "stop" && generation is null) throw new RejectedException("request.ownership_generation_required");
            if (action is "status" or "start" && generation is not null) throw new RejectedException("request.ownership_generation_not_allowed");
            return new Request(requestId, operationId, action, expiry, timeoutMs, generation);
        }
    }
}

internal sealed record Request(string RequestId, string OperationId, string Action, DateTimeOffset ExpiresAtUtc, int TimeoutMs, string? OwnershipGeneration);
internal sealed class RejectedException(string code) : Exception(code);
