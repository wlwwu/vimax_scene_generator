"""
SQLite database manager for scene storage.
Stores scene photos (locations like 平江路) that users can select
to generate walking videos with their person photos.
"""
import sqlite3
import os
from typing import Optional

DB_PATH = "scenes.db"
SCENES_DIR = "assets/scenes"


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: str = DB_PATH):
    """Create tables if they don't exist."""
    conn = get_connection(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS scenes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            description TEXT,
            image_path  TEXT NOT NULL,
            category    TEXT DEFAULT 'street',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS generations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            scene_id        INTEGER REFERENCES scenes(id),
            person_image    TEXT NOT NULL,
            composite_image TEXT,
            video_path      TEXT,
            prompt_used     TEXT,
            status          TEXT DEFAULT 'pending',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


def add_scene(name: str, image_path: str, description: str = "",
              category: str = "street", db_path: str = DB_PATH) -> int:
    """Add a scene to the database. Returns the new scene id."""
    conn = get_connection(db_path)
    cursor = conn.execute(
        "INSERT INTO scenes (name, description, image_path, category) VALUES (?, ?, ?, ?)",
        (name, description, image_path, category),
    )
    scene_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return scene_id


def list_scenes(category: Optional[str] = None, db_path: str = DB_PATH) -> list[dict]:
    """List all scenes, optionally filtered by category."""
    conn = get_connection(db_path)
    if category:
        rows = conn.execute(
            "SELECT * FROM scenes WHERE category = ? ORDER BY name", (category,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM scenes ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_scene(scene_id: int, db_path: str = DB_PATH) -> Optional[dict]:
    """Get a single scene by id."""
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_scene_by_name(name: str, db_path: str = DB_PATH) -> Optional[dict]:
    """Get a scene by its name."""
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM scenes WHERE name = ?", (name,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_scene(scene_id: int, db_path: str = DB_PATH):
    """Delete a scene by id."""
    conn = get_connection(db_path)
    conn.execute("DELETE FROM scenes WHERE id = ?", (scene_id,))
    conn.commit()
    conn.close()


def update_scene_description(scene_id: int, description: str, db_path: str = DB_PATH):
    """Update the cached description for a scene."""
    conn = get_connection(db_path)
    conn.execute(
        "UPDATE scenes SET description = ? WHERE id = ?", (description, scene_id)
    )
    conn.commit()
    conn.close()


def log_generation(scene_id: int, person_image: str, db_path: str = DB_PATH) -> int:
    """Log a new generation request. Returns generation id."""
    conn = get_connection(db_path)
    cursor = conn.execute(
        "INSERT INTO generations (scene_id, person_image, status) VALUES (?, ?, 'pending')",
        (scene_id, person_image),
    )
    gen_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return gen_id


def update_generation(gen_id: int, status: str, composite_image: str = "",
                      video_path: str = "", prompt_used: str = "",
                      db_path: str = DB_PATH):
    """Update a generation record with results."""
    conn = get_connection(db_path)
    conn.execute(
        """UPDATE generations
           SET status = ?, composite_image = ?, video_path = ?, prompt_used = ?
           WHERE id = ?""",
        (status, composite_image, video_path, prompt_used, gen_id),
    )
    conn.commit()
    conn.close()


def list_generations(limit: int = 20, db_path: str = DB_PATH) -> list[dict]:
    """List recent generations."""
    conn = get_connection(db_path)
    rows = conn.execute(
        """SELECT g.*, s.name as scene_name
           FROM generations g
           LEFT JOIN scenes s ON g.scene_id = s.id
           ORDER BY g.created_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize DB on import
os.makedirs(SCENES_DIR, exist_ok=True)
init_db()
