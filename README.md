# AI Scam Shield - Unified Online Fraud Detection Platform

A working prototype covering:
1. **Fake Job Posting Detector** (ML - TF-IDF + Logistic Regression, with Explainable AI word-impact breakdown)
2. **Phishing Link Checker** (rule-based heuristics, works fully offline)
3. **Fake Offer Letter Checker** (rule-based: fee/deposit requests, urgency language, sender email domain, missing standard details)
4. **Fake UPI/Payment Screenshot Detector** (OCR + rule-based checks, supports both UPI and bank-transfer formats)
5. **Login / Register / Admin Panel** (session-based auth, first user = admin)
6. **History & Stats** (per-user) and **Model Comparison** (Logistic Regression vs Random Forest vs Naive Bayes)

---

## Step 1: Install Python requirements

```
pip install -r requirements.txt
```

## Step 2: Install Tesseract-OCR (only needed for the Screenshot module)

**Windows:** Download from https://github.com/UB-Mannheim/tesseract/wiki and install
(default path `C:\Program Files\Tesseract-OCR\tesseract.exe` is auto-detected).

If it's installed somewhere else, open `screenshot_checker.py` and add the exact
path to `pytesseract.pytesseract.tesseract_cmd`.

The other modules work without this - only the Screenshot tab needs it.

## Step 3: The Job Detector model is already trained

`model/job_model.pkl` is included. To retrain it:
```
python train_job_model.py
```

## Step 4: Generate the Model Comparison data

```
python compare_models.py
```
This trains 3 different algorithms (Logistic Regression, Random Forest, Naive
Bayes) on the same dataset and saves `model_comparison.json`, which powers the
"Model Comparison" tab in the dashboard. Run this once before starting the app
(re-run any time you regenerate the dataset).

## Step 5: Run the app

```
python app.py
```

Open **http://localhost:5000**. You'll land on a Login page - register an
account (the first account ever created automatically becomes Admin), then
log in.

---

## Project structure

```
ai_scam_shield/
├── app.py                      # Main Flask app - auth + all module routes
├── phishing_checker.py         # Phishing link heuristic engine
├── screenshot_checker.py       # OCR + rule-based screenshot checker (UPI + bank transfer)
├── offer_letter_checker.py     # Rule-based fake offer letter checker
├── explainable_ai.py           # Extracts word-level impact from the Job Detector model
├── train_job_model.py          # Trains the job posting model
├── compare_models.py           # Trains & compares 3 algorithms for the Job Detector
├── model_comparison.json       # Output of compare_models.py (used by dashboard)
├── requirements.txt
├── history.db                  # Auto-created SQLite DB (users + history)
├── uploads/                    # Temp folder for screenshots (auto-cleared)
├── data/
│   ├── generate_job_data.py
│   ├── job_postings.csv
│   └── convert_kaggle_dataset.py   # Optional: convert real Kaggle dataset
├── model/
│   └── job_model.pkl
└── templates/
    ├── login.html
    ├── register.html
    ├── index.html               # Dashboard (6 tabs)
    └── admin.html                # Admin-only panel
```

---

## Important note for your submission

The Job Detector's dataset is **synthetically generated** (see
`data/generate_job_data.py`), since a public dataset could not be
downloaded in the development environment. A small amount of random label
noise (5%) is intentionally added so results look like a realistic
dataset rather than a suspiciously perfect 100% - this is a standard
technique and is documented in the script itself.

If asked in your viva, be upfront: this is a synthetic dataset built with
realistic templates, not a downloaded public dataset. For a stronger
project, you can replace `data/job_postings.csv` with the Kaggle "Real/Fake
Job Postings" dataset (same column names) and re-run `train_job_model.py`
and `compare_models.py`.

The **Phishing Link Checker** and **Offer Letter Checker** are both
rule-based (not ML) and work fully offline with no dataset needed - this
is intentional and fine to present as-is; many real-world fraud filters
use heuristic rules exactly like this.

### Upgrading to the real Kaggle dataset (optional, needs internet)

1. Go to https://www.kaggle.com/datasets/shivamb/real-or-fake-fake-jobposting-prediction
   (free Kaggle account needed) and download `fake_job_postings.csv`
   (~17,880 real job postings, ~866 of them fraudulent).
2. Put the downloaded file in this project's `data/` folder.
3. Run:
   ```
   python data/convert_kaggle_dataset.py
   ```
   This converts Kaggle's column format into the one our scripts expect
   and overwrites `data/job_postings.csv` with real data.
4. Retrain on the real data:
   ```
   python train_job_model.py
   python compare_models.py
   ```
5. Restart the app (`python app.py`) - the Job Detector, its Explainable
   AI breakdown, and the Model Comparison tab will all now reflect the
   real dataset.

Note: the real dataset is heavily imbalanced (~95% genuine, ~5%
fraudulent), which is realistic but means accuracy alone can be
misleading - that's exactly why this project reports Precision, Recall,
and F1-Score too, not just Accuracy.

## Model Comparison - what it shows and why

`compare_models.py` trains **three different classifiers** (Logistic
Regression, Random Forest, Naive Bayes) on the exact same TF-IDF features
and the same train/test split, then reports Accuracy, Precision, Recall,
and F1-Score for each. This demonstrates that the algorithm used in the
live Job Detector (Logistic Regression) was chosen after comparing
alternatives - a standard, defensible ML methodology to describe in your
viva.

## Explainable AI - what it shows and why

For the Job Detector, `explainable_ai.py` extracts which specific words
in your input most influenced the model's decision, using the trained
Logistic Regression model's coefficients combined with each word's TF-IDF
weight. Words are shown as red (pushed towards Fraud) or green (pushed
towards Genuine) bars, sized by how much they contributed. This makes the
AI's decision transparent rather than a black box.

## Offer Letter Checker - what it looks for

Since fake offer letters follow a well-known scam pattern (a "selected!"
message followed by a demand for money before joining), this module uses
targeted rule-based checks rather than a generic ML model:
- Requests for a security deposit, registration/processing fee, or
  "joining kit" charge before you can start work (the single strongest
  signal - genuine employers never charge you to hire you).
- Urgency/pressure language pushing you to respond immediately.
- Requests for sensitive personal information (Aadhaar, bank details, OTP) upfront.
- Sender email from a personal domain (Gmail/Yahoo/etc.) instead of the
  company's own domain, if you provide the sender's email.
- Missing standard offer-letter details (reporting manager, work location, HR contact).
