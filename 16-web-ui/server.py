#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""Personal AI Web UI - Local ChatGPT-like interface powered by Ollama."""

import http.server
import json
import os
import signal
import sys
import threading
import urllib.request
import urllib.error
from pathlib import Path

OLLAMA_BASE = "http://localhost:11434"
PORT = 3000
STATIC_DIR = Path(__file__).parent / "static"

# Track active generation requests for stop functionality
active_requests = {}
active_requests_lock = threading.Lock()


class ChatHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for the chat UI and API."""

    def log_message(self, format, *args):
        """Suppress default logging for cleaner output."""
        pass

    def send_cors_headers(self):
        """Add CORS headers to response."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Handle GET requests - static files and API."""
        if self.path == "/api/models":
            self.handle_models()
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.serve_static()

    def do_POST(self):
        """Handle POST requests - chat API."""
        if self.path == "/api/chat":
            self.handle_chat()
        elif self.path == "/api/chat/stop":
            self.handle_stop()
        else:
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()

    def serve_static(self):
        """Serve static files from the static directory."""
        path = self.path
        if path == "/" or path == "":
            path = "/index.html"

        file_path = STATIC_DIR / path.lstrip("/")

        if not file_path.exists() or not file_path.is_file():
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        content_types = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".png": "image/png",
            ".ico": "image/x-icon",
            ".svg": "image/svg+xml",
        }

        ext = file_path.suffix.lower()
        content_type = content_types.get(ext, "application/octet-stream")

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_cors_headers()
        self.end_headers()

        with open(file_path, "rb") as f:
            self.wfile.write(f.read())

    def handle_models(self):
        """List available Ollama models."""
        try:
            req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            models = [m["name"] for m in data.get("models", [])]

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"models": models}).encode())

        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Cannot connect to Ollama: {e}"}).encode())

    def handle_chat(self):
        """Stream chat responses from Ollama."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode())

            model = data.get("model", "llama3.2")
            messages = data.get("messages", [])
            request_id = data.get("request_id", "default")

            # Register this request as active
            with active_requests_lock:
                active_requests[request_id] = True

            # Build Ollama request
            ollama_payload = json.dumps({
                "model": model,
                "messages": messages,
                "stream": True
            }).encode()

            req = urllib.request.Request(
                f"{OLLAMA_BASE}/api/chat",
                data=ollama_payload,
                headers={"Content-Type": "application/json"}
            )

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_cors_headers()
            self.end_headers()

            with urllib.request.urlopen(req, timeout=300) as resp:
                for line in resp:
                    # Check if request was stopped
                    with active_requests_lock:
                        if request_id not in active_requests:
                            break

                    if line:
                        chunk = json.loads(line.decode())
                        event_data = json.dumps({
                            "content": chunk.get("message", {}).get("content", ""),
                            "done": chunk.get("done", False)
                        })
                        self.wfile.write(f"data: {event_data}\n\n".encode())
                        self.wfile.flush()

            # Clean up
            with active_requests_lock:
                active_requests.pop(request_id, None)

            # Send final done event
            self.wfile.write(f"data: {json.dumps({'content': '', 'done': True})}\n\n".encode())
            self.wfile.flush()

        except (BrokenPipeError, ConnectionResetError):
            with active_requests_lock:
                active_requests.pop(data.get("request_id", "default"), None)
        except Exception as e:
            try:
                error_event = json.dumps({"error": str(e), "done": True})
                self.wfile.write(f"data: {error_event}\n\n".encode())
                self.wfile.flush()
            except Exception:
                pass

    def handle_stop(self):
        """Stop an active generation request."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode()) if body else {}
            request_id = data.get("request_id", "default")

            with active_requests_lock:
                active_requests.pop(request_id, None)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "stopped"}).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())


class ThreadedHTTPServer(http.server.ThreadingHTTPServer):
    """Threaded HTTP server for handling concurrent requests."""
    allow_reuse_address = True


def main():
    """Start the web UI server."""
    server = ThreadedHTTPServer(("0.0.0.0", PORT), ChatHandler)

    def shutdown(sig, frame):
        print("\n🛑 Shutting down server...")
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print(f"""
╔══════════════════════════════════════════╗
║     🤖 Personal AI Web UI              ║
║                                          ║
║     http://localhost:{PORT}               ║
║     Ollama: {OLLAMA_BASE}       ║
╚══════════════════════════════════════════╝
""")

    server.serve_forever()


if __name__ == "__main__":
    main()
