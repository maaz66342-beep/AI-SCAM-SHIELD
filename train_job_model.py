import pandas as pd
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

df = pd.read_csv("data/job_postings.csv")
df["text"] = (
    df["title"].fillna("") + " " + df["company"].fillna("") + " " +
    df["description"].fillna("") + " " + df["salary"].fillna("") + " " +
    df["requirements"].fillna("")
)
X, y = df["text"], df["fraudulent"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(stop_words="english", max_features=3000, ngram_range=(1, 2))),
    ("clf", LogisticRegression(max_iter=1000)),
])
pipeline.fit(X_train, y_train)

y_pred = pipeline.predict(X_test)
print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nConfusion Matrix:\n", confusion_matrix(y_test, y_pred))
print("\nClassification Report:\n", classification_report(y_test, y_pred, target_names=["Genuine", "Fraudulent"]))

with open("model/job_model.pkl", "wb") as f:
    pickle.dump(pipeline, f)
print("\nModel saved to model/job_model.pkl")
