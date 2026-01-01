import os
import json
import uuid
import random
import requests
import pandas as pd

from flask import (
    Flask, render_template, request,
    redirect, session, url_for, jsonify
)
from datetime import timedelta, datetime, date
from dotenv import load_dotenv
from sklearn.preprocessing import LabelEncoder
from sklearn.neighbors import NearestNeighbors

# =====================================================
#                  APP CONFIG
# =====================================================
app = Flask(__name__)
app.secret_key = "wellora-secret-key"
app.permanent_session_lifetime = timedelta(minutes=60)

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =====================================================
#              IN-MEMORY STORAGE (NO DB)
# =====================================================
USERS = {}
ANALYSIS_HISTORY = []
FEEDBACK_HISTORY = []
HAIRFALL_PROGRESS = []
DANDRUFF_PROGRESS = []
STRESS_HISTORY = []

# =====================================================
#                SESSION HANDLER
# =====================================================
@app.before_request
def make_session_permanent():
    session.permanent = True
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

# =====================================================
#                LOAD JSON FILES
# =====================================================
def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ JSON load failed: {path}", e)
        return default

SKIN_DATA = load_json(os.path.join(BASE_DIR, "updated_products.json"), [])
WOMEN_DATA = load_json(os.path.join(BASE_DIR, "women.json"), {})

# =====================================================
#              SKIN PROBLEM MAP
# =====================================================
PROBLEM_MAP = {
    "whiteheads": "Black/White Heads",
    "blackheads": "Black/White Heads",
    "pimples": "Pimples",
    "darkspots": "Dark Circles"
}

DISPLAY_TO_URL_SAFE = {v: k for k, v in PROBLEM_MAP.items()}

# =====================================================
#                  BASIC ROUTES
# =====================================================
@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))

# =====================================================
#               AUTH (NO DATABASE)
# =====================================================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        e = request.form["email"]

        if u in USERS:
            return render_template("signup.html", error="User already exists")

        USERS[u] = {"password": p, "email": e}
        session["username"] = u
        return redirect(url_for("dashboard"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        e = request.form["email"]
        p = request.form["password"]

        for u, data in USERS.items():
            if data["email"] == e and data["password"] == p:
                session["username"] = u
                return redirect(url_for("dashboard"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

# =====================================================
#                   AI CHATBOT
# =====================================================
@app.route("/bot")
def bot():
    return render_template("bot.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")

    if not message:
        return jsonify({"reply": "Message required"}), 400

    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are Wellora, a caring self-care assistant."},
            {"role": "user", "content": message}
        ]
    }

    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30
        )
        reply = res.json()["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})

    except Exception as e:
        print("Chat error:", e)
        return jsonify({"reply": "AI unavailable"}), 500

# =====================================================
#                  SKIN MODULE
# =====================================================
@app.route("/skin")
def skin_advice():
    progress_data = {k: 0 for k in PROBLEM_MAP}
    return render_template("skin.html", progress_data=progress_data)

@app.route("/skin_analysis")
def skin_analysis():
    return render_template("skin_analysis.html")

@app.route("/skin/<problem>", methods=["GET", "POST"])
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

    gender = request.form.get("gender", "Female").title()
    skin_type = request.form.get("skin_type", "Normal").title()

    matches = [
        i for i in SKIN_DATA
        if i["SkinIssue"].lower() == problem_name.lower()
        and i["Gender"].lower() == gender.lower()
        and i["SkinType"].lower() == skin_type.lower()
    ]

    result = matches[0] if matches else random.choice(SKIN_DATA)

    ANALYSIS_HISTORY.append({
        "user": session.get("username"),
        "problem": problem_name,
        "date": datetime.now().isoformat()
    })

    return render_template(
        "results.html",
        problem_display_name=problem_name,
        problem_url_safe=problem_url,
        result=result
    )

# =====================================================
#              HAIRFALL & DANDRUFF
# =====================================================
@app.route("/hairfall", methods=["GET", "POST"])
def hairfall_form():
    if request.method == "POST":
        HAIRFALL_PROGRESS.append({
            "date": date.today().isoformat(),
            "improvement": random.randint(40, 85)
        })
        return redirect(url_for("progress_hairfall"))
    return render_template("hairfall_form.html")

@app.route("/dandruff", methods=["GET", "POST"])
def dandruff_form():
    if request.method == "POST":
        DANDRUFF_PROGRESS.append({
            "date": date.today().isoformat(),
            "improvement": random.randint(45, 90)
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
    return render_template(
        "progress_hairfall.html",
        progress=HAIRFALL_PROGRESS,
        feedback_list=[]
    )

@app.route("/progress_dandruff")
def progress_dandruff():
    return render_template(
        "progress_dandruff.html",
        progress=DANDRUFF_PROGRESS,
        feedback_list=[]
    )

# =====================================================
#                 ERROR HANDLERS
# =====================================================
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500

# =====================================================
#                  RUN APP
# =====================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

