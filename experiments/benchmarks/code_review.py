"""Code Review Benchmark — Agents collaboratively review code for issues."""

from harness.base import BenchmarkTask

CODE_SNIPPET = '''
import sqlite3
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_db():
    db = sqlite3.connect(os.environ.get("DB_PATH", "app.db"))
    return db

@app.route("/users/<user_id>")
def get_user(user_id):
    db = get_db()
    cursor = db.execute(f"SELECT * FROM users WHERE id = {user_id}")
    user = cursor.fetchone()
    if user:
        return jsonify({"id": user[0], "name": user[1], "email": user[2]})
    return jsonify({"error": "User not found"}), 404

@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
    db = get_db()
    db.execute(
        f"INSERT INTO users (name, email, password) VALUES ('{data['name']}', '{data['email']}', '{data['password']}')"
    )
    db.commit()
    return jsonify({"status": "created"}), 201

@app.route("/admin/delete_all", methods=["POST"])
def delete_all():
    db = get_db()
    db.execute("DELETE FROM users")
    db.commit()
    return jsonify({"status": "all users deleted"})

@app.route("/search")
def search():
    query = request.args.get("q", "")
    db = get_db()
    results = db.execute(f"SELECT * FROM users WHERE name LIKE '%{query}%'").fetchall()
    return "<html><body>" + "".join(f"<p>{r[1]}: {r[2]}</p>" for r in results) + "</body></html>"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
'''


def get_task() -> BenchmarkTask:
    return BenchmarkTask(
        id="code_review_01",
        name="Code Review",
        description=(
            "Review the following Python Flask application code for bugs, "
            "security vulnerabilities, performance issues, and best practice violations. "
            "Produce a structured code review report with severity ratings."
        ),
        input_data=f"Review this code:\n\n```python\n{CODE_SNIPPET}\n```",
        expected_aspects=[
            "SQL injection vulnerability in get_user (f-string in query)",
            "SQL injection vulnerability in create_user (f-string in INSERT)",
            "SQL injection vulnerability in search (f-string in LIKE query)",
            "XSS vulnerability in search (HTML output with unescaped user data)",
            "Password stored in plaintext (no hashing)",
            "No authentication on admin endpoint",
            "No CSRF protection",
            "Database connection not properly closed (no context manager)",
            "Debug mode enabled in production (debug=True)",
            "Bound to 0.0.0.0 (accessible from any network interface)",
            "No input validation on POST /users",
            "No rate limiting",
        ],
        evaluation_rubric={
            "completeness": "Did the review find all major issues? (SQL injection x3, XSS, plaintext password, no auth on admin, debug mode)",
            "severity_accuracy": "Are severity ratings appropriate? (SQL injection = Critical, debug mode = High, no rate limiting = Medium)",
            "actionability": "Does each finding include a specific fix recommendation?",
            "false_positives": "Are there any incorrect findings? Deduct for false positives.",
            "structure": "Is the review well-organized with clear sections?",
        },
        max_rounds=5,
        max_tokens=30000,
    )
