import smtplib

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_PASSWORD = "tjig hzla wijo oqmr"

variations = [
    "awap.ai.tool@gmail.com",
    "awap.ai.toolgmail@gmail.com",
    "awap.ai.tool.gmail@gmail.com",
    "awap.aitool@gmail.com"
]

def test_variations():
    for email in variations:
        print(f"Testing {email}...")
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(email, SMTP_PASSWORD)
                print(f"SUCCESS! Username is: {email}")
                return
        except Exception as e:
            print(f"Failed for {email}: {e}")

if __name__ == "__main__":
    test_variations()
