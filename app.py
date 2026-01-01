import os
import json
import uuid
import random
import requests
import pandas as pd
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from datetime import timedelta, date, datetime
from sklearn.preprocessing import LabelEncoder
from sklearn.neighbors import NearestNeighbors
from dotenv import load_dotenv

# ======================================================
#                    APP CONFIG
# ======================================================
app = Flask(__name__)
app.secret_key = "wellora-secret-key"
app.permanent_session_lifetime = timedelta(minutes=60)

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ======================================================
#              IN-MEMORY STORAGE (NO DB)
# ======================================================
USERS = {}
ANALYSIS_HISTORY = []
FEEDBACK_HISTORY = []
STRESS_HISTORY = []
HAIRFALL_PROGRESS = []
DANDRUFF_PROGRESS = []

# ======================================================
#              SESSION MANAGEMENT
# ======================================================
@app.before_request
def make_session_permanent():
    session.permanent = True
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())

# ======================================================
#                   BASIC ROUTES
# ======================================================
@app.route('/')
def landing():
    return render_template("landing.html")

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))

# ======================================================
#                  AUTH SYSTEM
# ======================================================
@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if username in USERS:
            return render_template("signup.html", error="User already exists")

        USERS[username] = {
            "email": email,
            "password": password
        }

        session['username'] = username
        session['user_id'] = username
        return redirect(url_for('dashboard'))

    return render_template("signup.html")

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        for user, data in USERS.items():
            if data["email"] == email and data["password"] == password:
                session['username'] = user
                session['user_id'] = user
                return redirect(url_for('dashboard'))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template("dashboard.html")

# ======================================================
#                     AI CHAT BOT
# ======================================================
@app.route('/bot')
def bot():
    return render_template("bot.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message")

    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are Wellora, a caring AI self-care assistant."},
            {"role": "user", "content": message}
        ]
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers
        )
        reply = res.json()["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})
    except:
        return jsonify({"reply": "AI is currently unavailable."})

# ======================================================
#               SKIN ANALYSIS (NO DB)
# ======================================================
@app.route('/skin_analysis')
def skin_analysis():
    return render_template("skin_analysis.html")

@app.route("/analyze_skin", methods=["POST"])
def analyze_skin():
    features = request.json.get("features")

    prompt = f"""
    Skin Brightness: {features['brightness']}
    Redness: {features['redness']}
    Tone: {features['overallTone']}
    """

    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json=payload,
        headers=headers
    )

    return jsonify({"reply": response.json()["choices"][0]["message"]["content"]})

# ======================================================
#              STRESS MANAGEMENT (NO DB)
# ======================================================
@app.route('/stress')
def stress_index():
    return render_template("stress_index.html")

@app.route('/stress/submit', methods=['POST'])
def stress_submit():
    data = request.form.to_dict()
    data["user"] = session.get("username")
    data["date"] = datetime.now().isoformat()

    STRESS_HISTORY.append(data)
    session['stress_progress'] = data

    return jsonify({"success": True})

@app.route('/stress/results/<stress_type>')
def stress_results(stress_type):
    return render_template("stress_results.html", stress_type=stress_type)

@app.route('/stress/progress')
def stress_progress_page():
    return render_template(
        "stress_progress.html",
        progress_data=session.get("stress_progress", {})
    )

# ======================================================
#             HAIRFALL & DANDRUFF (NO DB)
# ======================================================
@app.route('/hairfall', methods=['GET','POST'])
def hairfall():
    if request.method == 'POST':
        result = {
            "Routine": "Use mild shampoo twice a week",
            "Remedies": ["Aloe vera", "Onion juice"]
        }

        HAIRFALL_PROGRESS.append({
            "user": session['username'],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "progress": random.randint(60, 90)
        })

        return render_template("hairfall_result.html", result=result)

    return render_template("hairfall_form.html")

@app.route('/progress_hairfall')
def progress_hairfall():
    return render_template(
        "progress_hairfall.html",
        progress=HAIRFALL_PROGRESS
    )

@app.route('/dandruff', methods=['GET','POST'])
def dandruff():
    if request.method == 'POST':
        result = {
            "Routine": "Anti-dandruff shampoo",
            "Remedies": ["Neem", "Tea tree oil"]
        }

        DANDRUFF_PROGRESS.append({
            "user": session['username'],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "progress": random.randint(50, 85)
        })

        return render_template("dandruff_result.html", result=result)

    return render_template("dandruff_form.html")

@app.route('/progress_dandruff')
def progress_dandruff():
    return render_template(
        "progress_dandruff.html",
        progress=DANDRUFF_PROGRESS
    )

# ======================================================
#                  WOMEN & PREGNANCY
# ======================================================
@app.route('/women')
def women_home():
    return render_template("women.html")

@app.route('/pregnancy_form')
def pregnancy_form():
    return render_template("pregnancy_form.html")

@app.route('/pregnancy_result', methods=['POST'])
def pregnancy_result():
    data = request.form.to_dict()
    data["user"] = session['username']
    return render_template("pregnancy_result.html", data=data)

# ======================================================
#                 ERROR HANDLERS
# ======================================================
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500

# ======================================================
#                  RUN APP
# ======================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
