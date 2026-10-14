"""
Local SQLite Fallback Database for AgroNex
Provides zero-setup persistence for users, profiles, and crop history
whenever Supabase Cloud credentials are not configured or offline.
"""

import sqlite3
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

DB_PATH = Path(__file__).resolve().parent.parent / "agronex.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_local_db():
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                mobile TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                hashed_password TEXT NOT NULL,
                location TEXT,
                preferred_language TEXT DEFAULT 'en',
                created_at TEXT NOT NULL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS farmer_profiles (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT,
                mobile TEXT,
                farm_size REAL DEFAULT 0,
                primary_crop TEXT DEFAULT 'Paddy',
                location TEXT,
                preferred_language TEXT DEFAULT 'en',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS crop_analyses (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                crop_type TEXT NOT NULL,
                image_path TEXT,
                detected_disease TEXT NOT NULL,
                confidence REAL NOT NULL,
                severity TEXT DEFAULT 'Not determined',
                risk_level TEXT DEFAULT 'Not determined',
                created_at TEXT NOT NULL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """)
    finally:
        conn.close()

# Auto-initialize tables on module import
init_local_db()

# --- Users & Auth Helpers ---
def save_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    try:
        with conn:
            conn.execute("""
            INSERT INTO users (id, name, mobile, email, hashed_password, location, preferred_language, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                user_data["name"],
                user_data["mobile"],
                user_data.get("email"),
                user_data["hashed_password"],
                user_data.get("location"),
                user_data.get("preferred_language", "en"),
                now
            ))
            # Also create default farmer profile
            conn.execute("""
            INSERT INTO farmer_profiles (id, user_id, name, mobile, farm_size, primary_crop, location, preferred_language, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                user_id,
                user_data["name"],
                user_data["mobile"],
                2.5,
                "Paddy",
                user_data.get("location", "Tamil Nadu"),
                user_data.get("preferred_language", "en"),
                now
            ))
        return {
            "id": user_id,
            "name": user_data["name"],
            "mobile": user_data["mobile"],
            "email": user_data.get("email"),
            "location": user_data.get("location"),
            "preferred_language": user_data.get("preferred_language", "en")
        }
    finally:
        conn.close()

def find_user_by_identifier(identifier: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE mobile = ? OR email = ?", (identifier, identifier))
        row = cur.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()

def find_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, mobile, email, location, preferred_language, created_at FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()

# --- Farmer Profile Helpers ---
def get_or_create_profile(user_id: Optional[str] = None) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        if user_id:
            cur.execute("SELECT * FROM farmer_profiles WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if row:
                return dict(row)

        cur.execute("SELECT * FROM farmer_profiles ORDER BY updated_at DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            return dict(row)

        # Default farmer fallback
        return {
            "name": "Arun Kumar",
            "mobile": "9876543210",
            "location": "Coimbatore, Tamil Nadu",
            "farm_size": 3.5,
            "primary_crop": "Paddy, Tomato",
            "preferred_language": "ta"
        }
    finally:
        conn.close()

def update_farmer_profile(profile_data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    try:
        with conn:
            existing = None
            if user_id:
                cur = conn.cursor()
                cur.execute("SELECT id FROM farmer_profiles WHERE user_id = ?", (user_id,))
                existing = cur.fetchone()
            if not existing:
                cur = conn.cursor()
                cur.execute("SELECT id FROM farmer_profiles ORDER BY updated_at DESC LIMIT 1")
                existing = cur.fetchone()

            if existing:
                prof_id = existing["id"]
                conn.execute("""
                UPDATE farmer_profiles
                SET name = COALESCE(?, name),
                    mobile = COALESCE(?, mobile),
                    farm_size = COALESCE(?, farm_size),
                    primary_crop = COALESCE(?, primary_crop),
                    location = COALESCE(?, location),
                    preferred_language = COALESCE(?, preferred_language),
                    updated_at = ?
                WHERE id = ?
                """, (
                    profile_data.get("name"),
                    profile_data.get("mobile"),
                    profile_data.get("farm_size"),
                    profile_data.get("primary_crop"),
                    profile_data.get("location"),
                    profile_data.get("preferred_language"),
                    now,
                    prof_id
                ))
            else:
                prof_id = str(uuid.uuid4())
                conn.execute("""
                INSERT INTO farmer_profiles (id, user_id, name, mobile, farm_size, primary_crop, location, preferred_language, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    prof_id,
                    user_id,
                    profile_data.get("name", "Farmer"),
                    profile_data.get("mobile", "9876543210"),
                    profile_data.get("farm_size", 2.0),
                    profile_data.get("primary_crop", "Tomato"),
                    profile_data.get("location", "Tamil Nadu"),
                    profile_data.get("preferred_language", "en"),
                    now
                ))
        return get_or_create_profile(user_id)
    finally:
        conn.close()

# --- Crop Analysis History Helpers ---
def save_crop_analysis(record: Dict[str, Any]) -> str:
    conn = get_connection()
    rec_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    try:
        with conn:
            conn.execute("""
            INSERT INTO crop_analyses (id, user_id, crop_type, image_path, detected_disease, confidence, severity, risk_level, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec_id,
                record.get("user_id"),
                record.get("crop_type", "Unknown"),
                record.get("image_path"),
                record.get("detected_disease", "Unknown"),
                float(record.get("confidence", 0.0)),
                record.get("severity", "Not determined"),
                record.get("risk_level", "Not determined"),
                now
            ))
        return rec_id
    finally:
        conn.close()

def get_recent_crop_analyses(limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM crop_analyses ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
