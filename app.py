import os
import json
import uuid
import random
import pandas as pd
import mysql.connector
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from datetime import timedelta, date, datetime
from sklearn.preprocessing import LabelEncoder
from sklearn.neighbors import NearestNeighbors
from urllib.parse import unquote
import json

# ---------------- Flask App Init ---------------- #
app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Change for production
app.permanent_session_lifetime = timedelta(minutes=60)

# ---------------- Database Connection ---------------- #
def get_db_connection():
    """Establishes a connection to the MySQL database."""
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",  # Change as needed
        database="skin_care_app"
    )
from dotenv import load_dotenv
import os

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

@app.route('/bot')
def bot():
    return render_template('bot.html')
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()

    message = data.get("message")
    language = data.get("language", "en")
    category = data.get("category", "general")

    if not message:
        return jsonify({"reply": "Message is required"}), 400

    system_prompt = f"""
You are Wellora, a caring AI self-care assistant.

Category: {category}
Language: {language}

Rules:
- Be empathetic
- No medical diagnosis
- Simple, helpful advice
"""

    payload = {
        "model": "openai/gpt-4o-mini",   # ✅ FIXED MODEL
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5001",
        "X-Title": "Wellora"
    }

    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=30
        )

        print(res.text)  # 🔍 DEBUG LINE

        res.raise_for_status()
        reply = res.json()["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})

    except Exception as e:
        print("Chat error:", e)
        return jsonify({"reply": "AI is currently unavailable."}), 500



@app.route("/contact")
def contact():
    return render_template('contact.html')


@app.route('/about')
def about():
    return render_template('about.html')

# -----------------------------
# Session Management
# -----------------------------
@app.before_request
def make_session_permanent():
    session.permanent = True
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())



# ---------------- Skincare Data Loading ---------------- #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(BASE_DIR, "updated_products.json")

with open(json_path, "r", encoding="utf-8") as f:
    products = json.load(f)
    

# --- Problem Mapping for Display and DB Storage (User-Friendly Names) ---
PROBLEM_MAP = {
    "whiteheads": "Black/White Heads",
    "blackheads": "Black/White Heads",  # Aliasing for robustness
    "pimples": "Pimples",
    "darkspots": "Dark Circles"
}
# Map from Display Name (DB) to URL-safe Name for redirects
DISPLAY_TO_URL_SAFE = {v: k for k, v in PROBLEM_MAP.items()}

# ----------------------------- Auth & Main Routes ----------------------------- #
@app.route('/')
def landing():
    return render_template("landing.html")

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method=='POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s OR email=%s", (username,email))
        if cursor.fetchone():
            conn.close()
            return render_template('signup.html', error="Username or Email already exists.")
        cursor.execute("INSERT INTO users (username,password,email) VALUES (%s,%s,%s)",(username,password,email))
        conn.commit()
        conn.close()
        session['username'] = username
        return redirect(url_for('dashboard'))
    return render_template('signup.html')



@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s",(email,password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['username'] = user['username']
            # set user_id in session so stress module can use it as well (if users table has id)
            try:
                session['user_id'] = user.get('id') if isinstance(user, dict) and 'id' in user else None
            except Exception:
                session['user_id'] = None
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Invalid email or password.")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    # leave user_id if exists
    session.pop('user_id', None)
    return redirect(url_for('landing'))

# ----------------------------- Skincare Routes (FIXED FOR ROUTING) ----------------------------- #
import os
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()



OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"


@app.route("/skin_analysis")
def skin_analysis():
    return render_template("skin_analysis.html")


@app.route("/analyze_skin", methods=["POST"])
def analyze_skin():
    try:
        features = request.json.get("features")

        prompt = f"""
You are a professional dermatologist.

### 1. Skin Problems
### 2. Complete Morning Skincare Routine
### 3. Complete Night Skincare Routine
### 4. Home Remedies

Skin details:
Brightness: {features['brightness']}
Redness: {features['redness']}
Tone: {features['overallTone']}
"""

        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",
                "X-Title": "Wellora"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a dermatologist AI."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1200,
                "temperature": 0.7
            }
        )

        result = response.json()
        return jsonify({"reply": result["choices"][0]["message"]["content"]})

    except Exception as e:
        return jsonify({"error": str(e)}), 500







@app.route("/skin")
def skin_advice():
    """Show skin problem options with current average progress for each."""
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM users WHERE username=%s", (session['username'],))
    user_result = cursor.fetchone()

    if not user_result:
        conn.close()
        return redirect(url_for('login'))

    user_id = user_result['id']

    # --- Satisfaction Mapping ---
    satisfaction_map = {
        "Very Satisfied": 10,
        "Satisfied": 8,
        "Neutral": 6,
        "Dissatisfied": 4,
        "Very Dissatisfied": 2
    }

    progress_data = {}

    # --- Loop through each problem type to calculate average progress ---
    for url_safe, display_name in PROBLEM_MAP.items():
        cursor.execute("""
            SELECT satisfaction_level, effectiveness_rating, problem_solved
            FROM feedback_history
            WHERE user_id=%s AND skin_issue=%s
        """, (user_id, display_name))
        records = cursor.fetchall()

        if not records:
            progress_data[url_safe] = 0
            continue

        progress_scores = []
        for rec in records:
            sat_score = satisfaction_map.get((rec.get("satisfaction_level") or "").title(), 0)
            rating = rec.get("effectiveness_rating") or 0
            solved = 10 if rec.get("problem_solved") else 0
            progress = round((sat_score * 0.5) + (rating * 0.3) + (solved * 0.2), 1)
            if progress > 10:
                progress = 10
            progress_scores.append(progress)

        avg_progress = round(sum(progress_scores) / len(progress_scores), 1)
        progress_data[url_safe] = avg_progress

    conn.close()

    # Render the page with progress data
    return render_template("skin.html", progress_data=progress_data)


@app.route("/skin/<problem>", methods=["GET","POST"])
def problem_form(problem):
    """Handles the first form. 'problem' is the URL-safe name (e.g., 'whiteheads')."""
    if 'username' not in session:
        return redirect(url_for('login'))
   
    problem_url_safe = problem
    problem_display_name = PROBLEM_MAP.get(problem_url_safe.lower(), problem_url_safe)

    if request.method=="POST":
        # Defensive form data retrieval
        age = request.form.get("age", "25")
        gender = request.form.get("gender", "Female")
        skin_type = request.form.get("skin_type", "Normal")
        water_intake = request.form.get("water_intake", "Moderate")
        sleep_hours = request.form.get("sleep_hours", "7")
        chemical_treatment = request.form.get("chemical_treatment", "No")
        makeup = request.form.get("makeup", "No")
       
        # Pass BOTH names to the next template for correct routing
        return render_template("treatment_preference.html",
                               problem_url_safe=problem_url_safe,
                               problem_display_name=problem_display_name,
                               age=age, gender=gender, skin_type=skin_type, chemical_treatment=chemical_treatment,
                               makeup=makeup, water_intake=water_intake, sleep_hours=sleep_hours)
   
    return render_template("problem_form.html", problem_url_safe=problem_url_safe, problem_display_name=problem_display_name)


@app.route("/treatment", methods=["POST"])
def treatment():
    """Generates skincare treatment advice and stores user data."""
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get URL-safe name from the form
    problem_url_safe = request.form.get("problem_url_safe")
   
    if not problem_url_safe or problem_url_safe.lower() not in PROBLEM_MAP:
        print(f"Error: Missing or invalid skin problem: {problem_url_safe}")
        return redirect(url_for('skin_advice'))

    # Map to user-friendly problem name
    mapped_problem = PROBLEM_MAP.get(problem_url_safe.lower(), problem_url_safe)

    # Raw inputs from form
    gender = request.form.get("gender", "Female")
    skin_type = request.form.get("skin_type", "Normal")
    age = request.form.get("age", "25")
    chemical_treatment = request.form.get("chemical_treatment", "No")
    makeup = request.form.get("makeup", "No")
    sleep_hours = request.form.get("sleep_hours", "7")
    water_intake = request.form.get("water_intake", "Moderate")

    # ----------- FIX: Normalize inputs before matching or encoding ----------- #
    gender_clean = gender.strip().title()        # male → Male
    skin_type_clean = skin_type.strip().title()  # oily → Oily
    problem_clean = mapped_problem.strip().title()
    # ------------------------------------------------------------------------- #

    # --- Load skincare data ---
    data = SKIN_DATA

    # --- Exact match ---
    matched_routines = [
        item for item in data
        if item['SkinIssue'].lower() == mapped_problem.lower() and
           item['Gender'].lower() == gender_clean.lower() and
           item['SkinType'].lower() == skin_type_clean.lower()
    ]

    # --- Special case for Blackheads/Whiteheads ---
    if not matched_routines:
        if "blackhead" in mapped_problem.lower() or "whitehead" in mapped_problem.lower():
            for item in data:
                if ("blackhead" in item['SkinIssue'].lower() or "whitehead" in item['SkinIssue'].lower()) and \
                   item['Gender'].lower() == gender_clean.lower() and \
                   item['SkinType'].lower() == skin_type_clean.lower():
                    matched_routines.append(item)

    # --- Nearest Neighbor if no match ---
    if not matched_routines:
        df = pd.DataFrame(data)
        label_encoders = {}

        # Fit encoders on dataset
        for column in ['Gender', 'SkinIssue', 'SkinType']:
            le = LabelEncoder()
            df[column] = le.fit_transform(df[column])
            label_encoders[column] = le

        # Ensure SkinIssue exists
        if problem_clean not in label_encoders['SkinIssue'].classes_:
            problem_clean = label_encoders['SkinIssue'].classes_[0]

        # ----------- FIX: Safe transform using cleaned input ----------- #
        user_input = pd.DataFrame([{
            'Gender': label_encoders['Gender'].transform([gender_clean])[0],
            'SkinIssue': label_encoders['SkinIssue'].transform([problem_clean])[0],
            'SkinType': label_encoders['SkinType'].transform([skin_type_clean])[0]
        }])
        # ---------------------------------------------------------------- #

        nbrs = NearestNeighbors(n_neighbors=1)
        nbrs.fit(df[['Gender', 'SkinIssue', 'SkinType']])
        nearest_index = nbrs.kneighbors(user_input)[1][0][0]
        matched_routines = [data[nearest_index]]

    result = matched_routines[0] if matched_routines else None

    # --- Save to DB ---
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username=%s", (session['username'],))
    user_id = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO analysis_history
        (user_id, problem, age, gender, skin_type, chemical_treatment, makeup, sleep_hours, water_intake, result)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        user_id, mapped_problem, age, gender_clean, skin_type_clean, chemical_treatment,
        makeup, sleep_hours, water_intake,
        json.dumps(result) if result else None
    ))
    conn.commit()
    conn.close()

    # --- Clean up display text ---
    if result:
        if result.get("MorningRoutine"):
            result["MorningRoutine"] = result["MorningRoutine"].replace("→", "—")
        if result.get("NightRoutine"):
            result["NightRoutine"] = result["NightRoutine"].replace("→", "—")

    return render_template(
        "results.html",
        problem_display_name=mapped_problem,
        problem_url_safe=problem_url_safe,
        result=result
    )

# ----------------------------- FEEDBACK & PROGRESS ROUTES (FIXED FOR ROUTING/DATA) ----------------------------- #

@app.route("/feedback/<problem_url_safe>", methods=["GET"])
def feedback_form(problem_url_safe):
    """Renders the feedback submission form."""
    if 'username' not in session:
        return redirect(url_for('login'))
   
    problem_display_name = PROBLEM_MAP.get(problem_url_safe.lower(), problem_url_safe)
   
    # Pass BOTH names to the template for correct form submission and linking
    return render_template("feedback_form.html",
                           problem_url_safe=problem_url_safe,
                           problem_display_name=problem_display_name)

@app.route("/feedback/submit", methods=["POST"])
def submit_feedback():
    if 'username' not in session:
        return redirect(url_for('login'))

    skin_issue = request.form.get("skin_issue")
    problem_url_safe = DISPLAY_TO_URL_SAFE.get(skin_issue, skin_issue)

    # Boolean conversions
    follow_morning = int(request.form.get("follow_morning_routine", "No") == "Yes")
    follow_night = int(request.form.get("follow_night_routine", "No") == "Yes")
    products_changed = int(request.form.get("products_made_change", "No") == "Yes")
    remedies_helpful = int(request.form.get("remedies_helpful", "No") == "Yes")
    problem_solved = int(request.form.get("problem_solved", "No") == "Yes")

    # New feedback fields
    satisfaction_level = request.form.get("satisfaction_level")
    effectiveness_rating = request.form.get("effectiveness_rating")
    suggestions = request.form.get("suggestions", "")

    print("DEBUG satisfaction:", satisfaction_level, "rating:", effectiveness_rating)  # debug line

    # Guard in case of blank input
    if effectiveness_rating:
        effectiveness_rating = int(effectiveness_rating)
    else:
        effectiveness_rating = None

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username=%s", (session['username'],))
    user_id = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO feedback_history
        (user_id, skin_issue, date_submitted, follow_morning_routine, follow_night_routine,
         products_made_change, remedies_helpful, problem_solved, satisfaction_level,
         effectiveness_rating, suggestions)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        user_id, skin_issue, date.today(), follow_morning, follow_night,
        products_changed, remedies_helpful, problem_solved, satisfaction_level,
        effectiveness_rating, suggestions
    ))

    conn.commit()
    conn.close()

    return redirect(url_for('progress_history', problem_url_safe=problem_url_safe))

@app.route("/progress/<problem_url_safe>")
def progress_history(problem_url_safe):
    """Retrieves and displays all past feedback records and computes progress based on satisfaction, rating, and problem solved."""
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    problem_in_db = PROBLEM_MAP.get(problem_url_safe.lower(), problem_url_safe)

    try:
        cursor.execute("SELECT id FROM users WHERE username=%s", (session['username'],))
        user_result = cursor.fetchone()
        if not user_result:
            conn.close()
            return "User not found", 404
        user_id = user_result['id']

        cursor.execute("""
            SELECT
                fh.date_submitted,
                fh.follow_morning_routine,
                fh.follow_night_routine,
                fh.products_made_change,
                fh.remedies_helpful,
                fh.problem_solved,
                fh.satisfaction_level,
                fh.effectiveness_rating,
                fh.suggestions,
                (SELECT sleep_hours FROM analysis_history
                 WHERE user_id = fh.user_id AND problem = fh.skin_issue
                 ORDER BY id DESC LIMIT 1) as sleep_hours,
                (SELECT water_intake FROM analysis_history
                 WHERE user_id = fh.user_id AND problem = fh.skin_issue
                 ORDER BY id DESC LIMIT 1) as water_intake
            FROM feedback_history fh
            WHERE fh.user_id=%s AND fh.skin_issue=%s
            ORDER BY fh.date_submitted DESC
        """, (user_id, problem_in_db))

        history_raw = cursor.fetchall()
    except Exception as e:
        print(f"Database error during history retrieval: {e}")
        history_raw = []
    finally:
        conn.close()

    # --- Map satisfaction to base scores
    satisfaction_map = {
        "Very Satisfied": 10,
        "Satisfied": 8,
        "Neutral": 6,
        "Dissatisfied": 4,
        "Very Dissatisfied": 2
    }

    # --- Compute final progress for each record
    history_clean = []
    for record in history_raw:
        sat_score = satisfaction_map.get((record.get("satisfaction_level") or "").title(), 0)
        rating = record.get("effectiveness_rating") or 0
        solved = 10 if record.get("problem_solved") else 0

        # formula: satisfaction (50%) + rating (30%) + solved (20%)
        progress = round((sat_score * 0.5) + (rating * 0.3) + (solved * 0.2), 1)
        if progress > 10:
            progress = 10

        record["progress"] = progress

        # Clean up date formatting
        if isinstance(record.get("date_submitted"), (datetime, date)):
            record["date_submitted"] = record["date_submitted"].strftime("%Y-%m-%d")

        history_clean.append(record)

    # --- Average overall progress
    avg_progress = round(sum(r["progress"] for r in history_clean) / len(history_clean), 1) if history_clean else 0

    return render_template(
        "progress_history.html",
        history=history_clean,
        problem_url_safe=problem_url_safe,
        problem_display_name=problem_in_db,
        avg_progress=avg_progress
    )

# ----------------------------- Women's Health ----------------------------- #
# Safely load women's data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WOMEN_JSON = os.path.join(BASE_DIR, "women.json")

with open(WOMEN_JSON, "r", encoding="utf-8") as f:
    women_data = json.load(f)

    

@app.route('/women')
def women_home():
    return render_template("women.html")

@app.route('/menstrual', methods=['GET', 'POST'])
def menstrual():
    # Example: Get current logged-in user ID
    current_user_id = 1  # <-- Replace with dynamic user ID from session/login

    if request.method == 'POST':
        age = int(request.form.get('age', 0))
        cycle_length = request.form.get('cycle_length', "")
        pain_level = request.form.get('pain_level', "")
        symptoms = request.form.getlist('symptoms')
        exercise_freq = request.form.get('exercise_freq', 'Never')
        sleep_hours = int(request.form.get('sleep_hours', 7))

        symptoms_str = ', '.join(symptoms)

        try:
            db = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                database="skin_care_app"
            )
            cursor = db.cursor()

            insert_query = """
                INSERT INTO menstrual_data
                (user_id, age, cycle_length, pain_level, sleep_hours, exercise_freq, symptoms, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                current_user_id, age, cycle_length, pain_level, sleep_hours, exercise_freq, symptoms_str, datetime.now()
            )

            cursor.execute(insert_query, values)
            db.commit()
            cursor.close()
            db.close()
            print("✅ Data inserted successfully!")
        except Exception as e:
            print("❌ Database Error:", e)

        if sleep_hours <= 5:
            sleep_advice = data['lifestyle']['sleep']['0-5']
        elif sleep_hours <= 7:
            sleep_advice = data['lifestyle']['sleep']['6-7']
        else:
            sleep_advice = data['lifestyle']['sleep']['8-10']

        diet_advice = []
        for sym in symptoms:
            diet_advice += data['lifestyle']['diet'].get(sym, [])
        lifestyle = [sleep_advice] + diet_advice

        precautions = data['precautions'].get(pain_level, [])
        exercises = data['exercise'].get(exercise_freq, [])

        products = []
        for sym in symptoms:
            products += data['products'].get(sym, [])
        products_json = json.dumps(products)

        return render_template(
            "menstrual_result.html",
            age=age,
            cycle_length=cycle_length,
            pain_level=pain_level,
            sleep_hours=sleep_hours,
            exercise_freq=exercise_freq,
            symptoms=symptoms,
            lifestyle=lifestyle,
            precautions=precautions,
            exercises=exercises,
            products=products,
            products_json=products_json
        )

    return render_template("menstrual_form.html")

@app.route('/submit_feedback_form', methods=['POST'])
def submit_feedback_form():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    if not user:
        return "User not found!", 400
    user_id = user[0]

    cycle_length = request.form.get('cycle_length')
    pain_level = request.form.get('pain_level')
    sleep_hours = request.form.get('sleep_hours')
    exercise_freq = request.form.get('exercise_freq')
    products_used = request.form.get('products_used')
    overall_score = request.form.get('overall_score')

    cursor.execute("""
        INSERT INTO feedback (user_id, cycle_length, pain_level, sleep_hours, exercise_freq, products_used, overall_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (user_id, cycle_length, pain_level, sleep_hours, exercise_freq, products_used, overall_score))
   
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('women_dashboard'))

@app.route('/women_feedback')
def women_feedback():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template("women_feedback.html")

@app.route('/women_dashboard')
def women_dashboard():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    if not user:
        return "User not found!", 400
    user_id = user['id']

    cursor.execute("""
        SELECT date, cycle_length, pain_level, sleep_hours, exercise_freq, overall_score
        FROM feedback
        WHERE user_id=%s
        ORDER BY date ASC
    """, (user_id,))
    feedback_data = cursor.fetchall()
    cursor.close()
    conn.close()

    exercise_mapping = {
        "Never": 0,
        "Rarely": 2,
        "Occasionally": 5,
        "Often": 8,
        "Regularly": 10
    }

    chart_data = {
        "dates": [str(f["date"]) for f in feedback_data],
        "sleep": [float(f["sleep_hours"]) for f in feedback_data],
        "pain": [1 if f["pain_level"]=="Low" else 5 if f["pain_level"]=="Moderate" else 10 for f in feedback_data],
        "score": [float(f["overall_score"]) for f in feedback_data],
        "exercise": [exercise_mapping.get(f["exercise_freq"], 0) for f in feedback_data]
    }

    chart_data_json = json.dumps(chart_data)

    return render_template("women_dashboard.html", feedback=feedback_data, chart_data=chart_data_json)

@app.route('/pregnancy_form')
def pregnancy_form():
    return render_template('pregnancy_form.html')

@app.route('/pregnancy_result', methods=['POST'])
def pregnancy_result():
    import json, random, mysql.connector
    from flask import request, render_template, session
    from datetime import datetime

    user_id = session.get('user_id')  # should be set during login
    if not user_id:
        user_id = 1  # fallback for testing, remove in production

    age = request.form.get('age')
    weight = request.form.get('weight')
    height = request.form.get('height')
    blood_group = request.form.get('blood_group')
    month = request.form.get('pregnancy_month')
    conditions = request.form.getlist('conditions')
    sleep = request.form.get('sleep')
    fitness = request.form.get('fitness_level')

    conditions_str = ', '.join(conditions)

    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",  # put your MySQL password here
            database="skin_care_app"
        )
        cursor = db.cursor()
        insert_query = """
            INSERT INTO pregnancy_data
            (user_id, age, weight, height, pregnancy_month, blood_group, fitness_level, sleep_quality, existing_conditions, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (user_id, age, weight, height, month, blood_group, fitness, sleep, conditions_str, datetime.now())
        cursor.execute(insert_query, values)
        db.commit()
        cursor.close()
        db.close()
        print("✅ Pregnancy data inserted successfully!")
    except Exception as e:
        print("❌ Database Error:", e)

    with open('pre.json', 'r') as f:
        data = json.load(f)

    month_data = data.get(str(month), {}).get("general", {})
    lifestyle_tips = month_data.get("lifestyle", [])
    diet_recommendations = month_data.get("diet", [])
    precautions = month_data.get("precautions", [])
    exercises = month_data.get("exercise", [])

    for ex in exercises:
        if "photo" in ex:
            ex["image"] = f"images/{ex['photo'].split('/')[-1]}"

    condition_data = []
    conditions_json = data.get("conditions", {})
    for cond in conditions:
        if cond in conditions_json:
            condition_data.append({
                "condition": cond,
                "diet": conditions_json[cond].get("diet", []),
                "precautions": conditions_json[cond].get("precautions", [])
            })

    sleep_tips = data.get("sleep", {}).get(sleep, [])

    random.shuffle(lifestyle_tips)
    random.shuffle(diet_recommendations)
    random.shuffle(precautions)

    return render_template(
        'pregnancy_result.html',
        lifestyle_tips=lifestyle_tips[:4],
        diet_recommendations=diet_recommendations[:4],
        precautions=precautions[:4],
        exercises=exercises[:3],
        condition_data=condition_data,
        sleep_tips=sleep_tips,
        month=month,
        age=age,
        blood_group=blood_group,
        fitness=fitness
    )

# ====================================================================
#                      STRESS MANAGEMENT MODULE (ADDED)
# ====================================================================
# This module is namespaced under /stress to keep it separate
# and avoid collisions with the friend's existing routes.

def load_stress_tips():
    path = os.path.join('data', 'stress_tips.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print("Error loading stress_tips.json:", e)
        return {}

def load_stress_videos():
    path = os.path.join('data', 'stress_videos.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print("Error loading stress_videos.json:", e)
        return {}

def load_stress_music():
    path = os.path.join('data', 'stress_music.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print("Error loading stress_music.json:", e)
        return {}

def calculate_progress_score(feedback_data):
    """Calculates a simple stress management progress score."""
    base_score = 30
    try:
        rating_score = int(feedback_data.get('rating', 0)) * 6
    except Exception:
        rating_score = 0
    tips_score = len(feedback_data.get('tips_used', [])) * 10
    comments_bonus = 5 if feedback_data.get('comments', '').strip() else 0
    total_score = base_score + rating_score + tips_score + comments_bonus
    return min(100, total_score)

@app.route('/stress')
def stress_index():
    """Stress module home: shows types and links into forms."""
    stress_types = ['work', 'relationship', 'academic']
    return render_template('stress_index.html', stress_types=stress_types)

@app.route('/stress/work')
def work_stress_form():
    """Form page for Work Stress."""
    return render_template('stress_form_work.html', stress_type='work')


@app.route('/stress/relationship')
def relationship_stress_form():
    """Form page for Relationship Stress."""
    return render_template('stress_form_relationship.html', stress_type='relationship')


@app.route('/stress/academic')
def academic_stress_form():
    """Form page for Academic Stress."""
    return render_template('stress_form_academic.html', stress_type='academic')





# ---------------- Unified Submission Route ---------------- #

@app.route('/stress/submit', methods=['POST'])
def stress_submit():
    """Handles submission of stress forms and stores data into respective tables."""
   
    # Accept JSON or Form data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    stress_type = data.get('stress_type')

    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'error': 'Database connection failed.'}), 500

    try:
        cursor = conn.cursor()

        # Work Stress
        if stress_type == 'work':
            query = '''INSERT INTO work_stress
                (name, age, gender, stress_level, stress_duration, sleep_hours,
                 overloaded_work, supportive_colleagues, work_life_balance, condition_status)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
            values = (
                data['name'], data['age'], data['gender'], data['stress_level'],
                data['stress_duration'], data['sleep_hours'],
                data['q1'], data['q2'], data['q3'], data['condition']
            )

        # Relationship Stress
        elif stress_type == 'relationship':
            query = '''INSERT INTO relationship_stress
                (name, age, gender, stress_level, stress_duration, sleep_hours,
                 misunderstood, conflict_affects_mood, emotional_support, condition_status)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
            values = (
                data['name'], data['age'], data['gender'], data['stress_level'],
                data['stress_duration'], data['sleep_hours'],
                data['q1'], data['q2'], data['q3'], data['condition']
            )

        # Academic Stress
        elif stress_type == 'academic':
            query = '''INSERT INTO academic_stress
                (name, age, gender, stress_level, stress_duration, sleep_hours,
                 pressure_to_perform, enough_rest, exams_affect_mood, condition_status)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
            values = (
                data['name'], data['age'], data['gender'], data['stress_level'],
                data['stress_duration'], data['sleep_hours'],
                data['q1'], data['q2'], data['q3'], data['condition']
            )

       

        else:
            return jsonify({'success': False, 'error': 'Invalid stress type provided.'}), 400

        # Execute and commit
        cursor.execute(query, values)
        conn.commit()
        inserted_id = cursor.lastrowid
        session['stress_user_id'] = inserted_id

        return jsonify({'success': True, 'stress_user_id': inserted_id})

    except Exception as e:
        print("Error inserting stress data:", e)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/stress/results/<stress_type>')
def stress_results(stress_type):
    tips_data = load_stress_tips()
    videos_data = load_stress_videos()

    stress_tips = tips_data.get(stress_type, {})
    lifestyle_list = stress_tips.get('lifestyle', ["No lifestyle tips available"])
    lifestyle_tips = random.sample(lifestyle_list, min(5, len(lifestyle_list)))

    home_remedies_list = stress_tips.get('home_remedies', ["No home remedies available"])
    home_remedies = random.sample(home_remedies_list, min(5, len(home_remedies_list)))

    exercise_list = stress_tips.get('exercise', ["No exercise tips available"])
    exercise_tips = random.sample(exercise_list, min(5, len(exercise_list)))

    videos = videos_data.get(stress_type, [])
    if not videos:
        videos = [
            {'title': 'General Stress Relief Exercises', 'embed_url': 'https://www.youtube.com/embed/v7AYKMP6rOE', 'description': 'General stress management techniques'},
            {'title': 'Quick Anxiety Relief', 'embed_url': 'https://www.youtube.com/embed/1pc8_O7sjU4', 'description': 'Fast techniques to reduce anxiety'}
        ]
    random.shuffle(videos)
    videos = videos[:2]

    return render_template('stress_results.html',
                           stress_type=stress_type,
                           lifestyle_tips=lifestyle_tips,
                           home_remedies=home_remedies,
                           exercise_tips=exercise_tips,
                           videos=videos)

# --- FEEDBACK ROUTES FOR EACH STRESS TYPE ---

@app.route('/stress/feedback/work')
def feedback_work():
    return render_template('stress_feedback_work.html', stress_type='work')

@app.route('/stress/feedback/academic')
def feedback_academic():
    return render_template('stress_feedback_academic.html', stress_type='academic')

@app.route('/stress/feedback/relationship')
def feedback_relationship():
    return render_template('stress_feedback_relationship.html', stress_type='relationship')




@app.route('/stress/submit-feedback', methods=['POST'])
def stress_submit_feedback():
    try:
        data = request.get_json()
        stress_type = data.get('stress_type')
        username = session.get('username')

        if not username:
            return jsonify({'success': False, 'error': 'User not logged in'})

        table_map = {
            'work': 'feedback_work',
            'academic': 'feedback_academic',
            'relationship': 'feedback_relationship'
           
        }

        table = table_map.get(stress_type)
        if not table:
            return jsonify({'success': False, 'error': 'Invalid stress type'})

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="skin_care_app"
        )
        cursor = conn.cursor()

        # ✅ Exclude stress_type and username from data
        feedback_data = {k: v for k, v in data.items() if k not in ['stress_type', 'username']}
        fields = ', '.join(feedback_data.keys()) + ', username'
        placeholders = ', '.join(['%s'] * (len(feedback_data) + 1))
        values = list(feedback_data.values()) + [username]

        sql = f"INSERT INTO {table} ({fields}) VALUES ({placeholders})"
        cursor.execute(sql, values)
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Feedback submitted successfully!'})

    except Exception as e:
        print("Error saving feedback:", e)
        return jsonify({'success': False, 'error': str(e)})


@app.route('/stress/get-progress')
def get_progress():
    username = session.get('username')
    stress_type = request.args.get('stress_type', '').lower()  # lowercase for safety

    # 🔍 Debug info
    print(">>> Session username:", username)
    print(">>> Stress type received:", stress_type)

    if not username:
        return jsonify({'success': False, 'error': 'User not logged in'})
    if not stress_type:
        return jsonify({'success': False, 'error': 'Stress type missing'})

    table_map = {
        'work': 'feedback_work',
        'academic': 'feedback_academic',
        'relationship': 'feedback_relationship'
       
    }

    table = table_map.get(stress_type)
    if not table:
        return jsonify({'success': False, 'error': f'Invalid stress type: {stress_type}'})

    # ✅ Connect to DB
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="skin_care_app"
    )
    cursor = conn.cursor(dictionary=True)

    # ✅ Safe query
    sql = f"SELECT * FROM {table} WHERE username = %s ORDER BY submitted_at DESC"
    print(">>> SQL to run:", sql)
    print(">>> Parameters:", (username,))
    cursor.execute(sql, (username,))

    rows = cursor.fetchall()

    # 🕒 Format submitted_at nicely
    for r in rows:
        if 'submitted_at' in r and r['submitted_at']:
            try:
                r['submitted_at'] = r['submitted_at'].strftime("%Y-%m-%d %H:%M")
            except Exception as e:
                print("Date format error:", e)

    print(f">>> Retrieved {len(rows)} rows")

    conn.close()
    return jsonify({'success': True, 'history': rows})




@app.route('/stress/progress')
def stress_progress_page():
    progress_data = session.get('stress_progress', {})
    return render_template('stress_progress.html', progress_data=progress_data)

@app.route('/stress/music')
def stress_music_player():
    music_data = load_stress_music()
    music_videos = music_data.get('music_videos', [])
    return render_template('stress_music.html', music_videos=music_videos)

# ====================================================================
#                      ERROR HANDLERS (OPTIONAL)
# ====================================================================
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


# -----------------------------
# Helper Functions
# -----------------------------
def clean_yes_no(value):
    if pd.isna(value):
        return "No"
    value = str(value).strip().lower()
    return "Yes" if value in ["yes", "y"] else "No"

def clean_gender(value):
    if pd.isna(value):
        return "Female"
    value = str(value).strip().lower()
    return "Male" if value in ["male", "m"] else "Female"

# -----------------------------
# Hairfall Analysis
# -----------------------------
df_hairfall = pd.read_json("data/hairfall_dataset.json")
df_hairfall.columns = df_hairfall.columns.str.strip()
df_hairfall["Chem_Treatments"] = df_hairfall["Chem_Treatments"].apply(clean_yes_no)
df_hairfall["Oil_Scalp"] = df_hairfall["Oil_Scalp"].apply(clean_yes_no)
df_hairfall["Gender"] = df_hairfall["Gender"].apply(clean_gender)

hairfall_categorical = ["Gender", "Water_Intake", "Oil_Scalp", "Chem_Treatments"]
hairfall_encoders = {}
for col in hairfall_categorical:
    enc = LabelEncoder()
    df_hairfall[col] = enc.fit_transform(df_hairfall[col].astype(str))
    hairfall_encoders[col] = enc

hairfall_features = ["Age", "Sleep_Hours", "Gender", "Water_Intake", "Oil_Scalp", "Chem_Treatments"]
X_hairfall = df_hairfall[hairfall_features]
nn_hairfall = NearestNeighbors(n_neighbors=5, metric="euclidean")
nn_hairfall.fit(X_hairfall)

def analyze_hairfall(user_data):
    input_data = user_data.copy()
    for col, enc in hairfall_encoders.items():
        val = str(input_data[col])
        if val not in enc.classes_:
            val = enc.classes_[0]
        input_data[col] = enc.transform([val])[0]

    input_df = pd.DataFrame([input_data], columns=hairfall_features)
    distances, indices = nn_hairfall.kneighbors(input_df)

    row0 = df_hairfall.iloc[indices[0][0]]

    remedies = [r.strip() for r in str(row0.get("Remedies", "")).split(";") if r.strip()]
    routine = row0.get("Routine", "No routine found")
    amazon_products = row0.get("AmazonProducts", {})

    return {
        "Remedies": remedies,
        "Routine": routine,
        "AmazonProducts": amazon_products
    }


# -----------------------------
# Dandruff Analysis
# -----------------------------
df_dandruff = pd.read_json("data/dandruff_dataset.json")
df_dandruff.columns = df_dandruff.columns.str.strip()
dandruff_categorical = ["Gender", "Water_Intake", "Scalp_Type", "Oil_Scalp", "Chemical_Treatment"]
dandruff_encoders = {}
for col in dandruff_categorical:
    enc = LabelEncoder()
    df_dandruff[col] = enc.fit_transform(df_dandruff[col].astype(str))
    dandruff_encoders[col] = enc

dandruff_features = ["Age", "Sleep_Hours", "Gender", "Water_Intake", "Scalp_Type", "Oil_Scalp", "Chemical_Treatment"]
X_dandruff = df_dandruff[dandruff_features]
nn_dandruff = NearestNeighbors(n_neighbors=1, metric="euclidean")
nn_dandruff.fit(X_dandruff)

def analyze_dandruff(user_data):
    input_data = user_data.copy()
    for col, enc in dandruff_encoders.items():
        val = str(input_data[col])
        if val not in enc.classes_:
            val = enc.classes_[0]
        input_data[col] = enc.transform([val])[0]

    input_df = pd.DataFrame([input_data], columns=dandruff_features)
    _, idx = nn_dandruff.kneighbors(input_df)

    row = df_dandruff.iloc[idx[0][0]]

    remedies = [r.strip() for r in str(row.get("Remedies", "")).split(";") if r.strip()]
    routine = row.get("Routine", "No routine found")
    amazon_products = row.get("AmazonProducts", {})

    return {
        "Remedies": remedies,
        "Routine": routine,
        "AmazonProducts": amazon_products
    }
# -----------------------------
# Routes
# -----------------------------

@app.route('/hair_dashboard')
def hair_dashboard():
    """Retrieves and displays a combined view of Hairfall and Dandruff progress."""
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
   
    # 1. Get User ID
    cursor.execute("SELECT id FROM users WHERE username=%s", (session['username'],))
    user_result = cursor.fetchone()
    if not user_result:
        conn.close()
        return "User not found", 404
    user_id = user_result['id']

    # 2. Fetch Hairfall Progress
    cursor.execute("""
        SELECT * FROM hairfall_progress
        WHERE user_id =%s
        ORDER BY analysis_date DESC
    """, (session.get('user_id'),)) # Assuming session_id is used for hairfall tracking as per your table schema
    hairfall_history = cursor.fetchall()

    # 3. Fetch Dandruff Progress
    cursor.execute("""
        SELECT * FROM dandruff_progress
        WHERE user_id =%s
        ORDER BY analysis_date DESC
    """, (session.get('user_id'),)) # Assuming session_id is used for dandruff tracking as per your table schema
    dandruff_history = cursor.fetchall()
   
    conn.close()

    return render_template(
        "hair_dashboard.html",
        hairfall_history=hairfall_history,
        dandruff_history=dandruff_history
    )


# Hairfall Form & Result
@app.route("/hairfall", methods=["GET","POST"])
def hairfall_form():
    if request.method=="POST":
        user_data = {
            "Age": int(request.form.get("age")),
            "Gender": request.form.get("gender"),
            "Sleep_Hours": int(request.form.get("sleep_hours")),
            "Water_Intake": request.form.get("water_intake"),
            "Oil_Scalp": request.form.get("oil_scalp"),
            "Chem_Treatments": request.form.get("chemical_treatment")
        }
        session['current_hairfall_data'] = user_data
        result = analyze_hairfall(user_data)
        return render_template("hairfall_result.html", result=result)
    return render_template("hairfall_form.html")

# Dandruff Form & Result
@app.route("/dandruff", methods=["GET","POST"])
def dandruff_form():
    if request.method=="POST":
        user_data = {
            "Age": int(request.form.get("age")),
            "Gender": request.form.get("gender"),
            "Sleep_Hours": int(request.form.get("sleep_hours")),
            "Water_Intake": request.form.get("water_intake"),
            "Scalp_Type": request.form.get("scalp_type"),
            "Oil_Scalp": request.form.get("oil_scalp"),
            "Chemical_Treatment": request.form.get("chemical_treatment")
        }
        session['current_dandruff_data'] = user_data
        result = analyze_dandruff(user_data)
        return render_template("dandruff_result.html", result=result)
    return render_template("dandruff_form.html")

# Hairfall Feedback
@app.route('/feedback_hairfall', methods=['GET', 'POST'])
def feedback_hairfall():
    if request.method == 'POST':
        satisfaction = request.form.get('satisfaction_level', '')
        ease_of_use = request.form.get('ease_of_use', '')
        product_helpful = request.form.get('product_helpful', '')
        remedies_helpful = request.form.get('remedies_helpful', '')
        followed_routine = request.form.get('followed_routine', '')
        recommend_wellora = request.form.get('recommend_wellora', '')
        comments = request.form.get('comments', '')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Insert feedback
            cursor.execute("""
                INSERT INTO hairfall_feedback
                (user_id, satisfaction_level, ease_of_use, product_helpful, remedies_helpful,
                 followed_routine, recommend_wellora, comments)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                session['user_id'], satisfaction, ease_of_use, product_helpful,
                remedies_helpful, followed_routine, recommend_wellora, comments
            ))

            # Progress calculation
            satisfaction_score = {
                "Very Satisfied": 90,
                "Satisfied": 75,
                "Neutral": 50,
                "Dissatisfied": 30,
                "Very Dissatisfied": 10
            }.get(satisfaction, 50)

            improvement_percent = satisfaction_score
            if followed_routine == "Yes": improvement_percent += 5
            if product_helpful == "Yes": improvement_percent += 5
            if remedies_helpful == "Yes": improvement_percent += 5
            improvement_percent = min(improvement_percent, 100)

            # Insert progress
            cursor.execute("""
                INSERT INTO hairfall_progress
                (user_id, improvement_percent, satisfaction_level, comments, analysis_date, problem_type)
                VALUES (%s, %s, %s, %s, NOW(), 'hairfall')
            """, (session['user_id'], improvement_percent, satisfaction, comments))

            conn.commit()

        finally:
            cursor.close()
            conn.close()

        # 👉 Redirect to progress page
        return redirect(url_for('progress_hairfall'))

    # GET request → just show form
    return render_template(
        "hairfall_feedback.html",
        user_id=session.get('user_id')
    )



# Dandruff Feedback
@app.route('/feedback_dandruff', methods=['GET', 'POST'])
def feedback_dandruff():
    message = None

    if request.method == 'POST':
        satisfaction = request.form.get('satisfaction_level', '')
        ease_of_use = request.form.get('ease_of_use', '')
        product_helpful = request.form.get('product_helpful', '')
        remedies_helpful = request.form.get('remedies_helpful', '')
        followed_routine = request.form.get('followed_routine', '')
        recommend_wellora = request.form.get('recommend_wellora', '')
        comments = request.form.get('comments', '')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO dandruff_feedback
                (user_id, satisfaction_level, ease_of_use, product_helpful, remedies_helpful,
                 followed_routine, recommend_wellora, comments)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                session['user_id'], satisfaction, ease_of_use, product_helpful,
                remedies_helpful, followed_routine, recommend_wellora, comments
            ))

            # calculate improvement (same as before)
            satisfaction_score = {
                "Very Satisfied": 80,
                "Satisfied": 75,
                "Neutral": 40,
                "Dissatisfied": 30,
                "Very Dissatisfied": 10
            }.get(satisfaction, 50)

            improvement_percent = satisfaction_score
            if followed_routine == "Yes": improvement_percent += 5
            if product_helpful == "Yes": improvement_percent += 5
            if remedies_helpful == "Yes": improvement_percent += 5
            improvement_percent = min(improvement_percent, 100)

            cursor.execute("""
                INSERT INTO dandruff_progress
                (user_id, improvement_percent, satisfaction_level, comments, analysis_date, problem_type)
                VALUES (%s, %s, %s, %s, NOW(), 'dandruff')
            """, (session['user_id'], improvement_percent, satisfaction, comments))

            conn.commit()

        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('progress_dandruff'))

    # GET request -> show form always
    return render_template("dandruff_feedback.html", user_id=session.get('user_id'), message=message)





# Progress Routes
@app.route("/progress_hairfall")
def progress_hairfall():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        user_id = session.get('user_id')

        # --------------------------
        # FETCH PROGRESS (Chart Data)
        # --------------------------
        cursor.execute("""
            SELECT analysis_date, improvement_percent
            FROM hairfall_progress
            WHERE user_id = %s
            ORDER BY analysis_date ASC
        """, (user_id,))
        progress_data = cursor.fetchall()

        # Format date for the chart
        for d in progress_data:
            d['analysis_date'] = d['analysis_date'].strftime("%Y-%m-%d")

        # --------------------------
        # FETCH FEEDBACK (Table Data)
        # --------------------------
        cursor.execute("""
            SELECT satisfaction_level, ease_of_use, product_helpful,
                   remedies_helpful, followed_routine, recommend_wellora, comments
            FROM hairfall_feedback
            WHERE user_id = %s
            ORDER BY id DESC
        """, (user_id,))
        feedback_list = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "progress_hairfall.html",
            progress=progress_data,
            feedback_list=feedback_list
        )

    except Exception as e:
        return f"Error fetching hairfall progress: {e}"


@app.route("/progress_dandruff")
def progress_dandruff():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        user_id = session.get('user_id')

        # --------------------------
        # FETCH PROGRESS (Chart Data)
        # --------------------------
        cursor.execute("""
            SELECT analysis_date, improvement_percent
            FROM dandruff_progress
            WHERE user_id = %s
            ORDER BY analysis_date ASC
        """, (user_id,))
        progress_data = cursor.fetchall()

        # Format date for the chart
        for d in progress_data:
            d['analysis_date'] = d['analysis_date'].strftime("%Y-%m-%d")

        # --------------------------
        # FETCH FEEDBACK (Table Data)
        # --------------------------
        cursor.execute("""
            SELECT satisfaction_level, ease_of_use, product_helpful,
                   remedies_helpful, followed_routine, recommend_wellora, comments
            FROM dandruff_feedback
            WHERE user_id = %s
            ORDER BY id DESC
        """, (user_id,))
        feedback_list = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "progress_dandruff.html",
            progress=progress_data,
            feedback_list=feedback_list
        )

    except Exception as e:
        return f"Error fetching dandruff progress: {e}"
# ----------------------------- Run App ----------------------------- #
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)




