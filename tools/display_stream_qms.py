"""Closed QMS child entrypoint; never starts implicitly."""
import io, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools.hostessctl.display_stream_qms import checked_start, read_line, run

def main():
    if sys.argv[1:] != ["display-stream-qms-v1"]:
        return 2
    control = io.FileIO(sys.stdin.fileno(), "rb", closefd=False)
    start = checked_start(read_line(control))
    return run(start, control, sys.stdout.buffer)

if __name__ == "__main__":
    try: sys.exit(main())
    except Exception:
        sys.stderr.write("display_stream_request_rejected\n"); sys.exit(2)
