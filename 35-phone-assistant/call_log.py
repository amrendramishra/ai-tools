"""
Call Log - Database module for the AI Phone Call Assistant.
Handles storage and retrieval of call records, transcriptions, and classifications.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class CallLog:
    """Manages call/message database with SQLite backend."""

    def __init__(self, db_path: str = "calls.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL DEFAULT 'voicemail',
                audio_file TEXT,
                duration_seconds REAL,
                transcription TEXT,
                summary TEXT,
                caller_context TEXT,
                urgency TEXT DEFAULT 'normal',
                is_spam INTEGER DEFAULT 0,
                action_needed TEXT,
                classification TEXT,
                recorded_at TEXT NOT NULL,
                transcribed_at TEXT,
                status TEXT DEFAULT 'new',
                notes TEXT,
                tags TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                audio_file TEXT,
                duration_seconds REAL,
                transcription TEXT,
                notes TEXT,
                summary TEXT,
                action_items TEXT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                status TEXT DEFAULT 'recording'
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS meeting_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                audio_file TEXT,
                transcription TEXT,
                notes TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id INTEGER,
                message TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                FOREIGN KEY (call_id) REFERENCES calls(id)
            )
        """)

        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_call(self, audio_file: str, duration: float = 0,
                 call_type: str = "voicemail", caller_context: str = None) -> int:
        conn = self._get_conn()
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("""
            INSERT INTO calls (type, audio_file, duration_seconds, caller_context, recorded_at)
            VALUES (?, ?, ?, ?, ?)
        """, (call_type, audio_file, duration, caller_context, now))
        call_id = c.lastrowid
        conn.commit()
        conn.close()
        return call_id

    def update_transcription(self, call_id: int, transcription: str):
        conn = self._get_conn()
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("""
            UPDATE calls SET transcription = ?, transcribed_at = ?, status = 'transcribed'
            WHERE id = ?
        """, (transcription, now, call_id))
        conn.commit()
        conn.close()

    def update_classification(self, call_id: int, urgency: str, is_spam: bool,
                              action_needed: str, summary: str, classification: str):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
            UPDATE calls SET urgency = ?, is_spam = ?, action_needed = ?,
                summary = ?, classification = ?, status = 'classified'
            WHERE id = ?
        """, (urgency, int(is_spam), action_needed, summary, classification, call_id))
        conn.commit()
        conn.close()

    def get_call(self, call_id: int) -> Optional[dict]:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM calls WHERE id = ?", (call_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_history(self, limit: int = 20, offset: int = 0) -> list:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM calls ORDER BY recorded_at DESC LIMIT ? OFFSET ?", (limit, offset))
        results = [dict(row) for row in c.fetchall()]
        conn.close()
        return results

    def filter_calls(self, filter_type: str) -> list:
        conn = self._get_conn()
        c = conn.cursor()
        if filter_type == "urgent":
            c.execute("SELECT * FROM calls WHERE urgency IN ('urgent','high') ORDER BY recorded_at DESC")
        elif filter_type == "spam":
            c.execute("SELECT * FROM calls WHERE is_spam = 1 ORDER BY recorded_at DESC")
        elif filter_type == "missed":
            c.execute("SELECT * FROM calls WHERE status = 'new' AND is_spam = 0 ORDER BY recorded_at DESC")
        elif filter_type == "action":
            c.execute("SELECT * FROM calls WHERE action_needed IS NOT NULL AND action_needed != '' ORDER BY recorded_at DESC")
        else:
            c.execute("SELECT * FROM calls ORDER BY recorded_at DESC")
        results = [dict(row) for row in c.fetchall()]
        conn.close()
        return results

    def get_stats(self) -> dict:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM calls")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM calls WHERE urgency IN ('urgent','high')")
        urgent = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM calls WHERE is_spam = 1")
        spam = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM calls WHERE status = 'new'")
        unread = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM meetings")
        meetings = c.fetchone()[0]
        conn.close()
        return {"total_calls": total, "urgent": urgent, "spam": spam, "unread": unread, "meetings": meetings}

    def start_meeting(self, title: str = None, audio_file: str = None) -> int:
        conn = self._get_conn()
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("INSERT INTO meetings (title, audio_file, started_at, status) VALUES (?, ?, ?, 'recording')",
                  (title or f"Meeting {now[:10]}", audio_file, now))
        meeting_id = c.lastrowid
        conn.commit()
        conn.close()
        return meeting_id

    def add_meeting_chunk(self, meeting_id: int, chunk_index: int,
                          transcription: str, notes: str = None, audio_file: str = None):
        conn = self._get_conn()
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("""
            INSERT INTO meeting_chunks (meeting_id, chunk_index, audio_file, transcription, notes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (meeting_id, chunk_index, audio_file, transcription, notes, now))
        conn.commit()
        conn.close()

    def end_meeting(self, meeting_id: int, summary: str = None,
                    action_items: str = None, duration: float = None):
        conn = self._get_conn()
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("SELECT transcription FROM meeting_chunks WHERE meeting_id = ? ORDER BY chunk_index", (meeting_id,))
        chunks = c.fetchall()
        full_transcription = "\n".join(row[0] for row in chunks if row[0])
        c.execute("""
            UPDATE meetings SET ended_at = ?, duration_seconds = ?, transcription = ?,
                summary = ?, action_items = ?, status = 'completed'
            WHERE id = ?
        """, (now, duration, full_transcription, summary, action_items, meeting_id))
        conn.commit()
        conn.close()

    def get_meeting(self, meeting_id: int) -> Optional[dict]:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_meetings(self, limit: int = 10) -> list:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM meetings ORDER BY started_at DESC LIMIT ?", (limit,))
        results = [dict(row) for row in c.fetchall()]
        conn.close()
        return results

    def add_notification(self, call_id: int, message: str, notif_type: str = "info"):
        conn = self._get_conn()
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("INSERT INTO notifications (call_id, message, sent_at, type) VALUES (?, ?, ?, ?)",
                  (call_id, message, now, notif_type))
        conn.commit()
        conn.close()
