#!/usr/bin/env python3
"""AI SaaS Template - Ready-to-deploy AI API boilerplate."""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from functools import wraps

import requests
from flask import Flask, jsonify, request, send_from_directory

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saas.db")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

with open(CONFIG_PATH, "r") as f:
    CONFIG = json.load(f)

app = Flask(__name__, static_folder="static")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        tier TEXT NOT NULL DEFAULT 'free',
        created_at TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        tokens_used INTEGER DEFAULT 0,
        timestamp TEXT NOT NULL
    )""")
    conn.commit()
    c.execute("SELECT COUNT(*) FROM api_keys")
    if c.fetchone()[0] == 0:
        demo_key = "demo-" + uuid.uuid4().hex[:24]
        c.execute("INSERT INTO api_keys (key, name, tier, created_at) VALUES (?, ?, ?, ?)",
                  (demo_key, "Demo Key", "free", datetime.utcnow().isoformat()))
        conn.commit()
        print(f"Demo API key created: {demo_key}")
    conn.close()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def check_rate_limit(api_key, tier):
    limits = CONFIG["rate_limits"].get(tier, CONFIG["rate_limits"]["free"])
    window = limits["window_minutes"]
    max_req = limits["max_requests"]
    conn = get_db()
    since = (datetime.utcnow() - timedelta(minutes=window)).isoformat()
    count = conn.execute("SELECT COUNT(*) FROM usage WHERE api_key=? AND timestamp>?",
                         (api_key, since)).fetchone()[0]
    conn.close()
    return count < max_req, max_req - count


def track_usage(api_key, endpoint, tokens=0):
    conn = get_db()
    conn.execute("INSERT INTO usage (api_key, endpoint, tokens_used, timestamp) VALUES (?,?,?,?)",
                 (api_key, endpoint, tokens, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if not api_key:
            return jsonify({"success": False, "error": "Missing API key."}), 401
        conn = get_db()
        row = conn.execute("SELECT * FROM api_keys WHERE key=? AND active=1", (api_key,)).fetchone()
        conn.close()
        if not row:
            return jsonify({"success": False, "error": "Invalid or inactive API key."}), 403
        allowed, remaining = check_rate_limit(api_key, row["tier"])
        if not allowed:
            return jsonify({"success": False, "error": "Rate limit exceeded."}), 429
        request.api_key = api_key
        request.tier = row["tier"]
        request.remaining = remaining
        return f(*args, **kwargs)
    return decorated


def call_ollama(prompt, system_prompt=None):
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    if system_prompt:
        payload["system"] = system_prompt
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return {"text": data.get("response", ""), "tokens": data.get("eval_count", 0)}
    except requests.exceptions.ConnectionError:
        return {"error": "Ollama not reachable at " + OLLAMA_URL}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out."}
    except Exception as e:
        return {"error": str(e)}


@app.route("/")
def landing():
    return send_from_directory("static", "index.html")


@app.route("/health")
def health():
    ollama_ok = False
    try:
        ollama_ok = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).status_code == 200
    except Exception:
        pass
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat(),
                    "ollama_connected": ollama_ok, "version": "1.0.0"})


@app.route("/api/generate", methods=["POST"])
@require_api_key
def api_generate():
    data = request.get_json()
    if not data or "prompt" not in data:
        return jsonify({"success": False, "error": "Missing 'prompt'."}), 400
    result = call_ollama(data["prompt"], data.get("system_prompt"))
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]}), 503
    track_usage(request.api_key, "/api/generate", result.get("tokens", 0))
    return jsonify({"success": True, "data": {"response": result["text"],
                    "tokens_used": result.get("tokens", 0)},
                    "meta": {"model": OLLAMA_MODEL, "remaining_requests": request.remaining - 1}})


@app.route("/api/summarize", methods=["POST"])
@require_api_key
def api_summarize():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"success": False, "error": "Missing 'text'."}), 400
    length = {"short": "2-3 sentences", "medium": "a paragraph", "long": "several paragraphs"}
    inst = length.get(data.get("max_length", "medium"), "a paragraph")
    sys_p = f"Summarize the following text in {inst}. Be concise and capture key points."
    result = call_ollama(f"Summarize:\n\n{data['text']}", sys_p)
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]}), 503
    track_usage(request.api_key, "/api/summarize", result.get("tokens", 0))
    return jsonify({"success": True, "data": {"summary": result["text"],
                    "original_length": len(data["text"]), "tokens_used": result.get("tokens", 0)},
                    "meta": {"model": OLLAMA_MODEL, "remaining_requests": request.remaining - 1}})


@app.route("/api/translate", methods=["POST"])
@require_api_key
def api_translate():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"success": False, "error": "Missing 'text'."}), 400
    if "target_language" not in data:
        return jsonify({"success": False, "error": "Missing 'target_language'."}), 400
    target = data["target_language"]
    source = data.get("source_language", "auto-detect")
    sys_p = f"Translate to {target}. Output only the translation."
    result = call_ollama(f"Translate from {source} to {target}:\n\n{data['text']}", sys_p)
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]}), 503
    track_usage(request.api_key, "/api/translate", result.get("tokens", 0))
    return jsonify({"success": True, "data": {"translation": result["text"],
                    "source_language": source, "target_language": target,
                    "tokens_used": result.get("tokens", 0)},
                    "meta": {"model": OLLAMA_MODEL, "remaining_requests": request.remaining - 1}})


@app.route("/api/usage", methods=["GET"])
@require_api_key
def api_usage():
    conn = get_db()
    totals = conn.execute("SELECT COUNT(*) as t, COALESCE(SUM(tokens_used),0) as tk FROM usage WHERE api_key=?",
                          (request.api_key,)).fetchone()
    by_ep = [{"endpoint": r["endpoint"], "requests": r["c"], "tokens": r["tk"]}
             for r in conn.execute("SELECT endpoint, COUNT(*) as c, COALESCE(SUM(tokens_used),0) as tk FROM usage WHERE api_key=? GROUP BY endpoint",
                                   (request.api_key,)).fetchall()]
    conn.close()
    return jsonify({"success": True, "data": {"total_requests": totals["t"],
                    "total_tokens": totals["tk"], "tier": request.tier, "by_endpoint": by_ep}})


@app.route("/api/keys", methods=["POST"])
def create_api_key():
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"success": False, "error": "Missing 'name'."}), 400
    tier = data.get("tier", "free")
    if tier not in CONFIG["pricing_tiers"]:
        return jsonify({"success": False, "error": f"Invalid tier."}), 400
    new_key = f"{tier[:2]}-" + uuid.uuid4().hex[:28]
    conn = get_db()
    conn.execute("INSERT INTO api_keys (key, name, tier, created_at) VALUES (?,?,?,?)",
                 (new_key, data["name"], tier, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "data": {"api_key": new_key, "name": data["name"],
                    "tier": tier}}), 201


if __name__ == "__main__":
    init_db()
    print("AI SaaS Template running on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
