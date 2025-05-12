from flask import Flask, render_template, redirect, url_for
import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import re
import dateparser

app = Flask(__name__)

EMAIL = "shreelakshmisomshekar@gmail.com"
PASSWORD = "app password"

def categorize(subject, body):
    combined = (subject + " " + body).lower()
    if "internship" in combined:
        return "Internship"
    elif "full time" in combined or "full-time" in combined or "job" in combined:
        return "Full-time Job"
    elif "hackathon" in combined:
        return "Hackathon"
    elif any(k in combined for k in ["apply", "register", "opportunity", "opening", "recruitment", "role"]):
        return "Other Opportunities"
    else:
        return "Ignore"

def clean_email_body(raw_html):
    soup = BeautifulSoup(raw_html, 'html.parser')
    for tag in soup(["style", "script", "head", "meta", "title"]):
        tag.decompose()
    body = soup.body or soup
    text = body.get_text(separator="\n").strip()

    keywords = ['deadline', 'apply', 'CTC', 'salary', 'last date', 'job', 'internship']
    for kw in keywords:
        regex = re.compile(rf'\b({kw})\b', re.IGNORECASE)
        text = regex.sub(
            r'<span style="background: #fff3cd; color: #a76f00; font-weight: bold;">\1</span>', text)
    text = re.sub(r'(https?://[^\s]+)',
                  r'<a href="\1" target="_blank" style="color:#4b0082; text-decoration:underline;">\1</a>', text)
    return text

def fetch_emails():
    results = []
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(EMAIL, PASSWORD)
    imap.select("inbox")

    status, messages = imap.search(None, "ALL")
    email_ids = messages[0].split()

    for eid in email_ids[-50:]:
        _, msg_data = imap.fetch(eid, "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8", errors="ignore")
        from_ = msg.get("From")
        received = msg.get("Date", "Unknown")
        body = ""
        plain_text_body = ""
        app_link = "Not provided"
        deadline = "Not found"
        eligibility = "Not mentioned"

        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == "text/html":
                    raw_html = part.get_payload(decode=True).decode(errors="ignore")
                    soup = BeautifulSoup(raw_html, "html.parser")
                    plain_text_body = soup.get_text(separator="\n").strip()
                    body = clean_email_body(raw_html)
                    break
                elif ctype == "text/plain" and not plain_text_body:
                    plain_text_body = part.get_payload(decode=True).decode(errors="ignore")
                    body = clean_email_body(plain_text_body)
        else:
            raw_text = msg.get_payload(decode=True).decode(errors="ignore")
            plain_text_body = BeautifulSoup(raw_text, "html.parser").get_text(separator="\n").strip()
            body = clean_email_body(raw_text)

        # Extract apply link
        link_match = re.search(r'https?://[a-zA-Z0-9./?=_%-]+', body)
        if link_match:
            extracted_link = link_match.group(0)
            if "http" in extracted_link and "." in extracted_link:
                app_link = extracted_link

        # Deadline Extraction: keyword-based first
        found = False
        for line in plain_text_body.splitlines():
            for kw in ["deadline", "apply before", "last date", "register by", "before"]:
                if kw in line.lower():
                    parsed = dateparser.parse(line, settings={'PREFER_DATES_FROM': 'future'})
                    if parsed:
                        deadline = parsed.strftime("%d/%m/%Y")
                        found = True
                        break
            if found:
                break

        # If no keyword-based date, try any date
        if deadline == "Not found":
            for line in plain_text_body.splitlines():
                parsed = dateparser.parse(line, settings={'PREFER_DATES_FROM': 'future'})
                if parsed:
                    deadline = parsed.strftime("%d/%m/%Y")
                    break

        # Eligibility
        elig_match = re.search(r'(eligibility[^:\n]*[:\n])(.+)', body, re.IGNORECASE)
        if elig_match:
            eligibility = elig_match.group(2).strip()

        category = categorize(subject, body)

        if category != "Ignore":
            results.append({
                "title": subject.strip(),
                "from": from_,
                "received": received,
                "description": body,
                "deadline": deadline,
                "eligibility": eligibility,
                "application_link": app_link,
                "category": category
            })
            print(f"[DEBUG] {subject} → Deadline: {deadline}")

    imap.logout()
    return results

email_cache = []

@app.route('/')
def home():
    return render_template('landing.html')

@app.route('/analyze')
def analyze():
    global email_cache
    email_cache = fetch_emails()
    return redirect(url_for('show_categories'))

@app.route('/categories')
def show_categories():
    predefined = ["Internship", "Full-time Job", "Hackathon", "Other Opportunities"]
    category_counts = {cat: 0 for cat in predefined}

    for email in email_cache:
        cat = email["category"]
        if cat in category_counts:
            category_counts[cat] += 1
        else:
            category_counts["Other Opportunities"] += 1

    total = len(email_cache)
    return render_template("categories.html", category_counts=category_counts, total=total)

@app.route('/opportunities/<category>')
def show_opportunities(category):
    filtered = [e for e in email_cache if e["category"] == category]
    return render_template("opportunities.html", opportunities=filtered, category=category)

if __name__ == '__main__':
    app.run(debug=True)
