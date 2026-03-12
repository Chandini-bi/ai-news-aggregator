import requests
import mysql.connector
import time
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ==========================
# CONFIGURATION
# ==========================

API_KEY = "YOUR_API_KEY"
MYSQL_PASSWORD = "Chandini.25"

analyzer = SentimentIntensityAnalyzer()

# Risk keyword weights
risk_keywords = {
    "war": 30, "nuclear": 35, "military": 20, "conflict": 20, "attack": 25,
    "sanctions": 15, "terrorism": 40, "missile": 25, "border": 15, "defense": 10
}

# Sector classification keywords
sector_keywords = {
    "defence": ["military", "war", "army", "navy", "airforce", "missile"],
    "economy": ["economy", "inflation", "gdp", "market", "stocks"],
    "energy": ["oil", "gas", "energy", "renewable", "electricity"],
    "technology": ["technology", "ai", "cyber", "software", "chip"],
    "health": ["health", "pandemic", "vaccine", "disease"],
    "security": ["terror", "attack", "security", "border"],
}

# ==========================
# CONTINUOUS FETCH LOOP
# ==========================
print("\n[INIT] Starting Continuous Geopolitical News Fetcher.")
print("The script will fetch news every 30 minutes.")
print("Press CTRL+C to stop.\n")

while True:
    try:
        # Re-establish DB connection inside the loop to prevent connection timeouts over long periods.
        db = mysql.connector.connect(
            host="localhost", user="root", password=MYSQL_PASSWORD, database="geopolitical_news"
        )
        cursor = db.cursor()

        url = f"https://newsapi.org/v2/everything?q=geopolitics OR war OR military OR economy OR energy OR security OR technology&language=en&sortBy=publishedAt&pageSize=100&apiKey={API_KEY}"
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fetching & Analyzing News...")
        
        response = requests.get(url)
        data = response.json()
        articles = data.get("articles", [])
        
        inserted_count = 0
        duplicate_count = 0

        for article in articles:
            try:
                title = article.get("title") or ""
                content = article.get("description") or ""
                news_url = article.get("url")
                source = article.get("source", {}).get("name")
                published_at_raw = article.get("publishedAt")

                if published_at_raw:
                    published_at = datetime.strptime(published_at_raw, "%Y-%m-%dT%H:%M:%SZ")
                else:
                    published_at = None

                text = (title + " " + content).lower()

                # Sector Detection
                sector = "general"
                for key, words in sector_keywords.items():
                    for word in words:
                        if word in text:
                            sector = key
                            break
                    if sector != "general": break

                # Sentiment Analysis
                sentiment_score = analyzer.polarity_scores(text)
                if sentiment_score["compound"] >= 0.05:
                    sentiment = "Positive"
                    sentiment_modifier = -10
                elif sentiment_score["compound"] <= -0.05:
                    sentiment = "Negative"
                    sentiment_modifier = 20
                else:
                    sentiment = "Neutral"
                    sentiment_modifier = 5

                # Risk Calculation
                keyword_score = sum(weight for word, weight in risk_keywords.items() if word in text)
                risk_score = max(0, min(100, keyword_score + sentiment_modifier))

                if risk_score <= 25: risk_level = "LOW"
                elif risk_score <= 50: risk_level = "MEDIUM"
                elif risk_score <= 75: risk_level = "HIGH"
                else: risk_level = "CRITICAL"

                # Insert into DB
                sql = """
                INSERT INTO news 
                (title, content, url, source, published_at, sentiment, risk_score, risk_level, sector)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (title, content, news_url, source, published_at, sentiment, risk_score, risk_level, sector)
                cursor.execute(sql, values)
                db.commit()
                inserted_count += 1

            except mysql.connector.errors.IntegrityError:
                duplicate_count += 1
            except Exception as e:
                pass # Skip problematic individual articles

        cursor.close()
        db.close()

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Cycle Complete.")
        print(f"   -> Inserted: {inserted_count} new articles.")
        print(f"   -> Skipped (duplicates): {duplicate_count}")
        print("Sleeping for 30 minutes before the next fetch...\n")
        
        # Sleep for 30 minutes
        time.sleep(1800)

    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fatal Loop Error: {e}")
        print("Retrying in 60 seconds...\n")
        time.sleep(60)