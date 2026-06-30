using System.Text.Json;

internal static class DirectWifiProductMediaPlanTestArtifacts
{
    public static void WriteDirectWifiTopologyReport(string path, string probeId, bool promoted)
    {
        var peerClass = probeId == "QCL-041" ? "windows" : "android_phone";
        var report = new
        {
            schema = "rusty.quest.connectivity_topology_probe.v1",
            probe_id = probeId,
            status = "pass",
            topology = new
            {
                owner = "wifi_direct",
                network_provider = "wifi_direct",
                endpoint_direction = "peer_to_peer_group",
                peer_class = peerClass,
            },
            transport = new
            {
                family = "wifi_direct",
                route = "wifi_direct_lifecycle_artifact",
                payload_class = "bounded_tcp_probe",
            },
            promotion = new
            {
                allowed = promoted,
                target = "experimental topology descriptor",
                reason = promoted
                    ? "Live Wi-Fi Direct topology lifecycle is complete"
                    : "fixture-only Wi-Fi Direct topology remains candidate evidence",
            },
        };
        WriteJson(path, report);
    }

    public static void WriteQcl082ProductMediaReport(string path, bool promoted)
    {
        var report = new
        {
            schema = "rusty.quest.connectivity_probe.v1",
            probe_id = "QCL-082",
            status = "pass",
            media_stream_receiver_capture = new
            {
                capture_kind = "live_broker_stream",
                live_capture = true,
                source = new
                {
                    broker_or_quest_source = true,
                    source_owner = "rusty.quest.runtime",
                },
                product_topology = new
                {
                    ready = true,
                    network_provider = "wifi_direct",
                    product_gate = "product_tcp_media_over_direct_wifi",
                },
                product_listener_firewall = new
                {
                    ready = true,
                    product_gate = "product_tcp_media_listener_firewall_verified",
                },
            },
            measurements = new
            {
                media_product_topology_ready = true,
                media_product_listener_firewall_verified = true,
                media_frames_received = 4,
                media_bytes_received = 128,
            },
            promotion = new
            {
                allowed = promoted,
                reason = promoted
                    ? "QCL-082 RMANVID1 product media report proves TCP media over promoted direct-Wi-Fi"
                    : "candidate product-media fixture is not promotion-allowed",
            },
        };
        WriteJson(path, report);
    }

    private static void WriteJson<T>(string path, T report)
    {
        File.WriteAllText(
            path,
            JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true })
                + Environment.NewLine);
    }
}
