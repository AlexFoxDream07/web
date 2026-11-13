import os
import sqlite3
from pathlib import Path
from flask import Flask, jsonify, request
 
app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "tasks.sqlite3"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
 
 
def db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection
 
 
def initialize_db():
    connection = db_connection()
    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
    finally:
        connection.close()


@app.get("/")
def index():
    return jsonify({
        "service": os.getenv("APP_NAME", "Cloud Tasks"),
        "status": "running"
    })
 
 
@app.get("/health")
def health():
    return jsonify({"status": "ok"})
 
 
@app.get("/api/tasks")
def list_tasks():
    connection = db_connection()
    try:
        rows = connection.execute(
            "SELECT id, title, done, created_at "
            "FROM tasks ORDER BY id DESC"
        ).fetchall()
        return jsonify([dict(row) for row in rows])
    finally:
        connection.close()

 
@app.post("/api/tasks")
def create_task():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Ожидается JSON-объект"}), 400
 
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "Укажите название задачи"}), 400
    title = title.strip()
    if len(title) > 100:
        return jsonify({"error": "Слишком длинное название"}), 400
 
    connection = db_connection()
    try:
        cursor = connection.execute(
            "INSERT INTO tasks (title) VALUES (?)", (title,)
        )
        connection.commit()
        row = connection.execute(
            "SELECT id, title, done, created_at "
            "FROM tasks WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return jsonify(dict(row)), 201
    finally:
        connection.close()

@app.get("/api/tasks/<int:task_id>")
def get_task(task_id):
    connection = db_connection()
    try:
        row = connection.execute(
            "SELECT id, title, done, created_at FROM tasks WHERE id = ?",
            (task_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Задача не найдена"}), 404
        return jsonify(dict(row))
    finally:
        connection.close()

@app.patch("/api/tasks/<int:task_id>")
def update_task_status(task_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "done" not in data:
        return jsonify({"error": "Ожидается JSON с полем done"}), 400

    done_value = data["done"]
    if type(done_value) is not bool:
        return jsonify({"error": "Поле done должно быть логическим значением"}), 400

    connection = db_connection()
    try:
        cursor = connection.execute(
            "UPDATE tasks SET done = ? WHERE id = ?",
            (int(done_value), task_id)
        )
        connection.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "Задача не найдена"}), 404

        row = connection.execute(
            "SELECT id, title, done, created_at FROM tasks WHERE id = ?",
            (task_id,)
        ).fetchone()
        return jsonify(dict(row))
    finally:
        connection.close()

@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id):
    connection = db_connection()
    try:
        cursor = connection.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,)
        )
        connection.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "Задача не найдена"}), 404

        return "", 204
    finally:
        connection.close() 

@app.get("/api/stats")
def get_stats():
    connection = db_connection()
    try:
        row = connection.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) AS completed
            FROM tasks
        """).fetchone()

        total = row["total"]
        completed = row["completed"] or 0
        pending = total - completed

        return jsonify({
            "total": total,
            "completed": completed,
            "pending": pending
        })
    finally:
        connection.close()
 
initialize_db()
 
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)
