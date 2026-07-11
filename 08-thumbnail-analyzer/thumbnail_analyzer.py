#!/usr/bin/env python3
"""
Thumbnail AI Analyzer - Analyzes YouTube thumbnails using Ollama's LLaVA model.
Scores thumbnails on readability, contrast, faces, emotion, and click-worthiness.
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

# Add parent paths for shared venv
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "llava"
BEST_PRACTICES_FILE = Path(__file__).parent / "best_practices.json"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def load_best_practices():
    """Load thumbnail best practices data."""
    if BEST_PRACTICES_FILE.exists():
        with open(BEST_PRACTICES_FILE, "r") as f:
            return json.load(f)
    return {}


def encode_image(image_path: str) -> str:
    """Encode image to base64 for Ollama API."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def query_ollama(prompt: str, image_path: str = None) -> str:
    """Send a query to Ollama with optional image."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
    }

    if image_path:
        payload["images"] = [encode_image(image_path)]

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to Ollama at localhost:11434")
        print("Make sure Ollama is running: ollama serve")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("Error: Request to Ollama timed out. The model may be loading.")
        sys.exit(1)
    except Exception as e:
        print(f"Error communicating with Ollama: {e}")
        sys.exit(1)


def analyze_thumbnail(image_path: str) -> dict:
    """Analyze a single thumbnail image and return scores."""
    if not os.path.exists(image_path):
        print(f"Error: Image not found: {image_path}")
        sys.exit(1)

    best_practices = load_best_practices()

    analysis_prompt = """Analyze this YouTube thumbnail image in detail. Score each category from 1-10 and provide specific feedback.

Categories to evaluate:
1. TEXT READABILITY: Is text visible, legible at small sizes? Good font choices? Contrast with background?
2. COLOR CONTRAST: Are colors vibrant and eye-catching? Good use of complementary colors? Stands out in search results?
3. FACE DETECTION: Are there faces? Are expressions exaggerated/emotional? Are faces large and clear?
4. EMOTIONAL IMPACT: Does it evoke curiosity, excitement, shock, or other strong emotions? Would it make someone stop scrolling?
5. CLICK-WORTHINESS: Overall, would this thumbnail get clicked? Does it create a curiosity gap? Is it compelling?

For each category provide:
- Score (1-10)
- Brief explanation
- One specific improvement suggestion

Also provide:
- Overall score (average of all categories)
- Top 3 improvement suggestions ranked by impact

Format your response as structured text with clear sections."""

    response = query_ollama(analysis_prompt, image_path)

    # Parse the response into a structured format
    scores = parse_scores(response)
    scores["raw_analysis"] = response
    scores["image_path"] = image_path
    scores["best_practices_tips"] = best_practices.get("general_tips", [])

    return scores


def parse_scores(response: str) -> dict:
    """Parse AI response to extract scores. Falls back to defaults if parsing fails."""
    categories = [
        "text_readability",
        "color_contrast",
        "face_detection",
        "emotional_impact",
        "click_worthiness",
    ]

    scores = {}
    lines = response.lower()

    for category in categories:
        # Try to find score patterns
        score = None
        search_terms = category.replace("_", " ")
        for line in response.split("\n"):
            if search_terms in line.lower() or category in line.lower():
                # Look for number patterns like "7/10", "Score: 7", etc.
                import re
                matches = re.findall(r"(\d+)\s*/\s*10", line)
                if matches:
                    score = int(matches[0])
                    break
                matches = re.findall(r"(?:score|rating)[:\s]*(\d+)", line.lower())
                if matches:
                    score = int(matches[0])
                    break
                matches = re.findall(r"\b(\d+)\b", line)
                if matches:
                    for m in matches:
                        if 1 <= int(m) <= 10:
                            score = int(m)
                            break
                if score:
                    break

        scores[category] = min(max(score if score else 5, 1), 10)

    # Calculate overall
    scores["overall"] = round(sum(scores[c] for c in categories) / len(categories), 1)

    return scores


def display_scorecard(scores: dict):
    """Display a formatted score card."""
    print("\n" + "=" * 60)
    print("🎨 THUMBNAIL ANALYSIS SCORECARD")
    print("=" * 60)
    print(f"📁 Image: {scores.get('image_path', 'N/A')}")
    print("-" * 60)

    categories = {
        "text_readability": "📝 Text Readability",
        "color_contrast": "🌈 Color Contrast",
        "face_detection": "👤 Face Detection",
        "emotional_impact": "💥 Emotional Impact",
        "click_worthiness": "🖱️  Click-Worthiness",
    }

    for key, label in categories.items():
        score = scores.get(key, "N/A")
        bar = "█" * score + "░" * (10 - score) if isinstance(score, int) else ""
        print(f"  {label:25s} [{bar}] {score}/10")

    print("-" * 60)
    overall = scores.get("overall", "N/A")
    print(f"  {'⭐ OVERALL SCORE':25s} {overall}/10")
    print("=" * 60)

    if scores.get("raw_analysis"):
        print("\n📋 DETAILED ANALYSIS:")
        print("-" * 60)
        print(scores["raw_analysis"])

    if scores.get("best_practices_tips"):
        print("\n💡 BEST PRACTICES TIPS:")
        print("-" * 60)
        for tip in scores["best_practices_tips"][:5]:
            print(f"  • {tip}")

    print()


def compare_thumbnails(path1: str, path2: str):
    """Compare two thumbnails side by side."""
    print(f"\n🔄 Comparing thumbnails...")
    print(f"  Image A: {path1}")
    print(f"  Image B: {path2}")

    if not os.path.exists(path1):
        print(f"Error: Image not found: {path1}")
        sys.exit(1)
    if not os.path.exists(path2):
        print(f"Error: Image not found: {path2}")
        sys.exit(1)

    # Analyze both images
    print("\n📊 Analyzing Image A...")
    scores_a = analyze_thumbnail(path1)

    print("\n📊 Analyzing Image B...")
    scores_b = analyze_thumbnail(path2)

    # Compare
    comparison_prompt = f"""Compare these two YouTube thumbnails based on the following analyses:

Thumbnail A analysis scores:
- Text Readability: {scores_a['text_readability']}/10
- Color Contrast: {scores_a['color_contrast']}/10
- Face Detection: {scores_a['face_detection']}/10
- Emotional Impact: {scores_a['emotional_impact']}/10
- Click-Worthiness: {scores_a['click_worthiness']}/10
- Overall: {scores_a['overall']}/10

Thumbnail B analysis scores:
- Text Readability: {scores_b['text_readability']}/10
- Color Contrast: {scores_b['color_contrast']}/10
- Face Detection: {scores_b['face_detection']}/10
- Emotional Impact: {scores_b['emotional_impact']}/10
- Click-Worthiness: {scores_b['click_worthiness']}/10
- Overall: {scores_b['overall']}/10

Provide:
1. Which thumbnail is better overall and why
2. Specific strengths of each thumbnail
3. What each can learn from the other
4. Final recommendation for which to use"""

    comparison = query_ollama(comparison_prompt)

    print("\n" + "=" * 60)
    print("🔄 THUMBNAIL COMPARISON RESULTS")
    print("=" * 60)

    print(f"\n{'Category':<25} {'Image A':<12} {'Image B':<12} {'Winner'}")
    print("-" * 60)

    categories = {
        "text_readability": "Text Readability",
        "color_contrast": "Color Contrast",
        "face_detection": "Face Detection",
        "emotional_impact": "Emotional Impact",
        "click_worthiness": "Click-Worthiness",
    }

    for key, label in categories.items():
        a = scores_a.get(key, 0)
        b = scores_b.get(key, 0)
        winner = "A ✓" if a > b else ("B ✓" if b > a else "Tie")
        print(f"  {label:<23} {a}/10{'':<7} {b}/10{'':<7} {winner}")

    print("-" * 60)
    a_overall = scores_a.get("overall", 0)
    b_overall = scores_b.get("overall", 0)
    winner = "A ✓" if a_overall > b_overall else ("B ✓" if b_overall > a_overall else "Tie")
    print(f"  {'OVERALL':<23} {a_overall}/10{'':<5} {b_overall}/10{'':<5} {winner}")
    print("=" * 60)

    print("\n📋 DETAILED COMPARISON:")
    print("-" * 60)
    print(comparison)
    print()


def generate_text_suggestions(image_path: str = None):
    """Generate thumbnail text/title overlay suggestions."""
    prompt = """Suggest 10 compelling text overlays for a YouTube thumbnail. The text should be:
- Short (2-5 words max)
- High impact and curiosity-inducing
- Easy to read at small sizes
- Create urgency or curiosity gap

For each suggestion, provide:
1. The text itself
2. Recommended font style (bold, italic, etc.)
3. Recommended color scheme
4. Placement suggestion (top, bottom, center, etc.)

If an image was provided, tailor suggestions to the image content."""

    if image_path and os.path.exists(image_path):
        print(f"📝 Generating text suggestions for: {image_path}")
        response = query_ollama(prompt, image_path)
    else:
        print("📝 Generating generic thumbnail text suggestions...")
        response = query_ollama(prompt)

    print("\n" + "=" * 60)
    print("📝 THUMBNAIL TEXT SUGGESTIONS")
    print("=" * 60)
    print(response)
    print()


def batch_analyze(directory: str):
    """Analyze all thumbnails in a directory."""
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Error: Directory not found: {directory}")
        sys.exit(1)

    images = [
        f for f in dir_path.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ]

    if not images:
        print(f"No image files found in: {directory}")
        print(f"Supported formats: {', '.join(IMAGE_EXTENSIONS)}")
        sys.exit(1)

    print(f"\n📁 Batch analyzing {len(images)} thumbnails in: {directory}")
    print("=" * 60)

    results = []
    for i, img in enumerate(sorted(images), 1):
        print(f"\n[{i}/{len(images)}] Analyzing: {img.name}")
        scores = analyze_thumbnail(str(img))
        results.append(scores)
        display_scorecard(scores)

    # Summary
    print("\n" + "=" * 60)
    print("📊 BATCH ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"{'Image':<40} {'Overall':<10} {'Best Category'}")
    print("-" * 60)

    categories = ["text_readability", "color_contrast", "face_detection",
                  "emotional_impact", "click_worthiness"]

    for result in sorted(results, key=lambda x: x.get("overall", 0), reverse=True):
        name = Path(result["image_path"]).name[:38]
        overall = result.get("overall", 0)
        best_cat = max(categories, key=lambda c: result.get(c, 0))
        best_score = result.get(best_cat, 0)
        print(f"  {name:<38} {overall}/10{'':<5} {best_cat.replace('_', ' ').title()} ({best_score}/10)")

    # Export results
    output_file = dir_path / "batch_analysis_results.json"
    export_data = []
    for r in results:
        export_data.append({
            "image": r["image_path"],
            "text_readability": r.get("text_readability"),
            "color_contrast": r.get("color_contrast"),
            "face_detection": r.get("face_detection"),
            "emotional_impact": r.get("emotional_impact"),
            "click_worthiness": r.get("click_worthiness"),
            "overall": r.get("overall"),
        })

    with open(output_file, "w") as f:
        json.dump(export_data, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="🎨 Thumbnail AI Analyzer - Score and improve your YouTube thumbnails",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --image thumbnail.png
  %(prog)s --compare thumb_a.png thumb_b.png
  %(prog)s --generate-text --image thumbnail.png
  %(prog)s --batch ./thumbnails/
        """,
    )

    parser.add_argument(
        "--image", type=str, help="Path to thumbnail image to analyze"
    )
    parser.add_argument(
        "--compare", nargs=2, metavar=("PATH1", "PATH2"),
        help="Compare two thumbnails side by side"
    )
    parser.add_argument(
        "--generate-text", action="store_true",
        help="Generate thumbnail text/title overlay suggestions"
    )
    parser.add_argument(
        "--batch", type=str, metavar="DIRECTORY",
        help="Analyze all thumbnails in a folder"
    )

    args = parser.parse_args()

    if not any([args.image, args.compare, args.generate_text, args.batch]):
        parser.print_help()
        sys.exit(0)

    if args.compare:
        compare_thumbnails(args.compare[0], args.compare[1])
    elif args.batch:
        batch_analyze(args.batch)
    elif args.generate_text:
        generate_text_suggestions(args.image)
    elif args.image:
        scores = analyze_thumbnail(args.image)
        display_scorecard(scores)


if __name__ == "__main__":
    main()
