import sqlite3

from flask import Flask, render_template, request, redirect, session

app = Flask(__name__)
app.secret_key = "supersecretkey"

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        password TEXT NOT NULL
    )
    """)
    
    # Skills table

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        skill_name TEXT,
        skill_type TEXT,
        skill_level TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

def level_score(teacher_level, learner_level):
    levels = ["Beginner", "Intermediate", "Advanced"]

    teacher_index = levels.index(teacher_level)
    learner_index = levels.index(learner_level)

    if teacher_index >= learner_index:
        return 1
    return 0

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (name, password) VALUES (?, ?)",
            (name, password)
        )

        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        session["user_id"] = user_id

        return redirect("/dashboard")

    return render_template("register.html")

@app.route("/add_skills/<int:user_id>", methods=["GET", "POST"])
def add_skills(user_id):

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        teach = request.form["teach"].strip().lower()
        teach_level = request.form["teach_level"]

        learn = request.form["learn"].strip().lower()
        learn_level = request.form["learn_level"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO skills (user_id, skill_name, skill_type, skill_level) VALUES (?, ?, ?, ?)",
            (user_id, teach, "teach", teach_level)
        )

        cursor.execute(
            "INSERT INTO skills (user_id, skill_name, skill_type, skill_level) VALUES (?, ?, ?, ?)",
            (user_id, learn, "learn", learn_level)
        )

        conn.commit()
        conn.close()

        return redirect(f"/matches/{user_id}")

    return render_template("add_skills.html")


@app.route("/matches/<int:user_id>")
def matches(user_id):

    if "user_id" not in session or session["user_id"] != user_id:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Current user's teach skills
    cursor.execute("""
        SELECT skill_name, skill_level FROM skills 
        WHERE user_id = ? AND skill_type = 'teach'
    """, (user_id,))
    current_user_teach = cursor.fetchall()

    # Current user's learn skills
    cursor.execute("""
        SELECT skill_name, skill_level FROM skills 
        WHERE user_id = ? AND skill_type = 'learn'
    """, (user_id,))
    current_user_learn = cursor.fetchall()

    # Get all other users
    cursor.execute("SELECT id, name FROM users WHERE id != ?", (user_id,))
    other_users = cursor.fetchall()

    matched_users = []

    for other in other_users:
        other_id, other_name = other

        # Other user's teach skills
        cursor.execute("""
            SELECT skill_name, skill_level FROM skills 
            WHERE user_id = ? AND skill_type = 'teach'
        """, (other_id,))
        other_user_teach = cursor.fetchall()

        # Other user's learn skills
        cursor.execute("""
            SELECT skill_name, skill_level FROM skills 
            WHERE user_id = ? AND skill_type = 'learn'
        """, (other_id,))
        other_user_learn = cursor.fetchall()

        score = 0

        # Compare: current teaches → other learns
        for t_skill, t_level in current_user_teach:
            for o_skill, o_level in other_user_learn:
                if t_skill == o_skill:
                    score += level_score(t_level, o_level)

        # Compare: current learns → other teaches
        for l_skill, l_level in current_user_learn:
            for o_skill, o_level in other_user_teach:
                if l_skill == o_skill:
                    score += level_score(o_level, l_level)

        if score > 0:
            matched_users.append({
                "name": other_name,
                "score": score * 50
            })

    conn.close()

    return render_template("matches.html", matches=matched_users)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form["name"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE name=? AND password=?",
            (name, password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            return redirect("/dashboard")
        else:
            return "Invalid credentials"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect("/")

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    cursor.execute("""
        SELECT skill_name, skill_type, skill_level 
        FROM skills WHERE user_id = ?
    """, (user_id,))
    skills = cursor.fetchall()

    conn.close()

    return render_template("dashboard.html", 
                        username=user[0], 
                        skills=skills)

if __name__ == "__main__":
    app.run(debug=True)
    