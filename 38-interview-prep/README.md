# AI Interview Prep Bot

A comprehensive AI-powered interview preparation system covering DSA, System Design, and Behavioral interviews with a focus on Amazon Leadership Principles.

## Features

- **DSA Practice**: Timed coding problems with hints, complexity analysis, and AI evaluation
- **System Design**: Scenario-based design with follow-up questions and scoring
- **Behavioral (Amazon LP)**: STAR format evaluation with Leadership Principles mapping
- **Full Mock Interviews**: Simulated 3-round interview loops
- **Progress Tracking**: SQLite-based statistics and trend analysis
- **AI Coaching**: Personalized feedback, weak area identification, and study plans
- **Company-Specific**: Adjustable style for Amazon, Google, Meta, Microsoft

## Setup

```bash
source ~/Downloads/AI/.venv/bin/activate

# Ensure Ollama is running
ollama pull llama3.2
```

## Usage

### Practice by Mode

```bash
# DSA - various difficulties and topics
./interview_prep.py --mode dsa --difficulty easy
./interview_prep.py --mode dsa --difficulty medium --topic graphs
./interview_prep.py --mode dsa --difficulty hard --topic "dynamic_programming"

# System Design
./interview_prep.py --mode system_design --difficulty medium
./interview_prep.py --mode system_design --difficulty hard --topic streaming

# Behavioral (Amazon-focused)
./interview_prep.py --mode behavioral --company amazon
./interview_prep.py --mode behavioral --difficulty hard --topic leadership

# Mixed (random mode selection)
./interview_prep.py --mode mixed --difficulty medium
```

### Practice Mode (with hints)

```bash
./interview_prep.py --practice --mode dsa --difficulty medium
```

### Full Mock Interview

```bash
./interview_prep.py --mock --difficulty medium --company amazon
```

### Review & Stats

```bash
./interview_prep.py --stats           # View progress statistics
./interview_prep.py --review          # AI reviews recent performance
./interview_prep.py --weak-areas      # Identify areas to improve
```

## Question Bank

- **DSA**: 20 questions (6 easy, 8 medium, 6 hard)
  - Topics: arrays, stacks, linked_lists, trees, graphs, dynamic_programming, binary_search, heap, backtracking, design
- **System Design**: 11 questions (3 easy, 5 medium, 3 hard)
  - Topics: web_services, infrastructure, databases, social_media, messaging, real_time, microservices, search, streaming, geospatial
- **Behavioral**: 20 questions (4 easy, 8 medium, 8 hard)
  - Topics: introduction, motivation, achievement, conflict, failure, ambiguity, decision_making, pressure, influence, improvement, people, prioritization, leadership, backbone, innovation, crisis, trade_offs, change_management, strategy, mentoring

## Amazon Leadership Principles

All 16 LPs are included in `amazon_lps.json` with:
- Description of each principle
- Example interview questions
- Follow-up questions

## Scoring

Each answer is evaluated on a 0-100 scale across 4 dimensions:
- **DSA**: Correctness, Complexity, Code Quality, Communication
- **System Design**: Requirements, Architecture, Scalability, Trade-offs, Deep Dive
- **Behavioral**: STAR Format, Specificity, LP Alignment, Communication

## Data Storage

Progress is stored in `interview_stats.db` (SQLite) with:
- Session timestamps
- Scores and feedback
- Time taken
- Question details
