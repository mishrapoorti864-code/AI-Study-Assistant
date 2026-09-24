import os
import sqlite3

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, session, jsonify
from openai import OpenAI
from werkzeug.security import generate_password_hash, check_password_hash


# =========================
# LOAD ENVIRONMENT VARIABLES
# =========================

load_dotenv()


# =========================
# FLASK APP
# =========================

app = Flask(__name__)

app.secret_key = "ai-study-assistant-secret-key"


# =========================
# DATABASE
# =========================

def init_db():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            course TEXT,
            year TEXT,
            password TEXT NOT NULL
        )
    """)

    # Quiz results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            percentage REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# =========================
# HOME
# =========================

@app.route("/")
def home():

    return render_template("index.html")


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        course = request.form.get("course", "").strip()
        year = request.form.get("year", "").strip()
        password = request.form.get("password", "")

        # Check required fields
        if not name or not email or not password:

            return "Please fill all required fields."

        # Hash password
        hashed_password = generate_password_hash(password)

        try:

            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO users
                (name, email, course, year, password)
                VALUES (?, ?, ?, ?, ?)
            """, (
                name,
                email,
                course,
                year,
                hashed_password
            ))

            conn.commit()
            conn.close()

            return redirect("/login")

        except sqlite3.IntegrityError:

            return "Email already registered!"

        except Exception as e:

            print("REGISTER ERROR:", repr(e))

            return f"Registration failed: {str(e)}", 500

    return render_template("register.html")


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:

            return "Please enter email and password."

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM users
            WHERE email = ?
        """, (email,))

        user = cursor.fetchone()

        conn.close()

        # Check login
        if user and check_password_hash(user[5], password):

            session["user_id"] = user[0]
            session["user_name"] = user[1]

            return redirect("/dashboard")

        return "Invalid email or password!"

    return render_template("login.html")


# =========================
# PROFILE
# =========================

@app.route("/profile")
def profile():

    if "user_id" not in session:

        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, email, course, year
        FROM users
        WHERE id = ?
    """, (session["user_id"],))

    user = cursor.fetchone()

    conn.close()

    if not user:

        return redirect("/login")

    return render_template(
        "profile.html",
        name=user[0],
        email=user[1],
        course=user[2],
        year=user[3]
    )


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    user_id = session["user_id"]

    # Total quizzes
    cursor.execute("""
        SELECT COUNT(*)
        FROM quiz_results
        WHERE user_id = ?
    """, (user_id,))

    total_quizzes = cursor.fetchone()[0]

    # Average score
    cursor.execute("""
        SELECT AVG(percentage)
        FROM quiz_results
        WHERE user_id = ?
    """, (user_id,))

    average_score = cursor.fetchone()[0]

    if average_score is None:

        average_score = 0

    # Total topics
    cursor.execute("""
        SELECT COUNT(DISTINCT topic)
        FROM quiz_results
        WHERE user_id = ?
    """, (user_id,))

    topics = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        name=session["user_name"],
        total_quizzes=total_quizzes,
        average_score=round(average_score, 1),
        topics=topics
    )

# =========================
# SUBJECTS PAGE
# =========================

@app.route("/subjects")
def subjects():

    if "user_id" not in session:
        return redirect("/login")

    subjects_list = [
        {
            "name": "Data Structures",
            "icon": "📚",
            "topics": [
                "Array",
                "Linked List",
                "Stack",
                "Queue",
                "Tree",
                "Graph"
            ]
        },
        {
            "name": "Computer Organization",
            "icon": "💻",
            "topics": [
                "Computer Architecture",
                "Register",
                "Memory",
                "Instruction Cycle",
                "Addressing Modes",
                "CPU"
            ]
        },
        {
            "name": "Digital Electronics",
            "icon": "⚡",
            "topics": [
                "Logic Gates",
                "Adder",
                "Subtractor",
                "Multiplexer",
                "Decoder",
                "Counter"
            ]
        },
        {
            "name": "C++ Programming",
            "icon": "🧑‍💻",
            "topics": [
                "Variables",
                "Loops",
                "Functions",
                "Arrays",
                "Pointers",
                "OOP"
            ]
        },
        {
            "name": "Database Management",
            "icon": "🗄️",
            "topics": [
                "DBMS",
                "SQL",
                "Keys",
                "Normalization",
                "ER Diagram",
                "Transactions"
            ]
        },
        {
            "name": "Computer Networks",
            "icon": "🌐",
            "topics": [
                "Network Types",
                "OSI Model",
                "TCP/IP",
                "IP Address",
                "Routing",
                "Protocols"
            ]
        }
    ]

    return render_template(
        "subjects.html",
        subjects=subjects_list
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================
# AI CHAT PAGE
# =========================

@app.route("/chat")
def chat():

    if "user_id" not in session:

        return redirect("/login")

    return render_template("chat.html")


# =========================
# AI CHAT API
# =========================

@app.route("/api/chat", methods=["POST"])
def api_chat():

    data = request.get_json(silent=True)

    if not data:

        return jsonify({
            "error": "Invalid request."
        }), 400

    message = data.get("message", "").strip()

    if not message:

        return jsonify({
            "error": "Please enter a question."
        }), 400

    try:

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:

            print("AI ERROR: OPENAI_API_KEY not found.")

            return jsonify({
                "error": "OpenAI API key is not configured."
            }), 500

        client = OpenAI(api_key=api_key)

        response = client.responses.create(

            model="gpt-5.6-luna",

            instructions="""
You are an AI Study Assistant for college students.

Your job is to help students understand their subjects.

Rules:
1. Explain concepts in simple language.
2. Give step-by-step explanations when useful.
3. For programming questions, provide simple examples.
4. Use headings and bullet points when helpful.
5. If the student asks a very short question, give a clear and useful answer.
6. Do not unnecessarily make answers complicated.
""",

            input=message
        )

        return jsonify({
            "answer": response.output_text
        })

    except Exception as e:

        print("AI ERROR:", repr(e))

        return jsonify({
            "error": str(e)
        }), 500


# =========================
# NOTES PAGE
# =========================

@app.route("/notes")
def notes():

    if "user_id" not in session:

        return redirect("/login")

    return render_template("notes.html")


# =========================
# AI NOTES API
# =========================

@app.route("/api/notes", methods=["POST"])
def api_notes():

    data = request.get_json(silent=True)

    if not data:

        return jsonify({
            "error": "Invalid request."
        }), 400

    topic = data.get("topic", "").strip()
    subject = data.get("subject", "").strip()

    if not topic:

        return jsonify({
            "error": "Please enter a topic."
        }), 400

    try:

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:

            return jsonify({
                "error": "OpenAI API key is not configured."
            }), 500

        client = OpenAI(api_key=api_key)

        prompt = f"""
Create easy-to-understand study notes for a college student.

Subject: {subject}
Topic: {topic}

Include:

1. Definition
2. Important concepts
3. Step-by-step explanation
4. Examples where useful
5. Advantages/disadvantages if applicable
6. Important points for exams
7. A short summary

Use simple language and clear headings.
"""

        response = client.responses.create(

            model="gpt-5.6-luna",

            instructions="""
You are an AI Study Assistant.

Your job is to create clear, accurate and exam-friendly notes
for college students.
""",

            input=prompt
        )

        return jsonify({
            "notes": response.output_text
        })

    except Exception as e:

        print("NOTES AI ERROR:", repr(e))

        return jsonify({
            "error": str(e)
        }), 500


# =========================
# QUIZ PAGE
# =========================

@app.route("/quiz")
def quiz():

    if "user_id" not in session:

        return redirect("/login")

    return render_template("quiz.html")


# =========================
# AI QUIZ API
# =========================

@app.route("/api/quiz", methods=["POST"])
def api_quiz():

    data = request.get_json(silent=True)

    if not data:

        return jsonify({
            "error": "Invalid request."
        }), 400

    subject = data.get("subject", "").strip()
    topic = data.get("topic", "").strip()

    if not topic:

        return jsonify({
            "error": "Please enter a topic."
        }), 400

    try:

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:

            return jsonify({
                "error": "OpenAI API key is not configured."
            }), 500

        client = OpenAI(api_key=api_key)

        prompt = f"""
Create exactly 5 multiple-choice questions for a college student.

Subject: {subject}
Topic: {topic}

For every question provide:

- Question
- Four options: A, B, C, D
- Correct answer

Use this exact format:

Q1. Question
A. Option
B. Option
C. Option
D. Option
Answer: A

Q2. Question
A. Option
B. Option
C. Option
D. Option
Answer: B

Q3. Question
A. Option
B. Option
C. Option
D. Option
Answer: C

Q4. Question
A. Option
B. Option
C. Option
D. Option
Answer: D

Q5. Question
A. Option
B. Option
C. Option
D. Option
Answer: A

Make the questions accurate, educational and suitable for college exams.
"""

        response = client.responses.create(

            model="gpt-5.6-luna",

            instructions="""
You are an AI Quiz Generator for college students.

Generate accurate and clear MCQ questions.

Always provide exactly four options and one correct answer.
""",

            input=prompt
        )

        return jsonify({
            "quiz": response.output_text
        })

    except Exception as e:

        print("QUIZ AI ERROR:", repr(e))

        return jsonify({
            "error": str(e)
        }), 500


# =========================
# SAVE QUIZ RESULT
# =========================

@app.route("/api/quiz-result", methods=["POST"])
def save_quiz_result():

    if "user_id" not in session:

        return jsonify({
            "error": "Please login first."
        }), 401

    data = request.get_json(silent=True)

    if not data:

        return jsonify({
            "error": "Invalid request."
        }), 400

    subject = data.get("subject", "").strip()
    topic = data.get("topic", "").strip()
    score = data.get("score")
    total = data.get("total")

    if not subject or not topic:

        return jsonify({
            "error": "Subject and topic are required."
        }), 400

    try:

        score = int(score)
        total = int(total)

        if total <= 0 or score < 0 or score > total:

            return jsonify({
                "error": "Invalid score."
            }), 400

        percentage = (score / total) * 100

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO quiz_results
            (user_id, subject, topic, score, total, percentage)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            subject,
            topic,
            score,
            total,
            percentage
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Quiz result saved successfully."
        })

    except Exception as e:

        print("QUIZ RESULT ERROR:", repr(e))

        return jsonify({
            "error": str(e)
        }), 500


# =========================
# PROGRESS PAGE
# =========================

@app.route("/progress")
def progress():

    if "user_id" not in session:

        return redirect("/login")

    return render_template("progress.html")


# =========================
# PROGRESS API
# =========================

@app.route("/api/progress")
def api_progress():

    if "user_id" not in session:

        return jsonify({
            "error": "Please login first."
        }), 401

    try:

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        user_id = session["user_id"]

        # Total quizzes
        cursor.execute("""
            SELECT COUNT(*)
            FROM quiz_results
            WHERE user_id = ?
        """, (user_id,))

        total_quizzes = cursor.fetchone()[0]

        # Average score
        cursor.execute("""
            SELECT AVG(percentage)
            FROM quiz_results
            WHERE user_id = ?
        """, (user_id,))

        average_score = cursor.fetchone()[0]

        if average_score is None:

            average_score = 0

        # Topics completed
        cursor.execute("""
            SELECT COUNT(DISTINCT topic)
            FROM quiz_results
            WHERE user_id = ?
        """, (user_id,))

        topics = cursor.fetchone()[0]

        # Subject-wise performance
        cursor.execute("""
            SELECT subject, AVG(percentage)
            FROM quiz_results
            WHERE user_id = ?
            GROUP BY subject
        """, (user_id,))

        subject_data = cursor.fetchall()

        conn.close()

        subjects = []

        for subject, percentage in subject_data:

            subjects.append({
                "subject": subject,
                "percentage": round(percentage, 1)
            })

        return jsonify({

            "total_quizzes": total_quizzes,

            "average_score": round(
                average_score, 1
            ),

            "topics": topics,

            "subjects": subjects

        })

    except Exception as e:

        print("PROGRESS ERROR:", repr(e))

        return jsonify({
            "error": str(e)
        }), 500


# =========================
# QUIZ HISTORY API
# =========================

@app.route("/api/quiz-history")
def quiz_history():

    if "user_id" not in session:

        return jsonify({
            "error": "Please login first."
        }), 401

    try:

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                subject,
                topic,
                score,
                total,
                percentage,
                created_at
            FROM quiz_results
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (session["user_id"],))

        results = cursor.fetchall()

        conn.close()

        history = []

        for row in results:

            history.append({

                "subject": row[0],

                "topic": row[1],

                "score": row[2],

                "total": row[3],

                "percentage": round(
                    row[4], 1
                ),

                "date": row[5]

            })

        return jsonify({
            "history": history
        })

    except Exception as e:

        print("HISTORY ERROR:", repr(e))

        return jsonify({
            "error": str(e)
        }), 500


#=========================
#INITIALIZATION DATABASE
#==========================

init_db()


# =========================
# START FLASK
# =========================

if __name__ == "__main__":
      app.run(debug=True)