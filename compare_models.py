"""
Model Comparison Script - trains 3 different ML algorithms on the SAME
job posting dataset and compares their performance.

This demonstrates that the final model choice (Logistic Regression) was
picked after comparing alternatives, not arbitrarily.

Run: python compare_models.py
Output: prints a comparison table AND saves model_comparison.json
        (used by the "Model Comparison" tab in the dashboard)
"""
import json
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

df = pd.read_csv("data/job_postings.csv")
df["text"] = (
    df["title"].fillna("") + " " + df["company"].fillna("") + " " +
    df["description"].fillna("") + " " + df["salary"].fillna("") + " " +
    df["requirements"].fillna("")
)
X, y = df["text"], df["fraudulent"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# The 3 algorithms we're comparing - all get the SAME TF-IDF features,
# so the comparison is fair (only the classifier changes).
models = {
    "Logistic Regression": LogisticRegression(max_iter=1000),
    "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
    "Naive Bayes": MultinomialNB(),
}

results = []
print(f"{'Algorithm':<22}{'Accuracy':<12}{'Precision':<12}{'Recall':<12}{'F1-Score':<10}")
print("-" * 68)

for name, clf in models.items():
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(stop_words="english", max_features=3000, ngram_range=(1, 2))),
        ("clf", clf),
    ])
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    print(f"{name:<22}{acc*100:>6.2f}%     {prec*100:>6.2f}%     {rec*100:>6.2f}%     {f1*100:>6.2f}%")

    results.append({
        "name": name,
        "accuracy": round(acc * 100, 2),
        "precision": round(prec * 100, 2),
        "recall": round(rec * 100, 2),
        "f1_score": round(f1 * 100, 2),
    })

# Sort so the best model (by F1-score) is listed first
results.sort(key=lambda r: r["f1_score"], reverse=True)

with open("model_comparison.json", "w") as f:
    json.dump(results, f, indent=2)

print("\nBest model (by F1-Score):", results[0]["name"])
print("Saved comparison to model_comparison.json")
