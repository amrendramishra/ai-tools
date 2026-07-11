#!/usr/bin/env python3
"""
Mac Desktop AI Widget - Web-based alternative.
Starts a local server on port 3001 and opens a small browser window.
Queries Ollama at localhost:11434 with SSE streaming.
"""

import os
import sys
import json
import signal
import subprocess
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
PORT = 3001
HOST = "127.0.0.1"
STATIC_DIR = Path(__file__).parent / "static"


class WidgetHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the widget server."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)
    
    def do_GET(self):
        if self.path == "/":
            self.path = "/widget.html"
            return super().do_GET()
        elif self.path == "/api/models":
            self.handle_models()
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            return super().do_GET()
    
    def do_POST(self):
        if self.path == "/api/chat":
            self.handle_chat()
        else:
            self.send_error(404)
    
    def handle_models(self):
        """Fetch and return available Ollama models."""
        try:
            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                models = [m["name"] for m in data.get("models", [])]
        except Exception:
            models = ["llama3.2"]
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"models": models}).encode())
    
    def handle_chat(self):
        """Handle chat request with SSE streaming."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        request_data = json.loads(body)
        
        model = request_data.get("model", "llama3.2")
        messages = request_data.get("messages", [])
        
        # Set up SSE response
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        try:
            payload = json.dumps({
                "model": model,
                "messages": messages[-10:],
                "stream": True
            }).encode()
            
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            
            with urllib.request.urlopen(req, timeout=120) as resp:
                for line in resp:
                    if line:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            chunk = data["message"]["content"]
                            sse_data = json.dumps({"content": chunk, "done": False})
                            self.wfile.write(f"data: {sse_data}\n\n".encode())
                            self.wfile.flush()
                        if data.get("done"):
                            sse_data = json.dumps({"content": "", "done": True})
                            self.wfile.write(f"data: {sse_data}\n\n".encode())
                            self.wfile.flush()
                            break
        except Exception as e:
            error_data = json.dumps({"error": str(e), "done": True})
            self.wfile.write(f"data: {error_data}\n\n".encode())
            self.wfile.flush()
    
    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default logging for cleaner output."""
        pass


def open_browser():
    """Open browser in app mode for widget-like experience."""
    url = f"http://{HOST}:{PORT}"
    
    # Try Chrome app mode first (frameless, compact)
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ]
    
    for chrome in chrome_paths:
        if os.path.exists(chrome):
            try:
                subprocess.Popen([
                    chrome,
                    f"--app={url}",
                    "--window-size=340,480",
                    "--window-position=1100,50",
                    "--disable-extensions",
                    "--new-window"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"Opened in app mode: {os.path.basename(chrome)}")
                return
            except Exception:
                continue
    
    # Fallback: open in default browser
    try:
        subprocess.Popen(["open", url])
        print("Opened in default browser")
    except Exception:
        print(f"Open manually: {url}")


def main():
    # Ensure static directory exists
    if not STATIC_DIR.exists():
        print(f"Error: Static directory not found: {STATIC_DIR}")
        sys.exit(1)
    
    if not (STATIC_DIR / "widget.html").exists():
        print(f"Error: widget.html not found in {STATIC_DIR}")
        sys.exit(1)
    
    # Create server
    server = HTTPServer((HOST, PORT), WidgetHandler)
    
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\nShutting down widget server...")
        server.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print(f"╔══════════════════════════════════════╗")
    print(f"║   AI Desktop Widget (Web Mode)       ║")
    print(f"║   Server: http://{HOST}:{PORT}     ║")
    print(f"║   Press Ctrl+C to quit               ║")
    print(f"╚══════════════════════════════════════╝")
    
    # Open browser after short delay
    timer = threading.Timer(1.0, open_browser)
    timer.daemon = True
    timer.start()
    
    # Run server
    server.serve_forever()


if __name__ == "__main__":
    main()
