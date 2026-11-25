from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import sqlite3
import os
import re
from pathlib import Path
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "myday-development-secret-change-this")

DB_PATH = Path(os.environ.get("DATABASE_PATH", Path(__file__).with_name("tasks.db")))


# DATABASE CONNECTION
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# LOGIN REQUIRED
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


# DATABASE INITIALIZATION
def init_db():
    with get_db() as db:

        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'Medium',
                due_date TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        columns = [
            row["name"]
            for row in db.execute("PRAGMA table_info(tasks)").fetchall()
        ]

        if "user_id" not in columns:
            db.execute("ALTER TABLE tasks ADD COLUMN user_id INTEGER")


# SIGNUP PAGE
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill all fields.", "error")
            return redirect(url_for("signup"))

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Please enter a valid email.", "error")
            return redirect(url_for("signup"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for("signup"))

        hashed_password = generate_password_hash(password)

        try:
            with get_db() as db:

                cur = db.execute(
                    "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                    (name, email, hashed_password)
                )

                user_id = cur.lastrowid

                # Assign old tasks to the first registered account.
                db.execute(
                    "UPDATE tasks SET user_id = ? WHERE user_id IS NULL",
                    (user_id,)
                )

            session.clear()
            session["user_id"] = user_id
            session["user_name"] = name

            return redirect(url_for("home"))

        except sqlite3.IntegrityError:
            flash("Email already registered.", "error")
            return redirect(url_for("signup"))

    return render_template("signup.html")


# LOGIN PAGE
@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db() as db:
            user = db.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            ).fetchone()

        if user and check_password_hash(user["password"], password):

            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect(url_for("home"))

        flash("Incorrect email or password.", "error")

    return render_template("login.html")


# LOGOUT
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# DASHBOARD
@app.get("/")
@login_required
def home():

    return render_template("index.html")


# GET TASKS
@app.get("/api/tasks")
@login_required
def get_tasks():

    with get_db() as db:

        rows = db.execute(
            """
            SELECT * FROM tasks
            WHERE user_id = ?
            ORDER BY completed ASC, id DESC
            """,
            (session["user_id"],)
        ).fetchall()

    return jsonify([dict(row) for row in rows])


# ADD TASK
@app.post("/api/tasks")
@login_required
def add_task():

    data = request.get_json(silent=True) or {}

    title = str(data.get("title", "")).strip()
    priority = data.get("priority", "Medium")
    due_date = data.get("due_date") or None

    if not title:
        return jsonify({"error": "Please enter a task name."}), 400

    if len(title) > 180:
        return jsonify({"error": "Task name too long."}), 400

    if priority not in ("Low", "Medium", "High"):
        priority = "Medium"

    with get_db() as db:

        cur = db.execute(
            """
            INSERT INTO tasks (title, priority, due_date, user_id)
            VALUES (?, ?, ?, ?)
            """,
            (title, priority, due_date, session["user_id"])
        )

        row = db.execute(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
            (cur.lastrowid, session["user_id"])
        ).fetchone()

    return jsonify(dict(row)), 201


# UPDATE TASK
@app.patch("/api/tasks/<int:task_id>")
@login_required
def update_task(task_id):

    data = request.get_json(silent=True) or {}

    fields = []
    values = []

    if "completed" in data:
        fields.append("completed = ?")
        values.append(1 if data["completed"] else 0)

    if "title" in data:

        title = str(data["title"]).strip()

        if not title:
            return jsonify({"error": "Task name cannot be empty."}), 400

        fields.append("title = ?")
        values.append(title)

    if "priority" in data:

        priority = data["priority"]

        if priority not in ("Low", "Medium", "High"):
            priority = "Medium"

        fields.append("priority = ?")
        values.append(priority)

    if "due_date" in data:
        fields.append("due_date = ?")
        values.append(data["due_date"] or None)

    if not fields:
        return jsonify({"error": "No changes supplied."}), 400

    values.extend([task_id, session["user_id"]])

    with get_db() as db:

        cur = db.execute(
            f"""
            UPDATE tasks
            SET {', '.join(fields)}
            WHERE id = ? AND user_id = ?
            """,
            values
        )

        if cur.rowcount == 0:
            return jsonify({"error": "Task not found."}), 404

        row = db.execute(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, session["user_id"])
        ).fetchone()

    return jsonify(dict(row))


# DELETE TASK
@app.delete("/api/tasks/<int:task_id>")
@login_required
def delete_task(task_id):

    with get_db() as db:

        cur = db.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, session["user_id"])
        )

    if cur.rowcount == 0:
        return jsonify({"error": "Task not found."}), 404

    return jsonify({"success": True})


# CLEAR COMPLETED TASKS
@app.delete("/api/tasks")
@login_required
def clear_completed():

    with get_db() as db:

        db.execute(
            "DELETE FROM tasks WHERE completed = 1 AND user_id = ?",
            (session["user_id"],)
        )

    return jsonify({"success": True})


init_db()


if __name__ == "__main__":
    app.run(debug=True)