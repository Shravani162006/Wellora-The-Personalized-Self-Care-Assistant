import os
import json
import uuid
import random
import pandas as pd
import requests
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from datetime import timedelta, date, datetime
from sklearn.preprocessing import LabelEncoder
from sklearn.neighbors import NearestNeighbors
from dotenv import load_dotenv



# ---------------- Flask App Init ---------------- #
app = Flask(__name__)
app.secret_key = 'your-secret-key'
app.permanent_session_lifetime = timedelta(minutes=60)

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ---------------- In-Memory Storage ---------------- #
USERS = {}
ANALYSIS_HISTORY = []
FEEDBACK_HISTORY = []
STRESS_HISTORY = []
HAIRFALL_PROGRESS = []
DANDRUFF_PROGRESS = []


# ---------------- Session Management ---------------- #
@app.before_request
def make_session_permanent():
    session.permanent = True
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())

# ---------------- Load JSON Data ---------------- #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, "updated_products.json"), "r", encoding="utf-8") as f:
    SKIN_DATA = json.load(f)

with open(os.path.join(BASE_DIR, "women.json"), "r", encoding="utf-8") as f:
    WOMEN_DATA = json.load(f)

# ---------------- Problem Mapping ---------------- #
PROBLEM_MAP = {
    "whiteheads": "Black/White Heads",
    "blackheads": "Black/White Heads",
    "pimples": "Pimples",
    "darkspots": "Dark Circles"
}
DISPLAY_TO_URL_SAFE = {v: k for k, v in PROBLEM_MAP.items()}

# ---------------- Basic Routes ---------------- #
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

# ---------------- Auth Routes ---------------- #
@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if username in USERS:
            return render_template('signup.html', error="Username already exists")

        USERS[username] = {"email": email, "password": password}
        session['username'] = username
        return redirect(url_for('dashboard'))

    return render_template('signup.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        for u, data in USERS.items():
            if data["email"] == email and data["password"] == password:
                session['username'] = u
                return redirect(url_for('dashboard'))

        return render_template('login.html', error="Invalid credentials")

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# ---------------- AI Chatbot ---------------- #
@app.route('/bot')
def bot():
    return render_template('bot.html')

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
            headers=headers,
            timeout=30
        )
        reply = res.json()["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})
    except:
        return jsonify({"reply": "AI unavailable"}), 500

# ---------------- Skin Analysis ---------------- #
@app.route("/skin")
def skin_advice():
    progress_data = {k: 0 for k in PROBLEM_MAP}
    return render_template("skin.html", progress_data=progress_data)

@app.route("/skin/<problem>", methods=["GET","POST"])
def problem_form(problem):
    problem_display_name = PROBLEM_MAP.get(problem, problem)
    return render_template(
        "problem_form.html",
        problem_url_safe=problem,
        problem_display_name=problem_display_name
    )

@app.route("/treatment", methods=["POST"])
def treatment():
    problem_url_safe = request.form.get("problem_url_safe")
    mapped_problem = PROBLEM_MAP.get(problem_url_safe, problem_url_safe)

    gender = request.form.get("gender", "Female").title()
    skin_type = request.form.get("skin_type", "Normal").title()

    matched = [
        item for item in SKIN_DATA
        if item["SkinIssue"].lower() == mapped_problem.lower()
        and item["Gender"].lower() == gender.lower()
        and item["SkinType"].lower() == skin_type.lower()
    ]

    result = matched[0] if matched else random.choice(SKIN_DATA)

    ANALYSIS_HISTORY.append({
        "user": session['username'],
        "problem": mapped_problem,
        "result": result,
        "date": datetime.now().isoformat()
    })

    return render_template(
        "results.html",
        problem_display_name=mapped_problem,
        problem_url_safe=problem_url_safe,
        result=result
    )

# ---------------- Feedback ---------------- #
@app.route("/feedback/<problem_url_safe>")
def feedback_form(problem_url_safe):
    return render_template(
        "feedback_form.html",
        problem_url_safe=problem_url_safe,
        problem_display_name=PROBLEM_MAP.get(problem_url_safe, problem_url_safe)
    )

@app.route("/feedback/submit", methods=["POST"])
def submit_feedback():
    FEEDBACK_HISTORY.append({
        "user": session['username'],
        "skin_issue": request.form.get("skin_issue"),
        "satisfaction": request.form.get("satisfaction_level"),
        "rating": request.form.get("effectiveness_rating"),
        "suggestions": request.form.get("suggestions"),
        "date": date.today().isoformat()
    })

    return redirect(url_for('skin_advice'))

# ---------------- Women's Health ---------------- #
@app.route('/women')
def women_home():
    return render_template("women.html")

@app.route('/menstrual', methods=['GET','POST'])
def menstrual():
    if request.method == 'POST':
        return render_template("menstrual_result.html", **request.form)
    return render_template("menstrual_form.html")

@app.route('/pregnancy_form')
def pregnancy_form():
    return render_template('pregnancy_form.html')

@app.route('/pregnancy_result', methods=['POST'])
def pregnancy_result():
    return render_template("pregnancy_result.html", **request.form)
    
# ---------------- hair ---------------- #
@app.route('/hair_dashboard')
def hair_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Filter progress for current user
    user = session.get('username')

    hairfall_history = [
        h for h in HAIRFALL_PROGRESS if h.get("user") == user
    ]

    dandruff_history = [
        d for d in DANDRUFF_PROGRESS if d.get("user") == user
    ]

    return render_template(
        "hair_dashboard.html",
        hairfall_history=hairfall_history,
        dandruff_history=dandruff_history
    )
@app.route("/dandruff", methods=["GET","POST"])
def dandruff_form():
    if request.method == "POST":
        result = analyze_dandruff({
            "Age": int(request.form.get("age")),
            "Gender": request.form.get("gender"),
            "Sleep_Hours": int(request.form.get("sleep_hours")),
            "Water_Intake": request.form.get("water_intake"),
            "Scalp_Type": request.form.get("scalp_type"),
            "Oil_Scalp": request.form.get("oil_scalp"),
            "Chemical_Treatment": request.form.get("chemical_treatment")
        })

        DANDRUFF_PROGRESS.append({
            "user": session.get("username"),
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),
            "improvement_percent": random.randint(50, 85)
        })

        return render_template("dandruff_result.html", result=result)

    return render_template("dandruff_form.html")
@app.route('/hair_dashboard')
def hair_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = session.get('username')

    hairfall_history = [
        h for h in HAIRFALL_PROGRESS if h.get("user") == user
    ]

    dandruff_history = [
        d for d in DANDRUFF_PROGRESS if d.get("user") == user
    ]

    return render_template(
        "hair_dashboard.html",
        hairfall_history=hairfall_history,
        dandruff_history=dandruff_history
    )


# ---------------- Stress Management ---------------- #
@app.route('/stress')
def stress_index():
    return render_template('stress_index.html', stress_types=['work','academic','relationship'])

@app.route('/stress/submit', methods=['POST'])
def stress_submit():
    STRESS_HISTORY.append({
        "user": session.get("username"),
        "data": request.form.to_dict(),
        "date": datetime.now().isoformat()
    })
    session['stress_progress'] = request.form.to_dict()
    return jsonify({"success": True})

@app.route('/stress/results/<stress_type>')
def stress_results(stress_type):
    return render_template("stress_results.html", stress_type=stress_type)

@app.route('/stress/progress')
def stress_progress_page():
    return render_template("stress_progress.html", progress_data=session.get("stress_progress", {}))

@app.route('/stress/music')
def stress_music_player():
    return render_template("stress_music.html", music_videos=[])

# ---------------- Error Handlers ---------------- #
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500

# ---------------- Run App ---------------- #
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


