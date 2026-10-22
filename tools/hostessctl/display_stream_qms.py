"""One explicitly selected owned display producer; no service, power or app policy.

Stdout is RMANVID1 only. Root-selected bindings and typed stdin control select
one exact invocation. All uncertain native effects retain their original scope.
"""
from __future__ import annotations
import datetime, hashlib, io, json, os, pathlib, queue, re, socket, struct, subprocess, threading, time

START = {"schema", "sourceId", "invocationId", "generation", "stopNonce", "ownerBindingRef", "outputDirectory"}
STOP = {"schema", "sourceId", "invocationId", "generation", "stopNonce"}
BINDING = {"schema", "adb", "shellJar", "transport", "canonical", "bootId", "remotePort", "displayId", "width", "height", "fps", "bitrateBps"}
HEX = re.compile(r"[0-9a-f]{32}")
TOKEN = re.compile(r"[A-Za-z0-9._:-]{1,128}")
MAIN_CLASS = "io.github.mesmerprism.rustyquest.displaystream.ShellDisplayMirrorMain"
MAX_PACKET = 4 * 1024 * 1024 - 12


def require(value, message):
    if not value:
        raise ValueError(message)


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate control field")
            result[key] = value
        return result
    return json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs)


def read_line(stream, maximum=4096):
    output = bytearray()
    while True:
        value = stream.read(1)
        if value == b"\n":
            return bytes(output)
        if not value:
            require(not output, "truncated control")
            return None
        require(len(output) < maximum and value != b"\r", "control exceeds bound")
        output.extend(value)


def checked_start(raw):
    value = decode(raw)
    require(set(value) == START and value["schema"] == "questms.display.start.v1", "closed start required")
    require(all(type(value[k]) is str and TOKEN.fullmatch(value[k]) for k in ("sourceId", "generation")), "source/generation invalid")
    require(all(type(value[k]) is str and HEX.fullmatch(value[k]) for k in ("invocationId", "stopNonce")), "invocation/nonce invalid")
    require(type(value["outputDirectory"]) is str and pathlib.Path(value["outputDirectory"]).is_absolute(), "absolute new output required")
    return value


def checked_stop(raw, start):
    value = decode(raw)
    require(set(value) == STOP and value["schema"] == "questms.display.stop.v1", "closed stop required")
    require(all(value[k] == start[k] for k in STOP - {"schema"}), "stop identity differs")
    return value


def pin(path):
    path = pathlib.Path(path).resolve(strict=True)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest}


def read_binding(ref):
    require(type(ref) is dict and set(ref) == {"path", "bytes", "sha256"} and pin(ref["path"]) == ref, "binding bytes changed")
    value = decode(pathlib.Path(ref["path"]).read_bytes())
    require(set(value) == BINDING and value["schema"] == "rusty.hostess.display_stream.owner_binding.v1", "closed binding required")
    for name in ("adb", "shellJar"):
        require(pin(value[name]["path"]) == value[name], "selected tool changed")
    for name in ("transport", "canonical"):
        require(type(value[name]) is str and TOKEN.fullmatch(value[name]), "selected device invalid")
    require(type(value["bootId"]) is str and re.fullmatch(r"[0-9a-f-]{36}", value["bootId"]), "boot invalid")
    for name, lo, hi in [("remotePort", 1, 65535), ("displayId", 0, 32), ("width", 320, 4096), ("height", 240, 4096), ("fps", 1, 90), ("bitrateBps", 100000, 80000000)]:
        require(type(value[name]) is int and lo <= value[name] <= hi, "display setting invalid")
    require(value["width"] % 2 == value["height"] % 2 == 0, "even dimensions required")
    return value


def write_new(path, value):
    with pathlib.Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, separators=(",", ":")); stream.write("\n"); stream.flush(); os.fsync(stream.fileno())


def exact(stream, size):
    result = bytearray()
    while len(result) < size:
        part = stream.read(size - len(result))
        require(part, "truncated media")
        result.extend(part)
    return bytes(result)


def pump_media(source, target, start, stats):
    header = exact(source, 32)
    magic, version, codec, width, height, reserved, length = struct.unpack(">8s6I", header)
    require(magic == b"RMANVID1" and version == codec == 1 and reserved == 0, "display-v1 header required")
    require(0 < width <= 4096 and 0 < height <= 4096 and 0 < length <= 65536, "metadata bound")
    metadata_raw = exact(source, length); metadata = decode(metadata_raw)
    require(metadata.get("invocation_id") == start["invocationId"] and metadata.get("generation") == start["generation"], "media incarnation differs")
    target.write(header + metadata_raw); target.flush()
    last_pts = None; configured = False; keyed = False
    while True:
        first = source.read(1)
        if not first:
            return
        packet = first + exact(source, 31)
        pts, flags, length, elapsed, unix = struct.unpack(">QIIQQ", packet)
        require(flags & ~3 == 0 and 0 < length <= MAX_PACKET and pts <= (1 << 53) - 1, "packet bound/flags/PTS")
        config = bool(flags & 2)
        require(not config or length <= 262132, "config packet bound")
        if config:
            configured = True; keyed = False
        else:
            require(configured and (keyed or flags & 1) and (last_pts is None or pts > last_pts), "video config/key/PTS order")
            keyed = True; last_pts = pts
        payload = exact(source, length)
        target.write(packet); target.write(payload); target.flush()
        stats["packets"] += 1


class RemoteChild:
    def __init__(self, process, output, start):
        self.process, self.output, self.start = process, output, start
        self.records = queue.Queue(maxsize=4); self.eof = {}; self.errors = []; self.raw = {}
        self.threads = []
        for label in ("stdout", "stderr"):
            thread = threading.Thread(target=self._drain, args=(label,), daemon=True)
            self.threads.append(thread); thread.start()

    def _drain(self, label):
        kept = bytearray(); complete = True
        try:
            source = getattr(self.process, label)
            while True:
                line = source.readline(4097)
                if not line:
                    break
                if len(kept) + len(line) <= 32768:
                    kept.extend(line)
                else:
                    complete = False
                if label == "stdout":
                    try:
                        require(len(line) <= 4096 and line.endswith(b"\n"), "remote record bound")
                        self.records.put_nowait(decode(line))
                    except Exception:
                        self.errors.append("REMOTE_RECORD_INVALID")
            self.eof[label] = complete
        except Exception:
            self.eof[label] = False; self.errors.append("REMOTE_DRAIN_FAILED")
        finally:
            self.raw[label] = bytes(kept)
            try:
                with (self.output / ("REMOTE_" + label + ".raw")).open("xb") as stream:
                    stream.write(kept)
            except Exception:
                self.eof[label] = False; self.errors.append("REMOTE_RETENTION_FAILED")

    def record(self, schema):
        while True:
            try:
                value = self.records.get(timeout=0.1)
                break
            except queue.Empty:
                require("stdout" not in self.eof, "remote EOF before required receipt")
        require(value.get("schema") == schema, "remote record schema/order")
        keys = {"schema", "invocation_id", "generation", "stop_nonce", "pid", "uid", "start_ticks"}
        if schema == "rusty.quest.display_stream.terminal.v1":
            keys |= {"stop_observed", "worker_retired", "resources_retired", "state", "failure_code", "failures"}
        require(set(value) == keys and type(value["pid"]) is int and value["pid"] > 0
                and value["uid"] == 2000 and type(value["start_ticks"]) is int
                and value["start_ticks"] > 0, "closed remote actor record required")
        require(all(value.get(remote) == self.start[local] for remote, local in [("invocation_id", "invocationId"), ("generation", "generation"), ("stop_nonce", "stopNonce")]), "remote identity differs")
        return value

    def stop(self):
        value = {"schema": "rusty.quest.display_stream.control.v1", "action": "stop", "invocation_id": self.start["invocationId"], "generation": self.start["generation"], "stop_nonce": self.start["stopNonce"]}
        self.process.stdin.write(json.dumps(value, separators=(",", ":")).encode("ascii") + b"\n")
        self.process.stdin.flush(); self.process.stdin.close()

    def finish(self):
        code = self.process.wait()  # A report deadline cannot certify or force retirement.
        for thread in self.threads:
            thread.join()
        return code


class Adapter:
    def __init__(self, binding, output):
        self.binding, self.output, self.sequence = binding, output, 0

    def adb(self, args, check=True):
        command = [self.binding["adb"]["path"], "-s", self.binding["transport"], *args]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.sequence += 1
        stem = self.output / ("ADB_%03d" % self.sequence)
        with pathlib.Path(str(stem) + ".stdout").open("xb") as stream: stream.write(result.stdout)
        with pathlib.Path(str(stem) + ".stderr").open("xb") as stream: stream.write(result.stderr)
        write_new(str(stem) + ".json", {"arguments": args, "exit": result.returncode, "stdoutEof": True, "stderrEof": True})
        if check: require(result.returncode == 0, "owned ADB action failed")
        return result

    def guard(self):
        require(pin(self.binding["adb"]["path"]) == self.binding["adb"], "selected ADB bytes changed")
        require(self.adb(["shell", "getprop", "ro.serialno"]).stdout.decode().strip() == self.binding["canonical"], "canonical identity changed")
        require(self.adb(["shell", "cat", "/proc/sys/kernel/random/boot_id"]).stdout.decode().strip() == self.binding["bootId"], "boot changed")

    def listener(self):
        value = socket.socket(); value.bind(("127.0.0.1", 0)); value.listen(1); value.settimeout(15)
        return value

    def launch(self, command):
        return subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def require_actor(self, hello):
        require(type(hello.get("pid")) is int and hello["pid"] > 0 and hello.get("uid") == 2000, "shell actor required")
        raw = self.adb(["shell", "cat", "/proc/%d/stat" % hello["pid"]]).stdout.decode()
        require(int(raw.split(" ", 1)[0]) == hello["pid"] and int(raw.rsplit(") ", 1)[1].split()[19]) == hello["start_ticks"], "remote process incarnation changed")
        uid = self.adb(["shell", "cat", "/proc/%d/status" % hello["pid"]]).stdout
        require(re.search(rb"(?m)^Uid:\s+2000\s+2000\s+2000\s+2000\s*$", uid), "remote UID changed")

    def require_absent(self, hello):
        result = self.adb(["shell", "cat", "/proc/%d/stat" % hello["pid"]], check=False)
        if result.returncode != 0:
            require(not result.stdout and b"No such file or directory" in result.stderr, "remote absence unknown")
        else:
            require(int(result.stdout.decode().rsplit(") ", 1)[1].split()[19]) != hello["start_ticks"], "original remote actor still live")


def run(start, input_stream, binary_output, *, adapter_factory=Adapter):
    output = pathlib.Path(start["outputDirectory"]); output.mkdir(exist_ok=False)
    write_new(output / "INTENT.json", dict(start, automaticRetry=False))
    terminal = dict(schema="questms.display.terminal.v1", **{k: start[k] for k in ("sourceId", "invocationId", "generation", "stopNonce")}, state="unknown", nativeChildExitCode=None, nativeStdoutEof=False, nativeStderrEof=False, remoteAckMatched=False, resourcesRetired=False, receipt="NATIVE_OUTCOME.json")
    child = None; listener = None; media = None; pump = None; error = None; hello = None
    remote_started = False; effects_started = False; directory_owned = reverse_owned = False
    stats = {"packets": 0}; pump_errors = []; stop_sent = threading.Event(); control_errors = []
    remote_dir = "/data/local/tmp/rusty-quest-display-" + start["invocationId"]
    remote_jar = remote_dir + "/producer.jar"
    try:
        binding = read_binding(start["ownerBindingRef"]); adapter = adapter_factory(binding, output)
        adapter.guard()
        effects_started = True
        adapter.adb(["shell", "mkdir", remote_dir]); directory_owned = True
        adapter.guard(); adapter.adb(["push", binding["shellJar"]["path"], remote_jar])
        require(pin(binding["shellJar"]["path"]) == binding["shellJar"], "source changed during push")
        require(adapter.adb(["shell", "sha256sum", remote_jar]).stdout.decode().split()[0] == binding["shellJar"]["sha256"], "remote jar differs")
        listener = adapter.listener(); local_port = listener.getsockname()[1]; remote_port = "tcp:%d" % binding["remotePort"]
        adapter.guard(); adapter.adb(["reverse", "--no-rebind", remote_port, "tcp:%d" % local_port]); reverse_owned = True
        command = [binding["adb"]["path"], "-s", binding["transport"], "shell", "-T", "env", "CLASSPATH=" + remote_jar, "app_process", "/system/bin", MAIN_CLASS]
        for name, value in [("host", "127.0.0.1"), ("port", binding["remotePort"]), ("display-id", binding["displayId"]), ("width", binding["width"]), ("height", binding["height"]), ("fps", binding["fps"]), ("bitrate-bps", binding["bitrateBps"]), ("duration-seconds", 0), ("invocation-id", start["invocationId"]), ("generation", start["generation"]), ("stop-nonce", start["stopNonce"])]:
            command += ["--" + name, str(value)]
        adapter.guard(); write_new(output / "REMOTE_ONCE_INTENT.json", {"command": command, "automaticRetry": False})
        remote_started = True; child = RemoteChild(adapter.launch(command), output, start)
        hello = child.record("rusty.quest.display_stream.hello.v1"); adapter.require_actor(hello)
        def control():
            try:
                raw = read_line(input_stream)
                require(raw is not None, "parent control EOF without Stop")
                checked_stop(raw, start); adapter.guard(); adapter.require_actor(hello)
                write_new(output / "STOP_ONCE_INTENT.json", {"invocationId": start["invocationId"], "generation": start["generation"], "automaticRetry": False})
                stop_sent.set(); child.stop()
            except Exception:
                control_errors.append("CONTROL_UNKNOWN")
                # Closing only our stdin asks this exact child to retire after host loss.
                try: child.process.stdin.close()
                except Exception: pass
        controller = threading.Thread(target=control, daemon=True); controller.start()
        media, _ = listener.accept(); media_file = media.makefile("rb", buffering=0)
        def receive():
            try: pump_media(media_file, binary_output, start, stats)
            except Exception: pump_errors.append("MEDIA_FAILED")
            finally: media_file.close()
        pump = threading.Thread(target=receive); pump.start()
        ack = child.record("rusty.quest.display_stream.terminal.v1")
        if ack.get("stop_observed") is True:
            controller.join()
        terminal["remoteAckMatched"] = all(ack.get(k) == hello[k] for k in ("pid", "uid", "start_ticks")) and ack.get("stop_observed") is True and stop_sent.is_set()
        terminal["nativeChildExitCode"] = child.finish()
        terminal["nativeStdoutEof"] = child.eof.get("stdout", False)
        terminal["nativeStderrEof"] = child.eof.get("stderr", False)
        pump.join(); adapter.guard(); adapter.require_absent(hello)
        terminal["resourcesRetired"] = ack.get("worker_retired") is ack.get("resources_retired") is True
        require(ack.get("state") == "retired" and ack.get("failure_code") == "NONE" and ack.get("failures") == [], "remote retirement unconfirmed")
        require(terminal["remoteAckMatched"] and terminal["resourcesRetired"] and terminal["nativeChildExitCode"] == 0 and terminal["nativeStdoutEof"] and terminal["nativeStderrEof"] and not child.errors and child.records.empty() and not control_errors and not pump_errors, "capture/retirement unknown")
        terminal["state"] = "retired"
    except Exception as failure:
        error = type(failure).__name__
        terminal["state"] = "unknown" if effects_started else "failed"
    finally:
        if child is not None and terminal["nativeChildExitCode"] is None:
            try: child.process.stdin.close()
            except Exception: pass
            try:
                terminal["nativeChildExitCode"] = child.finish()
                terminal["nativeStdoutEof"] = child.eof.get("stdout", False)
                terminal["nativeStderrEof"] = child.eof.get("stderr", False)
            except Exception: pass
        if listener is not None: listener.close()
        if media is not None: media.close()
        # Remote effects are never force-killed or replayed after uncertainty.
        if terminal["state"] == "retired" or not remote_started:
            try:
                if reverse_owned:
                    adapter.guard()
                    rows = [line.split()[-2:] for line in adapter.adb(["reverse", "--list"]).stdout.decode().splitlines()]
                    matching = [row for row in rows if row and row[0] == remote_port]
                    require(matching == [[remote_port, "tcp:%d" % local_port]], "reverse ownership changed")
                    adapter.adb(["reverse", "--remove", remote_port])
                if directory_owned:
                    adapter.guard()
                    require(adapter.adb(["shell", "sha256sum", remote_jar]).stdout.decode().split()[0]
                            == binding["shellJar"]["sha256"], "staged jar ownership changed")
                    adapter.adb(["shell", "rm", remote_jar]); adapter.adb(["shell", "rmdir", remote_dir])
            except Exception:
                terminal["state"] = "unknown"; terminal["resourcesRetired"] = False
        write_new(output / "NATIVE_OUTCOME.json", dict(terminal, error=error, packetCount=stats["packets"], noReplay=True))
        write_new(output / "TERMINAL.json", terminal)
    return 0 if terminal["state"] == "retired" else 2
