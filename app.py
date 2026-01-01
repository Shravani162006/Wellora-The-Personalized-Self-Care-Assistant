import os
import json
import uuid
import random
import requests
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from datetime import timedelta, datetime, date
from dotenv import load_dotenv

# =====================================================
# APP CONFIG
# =====================================================
app = Flask(__name__)
app.secret_key = "wellora-secret-key"
app.permanent_session_lifetime = timedelta(minutes=60)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# =====================================================
# IN-MEMORY STORAGE (NO DATABASE)
# =====================================================
USERS = {}
ANALYSIS_HISTORY = []
HAIRFALL_PROGRESS = []
DANDRUFF_PROGRESS = []

# =====================================================
# SESSION SETUP
# =====================================================
@app.before_request
def setup_session():
    session.permanent = True
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

# =====================================================
# SAFE JSON LOADER
# =====================================================
def load_json(filename, default):
    try:
        with open(os.path.join(BASE_DIR, filename), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load {filename}:", e)
        return default

SKIN_DATA = load_json("updated_products.json", [])
WOMEN_DATA = load_json("women.json", {})

# =====================================================
# PROBLEM MAP
# =====================================================
PROBLEM_MAP = {
    "whiteheads": "Black/White Heads",
    "blackheads": "Black/White Heads",
    "pimples": "Pimples",
    "darkspots": "Dark Circles"
}

# =====================================================
# AUTH ROUTES
# =====================================================
@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        u = request.form["username"]
        USERS[u] = {
            "email": request.form["email"],
            "password": request.form["password"]
        }
        session["username"] = u
        return redirect(url_for("dashboard"))
    return render_template("signup.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        for u, d in USERS.items():
            if d["email"] == request.form["email"] and d["password"] == request.form["password"]:
                session["username"] = u
                return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))

# =====================================================
# AI CHAT
# =====================================================
@app.route("/bot")
def bot():
    return render_template("bot.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data or not data.get("message"):
        return jsonify({"reply": "Message required"}), 400

    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are Wellora, a caring self-care assistant."},
            {"role": "user", "content": data["message"]}
        ]
    }

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=20
        )
        return jsonify({"reply": r.json()["choices"][0]["message"]["content"]})
    except:
        return jsonify({"reply": "AI unavailable"}), 500

# =====================================================
# SKIN MODULE
# =====================================================
@app.route("/skin")
def skin_advice():
    progress_data = {k: 0 for k in PROBLEM_MAP}
    return render_template("skin.html", progress_data=progress_data)

@app.route("/skin_analysis")
def skin_analysis():
    return render_template("skin_analysis.html")

@app.route("/skin/<problem>")
def problem_form(problem):
    return render_template(
        "problem_form.html",
        problem_url_safe=problem,
        problem_display_name=PROBLEM_MAP.get(problem, problem)
    )

@app.route("/treatment", methods=["POST"])
def treatment():
    problem_url = request.form.get("problem_url_safe")
    problem_name = PROBLEM_MAP.get(problem_url, problem_url)

    result = random.choice(SKIN_DATA) if SKIN_DATA else {}
    return render_template(
        "results.html",
        problem_display_name=problem_name,
        problem_url_safe=problem_url,
        result=result
    )

# =====================================================
# 🔥 REQUIRED ROUTE (FIXES YOUR ERROR)
# =====================================================
@app.route("/progress/<problem_url_safe>")
def progress_history(problem_url_safe):
    return render_template(
        "progress_history.html",
        problem_url_safe=problem_url_safe,
        history=[],
        avg_progress=0
    )

# =====================================================
# HAIR MODULE
# =====================================================
@app.route("/hairfall", methods=["GET","POST"])
def hairfall_form():
    if request.method == "POST":
        HAIRFALL_PROGRESS.append({
            "analysis_date": date.today().strftime("%Y-%m-%d"),
            "improvement_percent": random.randint(50, 90)
        })
        return redirect(url_for("progress_hairfall"))
    return render_template("hairfall_form.html")

@app.route("/dandruff", methods=["GET","POST"])
def dandruff_form():
    if request.method == "POST":
        DANDRUFF_PROGRESS.append({
            "analysis_date": date.today().strftime("%Y-%m-%d"),
            "improvement_percent": random.randint(45, 85)
        })
        return redirect(url_for("progress_dandruff"))
    return render_template("dandruff_form.html")

@app.route("/hair_dashboard")
def hair_dashboard():
    return render_template(
        "hair_dashboard.html",
        hairfall_history=HAIRFALL_PROGRESS,
        dandruff_history=DANDRUFF_PROGRESS
    )

@app.route("/progress_hairfall")
def progress_hairfall():
    return render_template("progress_hairfall.html", progress=HAIRFALL_PROGRESS, feedback_list=[])

@app.route("/progress_dandruff")
def progress_dandruff():
    return render_template("progress_dandruff.html", progress=DANDRUFF_PROGRESS, feedback_list=[])

# =====================================================
# SAFE ERROR HANDLERS (NO 500.html REQUIRED)
# =====================================================
@app.errorhandler(404)
def not_found(e):
    return "404 – Page Not Found", 404

@app.errorhandler(500)
def server_error(e):
    return "500 – Internal Server Error", 500

# =====================================================
# RUN
# =====================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
