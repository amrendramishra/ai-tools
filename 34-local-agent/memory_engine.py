"""
Memory Engine - The learning and memory system for the AI agent.
Handles persistent storage, fact extraction, pattern detection, and predictions.
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class MemoryEngine:
    """Persistent memory system with learning capabilities."""

    def __init__(self, db_path: str = "agent_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with all required tables."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Facts: things learned about the user
        c.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                source TEXT DEFAULT 'conversation',
                learned_at TEXT NOT NULL,
                last_referenced TEXT,
                reference_count INTEGER DEFAULT 0,
                UNIQUE(category, key)
            )
        """)

        # Interactions: full conversation history
        c.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                context TEXT,
                embedding_hash TEXT,
                session_id TEXT
            )
        """)

        # Patterns: detected behavioral patterns
        c.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                description TEXT NOT NULL,
                data TEXT,
                confidence REAL DEFAULT 0.5,
                occurrences INTEGER DEFAULT 1,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                active INTEGER DEFAULT 1
            )
        """)

        # Predictions: what the user might need
        c.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction TEXT NOT NULL,
                basis TEXT,
                confidence REAL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                fulfilled INTEGER DEFAULT 0,
                fulfilled_at TEXT
            )
        """)

        # Sessions: track conversation sessions
        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                summary TEXT,
                topics TEXT
            )
        """)

        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # --- Facts Management ---

    def learn_fact(self, category: str, key: str, value: str,
                   confidence: float = 0.7, source: str = "conversation"):
        """Store a learned fact about the user."""
        conn = self._get_conn()
        c = conn.cursor()
        now = datetime.now().isoformat()

        try:
            c.execute("""
                INSERT INTO facts (category, key, value, confidence, source, learned_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(category, key) DO UPDATE SET
                    value = excluded.value,
                    confidence = MIN(1.0, confidence + 0.1),
                    last_referenced = ?,
                    reference_count = reference_count + 1
            """, (category, key, value, confidence, source, now, now))
            conn.commit()
        finally:
            conn.close()

    def get_facts(self, category: Optional[str] = None, limit: int = 50) -> list:
        """Retrieve learned facts, optionally filtered by category."""
        conn = self._get_conn()
        c = conn.cursor()

        if category:
            c.execute("""
                SELECT * FROM facts WHERE category = ?
                ORDER BY confidence DESC, reference_count DESC
                LIMIT ?
            """, (category, limit))
        else:
            c.execute("""
                SELECT * FROM facts
                ORDER BY confidence DESC, reference_count DESC
                LIMIT ?
            """, (limit,))

        results = [dict(row) for row in c.fetchall()]
        conn.close()
        return results

    def forget_topic(self, topic: str) -> int:
        """Remove memories related to a specific topic."""
        conn = self._get_conn()
        c = conn.cursor()

        # Remove from facts
        c.execute("""
            DELETE FROM facts
            WHERE key LIKE ? OR value LIKE ? OR category LIKE ?
        """, (f"%{topic}%", f"%{topic}%", f"%{topic}%"))
        facts_deleted = c.rowcount

        # Remove from patterns
        c.execute("""
            DELETE FROM patterns
            WHERE description LIKE ? OR data LIKE ?
        """, (f"%{topic}%", f"%{topic}%"))
        patterns_deleted = c.rowcount

        conn.commit()
        conn.close()
        return facts_deleted + patterns_deleted

    def search_facts(self, query: str) -> list:
        """Search facts by keyword."""
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM facts
            WHERE key LIKE ? OR value LIKE ? OR category LIKE ?
            ORDER BY confidence DESC
        """, (f"%{query}%", f"%{query}%", f"%{query}%"))
        results = [dict(row) for row in c.fetchall()]
        conn.close()
        return results

    # --- Interaction History ---

    def store_interaction(self, role: str, content: str,
                         context: Optional[dict] = None,
                         session_id: Optional[str] = None):
        """Store a conversation interaction."""
        conn = self._get_conn()
        c = conn.cursor()
        now = datetime.now().isoformat()
        embedding_hash = hashlib.md5(content.encode()).hexdigest()

        c.execute("""
            INSERT INTO interactions (role, content, timestamp, context, embedding_hash, session_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (role, content, now, json.dumps(context) if context else None,
              embedding_hash, session_id))
        conn.commit()
        conn.close()

    def get_recent_interactions(self, limit: int = 20, session_id: Optional[str] = None) -> list:
        """Get recent conversation history."""
        conn = self._get_conn()
        c = conn.cursor()

        if session_id:
            c.execute("""
                SELECT * FROM interactions
                WHERE session_id = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (session_id, limit))
        else:
            c.execute("""
                SELECT * FROM interactions
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))

        results = [dict(row) for row in c.fetchall()]
        conn.close()
        return list(reversed(results))

    def get_interaction_count(self) -> int:
        """Get total number of interactions."""
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM interactions")
        count = c.fetchone()[0]
        conn.close()
        return count

    # --- Pattern Detection ---

    def record_pattern(self, pattern_type: str, description: str,
                       data: Optional[dict] = None, confidence: float = 0.5):
        """Record or update a detected pattern."""
        conn = self._get_conn()
        c = conn.cursor()
        now = datetime.now().isoformat()

        # Check if similar pattern exists
        c.execute("""
            SELECT id, occurrences, confidence FROM patterns
            WHERE pattern_type = ? AND description = ? AND active = 1
        """, (pattern_type, description))
        existing = c.fetchone()

        if existing:
            new_confidence = min(1.0, existing['confidence'] + 0.05)
            c.execute("""
                UPDATE patterns
                SET occurrences = occurrences + 1,
                    confidence = ?,
                    last_seen = ?
                WHERE id = ?
            """, (new_confidence, now, existing['id']))
        else:
            c.execute("""
                INSERT INTO patterns (pattern_type, description, data, confidence, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (pattern_type, description, json.dumps(data) if data else None,
                  confidence, now, now))

        conn.commit()
        conn.close()

    def get_patterns(self, pattern_type: Optional[str] = None, active_only: bool = True) -> list:
        """Get detected patterns."""
        conn = self._get_conn()
        c = conn.cursor()

        query = "SELECT * FROM patterns WHERE 1=1"
        params = []

        if pattern_type:
            query += " AND pattern_type = ?"
            params.append(pattern_type)
        if active_only:
            query += " AND active = 1"

        query += " ORDER BY confidence DESC, occurrences DESC"
        c.execute(query, params)
        results = [dict(row) for row in c.fetchall()]
        conn.close()
        return results

    # --- Predictions ---

    def make_prediction(self, prediction: str, basis: str, confidence: float = 0.5):
        """Store a prediction about what the user might need."""
        conn = self._get_conn()
        c = conn.cursor()
        now = datetime.now().isoformat()

        c.execute("""
            INSERT INTO predictions (prediction, basis, confidence, created_at)
            VALUES (?, ?, ?, ?)
        """, (prediction, basis, confidence, now))
        conn.commit()
        conn.close()

    def get_predictions(self, unfulfilled_only: bool = True, limit: int = 10) -> list:
        """Get predictions."""
        conn = self._get_conn()
        c = conn.cursor()

        if unfulfilled_only:
            c.execute("""
                SELECT * FROM predictions
                WHERE fulfilled = 0
                ORDER BY confidence DESC, created_at DESC
                LIMIT ?
            """, (limit,))
        else:
            c.execute("""
                SELECT * FROM predictions
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))

        results = [dict(row) for row in c.fetchall()]
        conn.close()
        return results

    # --- Context Building ---

    def get_context_summary(self) -> dict:
        """Build a context summary for the AI to use."""
        now = datetime.now()
        facts = self.get_facts(limit=30)
        patterns = self.get_patterns()
        predictions = self.get_predictions(limit=5)
        interaction_count = self.get_interaction_count()

        # Group facts by category
        facts_by_category = {}
        for fact in facts:
            cat = fact['category']
            if cat not in facts_by_category:
                facts_by_category[cat] = []
            facts_by_category[cat].append(f"{fact['key']}: {fact['value']}")

        return {
            "time_context": {
                "current_time": now.strftime("%H:%M"),
                "day_of_week": now.strftime("%A"),
                "date": now.strftime("%Y-%m-%d"),
                "time_of_day": self._get_time_of_day(now.hour),
            },
            "user_facts": facts_by_category,
            "patterns": [
                {"type": p['pattern_type'], "desc": p['description'],
                 "confidence": p['confidence']}
                for p in patterns[:10]
            ],
            "predictions": [
                {"prediction": p['prediction'], "confidence": p['confidence']}
                for p in predictions
            ],
            "stats": {
                "total_interactions": interaction_count,
                "facts_known": len(facts),
                "patterns_detected": len(patterns),
            }
        }

    def _get_time_of_day(self, hour: int) -> str:
        """Get friendly time of day description."""
        if 5 <= hour < 9:
            return "early morning"
        elif 9 <= hour < 12:
            return "morning"
        elif 12 <= hour < 14:
            return "lunchtime"
        elif 14 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 20:
            return "evening"
        elif 20 <= hour < 23:
            return "night"
        else:
            return "late night"

    # --- Weekly Review Data ---

    def get_weekly_summary(self) -> dict:
        """Get data for weekly review."""
        conn = self._get_conn()
        c = conn.cursor()
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()

        # Interactions this week
        c.execute("""
            SELECT COUNT(*) as count, DATE(timestamp) as day
            FROM interactions
            WHERE timestamp > ?
            GROUP BY DATE(timestamp)
        """, (week_ago,))
        daily_activity = [dict(row) for row in c.fetchall()]

        # Facts learned this week
        c.execute("""
            SELECT * FROM facts WHERE learned_at > ?
            ORDER BY learned_at DESC
        """, (week_ago,))
        new_facts = [dict(row) for row in c.fetchall()]

        # Patterns detected this week
        c.execute("""
            SELECT * FROM patterns WHERE last_seen > ?
            ORDER BY occurrences DESC
        """, (week_ago,))
        active_patterns = [dict(row) for row in c.fetchall()]

        conn.close()

        return {
            "daily_activity": daily_activity,
            "new_facts_learned": new_facts,
            "active_patterns": active_patterns,
            "total_interactions_this_week": sum(d['count'] for d in daily_activity),
        }

    # --- Session Management ---

    def start_session(self, session_id: str):
        """Start a new conversation session."""
        conn = self._get_conn()
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("""
            INSERT OR IGNORE INTO sessions (id, started_at)
            VALUES (?, ?)
        """, (session_id, now))
        conn.commit()
        conn.close()

    def end_session(self, session_id: str, summary: str = None, topics: list = None):
        """End a conversation session."""
        conn = self._get_conn()
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("""
            UPDATE sessions SET ended_at = ?, summary = ?, topics = ?
            WHERE id = ?
        """, (now, summary, json.dumps(topics) if topics else None, session_id))
        conn.commit()
        conn.close()
