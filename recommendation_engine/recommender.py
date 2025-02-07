class Recommender:
    def get_recommendations(self, user_query):
        # Define categories of recommendations
        recommendations = {
            "machine learning": [
                "Machine Learning by Tom M. Mitchell",
                "Deep Learning by Ian Goodfellow",
                "Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow by Aurélien Géron"
            ],
            "python": [
                "Automate the Boring Stuff with Python by Al Sweigart",
                "Python Crash Course by Eric Matthes",
                "Fluent Python by Luciano Ramalho"
            ],
            "data science": [
                "Data Science for Business by Foster Provost",
                "Practical Statistics for Data Scientists by Peter Bruce",
                "Python for Data Analysis by Wes McKinney"
            ]
        }

        # Convert the query to lowercase for case-insensitive matching
        user_query_lower = user_query.lower()

        # Check if the query matches any predefined categories
        for key, rec_list in recommendations.items():
            if key in user_query_lower:
                return rec_list

        # If no match, return a default recommendation
        return ["No recommendations found for your query. Try a different topic."]
