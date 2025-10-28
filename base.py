import psycopg2
import smtplib
import random
import getpass
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from psycopg2 import sql
from admin import admin_login



# --- DB Config ---
DB_CONFIG = {
    "host": "localhost",
    "port" : 5433,
    "database": "test",
    "user": "postgres",
    "password": "root"
}

def get_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except psycopg2.Error as e:
        print("Database connection failed:", e)
        return None


# --- Email validation function ---
def is_valid_email(email):
    pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    # Basic pattern check
    if re.match(pattern, email) is None:
        return False

    # Reject consecutive dots anywhere in the address
    if '..' in email:
        return False

    # Reject leading/trailing dot in local or domain parts
    try:
        local, domain = email.rsplit('@', 1)
    except ValueError:
        return False
    if local.startswith('.') or local.endswith('.') or domain.startswith('.') or domain.endswith('.'):
        return False

    return True


# ---------- Register ----------
def register():
    print("\n-- Register User --")
    name = input("Enter your name: ").strip()
    email = input("Enter your email: ").strip()

    if not is_valid_email(email):
        print("Invalid email format. Please enter a valid email.")
        return

    while True:
        password = getpass.getpass("Enter your password: ")
        confirm_password = getpass.getpass("Confirm your password: ")
        if password == confirm_password:
            break
        print("⚠ Passwords do not match. Try again.")

    role = input("Enter your role (creative/marketer): ").strip().lower()
    portfolio_link = input("Enter your portfolio link: ").strip()

    # Generate OTP
    otp = str(random.randint(100000, 999999))
    
    # Send OTP Email
    sender_email = "creativeconnectproject@gmail.com"
    sender_password = "mxth cdzx qnrs wdto"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = email
    message["Subject"] = "Your OTP Verification Code"
    message.attach(MIMEText(f"Hello {name},\n\nYour OTP is {otp}.\nIt will expire in 5 minutes.", "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, email, message.as_string())
        server.quit()
        print(f"OTP sent to {email}")
    except Exception as e:
        print("Error sending email:", e)
        return

    user_otp = input("Enter the OTP you received: ").strip()
    if user_otp != otp:
        print("Invalid OTP. Registration failed.")
        return

    con = None
    cur = None
    try:
        con = psycopg2.connect(**DB_CONFIG)
        cur = con.cursor()

        insert_query = sql.SQL("""
            INSERT INTO users1 (name, email, password, verified, role, portfolio_link, approved)
            VALUES (%s, %s, %s, TRUE, %s, %s, FALSE)
        """)
        cur.execute(insert_query, (name, email, password, role, portfolio_link))
        con.commit()
        print("OTP Verified! Your account is pending admin approval.")

    except Exception as e:
        print("Database error:", e)
    finally:
        if cur:
            cur.close()
        if con:
            con.close()

# ---------- Login ----------
def login():
    print("\n-- Login User --")
    max_attempts = 3
    attempts = 0

    while attempts < max_attempts:
        email = input("Email (or 'q' to cancel): ").strip()
        if email.lower() == 'q':
            print("Login cancelled.")
            return
        password = getpass.getpass("Password: ")

        try:
            con = get_connection()
            if not con:
                print("❌ Cannot connect to database.")
                return

            cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)

            cur.execute("SELECT * FROM users1 WHERE email=%s AND password=%s", (email, password))
            user = cur.fetchone()

            if user:
                if not user['approved']:
                    print("Your account is pending approval by the admin.")
                    return
                elif user['role'] == 'creative':
                    from creative import creative_menu
                    print("Login successful!")
                    creative_menu(user)
                    return
                elif user['role'] == 'marketer':
                    from marketer import marketer_menu
                    print("Login successful!")
                    marketer_menu(user)
                    return
                else:
                    print("Login successful!")
                    return
            else:
                attempts += 1
                remaining = max_attempts - attempts
                if remaining > 0:
                    print(f"Invalid credentials. You have {remaining} attempt(s) left.")
                    continue
                else:
                    print("Invalid credentials. No attempts left.")
                    return

        except psycopg2.Error as e:
            print("Database error:", e)
            return
        finally:
            if 'cur' in locals() and cur:
                cur.close()
            if 'con' in locals() and con:
                con.close()


# ---------- Main Menu ----------
def start():
    while True:
        print("--- Welcome to Creative Connect ---")
        print("1. Register\n2. Login\n3. Login as admin\n4. Exit")

        try:
            choice = int(input("Enter your choice: "))
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue

        if choice == 1:
            register()
        elif choice == 2:
            login()
        elif choice == 3:
            admin_login()
        elif choice == 4:
            print("Goodbye.")
            break
        else:
            print("Choose a valid option.")


if __name__ == "__main__":
    start()
