import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# ---------- Send Email Helper ----------
def send_email(to_email, subject, body):
    sender_email = "creativeconnectproject@gmail.com"
    sender_password = "mxth cdzx qnrs wdto"   # Gmail app password (never use your actual Gmail password)

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, message.as_string())
        print(f"📧 Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Error sending email to {to_email}: {e}")
        return False
