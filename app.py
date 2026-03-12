from flask import Flask, render_template, request, redirect, session, send_file
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "super_secret_key"

MYSQL_PASSWORD = "Chandini.25"
SYSTEM_START_DATE = "2026-02-26"


# ================= DATABASE CONNECTION =================
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=MYSQL_PASSWORD,
        database="geopolitical_news"
    )


# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s,%s)",
            (username, password)
        )

        db.commit()
        cursor.close()
        db.close()

        return redirect("/login")

    return render_template("register.html")


# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE username=%s",
            (username,)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user and check_password_hash(user["password"], password):
            session["user"] = username
            return redirect("/")

        return "Invalid Credentials"

    return render_template("login.html")


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


# ================= DASHBOARD =================
@app.route("/")
def home():

    if "user" not in session:
        return redirect("/login")

    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    sector = request.args.get("sector")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT title, sentiment, risk_score, risk_level, published_at, sector
        FROM news
    """

    conditions = []
    values = []

    # Default data (from system start date)
    if not from_date and not to_date:
        conditions.append("published_at >= %s")
        values.append(SYSTEM_START_DATE)

    if from_date:
        conditions.append("published_at >= %s")
        values.append(from_date)

    if to_date:
        conditions.append("published_at <= %s")
        values.append(to_date + " 23:59:59")

    if sector:
        conditions.append("sector = %s")
        values.append(sector)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY published_at DESC"

    cursor.execute(query, values)

    news = cursor.fetchall()

    # ================= SUMMARY DATA =================

    total_articles = len(news)

    risk_summary = {
        "LOW":0,
        "MEDIUM":0,
        "HIGH":0,
        "CRITICAL":0
    }

    sentiment_summary = {
        "Positive":0,
        "Neutral":0,
        "Negative":0
    }

    sector_summary = {}

    for item in news:

        if item["risk_level"] in risk_summary:
            risk_summary[item["risk_level"]] += 1

        if item["sentiment"] in sentiment_summary:
            sentiment_summary[item["sentiment"]] += 1

        sector_name = item["sector"] or "unknown"

        if sector_name not in sector_summary:
            sector_summary[sector_name] = 0

        sector_summary[sector_name] += 1


    # ================= EXECUTIVE SUMMARY =================

    high_risk = risk_summary["HIGH"] + risk_summary["CRITICAL"]

    if total_articles == 0:
        summary_text = "No news articles found for the selected filters."

    elif high_risk > total_articles * 0.5:
        summary_text = "Recent geopolitical developments indicate significant global tensions with many high-risk events."

    elif high_risk > 0:
        summary_text = "Some geopolitical risks are emerging but the situation remains moderately stable."

    else:
        summary_text = "Most recent global developments appear stable with primarily low-risk news."

    if sentiment_summary["Negative"] > sentiment_summary["Positive"]:
        summary_text += " Overall sentiment in global coverage is mostly negative."

    cursor.close()
    db.close()

    return render_template(
        "index.html",
        news=news,
        total_articles=total_articles,
        risk_summary=risk_summary,
        sentiment_summary=sentiment_summary,
        sector_summary=sector_summary,
        summary_text=summary_text
    )


# ================= PDF REPORT =================
@app.route("/download-report")
def download_report():

    if "user" not in session:
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "SELECT title, risk_level, sentiment, published_at FROM news ORDER BY published_at DESC"
    )

    rows = cursor.fetchall()

    file_path = "geopolitical_report.pdf"

    doc = SimpleDocTemplate(file_path)

    elements = []
    styles = getSampleStyleSheet()

    elements.append(
        Paragraph("Geopolitical Intelligence Report", styles["Title"])
    )

    elements.append(Spacer(1,20))

    data = [["Title","Risk Level","Sentiment","Date"]]

    data.extend(rows)

    table = Table(data)

    elements.append(table)

    doc.build(elements)

    cursor.close()
    db.close()

    return send_file(file_path, as_attachment=True)


# ================= RUN APP =================
if __name__ == "__main__":
    app.run(debug=True)