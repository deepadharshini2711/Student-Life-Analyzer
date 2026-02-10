from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///student_life.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ------------------ Models ------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))

class DailyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    date = db.Column(db.Date)
    mood = db.Column(db.Integer)
    sleep_hours = db.Column(db.Float)
    study_hours = db.Column(db.Float)
    phone_hours = db.Column(db.Float)
    problem_text = db.Column(db.Text)
    problem_type = db.Column(db.String(50))
    severity_score = db.Column(db.Integer)

# ------------------ Helper Logic ------------------

def classify_problem(text):
    text = text.lower()

    stress_words = ["stress", "tension", "anxiety", "pressure", "worry"]
    health_words = ["sleep", "headache", "pain", "tired", "sick"]
    study_words = ["exam", "study", "test", "assignment", "syllabus"]
    distraction_words = ["phone", "reel", "instagram", "youtube", "game"]

    for w in stress_words:
        if w in text:
            return "Stress", 7

    for w in health_words:
        if w in text:
            return "Health", 6

    for w in study_words:
        if w in text:
            return "Study", 6

    for w in distraction_words:
        if w in text:
            return "Distraction", 5

    return "General", 4

def calculate_risk(logs):
    if not logs:
        return "Low"

    avg_sleep = sum([l.sleep_hours for l in logs]) / len(logs)
    avg_study = sum([l.study_hours for l in logs]) / len(logs)
    avg_phone = sum([l.phone_hours for l in logs]) / len(logs)

    stress_count = sum([1 for l in logs if l.problem_type == "Stress"])

    if avg_sleep < 5 and stress_count >= 3:
        return "High"
    elif avg_phone > 5 and avg_study < 2:
        return "Medium"
    else:
        return "Low"

# 🔥 NEW: Suggestions Generator
def generate_suggestions(logs):
    if not logs:
        return ["No data available. Start adding daily logs."]

    avg_sleep = sum([l.sleep_hours for l in logs]) / len(logs)
    avg_study = sum([l.study_hours for l in logs]) / len(logs)
    avg_phone = sum([l.phone_hours for l in logs]) / len(logs)

    stress_count = sum([1 for l in logs if l.problem_type == "Stress"])

    suggestions = []

    if avg_sleep < 5:
        suggestions.append("You are sleeping less. Try to get at least 7 hours of sleep.")

    if avg_phone > 5:
        suggestions.append("Your phone usage is high. Reduce screen time and focus on studies.")

    if avg_study < 2:
        suggestions.append("Your study time is low. Try using Pomodoro technique or fixed study schedule.")

    if stress_count >= 3:
        suggestions.append("You seem stressed frequently. Take breaks, do light exercise, and relax.")

    if not suggestions:
        suggestions.append("Good job! Maintain your current routine.")

    return suggestions

# ------------------ APIs ------------------

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"message": "User already exists"}), 400

    hashed = generate_password_hash(data["password"])
    user = User(name=data["name"], email=data["email"], password_hash=hashed)
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User registered successfully"})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(email=data["email"]).first()
    if not user or not check_password_hash(user.password_hash, data["password"]):
        return jsonify({"message": "Invalid credentials"}), 401

    return jsonify({"message": "Login successful", "user_id": user.id})

@app.route("/add_log", methods=["POST"])
def add_log():
    data = request.json

    problem_type, severity = classify_problem(data["problem_text"])

    log = DailyLog(
        user_id=data["user_id"],
        date=datetime.strptime(data["date"], "%Y-%m-%d").date(),
        mood=data["mood"],
        sleep_hours=data["sleep_hours"],
        study_hours=data["study_hours"],
        phone_hours=data["phone_hours"],
        problem_text=data["problem_text"],
        problem_type=problem_type,
        severity_score=severity
    )

    db.session.add(log)
    db.session.commit()

    return jsonify({
        "message": "Log added",
        "problem_type": problem_type,
        "severity_score": severity
    })

@app.route("/dashboard/<int:user_id>", methods=["GET"])
def dashboard(user_id):
    last_7_days = datetime.now().date() - timedelta(days=7)
    logs = DailyLog.query.filter(DailyLog.user_id == user_id, DailyLog.date >= last_7_days).all()

    risk = calculate_risk(logs)
    suggestions = generate_suggestions(logs)

    summary = {}
    for l in logs:
        summary[l.problem_type] = summary.get(l.problem_type, 0) + 1

    return jsonify({
        "risk_level": risk,
        "problem_summary": summary,
        "total_logs": len(logs),
        "suggestions": suggestions
    })

@app.route("/history/<int:user_id>", methods=["GET"])
def history(user_id):
    logs = DailyLog.query.filter_by(user_id=user_id).order_by(DailyLog.date.desc()).all()

    result = []
    for l in logs:
        result.append({
            "date": l.date.strftime("%Y-%m-%d"),
            "mood": l.mood,
            "sleep_hours": l.sleep_hours,
            "study_hours": l.study_hours,
            "phone_hours": l.phone_hours,
            "problem_text": l.problem_text,
            "problem_type": l.problem_type,
            "severity_score": l.severity_score
        })

    return jsonify(result)

# ------------------ Run ------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
