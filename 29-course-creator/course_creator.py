#!/usr/bin/env python3
"""AI Course Creator - Generate complete course content using local LLMs."""

import argparse
import json
import os
import sys
import re
import datetime
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"


def _update_model(new_model: str):
    """Update the global model name."""
    global MODEL
    MODEL = new_model


def query_ollama(prompt: str, model: str = None) -> str:
    """Send a prompt to Ollama and return the response."""
    import urllib.request
    import urllib.error

    if model is None:
        model = MODEL

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 4096}
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode())
            return data.get("response", "").strip()
    except urllib.error.URLError as e:
        print(f"Error connecting to Ollama: {e}")
        sys.exit(1)


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def get_platform_context(platform: str) -> str:
    """Get platform-specific guidelines."""
    contexts = {
        "udemy": "Platform: Udemy - Lectures 5-15 min each, practical exercises, section quizzes every 3-5 lectures, target 4+ hours total.",
        "skillshare": "Platform: Skillshare - Classes 15-60 min total, lessons 2-5 min each, project-based learning, concise and visual.",
        "youtube": "Platform: YouTube - Videos 10-20 min each, engaging hooks in first 30s, timestamps/chapters, somewhat standalone episodes.",
        "self-hosted": "Platform: Self-hosted - No time restrictions, thorough content, downloadable materials, progress checkpoints."
    }
    return contexts.get(platform, contexts["self-hosted"])


def generate_outline(topic: str, level: str, modules: int, platform: str) -> dict:
    """Generate course outline/structure."""
    platform_ctx = get_platform_context(platform)

    prompt = f"""Create a course outline for:
Topic: {topic}
Level: {level}
Modules: {modules}
{platform_ctx}

Return JSON:
{{"title": "Course Title", "subtitle": "One-line description", "description": "2-3 sentences", "target_audience": ["aud1","aud2","aud3"], "prerequisites": ["prereq1","prereq2"], "learning_outcomes": ["out1","out2","out3","out4"], "modules": [{{"module_number": 1, "title": "Module Title", "description": "Brief desc", "lessons": [{{"lesson_number": 1, "title": "Lesson Title", "objectives": ["obj1","obj2"], "duration_minutes": 15}}]}}], "total_duration_hours": 10}}

Generate exactly {modules} modules with 3-5 lessons each for {level} learners. ONLY valid JSON, no other text."""

    response = query_ollama(prompt)
    try:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group())
    except json.JSONDecodeError:
        pass
    return {"title": topic, "raw_outline": response, "modules": []}


def generate_lesson_content(topic: str, level: str, module_info: dict, lesson_info: dict, platform: str) -> dict:
    """Generate full content for a single lesson."""
    platform_ctx = get_platform_context(platform)

    prompt = f"""Create lesson content for:
Course: {topic} | Level: {level}
Module: {module_info.get('title', 'N/A')} (#{module_info.get('module_number', '')})
Lesson: {lesson_info.get('title', 'N/A')} (#{lesson_info.get('lesson_number', '')})
Objectives: {json.dumps(lesson_info.get('objectives', []))}
{platform_ctx}

Return JSON:
{{"title": "Lesson Title", "objectives": ["obj1","obj2"], "introduction": "Opening paragraph", "content_sections": [{{"heading": "Heading", "content": "Explanation", "examples": ["ex1"], "code_snippets": ["code"], "tips": ["tip"]}}], "quiz": {{"mcq": [{{"question": "Q?", "options": ["A","B","C","D"], "correct": "A", "explanation": "Why"}}], "short_answer": [{{"question": "Q?", "sample_answer": "Answer"}}]}}, "assignment": {{"title": "Title", "description": "What to do", "requirements": ["req1","req2"], "deliverables": ["del1"], "estimated_time_minutes": 30}}, "summary": {{"key_takeaways": ["t1","t2","t3"], "next_steps": "What's next"}}}}

Include 2-3 MCQs and 1-2 short answer questions. Content for {level} level. ONLY valid JSON."""

    response = query_ollama(prompt)
    try:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group())
    except json.JSONDecodeError:
        pass
    return {"title": lesson_info.get("title", "Lesson"), "raw_content": response, "objectives": lesson_info.get("objectives", [])}


def format_lesson_markdown(lesson_data: dict, module_num: int, lesson_num: int) -> str:
    """Format lesson content as Markdown."""
    lines = []
    title = lesson_data.get("title", f"Lesson {lesson_num}")
    lines.append(f"# Module {module_num} - Lesson {lesson_num}: {title}\n")

    objectives = lesson_data.get("objectives", [])
    if objectives:
        lines.append("## 🎯 Learning Objectives\n")
        for obj in objectives:
            lines.append(f"- {obj}")
        lines.append("")

    intro = lesson_data.get("introduction", "")
    if intro:
        lines.append("## Introduction\n")
        lines.append(f"{intro}\n")

    sections = lesson_data.get("content_sections", [])
    for section in sections:
        lines.append(f"## {section.get('heading', 'Section')}\n")
        lines.append(f"{section.get('content', '')}\n")
        for ex in section.get("examples", []):
            lines.append(f"- {ex}")
        if section.get("examples"):
            lines.append("")
        for snippet in section.get("code_snippets", []):
            lines.append(f"```\n{snippet}\n```\n")
        for tip in section.get("tips", []):
            lines.append(f"> 💡 **Tip:** {tip}\n")

    quiz = lesson_data.get("quiz", {})
    mcqs = quiz.get("mcq", [])
    short_answers = quiz.get("short_answer", [])
    if mcqs or short_answers:
        lines.append("## 📝 Quiz\n")
        if mcqs:
            lines.append("### Multiple Choice\n")
            for i, q in enumerate(mcqs, 1):
                lines.append(f"**{i}. {q.get('question', '')}**\n")
                for opt in q.get("options", []):
                    lines.append(f"  - {opt}")
                lines.append(f"\n<details><summary>Answer</summary>{q.get('correct', '')} - {q.get('explanation', '')}</details>\n")
        if short_answers:
            lines.append("### Short Answer\n")
            for i, q in enumerate(short_answers, 1):
                lines.append(f"**{i}. {q.get('question', '')}**\n")
                lines.append(f"<details><summary>Sample Answer</summary>{q.get('sample_answer', '')}</details>\n")

    assignment = lesson_data.get("assignment", {})
    if assignment:
        lines.append("## 📋 Assignment\n")
        lines.append(f"### {assignment.get('title', 'Practice Exercise')}\n")
        lines.append(f"{assignment.get('description', '')}\n")
        for req in assignment.get("requirements", []):
            lines.append(f"- {req}")
        if assignment.get("requirements"):
            lines.append("")
        time_est = assignment.get("estimated_time_minutes")
        if time_est:
            lines.append(f"⏱️ Estimated time: {time_est} minutes\n")

    summary = lesson_data.get("summary", {})
    if summary:
        lines.append("## 📌 Key Takeaways\n")
        for takeaway in summary.get("key_takeaways", []):
            lines.append(f"- {takeaway}")
        lines.append("")
        next_steps = summary.get("next_steps", "")
        if next_steps:
            lines.append(f"**Next:** {next_steps}\n")

    return "\n".join(lines)


def format_outline_markdown(outline: dict) -> str:
    """Format course outline as Markdown."""
    lines = []
    lines.append(f"# {outline.get('title', 'Course')}\n")
    lines.append(f"*{outline.get('subtitle', '')}*\n")
    lines.append(f"{outline.get('description', '')}\n")

    audience = outline.get("target_audience", [])
    if audience:
        lines.append("## 👥 Target Audience\n")
        for a in audience:
            lines.append(f"- {a}")
        lines.append("")

    prereqs = outline.get("prerequisites", [])
    if prereqs:
        lines.append("## ✅ Prerequisites\n")
        for p in prereqs:
            lines.append(f"- {p}")
        lines.append("")

    outcomes = outline.get("learning_outcomes", [])
    if outcomes:
        lines.append("## 🎯 Learning Outcomes\n")
        for o in outcomes:
            lines.append(f"- {o}")
        lines.append("")

    modules = outline.get("modules", [])
    lines.append("## 📚 Course Modules\n")
    for mod in modules:
        lines.append(f"### Module {mod.get('module_number', '')}: {mod.get('title', '')}\n")
        lines.append(f"{mod.get('description', '')}\n")
        for lesson in mod.get("lessons", []):
            dur = lesson.get("duration_minutes", "")
            dur_str = f" ({dur} min)" if dur else ""
            lines.append(f"  - **Lesson {lesson.get('lesson_number', '')}**: {lesson.get('title', '')}{dur_str}")
        lines.append("")

    total = outline.get("total_duration_hours", "")
    if total:
        lines.append(f"\n**Total Course Duration:** ~{total} hours\n")

    return "\n".join(lines)


def save_course_files(outline: dict, lessons: dict, output_dir: Path, fmt: str):
    """Save all course files to output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if fmt == "json":
        course_data = {"outline": outline, "lessons": lessons}
        (output_dir / "course.json").write_text(json.dumps(course_data, indent=2))
        print(f"✅ Saved course.json to {output_dir}")
    else:
        outline_md = format_outline_markdown(outline)
        (output_dir / "00-outline.md").write_text(outline_md)

        for key, lesson_data in lessons.items():
            mod_num, les_num = key.split("_")
            content_md = format_lesson_markdown(lesson_data, int(mod_num), int(les_num))
            filename = f"module-{mod_num.zfill(2)}-lesson-{les_num.zfill(2)}.md"
            (output_dir / filename).write_text(content_md)

        readme = f"# {outline.get('title', 'Course')}\n\n"
        readme += f"{outline.get('description', '')}\n\n"
        readme += f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n## Files\n\n"
        readme += "- `00-outline.md` - Course outline\n"
        for key in sorted(lessons.keys()):
            mod_num, les_num = key.split("_")
            filename = f"module-{mod_num.zfill(2)}-lesson-{les_num.zfill(2)}.md"
            readme += f"- `{filename}` - {lessons[key].get('title', 'Lesson')}\n"
        (output_dir / "README.md").write_text(readme)

        print(f"✅ Saved {len(lessons) + 2} files to {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="AI Course Creator - Generate complete courses with local LLMs",
        epilog="Examples:\n  %(prog)s --topic 'Python' --level beginner --generate outline\n  %(prog)s --topic 'React' --modules 10 --generate full\n  %(prog)s --topic 'ML' --generate lesson 3",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--topic", type=str, required=True, help="Course subject/topic")
    parser.add_argument("--level", type=str, default="intermediate",
                        choices=["beginner", "intermediate", "advanced"])
    parser.add_argument("--modules", type=int, default=8, help="Number of modules (default: 8)")
    parser.add_argument("--generate", type=str, nargs="+", required=True,
                        help="What to generate: outline, full, or lesson <number>")
    parser.add_argument("--format", type=str, default="markdown", choices=["markdown", "json"])
    parser.add_argument("--platform", type=str, default="self-hosted",
                        choices=["udemy", "skillshare", "youtube", "self-hosted"])
    parser.add_argument("--model", type=str, default=MODEL, help=f"Ollama model (default: {MODEL})")

    args = parser.parse_args()
    _update_model(args.model)

    gen_type = args.generate[0]
    gen_arg = args.generate[1] if len(args.generate) > 1 else None

    course_slug = slugify(args.topic)
    course_dir = OUTPUT_DIR / course_slug
    course_dir.mkdir(parents=True, exist_ok=True)

    print(f"📚 Course Creator")
    print(f"   Topic: {args.topic} | Level: {args.level} | Modules: {args.modules}")
    print(f"   Platform: {args.platform} | Format: {args.format}")
    print(f"   Output: {course_dir}\n")

    print("📋 Generating course outline...")
    outline = generate_outline(args.topic, args.level, args.modules, args.platform)

    if gen_type == "outline":
        if args.format == "json":
            (course_dir / "outline.json").write_text(json.dumps(outline, indent=2))
        else:
            outline_md = format_outline_markdown(outline)
            (course_dir / "00-outline.md").write_text(outline_md)
            print("\n" + outline_md)
        print(f"\n✅ Outline saved to {course_dir}")

    elif gen_type == "full":
        lessons = {}
        modules = outline.get("modules", [])
        if not modules:
            print("⚠️  Could not parse modules. Saving raw outline.")
            (course_dir / "outline.txt").write_text(str(outline))
            return

        total_lessons = sum(len(m.get("lessons", [])) for m in modules)
        current = 0
        for module in modules:
            mod_num = module.get("module_number", 0)
            for lesson in module.get("lessons", []):
                les_num = lesson.get("lesson_number", 0)
                current += 1
                print(f"  [{current}/{total_lessons}] M{mod_num} L{les_num}: {lesson.get('title', '')}")
                lesson_content = generate_lesson_content(args.topic, args.level, module, lesson, args.platform)
                lessons[f"{mod_num}_{les_num}"] = lesson_content

        save_course_files(outline, lessons, course_dir, args.format)

    elif gen_type == "lesson":
        if not gen_arg:
            print("Error: --generate lesson requires a number (e.g., --generate lesson 3)")
            sys.exit(1)
        lesson_num = int(gen_arg)
        modules = outline.get("modules", [])
        target_module = target_lesson = None
        count = 0
        for module in modules:
            for lesson in module.get("lessons", []):
                count += 1
                if count == lesson_num:
                    target_module = module
                    target_lesson = lesson
                    break
            if target_lesson:
                break

        if not target_lesson:
            print(f"Error: Lesson {lesson_num} not found (course has {count} lessons).")
            sys.exit(1)

        mod_num = target_module.get("module_number", 0)
        les_num = target_lesson.get("lesson_number", 0)
        print(f"📖 Generating: M{mod_num} L{les_num}: {target_lesson.get('title', '')}")
        lesson_content = generate_lesson_content(args.topic, args.level, target_module, target_lesson, args.platform)

        if args.format == "json":
            filename = f"lesson_{lesson_num}.json"
            (course_dir / filename).write_text(json.dumps(lesson_content, indent=2))
        else:
            content_md = format_lesson_markdown(lesson_content, mod_num, les_num)
            filename = f"module-{str(mod_num).zfill(2)}-lesson-{str(les_num).zfill(2)}.md"
            (course_dir / filename).write_text(content_md)
            print("\n" + content_md)
        print(f"\n✅ Saved to {course_dir / filename}")
    else:
        print(f"Unknown: {gen_type}. Use: outline, full, lesson <n>")
        sys.exit(1)


if __name__ == "__main__":
    main()
