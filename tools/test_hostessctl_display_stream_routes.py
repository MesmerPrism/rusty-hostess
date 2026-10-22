"""CLI/API and finite compatibility ownership checks; no device effects."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.hostessctl.cli_parser import build_hostessctl_parser
from tools.hostessctl import display_stream as display
from tools.hostessctl.hostessctl import dispatch_command

class DisplayRoutesTests(unittest.TestCase):
    def parser(self):
        return build_hostessctl_parser(broker_package="test.broker", broker_port=18765,
            broker_local_forward_port=28765, makepad_android_package="test.makepad",
            makepad_android_xr_activity="test.makepad/.Xr", makepad_provider_package="test.provider",
            makepad_provider_activity="test.provider/.Provider")

    def args(self, directory, source="shell-mirror"):
        return self.parser().parse_args(["display-stream", "run", "--source", source,
            "--adb", "model-adb", "--serial", "model-target", "--out", str(Path(directory)/"run.json"),
            "--fail-on-error"])

    def test_four_source_cli_uses_shared_dispatch_handler(self):
        with tempfile.TemporaryDirectory() as directory:
            for source in ["adb-screenrecord", "shell-mirror", "media-projection", "scrcpy"]:
                args=self.args(directory, source)
                self.assertEqual(args.duration_seconds, 5)
                with patch.object(display, "run_display_stream", return_value=7) as handler:
                    self.assertEqual(dispatch_command(args), 7)
                    handler.assert_called_once_with(args)

    def test_failed_device_preflight_has_no_cleanup_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            for source in ["shell-mirror", "media-projection"]:
                calls=[]
                def runner(command, **kwargs):
                    calls.append(command)
                    return subprocess.CompletedProcess(command, 1, "", "unavailable")
                self.assertEqual(display.run_display_stream(self.args(directory,source), run_func=runner),2)
                self.assertEqual(len(calls),1,calls)
                self.assertEqual(calls[0][-1],"get-state")

    def test_reverse_creation_never_replaces_existing_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            calls=[]
            def runner(command, **kwargs):
                calls.append(command)
                if command[-1]=="--list":
                    return subprocess.CompletedProcess(command,0,"model tcp:9079 tcp:9999\n","")
                return subprocess.CompletedProcess(command,1,"","cannot rebind")
            result=display.create_reverse(self.args(directory),runner)
            self.assertFalse(result["created"])
            self.assertIn("--no-rebind",calls[-1])

    def test_current_finite_shell_terminal_requires_same_actor_and_actual_exit(self):
        hello=dict(schema="rusty.quest.display_stream.hello.v1", invocation_id="a"*32,
            generation="legacy",stop_nonce="b"*32,pid=1234,uid=2000,start_ticks=99)
        terminal=dict(hello,schema="rusty.quest.display_stream.terminal.v1",stop_observed=False,
            worker_retired=True,resources_retired=True,state="retired",failure_code="NONE",failures=[])
        def result(**changes):
            return dict(returncode=0,stdout=json.dumps(hello)+"\n"+json.dumps(dict(terminal,**changes)))
        self.assertTrue(display.finite_shell_retired(result()))
        self.assertFalse(display.finite_shell_retired(result(pid=1235)))
        self.assertFalse(display.finite_shell_retired(result(resources_retired=False)))
        failed=result();failed["returncode"]=1
        self.assertFalse(display.finite_shell_retired(failed))

    def test_qms_executable_rejects_control_without_stdout_or_effects(self):
        entry=Path(__file__).parent/"display_stream_qms.py"
        result=subprocess.run([sys.executable,"-B",str(entry),"display-stream-qms-v1"],
            input=b'{"schema":"wrong"}\n',stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
        self.assertEqual(result.returncode,2)
        self.assertEqual(result.stdout,b"")
        self.assertEqual(result.stderr.splitlines(),[b"display_stream_request_rejected"])

    def test_screenrecord_never_kills_a_pid_discovered_after_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            args=self.args(directory,"adb-screenrecord")
            calls=[]
            def runner(command,**kwargs):
                calls.append(command)
                if command[-1]=="get-state": return subprocess.CompletedProcess(command,0,"device","")
                discovered="54321" if len([c for c in calls if "pidof" in c])>1 else ""
                return subprocess.CompletedProcess(command,0,discovered,"")
            def capture(command,path,**kwargs):
                path.write_bytes(b"\x00\x00\x00\x01\x65")
                return dict(returncode=0,bytes_written=5,chunk_count=1,preview={})
            with patch.object(display,"capture_binary_process",side_effect=capture):
                self.assertEqual(display.run_display_stream(args,run_func=runner),2)
            self.assertFalse(any("kill" in c for c in calls),calls)
            report=json.loads(Path(args.out).read_text())
            self.assertIn("hostess.issue.display_stream.screenrecord_cleanup_unknown",report["issue_codes"])

    def test_stop_cli_writes_only_local_request_and_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            args=self.parser().parse_args(["display-stream","stop","--stop-file",str(root/"stop.json"),"--out",str(root/"receipt.json")])
            self.assertEqual(dispatch_command(args),0)
            self.assertEqual(json.loads((root/"receipt.json").read_text())["schema"],display.STOP_REPORT_SCHEMA)
            self.assertTrue((root/"stop.json").is_file())

if __name__=="__main__": unittest.main()
