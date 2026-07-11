#!/Users/amrendranarayanmishra/Downloads/AI/.venv/bin/python3
"""AI API Gateway - Unified OpenAI-compatible API gateway routing to Ollama."""

import http.server
import json
import logging
import os
import signal
import sys
import threading
import time
import urllib.request
import urllib.error
from collections import defaultdict
from pathlib import Path

# ===== Configuration =====
CONFIG_PATH = Path(__file__).parent / "config.json"
OLLAMA_BASE = "http://localhost:11434"

def load_config():
    """Load gateway configuration."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {
        "port": 8080,
        "ollama_base": OLLAMA_BASE,
        "api_keys": ["sk-local-dev-key"],
        "rate_limit": {"requests_per_minute": 60, "tokens_per_minute": 100000},
        "routes": {
            "code": "codellama",
            "general": "llama3.2",
            "fast": "phi3",
            "reasoning": "gemma2",
            "vision": "llava"
        },
        "logging": {"file": "gateway.log", "level": "INFO"}
    }

CONFIG = load_config()

# ===== Logging Setup =====
log_file = Path(__file__).parent / CONFIG.get("logging", {}).get("file", "gateway.log")
logging.basicConfig(
    level=getattr(logging, CONFIG.get("logging", {}).get("level", "INFO")),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gateway")

# ===== Rate Limiter =====
class RateLimiter:
    """In-memory rate limiter per API key."""

    def __init__(self, rpm=60, tpm=100000):
        self.rpm = rpm
        self.tpm = tpm
        self.requests = defaultdict(list)  # key -> [timestamps]
        self.tokens = defaultdict(list)    # key -> [(timestamp, count)]
        self.lock = threading.Lock()

    def check(self, key):
        """Check if request is allowed. Returns (allowed, retry_after)."""
        now = time.time()
        window = 60  # 1 minute window

        with self.lock:
            # Clean old entries
            self.requests[key] = [t for t in self.requests[key] if now - t < window]
            self.tokens[key] = [(t, c) for t, c in self.tokens[key] if now - t < window]

            if len(self.requests[key]) >= self.rpm:
                oldest = self.requests[key][0]
                return False, int(window - (now - oldest)) + 1

            self.requests[key].append(now)
            return True, 0

    def add_tokens(self, key, count):
        """Record token usage."""
        with self.lock:
            self.tokens[key].append((time.time(), count))


rate_limiter = RateLimiter(
    rpm=CONFIG.get("rate_limit", {}).get("requests_per_minute", 60),
    tpm=CONFIG.get("rate_limit", {}).get("tokens_per_minute", 100000)
)


# ===== Helper Functions =====
def authenticate(headers):
    """Validate API key from Authorization header."""
    api_keys = CONFIG.get("api_keys", [])
    if not api_keys:
        return True  # No keys configured = open access

    auth = headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        return token in api_keys
    return False


def smart_route(task_description):
    """Auto-select the best model based on task description."""
    routes = CONFIG.get("routes", {})
    text = task_description.lower()

    # Code detection
    code_keywords = ["code", "program", "function", "debug", "syntax", "compile",
                     "algorithm", "implement", "refactor", "bug", "error", "python",
                     "javascript", "java", "rust", "sql", "api", "class", "method"]
    if any(kw in text for kw in code_keywords):
        return routes.get("code", "codellama")

    # Fast/simple detection
    fast_keywords = ["quick", "simple", "short", "brief", "yes or no", "one word",
                     "translate", "define", "spell", "count"]
    if any(kw in text for kw in fast_keywords):
        return routes.get("fast", "phi3")

    # Complex reasoning detection
    reasoning_keywords = ["analyze", "compare", "evaluate", "reason", "logic",
                         "philosophical", "complex", "detailed analysis", "pros and cons",
                         "explain in depth", "step by step", "mathematical proof",
                         "critical thinking"]
    if any(kw in text for kw in reasoning_keywords):
        return routes.get("reasoning", "gemma2")

    # Default to general
    return routes.get("general", "llama3.2")


def ollama_request(path, data=None, method="POST", stream=False):
    """Make a request to Ollama."""
    url = f"{CONFIG.get('ollama_base', OLLAMA_BASE)}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")

    if stream:
        return urllib.request.urlopen(req, timeout=300)
    else:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())


def convert_to_openai_response(ollama_resp, model):
    """Convert Ollama response to OpenAI format."""
    return {
        "id": f"chatcmpl-{int(time.time()*1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": ollama_resp.get("message", {}).get("content", "")
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": ollama_resp.get("prompt_eval_count", 0),
            "completion_tokens": ollama_resp.get("eval_count", 0),
            "total_tokens": ollama_resp.get("prompt_eval_count", 0) + ollama_resp.get("eval_count", 0)
        }
    }


# ===== Request Handler =====
class GatewayHandler(http.server.BaseHTTPRequestHandler):
    """API Gateway request handler."""

    def log_message(self, format, *args):
        """Log to file instead of stderr."""
        logger.info(f"{self.client_address[0]} - {format % args}")

    def send_json(self, status, data):
        """Send JSON response."""
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status, message, error_type="error"):
        """Send error response in OpenAI format."""
        self.send_json(status, {
            "error": {
                "message": message,
                "type": error_type,
                "code": status
            }
        })

    def read_body(self):
        """Read and parse JSON body."""
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode())

    def check_auth(self):
        """Check authentication. Returns True if authorized."""
        if not authenticate(dict(self.headers)):
            self.send_error_json(401, "Invalid API key", "authentication_error")
            return False
        return True

    def check_rate_limit(self):
        """Check rate limit. Returns True if allowed."""
        auth = self.headers.get("Authorization", "anonymous")
        key = auth[7:] if auth.startswith("Bearer ") else "anonymous"
        allowed, retry_after = rate_limiter.check(key)
        if not allowed:
            self.send_response(429)
            self.send_header("Content-Type", "application/json")
            self.send_header("Retry-After", str(retry_after))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": {
                    "message": f"Rate limit exceeded. Retry after {retry_after}s",
                    "type": "rate_limit_error",
                    "code": 429
                }
            }).encode())
            return False
        return True

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/v1/models":
            self.handle_list_models()
        elif self.path == "/health":
            self.handle_health()
        else:
            self.send_error_json(404, "Not found")

    def do_POST(self):
        """Handle POST requests."""
        if not self.check_auth():
            return
        if not self.check_rate_limit():
            return

        if self.path == "/v1/chat/completions":
            self.handle_chat_completions()
        elif self.path == "/v1/embeddings":
            self.handle_embeddings()
        elif self.path == "/v1/images/analyze":
            self.handle_image_analysis()
        elif self.path == "/route":
            self.handle_smart_route()
        else:
            self.send_error_json(404, "Not found")


    # ===== Endpoint Handlers =====
    def handle_health(self):
        """Health check endpoint."""
        try:
            req = urllib.request.Request(f"{CONFIG.get('ollama_base', OLLAMA_BASE)}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                ollama_status = "healthy"
        except Exception:
            ollama_status = "unhealthy"

        self.send_json(200, {
            "status": "healthy",
            "ollama": ollama_status,
            "uptime": time.time() - START_TIME,
            "version": "1.0.0"
        })

    def handle_list_models(self):
        """List available models in OpenAI format."""
        try:
            data = ollama_request("/api/tags", method="GET")
            models = []
            for m in data.get("models", []):
                models.append({
                    "id": m["name"],
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "ollama",
                    "permission": []
                })
            self.send_json(200, {"object": "list", "data": models})
        except Exception as e:
            self.send_error_json(502, f"Cannot connect to Ollama: {e}")

    def handle_chat_completions(self):
        """OpenAI-compatible chat completions endpoint."""
        try:
            body = self.read_body()
            model = body.get("model", CONFIG.get("routes", {}).get("general", "llama3.2"))
            messages = body.get("messages", [])
            stream = body.get("stream", False)

            if not messages:
                self.send_error_json(400, "messages field is required")
                return

            logger.info(f"Chat completion: model={model}, messages={len(messages)}, stream={stream}")

            if stream:
                self.handle_stream_chat(model, messages)
            else:
                ollama_data = {"model": model, "messages": messages, "stream": False}
                resp = ollama_request("/api/chat", ollama_data)
                openai_resp = convert_to_openai_response(resp, model)
                rate_limiter.add_tokens(
                    self.headers.get("Authorization", "anonymous"),
                    openai_resp["usage"]["total_tokens"]
                )
                self.send_json(200, openai_resp)

        except urllib.error.URLError as e:
            self.send_error_json(502, f"Ollama connection error: {e}")
        except Exception as e:
            logger.error(f"Chat error: {e}")
            self.send_error_json(500, str(e))

    def handle_stream_chat(self, model, messages):
        """Handle streaming chat completions."""
        try:
            ollama_data = {"model": model, "messages": messages, "stream": True}
            resp = ollama_request("/api/chat", ollama_data, stream=True)

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            for line in resp:
                if line:
                    chunk = json.loads(line.decode())
                    openai_chunk = {
                        "id": f"chatcmpl-{int(time.time()*1000)}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": chunk.get("message", {}).get("content", "")},
                            "finish_reason": "stop" if chunk.get("done") else None
                        }]
                    }
                    self.wfile.write(f"data: {json.dumps(openai_chunk)}\n\n".encode())
                    self.wfile.flush()

            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
            resp.close()

        except Exception as e:
            logger.error(f"Stream error: {e}")

    def handle_embeddings(self):
        """Generate embeddings using Ollama."""
        try:
            body = self.read_body()
            model = body.get("model", "nomic-embed-text")
            input_text = body.get("input", "")

            if isinstance(input_text, list):
                texts = input_text
            else:
                texts = [input_text]

            embeddings = []
            for i, text in enumerate(texts):
                resp = ollama_request("/api/embeddings", {
                    "model": model,
                    "prompt": text
                })
                embeddings.append({
                    "object": "embedding",
                    "embedding": resp.get("embedding", []),
                    "index": i
                })

            self.send_json(200, {
                "object": "list",
                "data": embeddings,
                "model": model,
                "usage": {"prompt_tokens": sum(len(t.split()) for t in texts), "total_tokens": sum(len(t.split()) for t in texts)}
            })

        except Exception as e:
            logger.error(f"Embedding error: {e}")
            self.send_error_json(500, str(e))

    def handle_image_analysis(self):
        """Analyze images using llava model."""
        try:
            body = self.read_body()
            model = CONFIG.get("routes", {}).get("vision", "llava")
            prompt = body.get("prompt", "Describe this image in detail.")
            images = body.get("images", [])  # Base64 encoded images

            if not images:
                self.send_error_json(400, "images field is required (base64 encoded)")
                return

            logger.info(f"Image analysis: model={model}, images={len(images)}")

            resp = ollama_request("/api/generate", {
                "model": model,
                "prompt": prompt,
                "images": images,
                "stream": False
            })

            self.send_json(200, {
                "model": model,
                "response": resp.get("response", ""),
                "done": True
            })

        except Exception as e:
            logger.error(f"Image analysis error: {e}")
            self.send_error_json(500, str(e))

    def handle_smart_route(self):
        """Smart routing - auto-select best model based on task."""
        try:
            body = self.read_body()
            task = body.get("task", body.get("prompt", body.get("message", "")))
            messages = body.get("messages", [])

            if not task and messages:
                task = messages[-1].get("content", "")

            if not task:
                self.send_error_json(400, "task or messages field is required")
                return

            selected_model = smart_route(task)
            logger.info(f"Smart route: task='{task[:50]}...' -> model={selected_model}")

            # If messages provided, also run the completion
            if messages or body.get("run", False):
                msgs = messages if messages else [{"role": "user", "content": task}]
                ollama_data = {"model": selected_model, "messages": msgs, "stream": False}
                resp = ollama_request("/api/chat", ollama_data)
                openai_resp = convert_to_openai_response(resp, selected_model)
                openai_resp["routed_model"] = selected_model
                openai_resp["routing_reason"] = f"Task classified and routed to {selected_model}"
                self.send_json(200, openai_resp)
            else:
                self.send_json(200, {
                    "model": selected_model,
                    "task": task[:100],
                    "routing_reason": f"Task classified and routed to {selected_model}"
                })

        except Exception as e:
            logger.error(f"Smart route error: {e}")
            self.send_error_json(500, str(e))


# ===== Server =====
START_TIME = time.time()


class ThreadedHTTPServer(http.server.ThreadingHTTPServer):
    """Threaded HTTP server."""
    allow_reuse_address = True


def main():
    """Start the API gateway."""
    port = CONFIG.get("port", 8080)
    server = ThreadedHTTPServer(("0.0.0.0", port), GatewayHandler)

    def shutdown(sig, frame):
        print("\n🛑 Shutting down gateway...")
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print(f"""
╔══════════════════════════════════════════════╗
║     🌐 AI API Gateway v1.0                  ║
║                                              ║
║     http://localhost:{port}                   ║
║     Ollama: {CONFIG.get('ollama_base', OLLAMA_BASE)}       ║
║                                              ║
║     Endpoints:                               ║
║       POST /v1/chat/completions              ║
║       POST /v1/embeddings                    ║
║       POST /v1/images/analyze                ║
║       GET  /v1/models                        ║
║       POST /route (smart routing)            ║
║       GET  /health                           ║
╚══════════════════════════════════════════════╝
""")

    logger.info(f"Gateway started on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
