import base64
import json
import socket
import struct
import unittest
from unittest import mock

from tools import trusted_local_control_cli as cli


class TrustedLocalControlCliTests(unittest.TestCase):
    def test_provider_call_is_serial_scoped_closed_and_decodes_receipt(self):
        receipt = {
            "schema": "rusty.quest.debug_local_control_receipt.v1",
            "confirmed": True,
            "pairing_code": "123456",
        }
        encoded = base64.b64encode(json.dumps(receipt).encode()).decode()
        completed = mock.Mock(returncode=0, stdout=f"Result: Bundle[{{receipt_b64={encoded}}}]")
        with mock.patch.object(cli.shutil, "which", return_value="adb"), mock.patch.object(
            cli.subprocess, "run", return_value=completed
        ) as run:
            self.assertEqual(cli.invoke_provider("SERIAL123", "status"), receipt)
        command = run.call_args.args[0]
        self.assertEqual(command[1:3], ["-s", "SERIAL123"])
        self.assertEqual(command[-2:], ["--method", "status"])

    def test_unknown_provider_method_and_unsafe_serial_fail_closed(self):
        with self.assertRaises(ValueError):
            cli.invoke_provider("SERIAL123", "shell")
        with self.assertRaises(ValueError):
            cli.invoke_provider("SERIAL123;rm", "status")

    def test_pair_and_open_bodies_are_canonical(self):
        paired = cli.canonical_json({"pairing_code": "123456", "request_id": "pair-1234567890123456"})
        opened = cli.canonical_json({"request_id": "open-1234567890123456"})
        self.assertEqual(
            paired,
            '{"pairing_code":"123456","request_id":"pair-1234567890123456"}',
        )
        self.assertEqual(opened, '{"request_id":"open-1234567890123456"}')

    def test_redaction_is_default_and_non_mutating(self):
        receipt = {"pairing_code": "123456", "confirmed": True}
        self.assertEqual(cli.redact(receipt, False)["pairing_code"], "<redacted>")
        self.assertEqual(receipt["pairing_code"], "123456")
        self.assertEqual(cli.redact(receipt, True)["pairing_code"], "123456")

    def test_dns_sd_records_are_bounded_and_parseable(self):
        instance = "Rusty Quest Video Control._rustyquest-control._tcp.local."
        host = "quest-control.local."

        def record(name, record_type, data):
            return (
                cli._dns_name(name)
                + struct.pack("!HHIH", record_type, 1, 120, len(data))
                + data
            )

        txt_items = [
            b"protocol=trusted_local_http_v1",
            b"access=open_lan_insecure",
            b"confidentiality=none",
            b"path=/",
        ]
        packet = struct.pack("!6H", 7, 0x8400, 0, 4, 0, 0) + b"".join(
            [
                record(cli.DISCOVERY_SERVICE, 12, cli._dns_name(instance)),
                record(instance, 33, struct.pack("!HHH", 0, 0, 43210) + cli._dns_name(host)),
                record(instance, 16, b"".join(bytes([len(item)]) + item for item in txt_items)),
                record(host, 1, socket.inet_aton("192.168.2.70")),
            ]
        )
        records = cli._parse_dns_records(packet)
        self.assertEqual(len(records), 4)
        ptr_name, _ = cli._read_dns_name(packet, records[0][3])
        self.assertEqual(ptr_name, instance.lower())

    def test_discovery_timeout_is_bounded(self):
        with self.assertRaises(ValueError):
            cli.discover_services(0.5)
        with self.assertRaises(ValueError):
            cli.discover_services(11)

    def test_video_selection_is_closed_to_the_advertised_catalog(self):
        videos = [
            {
                "video_id": "synthetic-grid-1s",
                "projection_shape": "flat",
                "stereo_layout": "mono",
            },
            {
                "video_id": "synthetic-360-top-bottom",
                "projection_shape": "equirect-360",
                "stereo_layout": "top-bottom",
            },
        ]
        self.assertEqual(
            cli.select_video_descriptor(videos, "synthetic-grid-1s", None)["video_id"],
            "synthetic-360-top-bottom",
        )
        self.assertEqual(
            cli.select_video_descriptor(
                videos, "synthetic-grid-1s", "synthetic-360-top-bottom"
            )["stereo_layout"],
            "top-bottom",
        )
        with self.assertRaises(RuntimeError):
            cli.select_video_descriptor(videos, "synthetic-grid-1s", "missing-video")
        with self.assertRaises(RuntimeError):
            cli.select_video_descriptor(
                videos, "synthetic-grid-1s", "synthetic-grid-1s"
            )
        with self.assertRaises(ValueError):
            cli.select_video_descriptor(videos, "synthetic-grid-1s", "../escape")

    def test_media_batch_limit_is_bounded_before_provider_use(self):
        with self.assertRaises(ValueError):
            cli.run_media_sequence(
                "SERIAL123",
                "paired",
                [f"synthetic-profile-{index}" for index in range(6)],
            )


if __name__ == "__main__":
    unittest.main()
