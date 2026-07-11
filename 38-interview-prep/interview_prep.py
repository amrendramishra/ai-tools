#!/usr/bin/env python3
"""
AI Interview Prep Bot - Comprehensive interview preparation system.
Supports DSA, System Design, and Behavioral (Amazon LP focused) interview modes.
Uses Ollama llama3.2 for AI evaluation and feedback.
"""

import argparse
import json
import os
import random
import readline
import signal
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# ─── Configuration ───────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3.2"
DB_PATH = SCRIPT_DIR / "interview_stats.db"
QUESTIONS_PATH = SCRIPT_DIR / "questions_bank.json"
LPS_PATH = SCRIPT_DIR / "amazon_lps.json"


# ─── Database Setup ──────────────────────────────────────────────────────────

def init_db():
    """Initialize SQLite database for tracking progress."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            mode TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            topic TEXT,
            company TEXT,
            question_id INTEGER,
            question_title TEXT,
            score REAL,
            feedback TEXT,
            time_taken_seconds INTEGER,
            strengths TEXT,
            weaknesses TEXT
        )
    """)
    conn.commit()
    return conn


def save_session(conn, mode, difficulty, topic, company, question_id, question_title,
                 score, feedback, time_taken, strengths="", weaknesses=""):
    """Save a practice session to the database."""
    c = conn.cursor()
    c.execute("""
        INSERT INTO sessions (timestamp, mode, difficulty, topic, company, question_id,
                            question_title, score, feedback, time_taken_seconds, strengths, weaknesses)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(), mode, difficulty, topic or "", company or "",
        question_id, question_title, score, feedback, time_taken, strengths, weaknesses
    ))
    conn.commit()


# ─── Ollama Integration ──────────────────────────────────────────────────────

def generate(prompt: str, system: str = "") -> str:
    """Generate response using Ollama."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={"model": MODEL, "messages": messages, "stream": False},
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


# ─── Data Loading ────────────────────────────────────────────────────────────

def load_questions() -> dict:
    """Load questions bank."""
    with open(QUESTIONS_PATH) as f:
        return json.load(f)


def load_lps() -> dict:
    """Load Amazon Leadership Principles."""
    with open(LPS_PATH) as f:
        return json.load(f)


def get_question(questions: dict, mode: str, difficulty: str, topic: str = None) -> dict:
    """Get a random question matching criteria."""
    pool = questions.get(mode, {}).get(difficulty, [])
    if topic:
        filtered = [q for q in pool if topic.lower() in q.get("topic", "").lower()
                    or topic.lower() in q.get("title", "").lower()
                    or topic.lower() in q.get("description", "").lower()]
        if filtered:
            pool = filtered
    if not pool:
        return None
    return random.choice(pool)


# ─── Timer Utilities ─────────────────────────────────────────────────────────

class Timer:
    def __init__(self):
        self.start_time = None
        self.elapsed = 0

    def start(self):
        self.start_time = time.time()

    def stop(self):
        if self.start_time:
            self.elapsed = int(time.time() - self.start_time)
        return self.elapsed

    def get_elapsed(self):
        if self.start_time:
            return int(time.time() - self.start_time)
        return self.elapsed


def get_multiline_input(prompt_text: str) -> str:
    """Get multi-line input from user (end with empty line or Ctrl+D)."""
    print(prompt_text)
    print("  (Type your answer. Press Enter twice to submit, or Ctrl+D)\n")
    lines = []
    empty_count = 0
    try:
        while True:
            line = input("  > ")
            if line == "":
                empty_count += 1
                if empty_count >= 2:
                    break
                lines.append("")
            else:
                empty_count = 0
                lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines).strip()


# ─── Company Style Adjustments ───────────────────────────────────────────────

COMPANY_STYLES = {
    "amazon": "Focus on Leadership Principles, data-driven decisions, customer impact, and bias for action. Expect deep-dive questions and 'tell me more' follow-ups. Use STAR format.",
    "google": "Focus on algorithmic thinking, code quality, scalability, and Googleyness (collaborative, humble, innovative). Expect to write actual code and discuss trade-offs.",
    "meta": "Focus on impact, moving fast, building for scale, and collaboration. Expect practical system design with emphasis on real-world constraints.",
    "microsoft": "Focus on growth mindset, collaboration, technical depth, and customer empathy. Expect balanced evaluation of technical skills and soft skills.",
}


# ─── DSA Mode ────────────────────────────────────────────────────────────────

def run_dsa(questions: dict, difficulty: str, topic: str, company: str, practice: bool, conn):
    """Run DSA interview question."""
    question = get_question(questions, "dsa", difficulty, topic)
    if not question:
        print("❌ No matching questions found. Try a different topic or difficulty.")
        return

    print("\n" + "=" * 70)
    print(f"📝 DSA Problem: {question['title']}")
    print(f"   Difficulty: {difficulty.upper()} | Topic: {question['topic']}")
    print("=" * 70)
    print(f"\n{question['description']}\n")

    if "expected_complexity" in question:
        print(f"   Target: Time {question['expected_complexity']['time']}, Space {question['expected_complexity']['space']}")
    print()

    timer = Timer()
    timer.start()

    hints_used = 0
    if practice and "hints" in question:
        print("💡 Hints available (type 'hint' for a hint)\n")

    # Get answer
    while True:
        answer = get_multiline_input("✍️  Your approach/solution:")
        if answer.lower() == "hint" and practice and hints_used < len(question.get("hints", [])):
            print(f"\n💡 Hint {hints_used + 1}: {question['hints'][hints_used]}\n")
            hints_used += 1
            continue
        if answer:
            break
        print("  Please provide an answer.")

    elapsed = timer.stop()
    print(f"\n⏱️  Time: {elapsed // 60}m {elapsed % 60}s")

    # AI evaluation
    print("\n🤖 Evaluating your answer...\n")
    company_context = COMPANY_STYLES.get(company, "")

    eval_prompt = f"""Evaluate this DSA interview answer.

Problem: {question['title']}
Description: {question['description']}
Expected Complexity: Time {question.get('expected_complexity', {}).get('time', 'N/A')}, Space {question.get('expected_complexity', {}).get('space', 'N/A')}
Candidate's Answer: {answer}
Time Taken: {elapsed} seconds
Hints Used: {hints_used}/{len(question.get('hints', []))}
{f'Company Style: {company_context}' if company_context else ''}

Evaluate on:
1. **Correctness** (0-25): Is the approach correct?
2. **Complexity Analysis** (0-25): Did they achieve optimal time/space complexity?
3. **Code Quality** (0-25): Clean, readable, well-structured?
4. **Communication** (0-25): Clear explanation of thought process?

Provide:
- Overall score (0-100)
- Strengths
- Areas for improvement
- Optimal solution hint (if they missed it)
- Follow-up questions an interviewer might ask

Format the score as: SCORE: X/100"""

    feedback = generate(eval_prompt, "You are a senior technical interviewer evaluating coding interview answers.")
    print(feedback)

    # Parse score
    score = 0
    for line in feedback.split("\n"):
        if "SCORE:" in line.upper():
            try:
                score = float("".join(c for c in line.split(":")[-1] if c.isdigit() or c == "."))
                if score > 100:
                    score = score / 10
            except (ValueError, IndexError):
                score = 50
            break

    save_session(conn, "dsa", difficulty, question["topic"], company,
                 question["id"], question["title"], score, feedback, elapsed)
    print(f"\n📊 Score saved: {score}/100")


# ─── System Design Mode ──────────────────────────────────────────────────────

def run_system_design(questions: dict, difficulty: str, topic: str, company: str, practice: bool, conn):
    """Run System Design interview question."""
    question = get_question(questions, "system_design", difficulty, topic)
    if not question:
        print("❌ No matching questions found. Try a different topic or difficulty.")
        return

    print("\n" + "=" * 70)
    print(f"🏗️  System Design: {question['title']}")
    print(f"   Difficulty: {difficulty.upper()} | Topic: {question['topic']}")
    print("=" * 70)
    print(f"\n{question['description']}\n")

    if "key_points" in question:
        print("   Key areas to cover:")
        for point in question["key_points"]:
            print(f"   • {point}")
    print()

    timer = Timer()
    timer.start()

    # Phase 1: Initial design
    answer = get_multiline_input("✍️  Present your design (requirements, architecture, components, trade-offs):")
    elapsed = timer.stop()

    # AI follow-up
    print("\n🤖 Reviewing your design and preparing follow-ups...\n")
    company_context = COMPANY_STYLES.get(company, "")

    followup_prompt = f"""You are conducting a system design interview.

Problem: {question['title']}
Description: {question['description']}
Key Points to Cover: {json.dumps(question.get('key_points', []))}
Candidate's Design: {answer}
{f'Company Style: {company_context}' if company_context else ''}

Ask 2-3 challenging follow-up questions about their design. Focus on:
- Scalability bottlenecks
- Failure scenarios
- Trade-offs they made
- Missing components"""

    followups = generate(followup_prompt, "You are a senior system design interviewer.")
    print(f"🔍 Follow-up Questions:\n{followups}\n")

    # Phase 2: Follow-up answers
    timer.start()
    followup_answer = get_multiline_input("✍️  Address the follow-up questions:")
    elapsed += timer.stop()

    print(f"\n⏱️  Total Time: {elapsed // 60}m {elapsed % 60}s")

    # Final evaluation
    print("\n🤖 Final evaluation...\n")
    eval_prompt = f"""Evaluate this system design interview comprehensively.

Problem: {question['title']}
Description: {question['description']}
Key Points: {json.dumps(question.get('key_points', []))}
Initial Design: {answer}
Follow-up Answers: {followup_answer}
Total Time: {elapsed} seconds
{f'Company Style: {company_context}' if company_context else ''}

Evaluate on:
1. **Requirements & Scope** (0-20): Clear requirements gathering and scope definition?
2. **High-Level Design** (0-20): Good architecture and component identification?
3. **Scalability** (0-20): Addressed scaling concerns, bottlenecks?
4. **Trade-offs** (0-20): Identified and justified design decisions?
5. **Deep Dive** (0-20): Detailed knowledge of specific components?

Provide:
- Overall score (0-100)
- Strengths of the design
- Critical gaps or missed areas
- Suggested improvements
- Key topics to study further

Format the score as: SCORE: X/100"""

    feedback = generate(eval_prompt, "You are a senior system design interviewer at a top tech company.")
    print(feedback)

    score = 0
    for line in feedback.split("\n"):
        if "SCORE:" in line.upper():
            try:
                score = float("".join(c for c in line.split(":")[-1] if c.isdigit() or c == "."))
                if score > 100:
                    score = score / 10
            except (ValueError, IndexError):
                score = 50
            break

    save_session(conn, "system_design", difficulty, question["topic"], company,
                 question["id"], question["title"], score, feedback, elapsed)
    print(f"\n📊 Score saved: {score}/100")


# ─── Behavioral Mode ─────────────────────────────────────────────────────────

def run_behavioral(questions: dict, difficulty: str, topic: str, company: str, practice: bool, conn):
    """Run Behavioral interview question."""
    lps = load_lps()
    question = get_question(questions, "behavioral", difficulty, topic)
    if not question:
        print("❌ No matching questions found. Try a different topic or difficulty.")
        return

    print("\n" + "=" * 70)
    print(f"🎯 Behavioral Question: {question['title']}")
    print(f"   Difficulty: {difficulty.upper()} | Topic: {question['topic']}")
    if question.get("lp_mapping"):
        print(f"   Leadership Principles: {', '.join(question['lp_mapping'])}")
    print("=" * 70)
    print(f"\n{question['description']}\n")

    if practice:
        print("💡 Tips:")
        print("   • Use STAR format (Situation, Task, Action, Result)")
        print("   • Be specific with numbers and outcomes")
        print("   • Focus on YOUR contribution, not the team's")
        print()

    timer = Timer()
    timer.start()

    answer = get_multiline_input("✍️  Your answer (use STAR format):")
    elapsed = timer.stop()
    print(f"\n⏱️  Time: {elapsed // 60}m {elapsed % 60}s")

    # AI evaluation
    print("\n🤖 Evaluating your response...\n")
    company_context = COMPANY_STYLES.get(company, "")
    lp_context = ""
    if question.get("lp_mapping"):
        relevant_lps = [lp for lp in lps["leadership_principles"]
                        if lp["name"] in question["lp_mapping"]]
        lp_context = "\n".join([f"- {lp['name']}: {lp['description']}" for lp in relevant_lps])

    eval_prompt = f"""Evaluate this behavioral interview answer.

Question: {question['title']}
Description: {question['description']}
Relevant Leadership Principles:
{lp_context}
Candidate's Answer: {answer}
Time Taken: {elapsed} seconds
{f'Company Style: {company_context}' if company_context else ''}

Evaluate on:
1. **STAR Format** (0-25): Clear Situation, Task, Action, Result?
2. **Specificity** (0-25): Concrete examples, numbers, and outcomes?
3. **Leadership Principles** (0-25): How well does it demonstrate the relevant LPs?
4. **Communication** (0-25): Clear, concise, compelling storytelling?

Provide:
- Overall score (0-100)
- STAR analysis (what was present, what was missing)
- LP alignment assessment
- Strengths of the response
- Improvement suggestions
- 2 follow-up questions the interviewer might ask
- Suggested answer improvements

Format the score as: SCORE: X/100"""

    feedback = generate(eval_prompt, "You are an Amazon Bar Raiser conducting behavioral interviews.")
    print(feedback)

    score = 0
    for line in feedback.split("\n"):
        if "SCORE:" in line.upper():
            try:
                score = float("".join(c for c in line.split(":")[-1] if c.isdigit() or c == "."))
                if score > 100:
                    score = score / 10
            except (ValueError, IndexError):
                score = 50
            break

    save_session(conn, "behavioral", difficulty, question["topic"], company,
                 question["id"], question["title"], score, feedback, elapsed)
    print(f"\n📊 Score saved: {score}/100")


# ─── Mock Interview ──────────────────────────────────────────────────────────

def run_mock_interview(questions: dict, difficulty: str, company: str, conn):
    """Run a full mock interview (3 questions: 1 DSA, 1 System Design, 1 Behavioral)."""
    print("\n" + "=" * 70)
    print(f"🎬 FULL MOCK INTERVIEW")
    print(f"   Company: {(company or 'General').upper()} | Difficulty: {difficulty.upper()}")
    print(f"   Format: 1 Behavioral → 1 DSA → 1 System Design")
    print("=" * 70)
    print("\nThis simulates a real interview loop. Take your time.")
    print("Press Enter to begin...\n")
    input()

    # Round 1: Behavioral
    print("\n" + "─" * 40)
    print("📋 ROUND 1: Behavioral (15 min target)")
    print("─" * 40)
    run_behavioral(questions, difficulty, None, company, False, conn)

    print("\n\nPress Enter for the next round...")
    input()

    # Round 2: DSA
    print("\n" + "─" * 40)
    print("💻 ROUND 2: DSA/Coding (30 min target)")
    print("─" * 40)
    run_dsa(questions, difficulty, None, company, False, conn)

    print("\n\nPress Enter for the next round...")
    input()

    # Round 3: System Design
    print("\n" + "─" * 40)
    print("🏗️  ROUND 3: System Design (35 min target)")
    print("─" * 40)
    run_system_design(questions, difficulty, None, company, False, conn)

    print("\n" + "=" * 70)
    print("✅ MOCK INTERVIEW COMPLETE!")
    print("   Use --stats to see your performance over time.")
    print("=" * 70)


# ─── Review Mode ─────────────────────────────────────────────────────────────

def run_review(conn):
    """AI reviews recent answers and gives comprehensive feedback."""
    c = conn.cursor()
    c.execute("SELECT * FROM sessions ORDER BY timestamp DESC LIMIT 10")
    sessions = c.fetchall()

    if not sessions:
        print("❌ No sessions found. Practice some questions first!")
        return

    print("\n📊 Review of Recent Performance\n")

    summary = []
    for s in sessions:
        summary.append(f"- {s[2].upper()} ({s[3]}): {s[7]} - Score: {s[8]}/100 ({s[9]//60}m)")

    review_prompt = f"""Analyze these recent interview practice sessions and provide coaching:

Sessions:
{chr(10).join(summary)}

Provide:
1. **Overall Assessment** - How is the candidate doing?
2. **Strongest Area** - Where they perform best
3. **Biggest Gap** - Most critical area to improve
4. **Pattern Analysis** - Any trends (improving? struggling with specific topics?)
5. **Action Plan** - Top 3 things to focus on next
6. **Encouragement** - Motivational feedback"""

    feedback = generate(review_prompt, "You are a career coach specializing in tech interview preparation.")
    print(feedback)


# ─── Stats Mode ──────────────────────────────────────────────────────────────

def show_stats(conn):
    """Show progress statistics."""
    c = conn.cursor()

    # Overall stats
    c.execute("SELECT COUNT(*), AVG(score), SUM(time_taken_seconds) FROM sessions")
    total, avg_score, total_time = c.fetchone()

    if not total:
        print("❌ No sessions recorded yet. Start practicing!")
        return

    total_time = total_time or 0
    avg_score = avg_score or 0

    print("\n" + "=" * 50)
    print("📊 INTERVIEW PREP STATISTICS")
    print("=" * 50)

    print(f"\n  Total Sessions: {total}")
    print(f"  Average Score:  {avg_score:.1f}/100")
    print(f"  Total Time:     {total_time // 3600}h {(total_time % 3600) // 60}m")

    # By mode
    print("\n  By Mode:")
    c.execute("SELECT mode, COUNT(*), AVG(score) FROM sessions GROUP BY mode")
    for mode, count, avg in c.fetchall():
        print(f"    {mode.upper():15} {count:3} sessions  Avg: {avg:.1f}/100")

    # By difficulty
    print("\n  By Difficulty:")
    c.execute("SELECT difficulty, COUNT(*), AVG(score) FROM sessions GROUP BY difficulty")
    for diff, count, avg in c.fetchall():
        print(f"    {diff.upper():15} {count:3} sessions  Avg: {avg:.1f}/100")

    # Recent trend
    print("\n  Recent Scores (last 10):")
    c.execute("SELECT timestamp, mode, question_title, score FROM sessions ORDER BY timestamp DESC LIMIT 10")
    for ts, mode, title, score in c.fetchall():
        date = ts[:10]
        bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
        print(f"    {date} [{mode[:4].upper()}] {bar} {score:.0f} - {title[:30]}")

    print()


# ─── Weak Areas ──────────────────────────────────────────────────────────────

def analyze_weak_areas(conn):
    """AI identifies areas that need improvement."""
    c = conn.cursor()
    c.execute("""
        SELECT mode, difficulty, topic, question_title, score, feedback
        FROM sessions ORDER BY timestamp DESC LIMIT 20
    """)
    sessions = c.fetchall()

    if not sessions:
        print("❌ No sessions recorded. Practice first!")
        return

    # Find low-scoring areas
    by_topic = {}
    by_mode = {}
    for mode, diff, topic, title, score, feedback in sessions:
        by_topic.setdefault(topic, []).append(score)
        by_mode.setdefault(mode, []).append(score)

    print("\n🔍 Weak Areas Analysis\n")

    # Lowest scoring topics
    topic_avgs = [(t, sum(s)/len(s)) for t, s in by_topic.items() if t]
    topic_avgs.sort(key=lambda x: x[1])

    if topic_avgs:
        print("  Weakest Topics:")
        for topic, avg in topic_avgs[:5]:
            print(f"    • {topic}: {avg:.0f}/100")

    # AI analysis
    sessions_text = "\n".join([
        f"- {mode}/{diff}/{topic}: {title} = {score}/100"
        for mode, diff, topic, title, score, _ in sessions
    ])

    analysis = generate(
        f"""Based on these interview practice results, identify weak areas and create a study plan:

{sessions_text}

Provide:
1. Top 3 weak areas with specific evidence
2. Root cause analysis (why these areas are weak)
3. Personalized 2-week study plan
4. Specific resources or practice suggestions for each weak area
5. Quick wins (easiest improvements to make)""",
        "You are an expert interview coach analyzing practice performance data."
    )
    print(f"\n{analysis}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AI Interview Prep Bot - Practice DSA, System Design, and Behavioral interviews",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mode dsa --difficulty medium                  Random medium DSA
  %(prog)s --mode dsa --topic graphs --difficulty hard     Graph problems
  %(prog)s --mode system_design --difficulty medium        System design practice
  %(prog)s --mode behavioral --company amazon             Amazon behavioral
  %(prog)s --mock --difficulty medium --company amazon     Full mock interview
  %(prog)s --practice --mode dsa --difficulty easy         Practice with hints
  %(prog)s --review                                        AI reviews your progress
  %(prog)s --stats                                         View statistics
  %(prog)s --weak-areas                                    Identify weak areas
        """,
    )

    parser.add_argument("--mode", choices=["dsa", "system_design", "behavioral", "mixed"],
                        help="Interview mode")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="medium",
                        help="Difficulty level (default: medium)")
    parser.add_argument("--topic", type=str, help="Specific topic to focus on")
    parser.add_argument("--mock", action="store_true", help="Full mock interview")
    parser.add_argument("--practice", action="store_true", help="Practice mode (hints available)")
    parser.add_argument("--review", action="store_true", help="AI reviews your answers")
    parser.add_argument("--company", choices=["amazon", "google", "meta", "microsoft"],
                        help="Company style")
    parser.add_argument("--stats", action="store_true", help="Show progress statistics")
    parser.add_argument("--weak-areas", action="store_true", help="AI identifies areas to improve")

    args = parser.parse_args()

    if not any([args.mode, args.mock, args.review, args.stats, args.weak_areas]):
        parser.print_help()
        sys.exit(1)

    # Check Ollama
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
    except Exception:
        print("❌ Cannot connect to Ollama at", OLLAMA_URL)
        print("   Make sure Ollama is running: ollama serve")
        sys.exit(1)

    conn = init_db()
    questions = load_questions()

    try:
        if args.stats:
            show_stats(conn)
        elif args.weak_areas:
            analyze_weak_areas(conn)
        elif args.review:
            run_review(conn)
        elif args.mock:
            run_mock_interview(questions, args.difficulty, args.company, conn)
        elif args.mode == "dsa":
            run_dsa(questions, args.difficulty, args.topic, args.company, args.practice, conn)
        elif args.mode == "system_design":
            run_system_design(questions, args.difficulty, args.topic, args.company, args.practice, conn)
        elif args.mode == "behavioral":
            run_behavioral(questions, args.difficulty, args.topic, args.company, args.practice, conn)
        elif args.mode == "mixed":
            mode = random.choice(["dsa", "system_design", "behavioral"])
            print(f"🎲 Random mode selected: {mode.upper()}\n")
            if mode == "dsa":
                run_dsa(questions, args.difficulty, args.topic, args.company, args.practice, conn)
            elif mode == "system_design":
                run_system_design(questions, args.difficulty, args.topic, args.company, args.practice, conn)
            else:
                run_behavioral(questions, args.difficulty, args.topic, args.company, args.practice, conn)
    except KeyboardInterrupt:
        print("\n\n👋 Session ended. Progress saved!")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
