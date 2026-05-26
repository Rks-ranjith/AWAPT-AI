import smtplib
from email.mime.text import MIMEText

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "awap.ai.tool@gmail.com"
SMTP_PASSWORD = "tjig hzla wijo oqmr"
SMTP_FROM = "awap.ai.tool@gmail.com"
TO_EMAIL = "rks.cybersec@gmail.com"

def test_smtp():
    print("Testing SMTP connection to smtp.gmail.com:587...")
    try:
        msg = MIMEText("This is a test email from AWAPT-AI to verify SMTP credentials.")
        msg["Subject"] = "AWAPT-AI SMTP Test"
        msg["From"] = SMTP_FROM
        msg["To"] = TO_EMAIL
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.set_debuglevel(1)
            print("Connecting...")
            server.connect(SMTP_HOST, SMTP_PORT)
            print("EHLO...")
            server.ehlo()
            print("StartTLS...")
            server.starttls()
            print("EHLO after TLS...")
            server.ehlo()
            print("Logging in...")
            server.login(SMTP_USER, SMTP_PASSWORD)
            print("Sending mail...")
            server.sendmail(SMTP_FROM, TO_EMAIL, msg.as_string())
            print("SUCCESS!")
    except Exception as e:
        print("FAILED with error:", e)

if __name__ == "__main__":
    test_smtp()
