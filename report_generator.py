import mysql.connector

MYSQL_PASSWORD = "Chandini.25"

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password=MYSQL_PASSWORD,
    database="geopolitical_news"
)

cursor = db.cursor()

# ===============================
# USER INPUT
# ===============================

start_date = input("Enter start date (YYYY-MM-DD): ")
end_date = input("Enter end date (YYYY-MM-DD): ")

# ===============================
# FETCH DATA
# ===============================

query = """
SELECT title, sentiment, risk_score, risk_level
FROM news
WHERE DATE(published_at) BETWEEN %s AND %s
ORDER BY risk_score DESC
"""

cursor.execute(query, (start_date, end_date))
rows = cursor.fetchall()

total_articles = len(rows)

risk_count = {
    "LOW": 0,
    "MEDIUM": 0,
    "HIGH": 0,
    "CRITICAL": 0
}

sentiment_count = {
    "Positive": 0,
    "Neutral": 0,
    "Negative": 0
}

for title, sentiment, risk_score, risk_level in rows:
    if risk_level in risk_count:
        risk_count[risk_level] += 1
    if sentiment in sentiment_count:
        sentiment_count[sentiment] += 1

# ===============================
# PRINT REPORT
# ===============================

print("\n========== GEOPOLITICAL INTELLIGENCE REPORT ==========")
print(f"From {start_date} to {end_date}")
print(f"\nTotal Articles: {total_articles}")

print("\n--- Risk Distribution ---")
for level, count in risk_count.items():
    print(f"{level}: {count}")

print("\n--- Sentiment Distribution ---")
for sentiment, count in sentiment_count.items():
    print(f"{sentiment}: {count}")

print("\n--- Top 5 Highest Risk Events ---")

for i, row in enumerate(rows[:5], start=1):
    title, sentiment, risk_score, risk_level = row
    print(f"\n{i}. {title}")
    print(f"   Risk Score: {risk_score}")
    print(f"   Risk Level: {risk_level}")
    print(f"   Sentiment: {sentiment}")

cursor.close()
db.close()

print("\n========== END OF REPORT ==========")