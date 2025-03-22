import os
import json
import threading
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ✅ Load Firebase credentials from Render environment variable
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

if firebase_credentials:
    cred_dict = json.loads(firebase_credentials)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    raise ValueError("🚨 FIREBASE_CREDENTIALS environment variable is missing!")

# ✅ GNews API Configuration
API_KEY = "97cc71ff679acf43dea029763925f7d3"  # Replace with your actual API key
NEWS_URL = f"https://gnews.io/api/v4/top-headlines?category=business&lang=en&country=in&max=10&apikey={API_KEY}"

# ✅ Fetch News from API and Store in Firebase
def update_news():
    try:
        response = requests.get(NEWS_URL)
        if response.status_code == 200:
            news_data = response.json().get("articles", [])

            if not news_data:
                print("❌ No news data retrieved")
                return

            # ✅ Delete old news before updating (to avoid duplicates)
            news_ref = db.collection("news")
            docs = news_ref.stream()
            for doc in docs:
                doc.reference.delete()

            # ✅ Store new articles
            for i, article in enumerate(news_data):
                news_doc = {
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "url": article.get("url", ""),
                    "image": article.get("image", ""),
                    "publishedAt": article.get("publishedAt", ""),
                    "source": article.get("source", {}).get("name", ""),
                }
                db.collection("news").document(f"news_{i}").set(news_doc)

            print("✅ News updated successfully!")
        else:
            print(f"❌ GNews API Error: {response.status_code} - {response.text}")

    except Exception as e:
        print("❌ Error updating news:", str(e))

    # ✅ Schedule Next Update (Every 15 Minutes)
    threading.Timer(900, update_news).start()  # 900 seconds = 15 minutes

# ✅ Start Background News Update Task
update_news()

@app.route('/')
def home():
    return "✅ News API with Firestore is Running!"

@app.route('/update-news')
def manual_update():
    try:
        update_news()
        return jsonify({"message": "✅ News updated successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/news')
def get_news():
    try:
        docs = db.collection("news").stream()
        news_list = [doc.to_dict() for doc in docs]
        return jsonify(news_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
