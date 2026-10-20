"""
Phishing Link Checker - rule-based heuristic engine.
No external API key required, works fully offline.
"""
import re
from urllib.parse import urlparse

SUSPICIOUS_TLDS = [".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".work", ".click", ".loan", ".win"]
URL_SHORTENERS = ["bit.ly", "tinyurl.com", "shorturl.at", "t.co", "is.gd", "goo.gl", "rebrand.ly"]
BRAND_KEYWORDS = ["paypal", "amazon", "flipkart", "google", "facebook", "instagram",
                  "sbi", "hdfc", "icici", "axisbank", "netflix", "microsoft", "apple",
                  "whatsapp", "irctc", "incometax"]


def check_link(raw_url):
    reasons = []
    score = 0

    url = raw_url.strip()
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    try:
        parsed = urlparse(url)
    except Exception:
        return {"result": "Invalid URL", "score": 0, "reasons": ["Could not parse the URL."]}

    domain = parsed.netloc.lower()
    full_url = url.lower()

    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", domain):
        reasons.append("Domain is a raw IP address instead of a proper website name.")
        score += 35

    if "@" in url:
        reasons.append("URL contains an '@' symbol, often used to hide the real destination.")
        score += 30

    if not url.startswith("https://"):
        reasons.append("Connection is not secured with HTTPS.")
        score += 10

    subdomain_count = domain.count(".")
    if subdomain_count >= 3:
        reasons.append("URL has an unusually high number of subdomains.")
        score += 20

    if domain.count("-") >= 2:
        reasons.append("Domain contains multiple hyphens, a common typosquatting pattern.")
        score += 15

    if any(domain.endswith(tld) for tld in SUSPICIOUS_TLDS):
        reasons.append("Domain uses a top-level domain (TLD) frequently linked to scam sites.")
        score += 25

    if any(short in domain for short in URL_SHORTENERS):
        reasons.append("This is a shortened URL - the real destination is hidden.")
        score += 20

    if len(url) > 90:
        reasons.append("URL is unusually long, which can be used to obscure the real domain.")
        score += 10

    for brand in BRAND_KEYWORDS:
        if brand in full_url:
            root_domain_parts = domain.split(".")
            is_root = brand in root_domain_parts
            if not is_root:
                reasons.append(f"Mentions the brand '{brand}' but it does not appear to be the official domain.")
                score += 25
            break

    score = min(score, 100)

    if score >= 60:
        result = "Malicious"
    elif score >= 25:
        result = "Suspicious"
    else:
        result = "Safe"

    if not reasons:
        reasons.append("No common phishing red flags detected in this URL.")

    return {"result": result, "score": score, "reasons": reasons, "checked_url": url}
