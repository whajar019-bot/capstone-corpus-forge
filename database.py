"""
Database module for Corpus Forge - AI-powered document knowledge platform.
Manages SQLite database operations for documents, artifacts, and usage tracking.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

# Database file path
DB_PATH = "corpus_forge.db"


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    Get a connection to the SQLite database.

    Args:
        db_path: Path to the database file (default: corpus_forge.db)

    Returns:
        sqlite3.Connection object
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def init_database(db_path: str = DB_PATH) -> None:
    """
    Initialize the database by creating all required tables if they don't exist.

    Args:
        db_path: Path to the database file (default: corpus_forge.db)
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        # Create documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                filetype TEXT NOT NULL,
                content TEXT NOT NULL,
                upload_date TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Create artifacts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK(type IN ('flashcard', 'quiz', 'code_review')),
                content TEXT NOT NULL,
                document_id INTEGER NOT NULL,
                created_date TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            )
        """)

        # Create usage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_count INTEGER NOT NULL DEFAULT 0,
                token_count INTEGER NOT NULL DEFAULT 0,
                timestamp TEXT NOT NULL
            )
        """)

        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Database initialization failed: {e}")
    finally:
        conn.close()


# ============================================================================
# DOCUMENT FUNCTIONS
# ============================================================================


def insert_document(
    filename: str, filetype: str, content: str, db_path: str = DB_PATH
) -> int:
    """
    Insert a new document into the database.

    Args:
        filename: Name of the document file
        filetype: Type of the file (e.g., 'pdf', 'txt', 'docx')
        content: Full text content of the document
        db_path: Path to the database file

    Returns:
        Document ID of the inserted record

    Raises:
        RuntimeError: If insertion fails
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        upload_date = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO documents (filename, filetype, content, upload_date, is_active)
            VALUES (?, ?, ?, ?, 1)
        """,
            (filename, filetype, content, upload_date),
        )
        conn.commit()
        document_id = cursor.lastrowid
        return document_id
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to insert document: {e}")
    finally:
        conn.close()


def get_all_documents(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Retrieve all documents from the database.

    Args:
        db_path: Path to the database file

    Returns:
        List of document dictionaries

    Raises:
        RuntimeError: If query fails
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM documents ORDER BY upload_date DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to retrieve documents: {e}")
    finally:
        conn.close()


def get_active_documents(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Retrieve all active documents from the database.

    Args:
        db_path: Path to the database file

    Returns:
        List of active document dictionaries

    Raises:
        RuntimeError: If query fails
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT * FROM documents WHERE is_active = 1 ORDER BY upload_date DESC"
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to retrieve active documents: {e}")
    finally:
        conn.close()


def toggle_document_active(document_id: int, db_path: str = DB_PATH) -> bool:
    """
    Toggle a document's active status (0 -> 1 or 1 -> 0).

    Args:
        document_id: ID of the document to toggle
        db_path: Path to the database file

    Returns:
        True if successful, False if document not found

    Raises:
        RuntimeError: If operation fails
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        # First, check if document exists
        cursor.execute("SELECT is_active FROM documents WHERE id = ?", (document_id,))
        row = cursor.fetchone()

        if row is None:
            return False

        # Toggle the status
        new_status = 1 - row[0]
        cursor.execute(
            "UPDATE documents SET is_active = ? WHERE id = ?", (new_status, document_id)
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to toggle document active status: {e}")
    finally:
        conn.close()


def delete_document(document_id: int, db_path: str = DB_PATH) -> bool:
    """
    Delete a document from the database (cascades to artifacts).

    Args:
        document_id: ID of the document to delete
        db_path: Path to the database file

    Returns:
        True if successful, False if document not found

    Raises:
        RuntimeError: If deletion fails
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to delete document: {e}")
    finally:
        conn.close()


# ============================================================================
# ARTIFACT FUNCTIONS
# ============================================================================


def insert_artifact(
    artifact_type: str,
    content: Dict[str, Any],
    document_id: int,
    db_path: str = DB_PATH,
) -> int:
    """
    Insert a new artifact into the database.

    Args:
        artifact_type: Type of artifact ('flashcard', 'quiz', or 'code_review')
        content: Artifact content as a dictionary (will be stored as JSON string)
        document_id: ID of the associated document (foreign key)
        db_path: Path to the database file

    Returns:
        Artifact ID of the inserted record

    Raises:
        ValueError: If artifact_type is invalid
        RuntimeError: If insertion fails
    """
    if artifact_type not in ("flashcard", "quiz", "code_review"):
        raise ValueError(
            f"Invalid artifact type: {artifact_type}. Must be 'flashcard', 'quiz', or 'code_review'"
        )

    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        created_date = datetime.now().isoformat()
        content_json = json.dumps(content)
        cursor.execute(
            """
            INSERT INTO artifacts (type, content, document_id, created_date)
            VALUES (?, ?, ?, ?)
        """,
            (artifact_type, content_json, document_id, created_date),
        )
        conn.commit()
        artifact_id = cursor.lastrowid
        return artifact_id
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to insert artifact: {e}")
    finally:
        conn.close()


def get_artifacts_by_type(
    artifact_type: str, db_path: str = DB_PATH
) -> List[Dict[str, Any]]:
    """
    Retrieve all artifacts of a specific type.

    Args:
        artifact_type: Type of artifact to retrieve ('flashcard', 'quiz', or 'code_review')
        db_path: Path to the database file

    Returns:
        List of artifact dictionaries with content parsed from JSON

    Raises:
        ValueError: If artifact_type is invalid
        RuntimeError: If query fails
    """
    if artifact_type not in ("flashcard", "quiz", "code_review"):
        raise ValueError(
            f"Invalid artifact type: {artifact_type}. Must be 'flashcard', 'quiz', or 'code_review'"
        )

    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT * FROM artifacts 
            WHERE type = ? 
            ORDER BY created_date DESC
        """,
            (artifact_type,),
        )
        rows = cursor.fetchall()

        artifacts = []
        for row in rows:
            artifact = dict(row)
            # Parse JSON content back to dictionary
            artifact["content"] = json.loads(artifact["content"])
            artifacts.append(artifact)

        return artifacts
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to retrieve artifacts: {e}")
    finally:
        conn.close()


# ============================================================================
# USAGE FUNCTIONS
# ============================================================================


def insert_usage_record(
    request_count: int = 0, token_count: int = 0, db_path: str = DB_PATH
) -> int:
    """
    Insert a new usage record into the database.

    Args:
        request_count: Number of API requests made
        token_count: Number of tokens consumed
        db_path: Path to the database file

    Returns:
        Usage record ID

    Raises:
        RuntimeError: If insertion fails
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        timestamp = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO usage (request_count, token_count, timestamp)
            VALUES (?, ?, ?)
        """,
            (request_count, token_count, timestamp),
        )
        conn.commit()
        usage_id = cursor.lastrowid
        return usage_id
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to insert usage record: {e}")
    finally:
        conn.close()


def get_total_usage_counts(db_path: str = DB_PATH) -> Dict[str, int]:
    """
    Get aggregated usage counts (total requests and tokens).

    Args:
        db_path: Path to the database file

    Returns:
        Dictionary with 'total_requests' and 'total_tokens' keys

    Raises:
        RuntimeError: If query fails
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT 
                COALESCE(SUM(request_count), 0) as total_requests,
                COALESCE(SUM(token_count), 0) as total_tokens
            FROM usage
        """)
        row = cursor.fetchone()

        return {
            "total_requests": row["total_requests"],
            "total_tokens": row["total_tokens"],
        }
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to retrieve usage counts: {e}")
    finally:
        conn.close()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def get_document_by_id(
    document_id: int, db_path: str = DB_PATH
) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific document by ID.

    Args:
        document_id: ID of the document
        db_path: Path to the database file

    Returns:
        Document dictionary or None if not found

    Raises:
        RuntimeError: If query fails
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to retrieve document: {e}")
    finally:
        conn.close()


def get_artifacts_by_document_id(
    document_id: int, db_path: str = DB_PATH
) -> List[Dict[str, Any]]:
    """
    Retrieve all artifacts associated with a specific document.

    Args:
        document_id: ID of the document
        db_path: Path to the database file

    Returns:
        List of artifact dictionaries with content parsed from JSON

    Raises:
        RuntimeError: If query fails
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT * FROM artifacts 
            WHERE document_id = ? 
            ORDER BY created_date DESC
        """,
            (document_id,),
        )
        rows = cursor.fetchall()

        artifacts = []
        for row in rows:
            artifact = dict(row)
            # Parse JSON content back to dictionary
            artifact["content"] = json.loads(artifact["content"])
            artifacts.append(artifact)

        return artifacts
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to retrieve artifacts for document: {e}")
    finally:
        conn.close()


def clear_database(db_path: str = DB_PATH) -> None:
    """
    Clear all data from all tables (useful for testing/reset).
    WARNING: This operation cannot be undone.

    Args:
        db_path: Path to the database file

    Raises:
        RuntimeError: If operation fails
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM artifacts")
        cursor.execute("DELETE FROM documents")
        cursor.execute("DELETE FROM usage")
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Failed to clear database: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    # Initialize the database when the module is run directly
    init_database()
    print(f"Database initialized at {DB_PATH}")
