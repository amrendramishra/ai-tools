#!/usr/bin/env python3
"""Memory management module for the Personal AI Assistant."""

import sqlite3
import json
from datetime import datetime
from typing import Optional


class MemoryDB:
    """SQLite-backed memory store for conversations, notes, and reminders."""

    def __init__(self, db_path: str = "assistant_memory.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT DEFAULT (datetime('now')),
                session_id TEXT
            );
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                confidence REAL DEFAULT 1.0,
                source TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                completed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp);
            CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key);
            CREATE INDEX IF NOT EXISTS idx_memories_cat ON memories(category);
            CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created_at);
            CREATE INDEX IF NOT EXISTS idx_reminders_at ON reminders(remind_at);
        """)
        self.conn.commit()

    # --- Conversation History ---
    def add_message(self, role: str, content: str, session_id: Optional[str] = None):
        """Store a conversation message."""
        self.conn.execute(
            "INSERT INTO conversations (role, content, session_id) VALUES (?, ?, ?)",
            (role, content, session_id))
        self.conn.commit()

    def get_recent_messages(self, limit: int = 20) -> list:
        """Get recent conversation history."""
        cursor = self.conn.execute(
            "SELECT role, content, timestamp FROM conversations ORDER BY id DESC LIMIT ?",
            (limit,))
        return [dict(row) for row in reversed(cursor.fetchall())]

    def get_conversation_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]

    # --- Long-term Memory ---
    def remember(self, key: str, value: str, category: str = "general", source: str = "conversation"):
        """Store a fact/preference in long-term memory."""
        self.conn.execute("""
            INSERT INTO memories (key, value, category, source)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value, updated_at=datetime('now'), source=excluded.source
        """, (key, value, category, source))
        self.conn.commit()

    def recall(self, query: str, limit: int = 10) -> list:
        """Search memories by key or value."""
        cursor = self.conn.execute("""
            SELECT * FROM memories
            WHERE key LIKE ? OR value LIKE ?
            ORDER BY updated_at DESC LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_all_memories(self) -> list:
        """Get all stored memories."""
        cursor = self.conn.execute(
            "SELECT * FROM memories ORDER BY category, key")
        return [dict(row) for row in cursor.fetchall()]

    def forget_all(self):
        """Clear all memories and conversations."""
        self.conn.executescript("""
            DELETE FROM conversations;
            DELETE FROM memories;
        """)
        self.conn.commit()

    # --- Notes ---
    def add_note(self, content: str, tags: Optional[list] = None):
        """Save a quick note."""
        tags_json = json.dumps(tags or [])
        self.conn.execute(
            "INSERT INTO notes (content, tags) VALUES (?, ?)",
            (content, tags_json))
        self.conn.commit()

    def search_notes(self, query: str, limit: int = 20) -> list:
        """Search notes by content."""
        cursor = self.conn.execute("""
            SELECT * FROM notes WHERE content LIKE ?
            ORDER BY created_at DESC LIMIT ?
        """, (f"%{query}%", limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_recent_notes(self, limit: int = 10) -> list:
        """Get recent notes."""
        cursor = self.conn.execute(
            "SELECT * FROM notes ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

    # --- Reminders ---
    def add_reminder(self, text: str, remind_at: str):
        """Add a reminder."""
        self.conn.execute(
            "INSERT INTO reminders (text, remind_at) VALUES (?, ?)",
            (text, remind_at))
        self.conn.commit()

    def get_pending_reminders(self) -> list:
        """Get all pending (uncompleted) reminders."""
        cursor = self.conn.execute("""
            SELECT * FROM reminders WHERE completed = 0
            ORDER BY remind_at ASC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_today_reminders(self) -> list:
        """Get reminders for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = self.conn.execute("""
            SELECT * FROM reminders
            WHERE remind_at LIKE ? AND completed = 0
            ORDER BY remind_at ASC
        """, (f"{today}%",))
        return [dict(row) for row in cursor.fetchall()]

    def complete_reminder(self, reminder_id: int):
        """Mark a reminder as completed."""
        self.conn.execute(
            "UPDATE reminders SET completed = 1 WHERE id = ?", (reminder_id,))
        self.conn.commit()

    # --- Preferences ---
    def set_preference(self, key: str, value: str):
        """Store a user preference."""
        self.conn.execute("""
            INSERT INTO preferences (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')
        """, (key, value))
        self.conn.commit()

    def get_preference(self, key: str) -> Optional[str]:
        """Get a preference value."""
        cursor = self.conn.execute(
            "SELECT value FROM preferences WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None

    # --- Context Building ---
    def build_context(self, limit: int = 10) -> str:
        """Build context string from recent memory for AI prompts."""
        parts = []
        memories = self.get_all_memories()
        if memories:
            parts.append("What I know about the user:")
            for m in memories[:20]:
                parts.append(f"  - {m['key']}: {m['value']}")

        recent = self.get_recent_messages(limit)
        if recent:
            parts.append("\nRecent conversation:")
            for msg in recent:
                parts.append(f"  {msg['role']}: {msg['content'][:200]}")

        reminders = self.get_pending_reminders()
        if reminders:
            parts.append("\nPending reminders:")
            for r in reminders[:5]:
                parts.append(f"  - {r['text']} (at {r['remind_at']})")

        return "\n".join(parts)

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
