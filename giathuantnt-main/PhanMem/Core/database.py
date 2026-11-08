"""Lớp lưu trữ SQLite. Mọi truy vấn đều dùng tham số (?)."""
import sqlite3
from datetime import datetime

DB_PATH = "integrity.db"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("PRAGMA foreign_keys = ON")
    return c


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS files(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL, algorithm TEXT NOT NULL,
            hash_value TEXT NOT NULL, file_size INTEGER, registered_at TEXT,
            UNIQUE(path, algorithm));
        CREATE TABLE IF NOT EXISTS scan_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
            scanned_at TEXT, new_hash TEXT, status TEXT);
        CREATE TABLE IF NOT EXISTS benchmark(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT, file_size INTEGER, algorithm TEXT,
            run_no INTEGER, elapsed_ms REAL);
        """)


def add_file(path, algo, hash_value, size):
    """True nếu thêm mới, False nếu cặp (path, algo) đã có."""
    try:
        with _conn() as c:
            c.execute("INSERT INTO files(path,algorithm,hash_value,file_size,registered_at)"
                      " VALUES(?,?,?,?,?)", (path, algo, hash_value, size, _now()))
        return True
    except sqlite3.IntegrityError:
        return False


def get_all_files():
    with _conn() as c:
        return c.execute("SELECT id,path,algorithm,hash_value,file_size,registered_at"
                         " FROM files ORDER BY id").fetchall()


def delete_file(file_id):
    with _conn() as c:
        c.execute("DELETE FROM files WHERE id=?", (file_id,))


def update_hash(file_id, new_hash, size=None):
    with _conn() as c:
        c.execute("UPDATE files SET hash_value=?, file_size=COALESCE(?,file_size) WHERE id=?",
                  (new_hash, size, file_id))


def add_scan(file_id, new_hash, status):
    with _conn() as c:
        c.execute("INSERT INTO scan_history(file_id,scanned_at,new_hash,status) VALUES(?,?,?,?)",
                  (file_id, _now(), new_hash, status))


def get_history(status=None):
    sql = ("SELECT h.scanned_at,f.path,f.algorithm,h.status,h.new_hash FROM scan_history h"
           " JOIN files f ON f.id=h.file_id")
    args = ()
    if status and status != "Tất cả":
        sql += " WHERE h.status=?"
        args = (status,)
    with _conn() as c:
        return c.execute(sql + " ORDER BY h.id DESC", args).fetchall()


def add_benchmark(file_name, size, algo, run_no, elapsed_ms):
    with _conn() as c:
        c.execute("INSERT INTO benchmark(file_name,file_size,algorithm,run_no,elapsed_ms)"
                  " VALUES(?,?,?,?,?)", (file_name, size, algo, run_no, elapsed_ms))
