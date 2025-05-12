import imaplib
import email
from email.header import decode_header
from textblob import TextBlob

EMAIL = "shreelakshmisomshekar@gmail.com"
PASSWORD = "app password"  # Your app password

KEYWORDS = ["hackathon", "internship", "full time job"]

imap = imaplib.IMAP4_SSL("imap.gmail.com")
imap.login(EMAIL, PASSWORD)
imap.select("inbox")

# Search all emails
status, messages = imap.search(None, "ALL")
email_ids = messages[0].split()
total_emails = len(email_ids)
matched_emails = 0

print(f"🔍 Analyzing {total_emails} emails...\n")

# Analyze last 50 emails (adjust if needed)
for eid in email_ids[-50:]:
    _, msg_data = imap.fetch(eid, "(RFC822)")
    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8", errors="ignore")

    from_ = msg.get("From")

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
                except:
                    pass
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")

    # Combine subject + body for keyword search
    combined_text = (subject + " " + body).lower()
    if any(keyword in combined_text for keyword in KEYWORDS):
        matched_emails += 1
        print(f"\n📩 Match Found!")
        print(f"From: {from_}")
        print(f"Subject: {subject}")
        print(f"Body Preview: {body[:150].strip()}...")
        blob = TextBlob(body)
        print(f"Sentiment → Polarity: {blob.sentiment.polarity:.2f}, Subjectivity: {blob.sentiment.subjectivity:.2f}")
        print("-" * 60)

imap.logout()

print(f"\n✅ Done. Total emails scanned: {total_emails}")
print(f"🔎 Emails matching keywords ({', '.join(KEYWORDS)}): {matched_emails}")
