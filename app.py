from flask import Flask, render_template, request, jsonify
from recommender import NetflixRecommender
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = Path(os.getenv("NETFLIX_DATA_PATH", BASE_DIR / "data" / "netflix_titles.csv"))

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
recommender = NetflixRecommender(DATA_PATH)

@app.get("/")
def home():
    stats = recommender.stats
    featured = recommender.featured_titles(8)
    genres = recommender.available_genres()
    return render_template("index.html", stats=stats, featured=featured, genres=genres)

@app.get("/recommend")
def recommend():
    title = request.args.get("title", "").strip()
    kind = request.args.get("type", "All")
    genre = request.args.get("genre", "All")
    limit = request.args.get("limit", 12, type=int)
    if not title:
        return render_template("index.html", stats=recommender.stats,
                               featured=recommender.featured_titles(8),
                               genres=recommender.available_genres(),
                               error="Enter a movie or show title to get recommendations.")
    match = recommender.find_title(title)
    if match is None:
        suggestions = recommender.search_titles(title, 5)
        return render_template("index.html", stats=recommender.stats,
                               featured=recommender.featured_titles(8),
                               genres=recommender.available_genres(),
                               error="We couldn't find that exact title. Try one of these suggestions:",
                               suggestions=suggestions, query=title)
    recommendations = recommender.recommend(match["title"], limit=limit, kind=kind, genre=genre)
    return render_template("results.html", selected=match,
                           recommendations=recommendations,
                           genres=recommender.available_genres(),
                           result_count=len(recommendations))

@app.get("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    return jsonify(recommender.search_titles(q, 8) if len(q) >= 2 else [])

@app.get("/api/recommendations/<path:title>")
def api_recommendations(title):
    match = recommender.find_title(title)
    if match is None:
        return jsonify({"error": "Title not found"}), 404
    return jsonify({"selected": match, "recommendations": recommender.recommend(title)})

@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG") == "1")
