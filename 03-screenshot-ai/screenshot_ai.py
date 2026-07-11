#!/usr/bin/env python3
"""Screenshot AI - Capture and analyze screenshots using Ollama's llava model."""

import argparse
import base64
import json
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
MODEL = "llava"
CAPTURES_DIR = Path(__file__).parent / "captures"


def ensure_captures_dir():
    """Ensure the captures directory exists."""
    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)


def get_latest_screenshot():
    """Get the most recent screenshot from captures directory."""
    ensure_captures_dir()
    screenshots = sorted(
        CAPTURES_DIR.glob("*.png"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return screenshots[0] if screenshots else None


def capture_screenshot(mode="full"):
    """Take a screenshot using macOS screencapture command."""
    ensure_captures_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = CAPTURES_DIR / f"screenshot_{timestamp}.png"

    cmd = ["screencapture"]
    if mode == "selection":
        cmd.append("-i")
    elif mode == "window":
        cmd.extend(["-i", "-w"])

    cmd.append(str(filename))

    print(f"📸 Taking screenshot ({mode} mode)...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Screenshot failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    if not filename.exists():
        print("❌ Screenshot was cancelled.", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Screenshot saved: {filename}")
    return filename


def image_to_base64(image_path):
    """Convert an image file to base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def query_ollama(prompt, image_path):
    """Send an image to Ollama's llava model for analysis."""
    image_b64 = image_to_base64(image_path)

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "No response received.")
    except urllib.error.URLError as e:
        return f"Error connecting to Ollama: {e}\nMake sure Ollama is running and llava model is pulled."
    except Exception as e:
        return f"Error: {e}"


def analyze_screenshot(image_path):
    """Analyze a screenshot - extract text and describe content."""
    prompt = (
        "Analyze this screenshot. Extract any visible text and describe "
        "what you see. Include: UI elements, text content, application name "
        "if visible, and any notable information."
    )
    return query_ollama(prompt, image_path)


def explain_screenshot(image_path):
    """Explain what's happening on screen."""
    prompt = (
        "Explain what is happening on this screen. What application is being "
        "used? What task is the user performing? Provide a clear, concise "
        "explanation that would help someone understand the context."
    )
    return query_ollama(prompt, image_path)


def ocr_fallback(image_path):
    """Fallback OCR using macOS Vision framework via swift subprocess."""
    swift_code = """
import Cocoa
import Vision

let args = CommandLine.arguments
guard args.count > 1 else { exit(1) }
let imagePath = args[1]
guard let image = NSImage(contentsOfFile: imagePath),
      let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("Error: Could not load image")
    exit(1)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
try? handler.perform([request])

guard let observations = request.results else { exit(1) }
for observation in observations {
    if let candidate = observation.topCandidates(1).first {
        print(candidate.string)
    }
}
"""
    swift_file = Path("/tmp/ocr_helper.swift")
    swift_file.write_text(swift_code)

    try:
        result = subprocess.run(
            ["swift", str(swift_file), str(image_path)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def main():
    parser = argparse.ArgumentParser(
        description="Screenshot AI - Capture and analyze screenshots with Ollama llava",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --capture                  # Full screen capture
  %(prog)s --capture --mode selection # Interactive selection
  %(prog)s --capture --mode window    # Capture a specific window
  %(prog)s --analyze                  # Analyze the last screenshot
  %(prog)s --explain                  # Explain what's on screen
  %(prog)s --capture --analyze        # Capture and immediately analyze
  %(prog)s --analyze --image path.png # Analyze a specific image
        """,
    )

    parser.add_argument("--capture", action="store_true", help="Take a screenshot")
    parser.add_argument(
        "--mode", choices=["full", "selection", "window"], default="full",
        help="Screenshot mode (default: full)",
    )
    parser.add_argument("--analyze", action="store_true", help="Analyze the screenshot")
    parser.add_argument("--explain", action="store_true", help="Explain what's on screen")
    parser.add_argument("--image", type=str, help="Path to a specific image to analyze")
    parser.add_argument("--ocr", action="store_true", help="Use macOS native OCR fallback")

    args = parser.parse_args()

    if not any([args.capture, args.analyze, args.explain]):
        parser.print_help()
        sys.exit(0)

    image_path = None

    if args.capture:
        image_path = capture_screenshot(args.mode)

    if args.analyze or args.explain:
        if args.image:
            image_path = Path(args.image)
            if not image_path.exists():
                print(f"❌ Image not found: {image_path}", file=sys.stderr)
                sys.exit(1)
        elif image_path is None:
            image_path = get_latest_screenshot()
            if image_path is None:
                print("❌ No screenshots found. Use --capture first.", file=sys.stderr)
                sys.exit(1)
            print(f"📎 Using latest screenshot: {image_path.name}")

    if args.ocr and image_path:
        print("\n🔍 Running macOS native OCR...")
        text = ocr_fallback(image_path)
        if text:
            print("\n📝 Extracted Text:\n")
            print(text)
        else:
            print("⚠️  No text extracted (OCR may require macOS 12+).")
        return

    if args.analyze and image_path:
        print("\n🔍 Analyzing screenshot with llava model...")
        result = analyze_screenshot(image_path)
        print("\n📋 Analysis:\n")
        print(result)

    if args.explain and image_path:
        print("\n🧠 Explaining screenshot with llava model...")
        result = explain_screenshot(image_path)
        print("\n💡 Explanation:\n")
        print(result)


if __name__ == "__main__":
    main()
