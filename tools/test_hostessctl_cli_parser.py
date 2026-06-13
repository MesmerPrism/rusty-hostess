import unittest

from tools.hostessctl.cli_parser import build_hostessctl_parser


class HostessCtlCliParserTests(unittest.TestCase):
    def build_parser(self):
        return build_hostessctl_parser(
            broker_package="test.broker",
            broker_port=18765,
            broker_local_forward_port=28765,
            makepad_android_package="test.makepad",
            makepad_android_xr_activity="test.makepad/.Xr",
            makepad_provider_package="test.provider",
            makepad_provider_activity="test.provider/.Provider",
        )

    def test_record_values_uses_injected_platform_defaults(self) -> None:
        args = self.build_parser().parse_args(
            [
                "record-values",
                "--target",
                "quest",
                "--value",
                "stream.motion.object_pose",
                "--out",
                "recording.json",
                "--packages-root",
                "packages",
                "--duration-seconds",
                "1",
            ]
        )

        self.assertEqual(args.command, "record-values")
        self.assertEqual(args.broker_package, "test.broker")
        self.assertEqual(args.broker_port, 18765)
        self.assertEqual(args.broker_local_port, 28765)
        self.assertEqual(args.makepad_provider_package, "test.provider")
        self.assertEqual(args.makepad_provider_activity, "test.provider/.Provider")

    def test_makepad_shell_contract_uses_injected_makepad_default(self) -> None:
        args = self.build_parser().parse_args(
            [
                "launch-makepad-shell-contract",
                "--target",
                "quest",
                "--launch-handoff",
                "handoff.json",
                "--out",
                "evidence.json",
            ]
        )

        self.assertEqual(args.command, "launch-makepad-shell-contract")
        self.assertEqual(args.makepad_package, "test.makepad")


if __name__ == "__main__":
    unittest.main()
