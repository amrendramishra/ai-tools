#!/usr/bin/env python3
"""
AI Course Generator for Udemy - Generate complete publishable courses using Ollama LLM.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"
OUTPUT_DIR = Path(__file__).parent / "output"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:80]


def call_ollama(prompt: str, system: str = "", temperature: float = 0.7) -> str:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": 4096}
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json().get("response", "")
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to Ollama at localhost:11434")
        print("   Make sure Ollama is running: ollama serve")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error calling Ollama: {e}")
        return ""


def extract_json_obj(text: str) -> dict:
    try:
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            return json.loads(m.group())
    except json.JSONDecodeError:
        pass
    return {}


def extract_json_arr(text: str) -> list:
    try:
        m = re.search(r'\[[\s\S]*\]', text)
        if m:
            return json.loads(m.group())
    except json.JSONDecodeError:
        pass
    return []


def generate_outline(topic: str, sections: int, language: str, platform: str) -> dict:
    lang_note = f"Respond entirely in {language}." if language == "hindi" else ""
    plat_note = {
        "udemy": "Structure for Udemy (sections with multiple lectures, 5-15 min each).",
        "skillshare": "Structure for Skillshare (shorter lessons, project-based, 3-10 min each).",
        "youtube_playlist": "Structure as YouTube playlist (standalone videos, 8-20 min each)."
    }.get(platform, "")

    prompt = f"""Create a detailed course outline for: "{topic}"
- Exactly {sections} sections, each with 3-6 lectures
- Include intro and conclusion sections
- {plat_note} {lang_note}

Return ONLY valid JSON:
{{"course_title":"...","course_subtitle":"...","sections":[{{"section_number":1,"section_title":"...","section_objective":"...","lectures":[{{"lecture_number":1,"title":"...","duration_minutes":8,"type":"video","description":"..."}}]}}],"total_duration_hours":0,"difficulty_level":"beginner"}}"""

    resp = call_ollama(prompt, "You are an expert course designer. Return ONLY valid JSON.", 0.6)
    result = extract_json_obj(resp)
    if result and "sections" in result:
        return result

    # Fallback
    secs = []
    for i in range(1, sections + 1):
        title = "Introduction & Overview" if i == 1 else ("Conclusion & Next Steps" if i == sections else f"Core Module {i-1}")
        lectures = [{"lecture_number": j, "title": f"Lecture {j}", "duration_minutes": 8, "type": "video", "description": ""} for j in range(1, 5)]
        secs.append({"section_number": i, "section_title": title, "section_objective": f"Learn {title}", "lectures": lectures})
    return {"course_title": topic, "course_subtitle": f"Complete guide to {topic}", "sections": secs, "total_duration_hours": sections * 0.8, "difficulty_level": "beginner"}


def generate_script(topic: str, section_title: str, lecture_title: str, duration_min: int, language: str) -> str:
    lang_note = f"Write in {language} (Hinglish with technical terms in English)." if language == "hindi" else ""
    prompt = f"""Write a complete video lecture script.
Course: {topic} | Section: {section_title} | Lecture: {lecture_title} | Duration: {duration_min} min
{lang_note}
- Start with hook, include [PAUSE] markers, [SLIDE: desc] markers
- ~{duration_min * 150} words, conversational tone, timestamps like [00:00]
- End with summary and next lecture preview"""
    return call_ollama(prompt, "You are an expert online course instructor.", 0.7)


def generate_quiz(topic: str, section_title: str, language: str) -> list:
    lang_note = f"Write in {language}." if language == "hindi" else ""
    prompt = f"""Create 5 MCQ quiz questions for: Course "{topic}", Section "{section_title}". {lang_note}
Return ONLY JSON array: [{{"question":"...","options":["A)...","B)...","C)...","D)..."],"correct_answer":"A","explanation":"..."}}]"""
    result = extract_json_arr(call_ollama(prompt, "Return ONLY valid JSON array.", 0.5))
    if result:
        return result
    return [{"question": f"Q{i} about {section_title}", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "correct_answer": "A", "explanation": "..."} for i in range(1, 6)]


def generate_description(topic: str, outline: dict, platform: str, language: str) -> dict:
    prompt = f"""Create course listing for "{topic}" on {platform}.
Sections: {len(outline.get('sections',[]))} | Duration: {outline.get('total_duration_hours',10)}h
Return ONLY JSON: {{"title":"...","subtitle":"...","description":"HTML description 500+ words","requirements":["..."],"target_audience":["..."],"what_youll_learn":["..."],"tags":["..."],"category":"...","subcategory":"...","pricing_recommendation":{{"suggested_price_usd":19.99,"tier":"mid","reasoning":"..."}},"seo_keywords":["..."]}}"""
    result = extract_json_obj(call_ollama(prompt, "You are a course marketing expert. Return ONLY valid JSON.", 0.6))
    if result and "title" in result:
        return result
    return {"title": topic, "subtitle": f"Complete guide to {topic}", "description": f"<p>Learn {topic}</p>", "requirements": ["Computer", "Internet"], "target_audience": ["Beginners"], "what_youll_learn": [f"Master {topic}"], "tags": topic.split()[:5], "category": "Development", "subcategory": "Programming", "pricing_recommendation": {"suggested_price_usd": 19.99, "tier": "mid", "reasoning": "Standard"}, "seo_keywords": topic.split()[:5]}


def generate_assignments(topic: str, section_title: str) -> list:
    prompt = f"""Create 2 assignments for Course "{topic}", Section "{section_title}".
Return ONLY JSON array: [{{"title":"...","description":"...","difficulty":"medium","estimated_time_minutes":30,"deliverables":["..."],"rubric":["..."]}}]"""
    result = extract_json_arr(call_ollama(prompt, "Return ONLY valid JSON array.", 0.6))
    return result if result else [{"title": f"Practice: {section_title}", "description": "Apply concepts", "difficulty": "medium", "estimated_time_minutes": 30, "deliverables": ["Completed project"], "rubric": ["Correctness"]}]


def generate_talking_points(topic: str, lecture_title: str, section_title: str) -> list:
    prompt = f"""Create slide-by-slide talking points for: Course "{topic}", Section "{section_title}", Lecture "{lecture_title}".
Return ONLY JSON array: [{{"slide_number":1,"slide_title":"...","bullet_points":["..."],"speaker_notes":"...","visual_suggestion":"..."}}]"""
    result = extract_json_arr(call_ollama(prompt, "Return ONLY valid JSON array.", 0.6))
    return result if result else [{"slide_number": 1, "slide_title": lecture_title, "bullet_points": ["Key point"], "speaker_notes": "Explain", "visual_suggestion": "Diagram"}]


def save_course(course_slug: str, data: dict):
    course_dir = OUTPUT_DIR / course_slug
    course_dir.mkdir(parents=True, exist_ok=True)

    with open(course_dir / "course_complete.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    if "outline" in data:
        with open(course_dir / "outline.json", "w", encoding="utf-8") as f:
            json.dump(data["outline"], f, indent=2, ensure_ascii=False)

    if "scripts" in data:
        scripts_dir = course_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        for sk, lectures in data["scripts"].items():
            sd = scripts_dir / sk
            sd.mkdir(exist_ok=True)
            for lk, script in lectures.items():
                with open(sd / f"{lk}.md", "w", encoding="utf-8") as f:
                    f.write(script)

    if "quizzes" in data:
        qd = course_dir / "quizzes"
        qd.mkdir(exist_ok=True)
        for sk, quiz in data["quizzes"].items():
            with open(qd / f"{sk}.json", "w", encoding="utf-8") as f:
                json.dump(quiz, f, indent=2, ensure_ascii=False)

    if "description" in data:
        with open(course_dir / "description.json", "w", encoding="utf-8") as f:
            json.dump(data["description"], f, indent=2, ensure_ascii=False)

    if "assignments" in data:
        ad = course_dir / "assignments"
        ad.mkdir(exist_ok=True)
        for sk, a in data["assignments"].items():
            with open(ad / f"{sk}.json", "w", encoding="utf-8") as f:
                json.dump(a, f, indent=2, ensure_ascii=False)

    if "talking_points" in data:
        td = course_dir / "talking_points"
        td.mkdir(exist_ok=True)
        for sk, lectures in data["talking_points"].items():
            sd = td / sk
            sd.mkdir(exist_ok=True)
            for lk, pts in lectures.items():
                with open(sd / f"{lk}.json", "w", encoding="utf-8") as f:
                    json.dump(pts, f, indent=2, ensure_ascii=False)

    # Summary README
    readme = f"# {data.get('topic','Course')}\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\nPlatform: {data.get('platform','udemy')}\nLanguage: {data.get('language','english')}\n\n## Structure\n"
    if "outline" in data:
        for s in data["outline"].get("sections", []):
            readme += f"\n### Section {s['section_number']}: {s['section_title']}\n"
            for l in s.get("lectures", []):
                readme += f"  - {l['lecture_number']}. {l['title']} ({l['duration_minutes']} min)\n"
    with open(course_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme)

    print(f"\n✅ Course saved to: {course_dir}")


def run_generate(args):
    topic = args.topic
    course_slug = slugify(topic)
    print(f"🎓 AI Course Generator\n{'='*50}")
    print(f"Topic: {topic} | Language: {args.language} | Sections: {args.sections}")
    print(f"Platform: {args.platform} | Generate: {args.generate}\n{'='*50}\n")

    data = {"topic": topic, "language": args.language, "platform": args.platform, "generated_at": datetime.now().isoformat()}

    print("📋 Generating outline...")
    outline = generate_outline(topic, args.sections, args.language, args.platform)
    data["outline"] = outline
    print(f"   ✓ {len(outline.get('sections',[]))} sections")

    if args.generate == "outline":
        save_course(course_slug, data)
        return

    if args.generate in ("description", "full"):
        print("\n📝 Generating description...")
        data["description"] = generate_description(topic, outline, args.platform, args.language)
        print("   ✓ Done")

    if args.generate == "description":
        save_course(course_slug, data)
        return

    if args.generate in ("scripts", "full"):
        print("\n🎬 Generating scripts...")
        scripts = {}
        for s in outline.get("sections", []):
            sk = slugify(s["section_title"])
            scripts[sk] = {}
            for l in s.get("lectures", []):
                if l.get("type", "video") == "video":
                    lk = slugify(l["title"])
                    print(f"   📄 S{s['section_number']}/L{l['lecture_number']}: {l['title']}")
                    scripts[sk][lk] = generate_script(topic, s["section_title"], l["title"], l.get("duration_minutes", 8), args.language)
        data["scripts"] = scripts
        print("   ✓ All scripts done")

    if args.generate == "scripts":
        save_course(course_slug, data)
        return

    if args.generate in ("quizzes", "full"):
        print("\n❓ Generating quizzes...")
        quizzes = {}
        for s in outline.get("sections", []):
            sk = slugify(s["section_title"])
            quizzes[sk] = generate_quiz(topic, s["section_title"], args.language)
        data["quizzes"] = quizzes
        print(f"   ✓ {len(quizzes)} quizzes")

    if args.generate == "quizzes":
        save_course(course_slug, data)
        return

    if args.generate == "full":
        print("\n📚 Generating assignments...")
        assignments = {}
        for s in outline.get("sections", []):
            sk = slugify(s["section_title"])
            assignments[sk] = generate_assignments(topic, s["section_title"])
        data["assignments"] = assignments

        print("\n🎯 Generating talking points...")
        tp = {}
        for s in outline.get("sections", []):
            sk = slugify(s["section_title"])
            tp[sk] = {}
            for l in s.get("lectures", []):
                if l.get("type", "video") == "video":
                    tp[sk][slugify(l["title"])] = generate_talking_points(topic, l["title"], s["section_title"])
        data["talking_points"] = tp
        print("   ✓ Done")

    save_course(course_slug, data)


def main():
    parser = argparse.ArgumentParser(description="🎓 AI Course Generator - Create publishable courses with AI")
    parser.add_argument("--topic", required=True, help="Course topic")
    parser.add_argument("--language", choices=["hindi", "english"], default="english")
    parser.add_argument("--sections", type=int, default=10, help="Number of sections")
    parser.add_argument("--generate", required=True, choices=["outline", "full", "scripts", "quizzes", "description"])
    parser.add_argument("--platform", choices=["udemy", "skillshare", "youtube_playlist"], default="udemy")
    args = parser.parse_args()
    run_generate(args)


if __name__ == "__main__":
    main()
