import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Use the credentials we verified
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "awap.ai.tool@gmail.com"
SMTP_PASSWORD = "tjig hzla wijo oqmr"
SMTP_FROM = "awap.ai.tool@gmail.com"
TO_EMAIL = "rks.cybersec@gmail.com"

def test_send_pdf():
    # Find any pdf file in reports
    pdf_path = None
    for root, dirs, files in os.walk("reports"):
        for f in files:
            if f.endswith(".pdf"):
                pdf_path = os.path.join(root, f)
                break
        if pdf_path:
            break

    if not pdf_path:
        print("No PDF file found to test with.")
        return

    print(f"Testing sending email with PDF attachment: {pdf_path} (size: {os.path.getsize(pdf_path)} bytes)")

    try:
        msg = MIMEMultipart("mixed") # mixed for attachment
        msg["Subject"] = "AWAPT-AI PDF Attachment Test"
        msg["From"] = SMTP_FROM
        msg["To"] = TO_EMAIL

        # Body
        body = MIMEMultipart("alternative")
        body.attach(MIMEText("Plain text body", "plain"))
        body.attach(MIMEText("<html><body><h1>HTML body</h1></body></html>", "html"))
        msg.attach(body)

        # Attachment
        filename = os.path.basename(pdf_path)
        with open(pdf_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={filename}",
            )
            msg.attach(part)

        print("Connecting to SMTP...")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.set_debuglevel(1)
            server.connect(SMTP_HOST, SMTP_PORT)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            print("Sending email...")
            server.sendmail(SMTP_FROM, TO_EMAIL, msg.as_string())
            print("SUCCESS sending email with PDF!")

    except Exception as e:
        print("FAILED with error:", e)

if __name__ == "__main__":
    test_send_pdf()
