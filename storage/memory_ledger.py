import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "reposeer_profile.db")

def get_db_connection():
    """Establishes a thread-safe connection to the local SQLite ledger."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_ledger():
    """Initialises the database schemas if they do not already exist on disk."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Sessions Meta Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            session_mode TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            interviewer_persona TEXT NOT NULL
        )
    """)
    
    # 2. Skill Category Performance Percentages Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS category_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            category_name TEXT NOT NULL,
            score_percentage REAL NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    """)
    
    # 3. Weakness Frequency Tracker Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weakness_tracker (
            topic_tag TEXT PRIMARY KEY,
            occurrence_count INTEGER DEFAULT 1,
            last_flagged TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    print("💾 [Memory Ledger]: Adaptive persistence engine initialised successfully.")

def log_completed_session(metadata: Dict[str, Any], scores: Dict[str, float], weaknesses: List[str]):
    """
    Saves the entire performance blueprint to the database at the end of a run.
    Increments the historical frequency of missing engineering markers.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # Insert Session
        cursor.execute("""
            INSERT INTO sessions (timestamp, session_mode, difficulty, interviewer_persona)
            VALUES (?, ?, ?, ?)
        """, (now_str, metadata["session_mode"], metadata["difficulty"], metadata["interviewer_persona"]))
        session_id = cursor.lastrowid
        
        # Insert Category Metrics
        for category, score in scores.items():
            cursor.execute("""
                INSERT INTO category_scores (session_id, category_name, score_percentage)
                VALUES (?, ?, ?)
            """, (session_id, category, score))
            
        # Merge / Update Weakness Counts
        for topic in weaknesses:
            cursor.execute("""
                INSERT INTO weakness_tracker (topic_tag, occurrence_count, last_flagged)
                VALUES (?, 1, ?)
                ON CONFLICT(topic_tag) DO UPDATE SET 
                    occurrence_count = occurrence_count + 1,
                    last_flagged = ?
            """, (topic.strip().lower(), now_str, now_str))
            
        conn.commit()
        print(f"💾 [Memory Ledger]: Successfully synced performance metrics to Session Profile #{session_id}.")
    except Exception as e:
        conn.rollback()
        print(f"⚠️ [Memory Ledger Error]: Failed to write session data: {e}")
    finally:
        conn.close()

def get_historical_weaknesses(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Queries the database for your highest-frequency conceptual gaps.
    Used by the Interview Agent to dynamically adjust question focus.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT topic_tag, occurrence_count 
        FROM weakness_tracker 
        WHERE occurrence_count > 0 
        ORDER BY occurrence_count DESC 
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    return [{"topic": row["topic_tag"], "weight": row["occurrence_count"]} for row in rows]

# Auto-initialize on import execution entry point
if __name__ == "__main__":
    initialize_ledger()