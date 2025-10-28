import psycopg2
import psycopg2.extras
from datetime import datetime
from psycopg2 import sql


# ---------- Database Connection ----------
def get_connection():
    try:
        return psycopg2.connect(
            host="localhost",
            port = 5433,                     
            user="postgres",
            password="root",
            dbname="test"
        )
    except psycopg2.Error as e:
        print(f"Database connection failed: {e}")
        return None


# ---------- Chat Interface ----------
def chat_interface(user, booking_id):
    with get_connection() as con:
        cursor = con.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Allow chat when booking exists and is either pending or accepted
        cursor.execute("SELECT * FROM bookings WHERE booking_id=%s AND status IN ('pending','accepted')", (booking_id,))
        booking = cursor.fetchone()
        if not booking:
            print("⚠ Chat not available for this booking.")
            return

        # Ensure the user is a participant in the booking (creative or marketer)
        if user.get('id') not in (booking.get('creative_id'), booking.get('marketer_id')):
            print("⚠ You are not a participant in this booking.")
            return

        print("\n--- Chat Session ---")
        while True:
            # Show last 5 messages
            cursor.execute("""
                SELECT cm.message_id, u.name, cm.message, cm.created_at
                FROM chat_messages cm
                JOIN users1 u ON cm.sender_id = u.id
                WHERE cm.booking_id=%s
                ORDER BY cm.created_at DESC
                LIMIT 5
            """, (booking_id,))
            messages = cursor.fetchall()

            print("\nRecent messages:")
            if not messages:
                print("No messages yet.")
            else:
                for msg in reversed(messages):
                    print(f"[{msg['created_at']}] {msg['name']}: {msg['message']}")

            print("\nOptions: 1. Send message  2. Refresh  3. Exit chat")
            action = input("Choose: ").strip()

            if action == "1":
                msg = input("Enter your message: ").strip()
                if msg:
                    cursor.execute("""
                        INSERT INTO chat_messages (booking_id, sender_id, message, created_at)
                        VALUES (%s, %s, %s, %s)
                    """, (booking_id, user['id'], msg, datetime.now()))
                    con.commit()
                    print("Message sent.")
            elif action == "2":
                continue
            elif action == "3":
                print("Exiting chat...")
                break
            else:
                print("Invalid choice.")
