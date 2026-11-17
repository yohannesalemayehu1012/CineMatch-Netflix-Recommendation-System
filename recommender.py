"""Content-based Netflix title recommender using TF-IDF and cosine similarity."""
from pathlib import Path
import re
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from difflib import get_close_matches

TEXT_COLUMNS = ["director", "cast", "listed_in", "description", "country"]

class NetflixRecommender:
    def __init__(self, csv_path: Path):
        if not Path(csv_path).exists():
            raise FileNotFoundError(f"Dataset not found: {csv_path}")
        self.data = pd.read_csv(csv_path).fillna("")
        self.data["title"] = self.data["title"].astype(str)
        self.data["release_year"] = pd.to_numeric(self.data["release_year"], errors="coerce")
        self.data["search_title"] = self.data["title"].map(self._normalize)
        self.data["content"] = self.data.apply(self._build_content, axis=1)
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2),
                                          min_df=1, max_features=45000, sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform(self.data["content"])
        self._title_to_indices = self.data.groupby("search_title").indices
        self.stats = {
            "titles": int(len(self.data)),
            "movies": int((self.data["type"] == "Movie").sum()),
            "shows": int((self.data["type"] == "TV Show").sum()),
            "genres": int(self.available_genres_count()),
        }

    @staticmethod
    def _normalize(value):
        return re.sub(r"[^a-z0-9]+", "", str(value).lower())

    @staticmethod
    def _clean(value):
        if isinstance(value, list):
            value = " ".join(value)
        return re.sub(r"[^a-zA-Z0-9 ]", " ", str(value)).lower()

    def _build_content(self, row):
        parts = [self._clean(row.get(col, "")) for col in TEXT_COLUMNS]
        # Genre and cast/director terms are represented alongside the synopsis.
        return " ".join(parts)

    def _record(self, row, score=None):
        year = row.get("release_year", "")
        return {
            "title": str(row.get("title", "Untitled")),
            "type": str(row.get("type", "")),
            "year": int(year) if pd.notna(year) and year != "" else "",
            "rating": str(row.get("rating", "Not rated")) or "Not rated",
            "duration": str(row.get("duration", "")),
            "genres": [x.strip() for x in str(row.get("listed_in", "")).split(",") if x.strip()],
            "description": str(row.get("description", "")),
            "director": str(row.get("director", "")),
            "cast": [x.strip() for x in str(row.get("cast", "")).split(",") if x.strip()][:5],
            "country": str(row.get("country", "")),
            "score": round(float(score) * 100, 1) if score is not None else None,
        }

    def find_title(self, title):
        key = self._normalize(title)
        if not key:
            return None
        indices = self._title_to_indices.get(key)
        if indices is None:
            return None
        return self._record(self.data.iloc[int(indices[0])])

    def search_titles(self, query, limit=8):
        q = self._normalize(query)
        if not q:
            return []
        titles = self.data[["title", "type", "release_year"]].drop_duplicates("title")
        exact = titles[titles["title"].map(self._normalize).str.contains(q, regex=False)]
        rows = exact.head(limit).to_dict("records")
        return [{"title": r["title"], "type": r["type"],
                 "year": int(r["release_year"]) if pd.notna(r["release_year"]) and r["release_year"] != "" else ""}
                for r in rows]

    def recommend(self, title, limit=12, kind="All", genre="All"):
        key = self._normalize(title)
        indices = self._title_to_indices.get(key)
        if indices is None:
            return []
        source_idx = int(indices[0])
        similarities = cosine_similarity(self.matrix[source_idx], self.matrix).ravel()
        ranked = similarities.argsort()[::-1]
        output = []
        for idx in ranked:
            if idx == source_idx or similarities[idx] <= 0:
                continue
            row = self.data.iloc[int(idx)]
            if kind != "All" and row["type"] != kind:
                continue
            row_genres = str(row.get("listed_in", ""))
            if genre != "All" and genre.lower() not in row_genres.lower():
                continue
            output.append(self._record(row, similarities[idx]))
            if len(output) >= max(1, min(int(limit), 30)):
                break
        return output

    def featured_titles(self, limit=8):
        # A deterministic sample of recognizable, non-empty catalog entries.
        sample = self.data[self.data["description"].astype(str).str.len() > 40].sort_values(
            ["release_year", "title"], ascending=[False, True]).head(limit)
        return [self._record(row) for _, row in sample.iterrows()]

    def available_genres(self):
        genres = set()
        for value in self.data["listed_in"].astype(str):
            genres.update(x.strip() for x in value.split(",") if x.strip())
        return sorted(genres)

    def available_genres_count(self):
        return len(self.available_genres())
