"""
Explainable AI helper.

For a Logistic Regression model trained on TF-IDF features, each feature
(word/phrase) has a learned coefficient. A positive coefficient pushes the
prediction towards class 1 (Fraud/Scam); a negative coefficient pushes it
towards class 0 (Genuine).

For a given input, we find which of ITS words/phrases actually appear in
the TF-IDF vocabulary, multiply each one's TF-IDF weight by its model
coefficient, and return the top contributing words in each direction.
This gives a simple, honest "why did the model decide this" explanation -
it is not a full SHAP/LIME implementation, but it accurately reflects
what a linear model is actually doing internally.
"""


def explain_prediction(pipeline, text, top_n=5):
    tfidf = pipeline.named_steps["tfidf"]
    clf = pipeline.named_steps["clf"]

    # Only works for linear models that expose coef_ (Logistic Regression).
    if not hasattr(clf, "coef_"):
        return {"fraud_words": [], "genuine_words": []}

    feature_names = tfidf.get_feature_names_out()
    coefficients = clf.coef_[0]

    vector = tfidf.transform([text])
    nonzero_indices = vector.nonzero()[1]

    contributions = []
    for idx in nonzero_indices:
        word = feature_names[idx]
        tfidf_weight = vector[0, idx]
        contribution = tfidf_weight * coefficients[idx]
        contributions.append((word, contribution))

    # Positive contribution = pushed towards Fraud/Scam (class 1)
    # Negative contribution = pushed towards Genuine (class 0)
    fraud_words = sorted([c for c in contributions if c[1] > 0], key=lambda x: -x[1])[:top_n]
    genuine_words = sorted([c for c in contributions if c[1] < 0], key=lambda x: x[1])[:top_n]

    return {
        "fraud_words": [{"word": w, "weight": round(float(v), 4)} for w, v in fraud_words],
        "genuine_words": [{"word": w, "weight": round(float(abs(v)), 4)} for w, v in genuine_words],
    }
