"""
Database Layer - Handles all database operations
Supports both PostgreSQL (production) and SQLite (development)
"""

import os
import sqlite3

try:
    import psycopg2
    import psycopg2.extras
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

from werkzeug.security import generate_password_hash


# ── Configuration ──────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(BASE_DIR, "matrimonial.db")

# Database configuration
USE_POSTGRES = bool(os.getenv("DATABASE_URL"))
DATABASE_URL = os.getenv("DATABASE_URL")

# Track if we're using in-memory database
_use_memory_db = False
_memory_db_connection = None  # Keep persistent connection for in-memory DB


# ── Connection Management ──────────────────────────────────────────────────────

def get_db_connection():
    """
    Get database connection (PostgreSQL for production, SQLite for local development)
    Returns: Connection object with cursor available
    """
    global _use_memory_db
    
    # Try PostgreSQL first if DATABASE_URL is set
    if USE_POSTGRES and HAS_POSTGRES:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.cursor_factory = psycopg2.extras.DictCursor
            print("✓ Connected to PostgreSQL")
            return conn
        except Exception as e:
            print(f"✗ PostgreSQL connection failed: {e}")
    
    # Try SQLite file database
    if not _use_memory_db:
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH, timeout=5)
            conn.row_factory = sqlite3.Row
            print(f"✓ Connected to SQLite: {SQLITE_DB_PATH}")
            return conn
        except (OSError, PermissionError, sqlite3.Error) as e:
            print(f"✗ Cannot access SQLite file ({SQLITE_DB_PATH}): {e}")
            print("→ Switching to in-memory database")
            _use_memory_db = True
    
    # Use shared in-memory database (allows multiple connections to same DB)
    if _use_memory_db:
        try:
            conn = sqlite3.connect('file::memory:?cache=shared', uri=True)
            conn.row_factory = sqlite3.Row
            print("⚠ Using shared in-memory SQLite database (data persists for this session)")
            return conn
        except Exception as e:
            print(f"✗ Failed to connect to shared memory DB: {e}")
            # Fallback to regular in-memory (will create separate DB per connection)
            conn = sqlite3.connect(':memory:')
            conn.row_factory = sqlite3.Row
            print("⚠ Using non-shared in-memory database (data may not persist)")
            return conn


def close_db_connection(conn):
    """Close database connection"""
    if conn:
        conn.close()


# ── Database Initialization ────────────────────────────────────────────────────

def init_db():
    """Initialize database schema (create tables if they don't exist)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES and HAS_POSTGRES:
            # PostgreSQL schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id          VARCHAR(50) PRIMARY KEY,
                    name        VARCHAR(255) NOT NULL,
                    email       VARCHAR(255) UNIQUE NOT NULL,
                    phone       VARCHAR(20),
                    dob         DATE,
                    gender      VARCHAR(20),
                    religion    VARCHAR(50),
                    caste       VARCHAR(50),
                    education   VARCHAR(50),
                    occupation  VARCHAR(100),
                    income      VARCHAR(50),
                    height      VARCHAR(20),
                    city        VARCHAR(100),
                    state       VARCHAR(100),
                    country     VARCHAR(100) DEFAULT 'India',
                    bio         TEXT,
                    photo       VARCHAR(255),
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id            SERIAL PRIMARY KEY,
                    email         VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            # SQLite schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    email       TEXT UNIQUE NOT NULL,
                    phone       TEXT,
                    dob         TEXT,
                    gender      TEXT,
                    religion    TEXT,
                    caste       TEXT,
                    education   TEXT,
                    occupation  TEXT,
                    income      TEXT,
                    height      TEXT,
                    city        TEXT,
                    state       TEXT,
                    country     TEXT DEFAULT 'India',
                    bio         TEXT,
                    photo       TEXT,
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    email         TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        conn.commit()
        cursor.close()
        close_db_connection(conn)
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"✗ Database initialization error: {e}")
        print("→ Attempting to re-initialize with in-memory database")
        
        # Force in-memory database and try again
        global _use_memory_db
        _use_memory_db = True
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # Create SQLite tables for in-memory DB
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    email       TEXT UNIQUE NOT NULL,
                    phone       TEXT,
                    dob         TEXT,
                    gender      TEXT,
                    religion    TEXT,
                    caste       TEXT,
                    education   TEXT,
                    occupation  TEXT,
                    income      TEXT,
                    height      TEXT,
                    city        TEXT,
                    state       TEXT,
                    country     TEXT DEFAULT 'India',
                    bio         TEXT,
                    photo       TEXT,
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    email         TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            cursor.close()
            close_db_connection(conn)
            print("✓ Database re-initialized with in-memory storage")
        except Exception as e2:
            print(f"✗ Failed to initialize in-memory database: {e2}")
            raise


def _ensure_tables_exist():
    """Ensure database tables exist (called before operations)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if users table exists
        if USE_POSTGRES and HAS_POSTGRES:
            cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_name='users'")
        else:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        
        table_exists = cursor.fetchone() is not None
        cursor.close()
        close_db_connection(conn)
        
        if not table_exists:
            print("⚠ Tables don't exist, initializing database...")
            init_db()
    except Exception as e:
        print(f"Warning: Could not check tables: {e}")


# ── User Operations ────────────────────────────────────────────────────────────

def get_user_by_email(email):
    """
    Fetch user by email address
    Args: email (str) - User email
    Returns: User row or None
    """
    try:
        _ensure_tables_exist()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES and HAS_POSTGRES:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        else:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        
        row = cursor.fetchone()
        cursor.close()
        close_db_connection(conn)
        return row
    except Exception as e:
        print(f"Error fetching user: {e}")
        raise


def create_user(email, password):
    """
    Create a new user account
    Args: email (str), password (str)
    Returns: None
    Raises: Exception on database error
    """
    try:
        _ensure_tables_exist()
        password_hash = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES and HAS_POSTGRES:
            cursor.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (email, password_hash))
        else:
            cursor.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, password_hash))
        
        conn.commit()
        cursor.close()
        close_db_connection(conn)
    except Exception as e:
        print(f"Error creating user: {e}")
        raise


# ── Profile Operations ─────────────────────────────────────────────────────────

def create_profile(profile_id, data, photo_filename=None):
    """
    Create a new profile
    Args: profile_id (str), data (dict with profile fields), photo_filename (str or None)
    Returns: None
    Raises: Exception on database error
    """
    try:
        _ensure_tables_exist()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES and HAS_POSTGRES:
            cursor.execute("""
                INSERT INTO profiles
                    (id, name, email, phone, dob, gender, religion, caste,
                     education, occupation, income, height, city, state, country, bio, photo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                profile_id,
                data.get("name"), data.get("email"), data.get("phone"),
                data.get("dob"), data.get("gender"), data.get("religion"),
                data.get("caste"), data.get("education"), data.get("occupation"),
                data.get("income"), data.get("height"), data.get("city"),
                data.get("state"), data.get("country", "India"),
                data.get("bio"), photo_filename
            ))
        else:
            cursor.execute("""
                INSERT INTO profiles
                    (id, name, email, phone, dob, gender, religion, caste,
                     education, occupation, income, height, city, state, country, bio, photo)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                profile_id,
                data.get("name"), data.get("email"), data.get("phone"),
                data.get("dob"), data.get("gender"), data.get("religion"),
                data.get("caste"), data.get("education"), data.get("occupation"),
                data.get("income"), data.get("height"), data.get("city"),
                data.get("state"), data.get("country", "India"),
                data.get("bio"), photo_filename
            ))
        
        conn.commit()
        cursor.close()
        close_db_connection(conn)
    except Exception as e:
        print(f"Error creating profile: {e}")
        raise


def get_profile_by_id(profile_id):
    """
    Fetch profile by ID
    Args: profile_id (str)
    Returns: Profile row or None
    """
    try:
        _ensure_tables_exist()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES and HAS_POSTGRES:
            cursor.execute("SELECT * FROM profiles WHERE id = %s", (profile_id,))
        else:
            cursor.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        
        row = cursor.fetchone()
        cursor.close()
        close_db_connection(conn)
        return row
    except Exception as e:
        print(f"Error fetching profile: {e}")
        raise


def search_profiles(query, limit=20):
    """
    Search profiles by name, email, or ID
    Args: query (str), limit (int)
    Returns: List of profile rows
    """
    try:
        _ensure_tables_exist()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        like_query = f"%{query}%"
        if USE_POSTGRES and HAS_POSTGRES:
            cursor.execute("""
                SELECT * FROM profiles
                WHERE id ILIKE %s OR name ILIKE %s OR email ILIKE %s
                ORDER BY created_at DESC LIMIT %s
            """, (like_query, like_query, like_query, limit))
        else:
            cursor.execute("""
                SELECT * FROM profiles
                WHERE id LIKE ? OR name LIKE ? OR email LIKE ?
                ORDER BY created_at DESC LIMIT ?
            """, (like_query, like_query, like_query, limit))
        
        rows = cursor.fetchall()
        cursor.close()
        close_db_connection(conn)
        return rows
    except Exception as e:
        print(f"Error searching profiles: {e}")
        raise


def get_all_profiles(limit=None):
    """
    Get all profiles ordered by creation date
    Args: limit (int or None)
    Returns: List of profile rows
    """
    try:
        _ensure_tables_exist()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if limit:
            if USE_POSTGRES and HAS_POSTGRES:
                cursor.execute("SELECT * FROM profiles ORDER BY created_at DESC LIMIT %s", (limit,))
            else:
                cursor.execute("SELECT * FROM profiles ORDER BY created_at DESC LIMIT ?", (limit,))
        else:
            cursor.execute("SELECT * FROM profiles ORDER BY created_at DESC")
        
        rows = cursor.fetchall()
        cursor.close()
        close_db_connection(conn)
        return rows
    except Exception as e:
        print(f"Error fetching all profiles: {e}")
        raise


def row_to_dict(row):
    """
    Convert database row to dictionary
    Works with both SQLite Row and PostgreSQL DictRow
    """
    if isinstance(row, dict):
        return dict(row)
    else:
        return dict(row)
