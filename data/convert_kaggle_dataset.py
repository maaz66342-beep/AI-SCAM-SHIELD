"""
Converts the Kaggle "[Real or Fake] Fake Job Posting Prediction" dataset
(by Shivam Bansal) into the column format our train_job_model.py and
compare_models.py scripts expect.

HOW TO USE:
1. Download 'fake_job_postings.csv' from:
   https://www.kaggle.com/datasets/shivamb/real-or-fake-fake-jobposting-prediction
   (You'll need a free Kaggle account to download it.)
2. Put the downloaded 'fake_job_postings.csv' file in this project's
   'data/' folder.
3. Run: python data/convert_kaggle_dataset.py
   This creates data/job_postings.csv (real data), replacing the
   synthetic one.
4. Retrain everything on the real data:
   python train_job_model.py
   python compare_models.py
"""
import pandas as pd
import os

RAW_PATH = os.path.join(os.path.dirname(__file__), "fake_job_postings.csv")
OUT_PATH = os.path.join(os.path.dirname(__file__), "job_postings.csv")

if not os.path.exists(RAW_PATH):
    print(f"ERROR: Could not find {RAW_PATH}")
    print("Download 'fake_job_postings.csv' from Kaggle first (see instructions")
    print("at the top of this script) and place it in the data/ folder.")
    raise SystemExit(1)

df = pd.read_csv(RAW_PATH)

# The Kaggle dataset's raw columns don't exactly match ours, so we map them:
#   title              -> title
#   company_profile    -> company (it's a text blurb, not a clean name, but
#                          it's the closest available field)
#   description        -> description
#   salary_range       -> salary
#   requirements       -> requirements
#   fraudulent         -> fraudulent (already 0/1, same as ours)
out = pd.DataFrame({
    "title": df["title"].fillna(""),
    "company": df["company_profile"].fillna("").str.slice(0, 100),  # trim long profiles
    "description": df["description"].fillna(""),
    "salary": df["salary_range"].fillna(""),
    "requirements": df["requirements"].fillna(""),
    "fraudulent": df["fraudulent"],
})

# Drop rows with no meaningful text at all (a few rows in the raw dataset are near-empty)
out = out[(out["title"].str.len() > 0) | (out["description"].str.len() > 0)]

out.to_csv(OUT_PATH, index=False)

print(f"Converted {len(out)} rows -> {OUT_PATH}")
print(f"Genuine: {(out['fraudulent'] == 0).sum()}  |  Fraudulent: {(out['fraudulent'] == 1).sum()}")
print("\nNext steps:")
print("  python train_job_model.py")
print("  python compare_models.py")
