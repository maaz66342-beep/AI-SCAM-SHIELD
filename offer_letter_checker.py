"""
Fake Offer Letter Checker.

Fake/fraudulent offer letters are a common scam after fake interviews -
scammers send a "selected!" letter and then ask for a security deposit,
registration fee, or laptop/kit charge before the person can "join".

Detection uses a mix of:
  - Flexible REGEX patterns (so wording variations like "registration and
    joining charges" are caught, not just exact phrases like
    "registration fee").
  - A keyword list as a second layer for common fixed terms.
This two-layer approach avoids missing real-world scam letters that don't
use the exact same wording every time.
"""
import re

# Catches "pay ... fee/charge/deposit/amount/money" in any order/wording,
# e.g. "pay Rs. 3,500 registration and joining charges",
# "you have to pay a security deposit", "pay processing amount".
FEE_REQUEST_REGEX = re.compile(
    r"\bpay\b[^.]{0,60}?\b(fee|fees|charge|charges|deposit|amount|token|bond|money)\b",
    re.IGNORECASE,
)
# Also catches the reverse order: "registration charges of Rs.3500" / "a refundable deposit of Rs.2000"
FEE_REQUEST_REGEX_2 = re.compile(
    r"\b(registration|processing|joining|security|refundable|training|documentation|activation|confirmation)\b[^.]{0,20}?\b(fee|fees|charge|charges|deposit|amount)\b",
    re.IGNORECASE,
)
# Explicit fixed phrases as a fallback/extra layer
FEE_REQUEST_KEYWORDS = [
    "security deposit", "registration fee", "processing fee", "processing charge",
    "refundable deposit", "joining fee", "training fee", "documentation fee",
    "laptop kit", "joining kit", "courier charge", "confirm your seat",
    "activation fee", "send the payment screenshot", "send payment screenshot",
]

URGENCY_REGEX = re.compile(
    r"\b(within\s+\d+\s*(hours?|hrs?|days?)|immediately|urgent(ly)?|act\s+now|"
    r"right\s+now|as\s+soon\s+as\s+possible|asap|today\s+only|expires?\s+(today|soon))\b",
    re.IGNORECASE,
)

# Catches variations like "Aadhaar Card", "Aadhar number", "PAN Card",
# "bank details", "bank account", "ATM pin", sharing OTP, etc.
SENSITIVE_INFO_REGEX = re.compile(
    r"\b(aadhaar|aadhar|pan\s*card|bank\s*(details|account)|atm\s*pin|otp|"
    r"credit\s*card\s*number|debit\s*card\s*number|\bcvv\b)\b",
    re.IGNORECASE,
)

PERSONAL_EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "rediffmail.com"]

MISSING_DETAIL_CHECKS = {
    "reporting_manager": ["reporting manager", "report to", "reporting to"],
    "work_location": ["work location", "office address", "location:"],
    "hr_contact": ["hr department", "human resources", "contact person", "hr manager"],
}


def check_offer_letter(text, sender_email=""):
    reasons = []
    score = 0
    text_lower = text.lower()

    # 1. Fee/payment requests - the single strongest fraud signal for offer letters.
    #    Combine regex matches + fixed keyword matches so both exact phrases
    #    and flexible real-world wording are caught.
    fee_hits = set()
    m = FEE_REQUEST_REGEX.search(text)
    if m:
        fee_hits.add(m.group(0).strip())
    m2 = FEE_REQUEST_REGEX_2.search(text)
    if m2:
        fee_hits.add(m2.group(0).strip())
    for kw in FEE_REQUEST_KEYWORDS:
        if kw in text_lower:
            fee_hits.add(kw)

    if fee_hits:
        sample = list(fee_hits)[:3]
        reasons.append(
            f"Asks for payment before joining (\"{', '.join(sample)}\") - "
            "legitimate companies never charge a fee to hire you."
        )
        score += 50

    # 2. Urgency / pressure tactics
    if URGENCY_REGEX.search(text):
        reasons.append("Uses urgency/pressure language (e.g. a tight deadline or 'immediately') to rush your decision.")
        score += 20

    # 3. Requests for sensitive personal info upfront
    sensitive_matches = set(m.group(0).lower() for m in SENSITIVE_INFO_REGEX.finditer(text))
    if sensitive_matches:
        reasons.append(f"Requests sensitive personal information upfront ({', '.join(list(sensitive_matches)[:3])}).")
        score += 25

    # 4. Sender email uses a personal/free domain instead of a company domain
    if sender_email:
        domain = sender_email.strip().lower().split("@")[-1]
        if any(domain == pd for pd in PERSONAL_EMAIL_DOMAINS):
            reasons.append(
                f"Sent from a personal email domain ({domain}) instead of an official "
                "company email address - genuine offer letters come from the company's domain."
            )
            score += 30

    # 5. Missing standard offer-letter details (weak signal, small penalty)
    missing = []
    for label, keywords in MISSING_DETAIL_CHECKS.items():
        if not any(kw in text_lower for kw in keywords):
            missing.append(label.replace("_", " "))
    if len(missing) >= 2:
        reasons.append(
            f"Missing standard offer-letter details typically included: {', '.join(missing)}."
        )
        score += 10

    score = min(score, 100)

    if score >= 55:
        result = "Likely Fake"
    elif score >= 25:
        result = "Needs Manual Verification"
    else:
        result = "Likely Genuine"

    if not reasons:
        reasons.append("No common offer-letter scam patterns detected.")

    return {"result": result, "score": score, "reasons": reasons}
