import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "dash_integration" / "output"

TRACE_FILE = OUTPUT / "dash_playback_trace.json"
P1203_FILE = OUTPUT / "p1203_dash_input.json"

HOST = "127.0.0.1"
PORT = 8765


class Handler(BaseHTTPRequestHandler):

    def _send_json(self, status, data):
        body = json.dumps(data, indent=2).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):

        if self.path == "/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "service": "DASH -> P.1203 bridge"
                }
            )
            return

        if self.path == "/result":

            result_file = OUTPUT / "p1203_result.json"

            if not result_file.exists():
                self._send_json(
                    404,
                    {
                        "error": "No P.1203 result available yet."
                    }
                )
                return

            try:
                data = json.loads(
                    result_file.read_text(encoding="utf-8")
                )

                self._send_json(200, data)

            except Exception as exc:
                self._send_json(
                    500,
                    {
                        "error": str(exc)
                    }
                )

            return

        self._send_json(
            404,
            {
                "error": "Not found"
            }
        )

    def do_POST(self):

        if self.path != "/trace":
            self._send_json(
                404,
                {
                    "error": "Not found"
                }
            )
            return

        try:

            length = int(
                self.headers.get("Content-Length", "0")
            )

            raw = self.rfile.read(length)

            trace_data = json.loads(
                raw.decode("utf-8")
            )

            if "trace" not in trace_data:
                raise ValueError(
                    "Request does not contain 'trace'."
                )

            OUTPUT.mkdir(
                parents=True,
                exist_ok=True
            )

            TRACE_FILE.write_text(
                json.dumps(
                    trace_data,
                    indent=2
                ),
                encoding="utf-8"
            )

            print()
            print("=" * 60)
            print("DASH TRACE RECEIVED")
            print("=" * 60)

            print(
                f"Duration: "
                f"{trace_data.get('duration')}"
            )

            print(
                f"Events: "
                f"{len(trace_data.get('trace', []))}"
            )

            print(
                f"Saved: {TRACE_FILE}"
            )

            # Convert DASH trace -> P.1203 input
            conversion = subprocess.run(
                [
                    sys.executable,
                    str(
                        ROOT /
                        "dash_integration" /
                        "trace_to_p1203.py"
                    )
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True
            )

            if conversion.returncode != 0:

                print(conversion.stdout)
                print(conversion.stderr)

                self._send_json(
                    500,
                    {
                        "error":
                            "DASH -> P.1203 conversion failed",
                        "stdout":
                            conversion.stdout,
                        "stderr":
                            conversion.stderr
                    }
                )

                return

            print(conversion.stdout)

            # Run P.1203
            p1203 = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "itu_p1203",
                    str(P1203_FILE),
                    "--cpu-count",
                    "1",
                    "--accept-notice"
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True
            )

            if p1203.returncode != 0:

                print(p1203.stdout)
                print(p1203.stderr)

                self._send_json(
                    500,
                    {
                        "error":
                            "P.1203 calculation failed",
                        "stdout":
                            p1203.stdout,
                        "stderr":
                            p1203.stderr
                    }
                )

                return

            try:
                result = json.loads(
                    p1203.stdout
                )
            except json.JSONDecodeError:

                result = {
                    "raw_output":
                        p1203.stdout
                }

            result_file = OUTPUT / "p1203_result.json"

            result_file.write_text(
                json.dumps(
                    result,
                    indent=2
                ),
                encoding="utf-8"
            )

            print()
            print("=" * 60)
            print("P.1203 CALCULATION COMPLETE")
            print("=" * 60)

            print(
                json.dumps(
                    result,
                    indent=2
                )
            )

            self._send_json(
                200,
                result
            )

        except Exception as exc:

            print(
                "Bridge error:",
                repr(exc)
            )

            self._send_json(
                500,
                {
                    "error": str(exc)
                }
            )


if __name__ == "__main__":

    print("=" * 60)
    print("DASH -> P.1203 BRIDGE")
    print("=" * 60)

    print(
        f"Listening on http://{HOST}:{PORT}"
    )

    print(
        "Health: http://"
        f"{HOST}:{PORT}/health"
    )

    print(
        "Trace endpoint: POST /trace"
    )

    print(
        "Result endpoint: "
        f"http://{HOST}:{PORT}/result"
    )

    print()

    server = ThreadingHTTPServer(
        (HOST, PORT),
        Handler
    )

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nStopping server...")

    finally:
        server.server_close()