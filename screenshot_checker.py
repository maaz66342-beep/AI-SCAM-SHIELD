"""
Fake UPI / Payment Screenshot Detector.
Uses OCR (pytesseract) to read text from an uploaded screenshot, then
applies rule-based checks to flag likely-fake payment screenshots.

Supports TWO payment formats:
  1. UPI payments (PhonePe/GPay/Paytm style) - identified by a UPI ID
     like "name@bankhandle".
  2. Bank transfers (NEFT/IMPS/RTGS) - identified by bank-transfer
     keywords (account number, IFSC, banking name, NEFT/IMPS/RTGS)
     instead of a UPI ID.
A screenshot only needs to look complete for WHICHEVER format it is -
a genuine bank transfer is not penalised for not having a UPI ID.
"""
import re
import os

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True

    _common_windows_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for _path in _common_windows_paths:
        if os.path.isfile(_path):
            pytesseract.pytesseract.tesseract_cmd = _path
            break

except ImportError:
    OCR_AVAILABLE = False

KNOWN_SCAM_UPI_IDS = [
    "refund.help@oksbi", "support.kyc@okaxis", "prize.winner@okicici",
    "job.registration@paytm", "cashback.offer@ybl",
]

UPI_PATTERN = re.compile(r"[\w.\-]{2,}@[a-zA-Z]{2,}")

# ₹ is very commonly misread by OCR as ¥, %, Z, 2, or dropped entirely.
# We treat any of those symbols directly touching a number as a possible
# amount too, in addition to the normal Rs./INR/₹ forms.
AMOUNT_PATTERN = re.compile(r"(?:rs\.?|inr|₹|rupees|¥|%(?=\s?\d))\s?([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)
AMOUNT_FALLBACK_PATTERN = re.compile(
    r"(?:amount|paid|total)\D{0,15}([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE
)
# A bare "20.00" / "2,500.00" style number (2 decimal places) anywhere in
# the text is also a strong signal of a payment amount, even with no
# label nearby - real payment apps almost always show paise/cents.
AMOUNT_BARE_PATTERN = re.compile(r"\b(\d{1,3}(?:,\d{3})*\.\d{2})\b")

TXN_ID_PATTERN = re.compile(r"\b(?:txn|transaction|utr|ref)[\s.:#no]*([a-zA-Z0-9]{8,})\b", re.IGNORECASE)
TXN_ID_FALLBACK_PATTERN = re.compile(r"\b(\d{10,22})\b")

BANK_TRANSFER_MARKERS = [
    "neft", "imps", "rtgs", "ifsc", "account number", "a/c no", "a/c number",
    "bank transfer", "banking name", "account no",
]


def extract_text_from_image(image_path):
    if not OCR_AVAILABLE:
        raise RuntimeError(
            "OCR engine not available. Install pytesseract + Tesseract-OCR "
            "(see README.md) to use this module."
        )
    img = Image.open(image_path)
    try:
        text = pytesseract.image_to_string(img)
    except pytesseract.TesseractNotFoundError:
        raise RuntimeError(
            "Tesseract-OCR is installed but this app could not find "
            "tesseract.exe automatically. Open screenshot_checker.py and "
            "set pytesseract.pytesseract.tesseract_cmd to the exact path "
            "of your tesseract.exe."
        )
    return text


def analyze_screenshot(image_path):
    reasons = []
    score = 0

    try:
        text = extract_text_from_image(image_path)
    except RuntimeError as e:
        return {"result": "Error", "score": 0, "reasons": [str(e)], "extracted_text": ""}

    text_lower = text.lower()

    upi_ids = UPI_PATTERN.findall(text)

    amounts = AMOUNT_PATTERN.findall(text)
    if not amounts:
        amounts = AMOUNT_FALLBACK_PATTERN.findall(text)
    if not amounts:
        amounts = AMOUNT_BARE_PATTERN.findall(text)

    txn_ids = TXN_ID_PATTERN.findall(text)
    if not txn_ids:
        txn_ids = TXN_ID_FALLBACK_PATTERN.findall(text)

    is_bank_transfer = any(marker in text_lower for marker in BANK_TRANSFER_MARKERS)

    # --- UPI ID check: only penalise a missing UPI ID if this does NOT
    # look like a bank-transfer screenshot instead. ---
    if not upi_ids and not is_bank_transfer:
        reasons.append("No UPI ID could be detected in the screenshot text.")
        score += 30
    elif not upi_ids and is_bank_transfer:
        reasons.append("This looks like a bank transfer (not UPI) - checked for bank details instead of a UPI ID.")

    normalized_text = re.sub(r"[\s.]+", ".", text_lower)
    for scam_id in KNOWN_SCAM_UPI_IDS:
        if scam_id.lower() in normalized_text:
            reasons.append(f"Text closely matches a known reported scam UPI handle ('{scam_id}').")
            score += 45
            break

    if not txn_ids:
        reasons.append("No transaction ID / UTR number could be detected.")
        score += 20

    if not amounts:
        reasons.append("No payment amount could be clearly detected in the image.")
        score += 15

    fake_markers = ["screenshot", "sample", "demo", "template", "watermark"]
    for marker in fake_markers:
        if marker in text_lower:
            reasons.append(f"The word '{marker}' was found in the image text, which is unusual for a real payment screenshot.")
            score += 25

    score = min(score, 100)

    if score >= 55:
        result = "Likely Fake"
    elif score >= 25:
        result = "Needs Manual Verification"
    else:
        result = "Likely Genuine"

    if not reasons:
        reasons.append("No red flags detected. Payment details all look present.")

    return {
        "result": result,
        "score": score,
        "reasons": reasons,
        "extracted_text": text.strip(),
        "detected_upi_ids": upi_ids,
        "detected_amounts": amounts,
        "is_bank_transfer": is_bank_transfer,
    }
