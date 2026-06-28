import sqlite3
import json

def get_connection():
    conn = sqlite3.connect("conversations.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            session_id TEXT PRIMARY KEY,
            messages TEXT
        )
    """)
    return conn

def load_conversation(session_id):
    conn = get_connection()
    cursor = conn.execute(
        "SELECT messages FROM conversations WHERE session_id = ?",
        (session_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return json.loads(row[0])
    else:
        return None

def save_conversation(session_id, messages):
    conn = get_connection()
    messages_json = json.dumps(messages, default=lambda o: o.__dict__)
    conn.execute(
        "INSERT OR REPLACE INTO conversations (session_id, messages) VALUES (?, ?)",
        (session_id, messages_json)
    )
    conn.commit()
    conn.close()