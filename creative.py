import psycopg2
import psycopg2.extras
from psycopg2 import sql
from marketer import support


# ---------- Database Connection ----------
def get_connection():
    return psycopg2.connect(
        host="localhost",
        port = 5433,
        user="postgres",
        password="root",
        dbname="test"
    )


# ---------- Creative Menu ----------
def creative_menu(user):
    while True:
        print(f"\n-- Welcome {user['name']} (Creative) --")
        print("1. Create/Update Profile")
        print("2. View My Profile")
        print("3. Set Availability")
        print("4. View & Manage Bookings")
        print("5. Raise a Ticket")
        print("6. Logout")
        choice = input("Enter choice: ")

        if choice == '1':
            create_or_update_profile(user)
        elif choice == '2':
            view_profile(user)
        elif choice == '3':
            set_availability(user)
        elif choice == '4':
            manage_bookings(user)
        elif choice == '5':
            support(user)
        elif choice == '6':
            print("Logged out.")
            break
        else:
            print("Invalid choice.")


# ---------- Create or Update Profile ----------
def create_or_update_profile(user):
    try:
        con = get_connection()
        cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("SELECT * FROM creative_profiles WHERE user_id=%s", (user['id'],))
        profile = cur.fetchone()

        if profile:
            # Show current details
            print("\nCurrent Profile:")
            for key in ("category", "skills", "location", "portfolio_links", "availability"):
                if key in profile:
                    print(f"{key}: {profile.get(key)}")

            do_update = input("Do you want to update your profile? (y/N): ").strip().lower()
            if do_update != 'y':
                print("No changes made.")
                return

            # Show available categories
            cur.execute("SELECT category_id, name FROM categories ORDER BY category_id")
            cats = cur.fetchall()
            if cats:
                print("\nAvailable Categories:")
                id_width = max(len("ID"), max(len(str(c['category_id'])) for c in cats))
                name_width = max(len("Name"), max(len(c['name']) for c in cats))
                sep = "+-" + ("-" * id_width) + "-+-" + ("-" * name_width) + "-+"
                header = f"| {'ID'.ljust(id_width)} | {'Name'.ljust(name_width)} |"
                print(sep)
                print(header)
                print(sep)
                for c in cats:
                    print(f"| {str(c['category_id']).ljust(id_width)} | {c['name'].ljust(name_width)} |")
                print(sep)
                cid = input(f"Enter category ID to select (blank to keep '{profile.get('category','')}'): ").strip()
                if cid == "":
                    category = profile.get('category')
                elif cid.isdigit() and int(cid) != 0:
                    match = next((c for c in cats if c['category_id'] == int(cid)), None)
                    if match:
                        category = match['name']
                    else:
                        print("Invalid category ID. Keeping existing category.")
                        category = profile.get('category')
                else:
                    print("Invalid input. Keeping existing category.")
                    category = profile.get('category')
            else:
                # No categories available; fallback to free text
                category = input(f"Enter your category [{profile.get('category','')}]: ").strip() or profile.get('category')

            # Skills prompt (blank keeps current)
            skills = input(f"Enter your skills (comma separated) [{profile.get('skills','')}]: ").strip() or profile.get('skills')

            # Show available locations
            cur.execute("SELECT DISTINCT location FROM creative_profiles WHERE location IS NOT NULL ORDER BY location")
            locs = [r['location'] for r in cur.fetchall()]
            if locs:
                print("\nAvailable Locations:")
                for idx, loc in enumerate(locs, start=1):
                    print(f"{idx}. {loc}")
                lsel = input(f"Enter location number to select (blank to keep '{profile.get('location','')}'): ").strip()
                if lsel == "":
                    location = profile.get('location')
                elif lsel.isdigit() and 1 <= int(lsel) <= len(locs):
                    location = locs[int(lsel) - 1]
                else:
                    print("Invalid selection. Keeping existing location.")
                    location = profile.get('location')
            else:
                location = input(f"Location [{profile.get('location','')}]: ").strip() or profile.get('location')

            portfolio_links = input(f"Portfolio Links [{profile.get('portfolio_links','')}]: ").strip() or profile.get('portfolio_links')

            cur.execute("""
                UPDATE creative_profiles 
                SET category=%s, skills=%s, location=%s, portfolio_links=%s
                WHERE user_id=%s
            """, (category, skills, location, portfolio_links, user['id']))

        else:
            # No profile yet: create one. Show categories and locations to choose from.
            cur.execute("SELECT category_id, name FROM categories ORDER BY category_id")
            cats = cur.fetchall()
            category = ''
            if cats:
                print("\nAvailable Categories:")
                id_width = max(len("ID"), max(len(str(c['category_id'])) for c in cats))
                name_width = max(len("Name"), max(len(c['name']) for c in cats))
                sep = "+-" + ("-" * id_width) + "-+-" + ("-" * name_width) + "-+"
                header = f"| {'ID'.ljust(id_width)} | {'Name'.ljust(name_width)} |"
                print(sep)
                print(header)
                print(sep)
                for c in cats:
                    print(f"| {str(c['category_id']).ljust(id_width)} | {c['name'].ljust(name_width)} |")
                print(sep)
                cid = input("Enter category ID to select (0 for custom / blank to skip): ").strip()
                if cid.isdigit() and int(cid) != 0:
                    match = next((c for c in cats if c['category_id'] == int(cid)), None)
                    if match:
                        category = match['name']
                elif cid == '0':
                    category = input("Enter custom category: ").strip()
            else:
                category = input("Enter your category (e.g., Video Editor): ").strip()

            skills = input("Enter your skills (comma separated): ").strip()

            # Locations
            cur.execute("SELECT DISTINCT location FROM creative_profiles WHERE location IS NOT NULL ORDER BY location")
            locs = [r['location'] for r in cur.fetchall()]
            location = ''
            if locs:
                print("\nAvailable Locations:")
                for idx, loc in enumerate(locs, start=1):
                    print(f"{idx}. {loc}")
                lsel = input("Enter location number to select (0 for custom / blank to skip): ").strip()
                if lsel.isdigit() and int(lsel) != 0:
                    if 1 <= int(lsel) <= len(locs):
                        location = locs[int(lsel) - 1]
                elif lsel == '0':
                    location = input("Enter custom location: ").strip()
            else:
                location = input("Location: ").strip()

            portfolio_links = input("Portfolio Links: ").strip()

            cur.execute("""
                INSERT INTO creative_profiles (user_id, category, skills, location, portfolio_links)
                VALUES (%s, %s, %s, %s, %s)
            """, (user['id'], category, skills, location, portfolio_links))

        con.commit()
        print("Profile saved.")
    except psycopg2.Error as e:
        print("Database error:", e)
    finally:
        if 'cur' in locals() and cur:
            cur.close()
        if 'con' in locals() and con:
            con.close()


# ---------- View Profile ----------
def view_profile(user):
    try:
        con = get_connection()
        cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("SELECT * FROM creative_profiles WHERE user_id=%s", (user['id'],))
        profile = cur.fetchone()
        if profile:
            print("\nYour Profile:")
            for key, value in profile.items():
                print(f"{key}: {value}")
        else:
            print("No profile found.")
    except psycopg2.Error as e:
        print("Database error:", e)
    finally:
        cur.close()
        con.close()


# ---------- Set Availability ----------
def set_availability(user):
    status = input("Set availability (yes/no): ").lower() == 'yes'

    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("UPDATE creative_profiles SET availability=%s WHERE user_id=%s", (status, user['id']))
        con.commit()
        print("Availability updated.")
    except psycopg2.Error as e:
        print("Database error:", e)
    finally:
        cur.close()
        con.close()


# ---------- Manage Bookings ----------
def manage_bookings(user):
    try:
        con = get_connection()
        cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("""
            SELECT b.booking_id, m.name AS marketer_name, b.status, b.note, b.created_at, b.scheduled_date
            FROM bookings b
            JOIN users1 m ON m.id = b.marketer_id
            WHERE b.creative_id = %s
            ORDER BY b.created_at DESC
        """, (user['id'],))

        bookings = cur.fetchall()

        if not bookings:
            print("\nNo bookings yet.")
            return

        print("\nYour Bookings:")
        for b in bookings:
            sched = b.get('scheduled_date') if isinstance(b, dict) or hasattr(b, 'get') else None
            # If scheduled_date not present or None, fall back to created_at
            date_str = sched if sched else b.get('created_at') if hasattr(b, 'get') else ''
            print(f"ID: {b['booking_id']} | Marketer: {b['marketer_name']} | "
                  f"Status: {b['status']} | Note: {b['note']} | Scheduled: {date_str}")

        try:
            booking_id = int(input("\nEnter Booking ID to manage (0 to go back): "))
        except ValueError:
            print("Invalid input.")
            return

        if booking_id == 0:
            return

        # Verify booking belongs to this creative
        cur.execute("SELECT status FROM bookings WHERE booking_id=%s AND creative_id=%s",
                    (booking_id, user['id']))
        booking = cur.fetchone()

        if not booking:
            print("Booking not found or not yours.")
            return

        if booking['status'] == 'pending':
            # pending: allow accept or reject
            print("\n1. Accept Booking")
            print("2. Reject Booking")
            action = input("Choose action: ")

            if action == "1":
                cur.execute("""
                    UPDATE bookings 
                    SET status='accepted' 
                    WHERE booking_id=%s AND creative_id=%s
                """, (booking_id, user['id']))
                con.commit()
                print(f"Booking {booking_id} accepted.")

                # Optional: mark creative unavailable
                cur.execute("UPDATE creative_profiles SET availability=FALSE WHERE user_id=%s", (user['id'],))
                con.commit()

            elif action == "2":
                cur.execute("""
                    UPDATE bookings 
                    SET status='rejected' 
                    WHERE booking_id=%s AND creative_id=%s
                """, (booking_id, user['id']))
                con.commit()
                print(f"Booking {booking_id} rejected.")
            else:
                print("Invalid choice.")

        elif booking['status'] == 'accepted':
            # accepted: allow marking as completed
            print("\n1. Mark as completed")
            print("2. Back")
            action = input("Choose action: ")
            if action == "1":
                cur.execute("""
                    UPDATE bookings SET status='completed' WHERE booking_id=%s AND creative_id=%s
                """, (booking_id, user['id']))
                if cur.rowcount > 0:
                    con.commit()
                    print(f"Booking {booking_id} marked as completed.")
                    # Optionally mark creative available again
                    cur.execute("UPDATE creative_profiles SET availability=TRUE WHERE user_id=%s", (user['id'],))
                    con.commit()
                else:
                    print("Unable to mark booking as completed.")
            else:
                print("Back to bookings list.")

        else:
            print(f"Booking is already {booking['status']}.")
            return

        print("\n1. Accept Booking")
        print("2. Reject Booking")
        print("3. Chat with Marketer")
        action = input("Choose action: ")

        if action == "1":
            cur.execute("""
                UPDATE bookings 
                SET status='accepted' 
                WHERE booking_id=%s AND creative_id=%s
            """, (booking_id, user['id']))
            con.commit()
            print(f"Booking {booking_id} accepted.")

            # Optional: mark creative unavailable
            cur.execute("UPDATE creative_profiles SET availability=FALSE WHERE user_id=%s", (user['id'],))
            con.commit()

        elif action == "2":
            cur.execute("""
                UPDATE bookings 
                SET status='rejected' 
                WHERE booking_id=%s AND creative_id=%s
            """, (booking_id, user['id']))
            con.commit()
            print(f"Booking {booking_id} rejected.")
        elif action == "3":
            # Chat with marketer before accepting/rejecting
            try:
                from chat import chat_interface
                # Pass the creative user and booking id to the chat interface
                chat_interface(user, booking_id)
            except Exception as e:
                print("Unable to open chat:", e)
        else:
            print("Invalid choice.")

    except psycopg2.Error as e:
        print("Database error:", e)
    finally:
        cur.close()
        con.close()
