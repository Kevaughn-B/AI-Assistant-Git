from serpapi import GoogleSearch
import os
class Recommender:

    def search_google(self, query):
        params = {
            "q": query,
            "api_key": os.environ.get("SERPAPI_KEY"),
            "num": 5
        }

        search = GoogleSearch(params)
        results = search.get_dict()

        output = []
        for r in results.get("organic_results", []):
            output.append({
                "title": r.get("title"),
                "link": r.get("link"),
                "type": "Google Search"
            })

        return output

    def rank_results(self, results, query):
        ranked = []

        for r in results:
            score = 0

            if query.lower() in r["title"].lower():
                score += 2

            if r["type"] == "Google Books":
                score += 3

            ranked.append((score, r))

        ranked.sort(reverse=True, key=lambda x: x[0])

        return [r[1] for r in ranked]

    def get_recommendations(self, query, local_results, book_results):
        google_results = self.search_google(query)

        combined = google_results + book_results + local_results

        ranked = self.rank_results(combined, query)

        return ranked