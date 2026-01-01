import os
import json
import uuid
import random
import requests
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from datetime import timedelta, date, datetime
from dotenv import load_dotenv

# ==================================================
#                APP CONFIG
# ==================================================
app = Flask(__name__)
app.secret_key = "wellora-secret-key"
app.permanent_session_lifetime = timedelta(minutes=60)

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==================================================
#            IN-MEMORY STORAGE (NO DB)
# ==================================================
USERS = {}
ANALYSIS_HISTORY = []
FEEDBACK_HISTORY = []
HAIRFALL_PROGRESS = []
DANDRUFF_PROGRESS = []
STRESS_HISTORY = []

# ==================================================
#              SESSION MANAGEMENT
# ==================================================
@app.before_request
def make_session_permanent():
    session.permanent = True
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

# ==================================================
#                LOAD JSON DATA
# ==================================================
with open(os.path.join(BASE_DIR, "updated_products.json"), "r", encoding="utf-8") as f:
    SKIN_DATA = json.load(f)

with open(os.path.join(BASE_DIR, "women.json"), "r", encoding="utf-8") as f:
    WOMEN_DATA = json.load(f)

# ==================================================
#                CONSTANTS
# ==================================================
PROBLEM_MAP = {
    "whiteheads": "Black/White Heads",
    "blackheads": "Black/White Heads",
    "pimples": "Pimples",
    "darkspots": "Dark Circles"
}

# ==================================================
#                BASIC ROUTES
# ==================================================
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

# ==================================================
#                AUTH (IN-MEMORY)
# ==================================================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if username in USERS:
            return render_template("signup.html", error="Username already exists")

        USERS[username] = {"email": email, "password": password}
        session["username"] = username
        return redirect(url_for("dashboard"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        for u, data in USERS.items():
            if data["email"] == email and data["password"] == password:
                session["username"] = u
                return redirect(url_for("dashboard"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

# ==================================================
#                AI CHATBOT
# ==================================================
@app.route("/bot")
def bot():
    return render_template("bot.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message")

    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are Wellora, a caring AI self-care assistant."},
            {"role": "user", "content": message}
        ],
        "temperature": 0.7,
        "max_tokens": 400
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=30
        )
        res.raise_for_status()
        reply = res.json()["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})
    except Exception as e:
        print("AI Error:", e)
        return jsonify({"reply": "AI temporarily unavailable"}), 500

# ==================================================
#                SKIN MODULE
# ==================================================
@app.route("/skin")
def skin_advice():
    progress_data = {k: 0 for k in PROBLEM_MAP}
    return render_template("skin.html", progress_data=progress_data)

@app.route("/skin/<problem>")
def problem_form(problem):
    return render_template(
        "problem_form.html",
        problem_url_safe=problem,
        problem_display_name=PROBLEM_MAP.get(problem, problem)
    )

@app.route("/treatment", methods=["POST"])
def treatment():
    result = random.choice(SKIN_DATA)
    return render_template(
        "results.html",
        problem_display_name=PROBLEM_MAP.get(request.form.get("problem_url_safe")),
        problem_url_safe=request.form.get("problem_url_safe"),
        result=result
    )

# ==================================================
#                HAIR MODULE (FIXED)
# ==================================================
@app.route("/hairfall", methods=["GET", "POST"])
def hairfall_form():
    if request.method == "POST":
        HAIRFALL_PROGRESS.append({
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),
            "improvement_percent": random.randint(60, 90),
            "problem_type": "hairfall"
        })
        return render_template("hairfall_result.html")
    return render_template("hairfall_form.html")

@app.route("/dandruff", methods=["GET", "POST"])
def dandruff_form():
    if request.method == "POST":
        DANDRUFF_PROGRESS.append({
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),
            "improvement_percent": random.randint(50, 85),
            "problem_type": "dandruff"
        })
        return render_template("dandruff_result.html")
    return render_template("dandruff_form.html")

@app.route("/hair_dashboard")
def hair_dashboard():
    return render_template(
        "hair_dashboard.html",
        hairfall_history=HAIRFALL_PROGRESS or [],
        dandruff_history=DANDRUFF_PROGRESS or []
    )

# ==================================================
#                WOMEN MODULE
# ==================================================
@app.route("/women")
def women_home():
    return render_template("women.html")

@app.route("/menstrual", methods=["GET", "POST"])
def menstrual():
    if request.method == "POST":
        return render_template("menstrual_result.html", **request.form)
    return render_template("menstrual_form.html")

# ==================================================
#                STRESS MODULE
# ==================================================
@app.route("/stress")
def stress_index():
    return render_template("stress_index.html", stress_types=["work", "academic", "relationship"])

@app.route("/stress/submit", methods=["POST"])
def stress_submit():
    STRESS_HISTORY.append(request.form.to_dict())
    session["stress_progress"] = request.form.to_dict()
    return jsonify({"success": True})

@app.route("/stress/results/<stress_type>")
def stress_results(stress_type):
    return render_template("stress_results.html", stress_type=stress_type)

@app.route("/stress/progress")
def stress_progress():
    return render_template("stress_progress.html", progress_data=session.get("stress_progress", {}))

@app.route("/stress/music")
def stress_music():
    return render_template("stress_music.html", music_videos=[])

# ==================================================
#                ERROR HANDLER
# ==================================================
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

# ==================================================
#                RUN
# ==================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
