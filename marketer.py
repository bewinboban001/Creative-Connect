import psycopg2
import psycopg2.extras
import getpass
from datetime import datetime, date, timedelta
import calendar
import webbrowser

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except Exception:
    HAS_TABULATE = False


# ---------- Database Connection ----------
def get_connection():
    return psycopg2.connect(
        host="localhost",
        port = 5433,
        user="postgres",
        password="root",
        dbname="test"
    )


# ---------- Utility ----------
def _print_rows(rows, headers):
    if not rows:
        print("No records found.")
        return
    if HAS_TABULATE:
        try:
            # tabulate expects headers for a list of dicts to be a dict or the keyword "keys".
            # Detect mapping-like rows (psycopg2 DictRow behaves like a dict) and use headers="keys".
            first = rows[0]
            is_mapping = hasattr(first, 'keys') or hasattr(first, 'items')
            if is_mapping:
                print(tabulate(rows, headers="keys", tablefmt="psql"))
            else:
                print(tabulate(rows, headers=headers, tablefmt="psql"))
        except Exception:
            # Fallback: convert mapping rows to list-of-lists using provided headers
            print(" | ".join(headers))
            print("-" * (len(headers) * 8))
            for r in rows:
                try:
                    # r may be a mapping (DictRow) or a sequence
                    if hasattr(r, 'get'):
                        print(" | ".join([str(r.get(h, "")) for h in headers]))
                    else:
                        print(" | ".join([str(x) for x in r]))
                except Exception:
                    print(r)
    else:
        print(" | ".join(headers))
        print("-" * (len(headers) * 8))
        for r in rows:
            print(" | ".join([str(r.get(h, "")) for h in headers]))


def _input_nonempty(prompt):
    while True:
        val = input(prompt).strip()
        if val:
            return val
        print("This field cannot be empty.")


# ---------- Marketer Menu ----------
def marketer_menu(user):
    while True:
        print(f"\n-- Welcome {user['name']} (Marketer) --")
        print("1. Search by Category/Location")
        print("2. Booking/Cancellation Option")
        print("3. Add Review")
        print("4. History")
        print("5. Raise a Ticket")
        print("6. Logout")
        choice = input("Enter choice: ")

        if choice == '1':
            search_creatives()
        elif choice == '2':
            book_creative(user)
        elif choice == '3':
            add_review(user)
        elif choice == '4':
            view_history(user)
        elif choice == '5':
            support(user)
        elif choice == '6':
            print("Logged out.")
            break
        else:
            print("Invalid choice.")


# ---------- Search Creatives ----------
def search_creatives():
    print("\n-- Search Creatives --")
    availability = input("Availability (yes/no, blank to skip): ").strip().lower()

    # We'll let the user pick a category from the categories table (or skip)
    con = None
    cur = None
    try:
        con = get_connection()
        cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Fetch categories
        cur.execute("SELECT category_id, name FROM categories ORDER BY category_id")
        cats = cur.fetchall()
        selected_category = None
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

            cid = input("Enter category ID to filter (0 to skip): ").strip()
            if cid.isdigit() and int(cid) != 0:
                cid = int(cid)
                match = next((c for c in cats if c['category_id'] == cid), None)
                if match:
                    selected_category = match['name']
                else:
                    print("Invalid category ID selected. Continuing without category filter.")

        else:
            print("No categories defined. You can still search by location or availability.")

        # Fetch distinct locations from creative_profiles
        cur.execute("SELECT DISTINCT location FROM creative_profiles WHERE location IS NOT NULL ORDER BY location")
        locs = [r['location'] for r in cur.fetchall()]
        selected_location = None
        if locs:
            print("\nAvailable Locations:")
            for idx, loc in enumerate(locs, start=1):
                print(f"{idx}. {loc}")
            lsel = input("Enter location number to filter (0 to skip): ").strip()
            if lsel.isdigit() and int(lsel) != 0:
                lsel_i = int(lsel)
                if 1 <= lsel_i <= len(locs):
                    selected_location = locs[lsel_i - 1]
                else:
                    print("Invalid location selection. Continuing without location filter.")

        # Build query
        query = """
            SELECT 
                u.id AS user_id, u.name, u.email,
                c.category, c.skills, c.location, 
                c.portfolio_links, c.availability
            FROM users1 u
            JOIN creative_profiles c ON u.id = c.user_id
            WHERE u.role = 'creative' AND u.approved = TRUE
        """
        params = []
        if selected_category:
            query += " AND c.category = %s"
            params.append(selected_category)
        if selected_location:
            query += " AND c.location = %s"
            params.append(selected_location)
        if availability in ("yes", "no"):
            query += " AND c.availability = %s"
            params.append(availability == "yes")

        cur.execute(query, params)
        rows = cur.fetchall()
        headers = ["user_id", "name", "email", "category", "skills", "location", "portfolio_links", "availability"]
        _print_rows(rows, headers)

    except psycopg2.Error as e:
        print("Database error:", e)
    finally:
        if cur:
            cur.close()
        if con:
            con.close()


# ---------- Booking / Cancellation ----------
def book_creative(marketer):
    print("\n-- Book a Creative --")

    try:
        con = get_connection()
        cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # List available creatives
        cur.execute("""
            SELECT u.id AS user_id, u.name, c.category, c.skills, c.location, 
                   c.availability, c.portfolio_links
            FROM users1 u
            JOIN creative_profiles c ON u.id = c.user_id
            WHERE u.role = 'creative' AND u.approved = TRUE AND c.availability = TRUE
        """)
        creatives = cur.fetchall()

        if not creatives:
            print("No creatives available right now.")
            return

        print("\nAvailable Creatives:")
        headers = ["user_id", "name", "category", "skills", "location", "availability", "portfolio_links"]
        _print_rows(creatives, headers)

        print("\nWhat would you like to do?")
        print("1. Book a creative")
        print("2. Cancel a booking")
        print("3. Chat with a creative")
        choice = input("Enter choice (1/2/3): ").strip()

        # ---------- Booking ----------
        if choice == "1":
            try:
                creative_id = int(_input_nonempty("\nEnter creative user_id to book: "))
            except ValueError:
                print("Please enter a valid numeric user_id.")
                return

            # Validate creative
            cur.execute("""
                SELECT u.id, c.portfolio_links
                FROM users1 u 
                JOIN creative_profiles c ON u.id = c.user_id 
                WHERE u.id=%s AND u.role='creative' AND u.approved=TRUE
            """, (creative_id,))
            creative = cur.fetchone()
            if not creative:
                print("Creative not found or not approved.")
                return

            # Show booking history
            cur.execute("""
                SELECT b.booking_id, b.status, b.created_at, m.name AS marketer_name
                FROM bookings b
                JOIN users1 m ON m.id = b.marketer_id
                WHERE b.creative_id = %s
                ORDER BY b.created_at DESC
            """, (creative_id,))
            history = cur.fetchall()
            print("\nPrevious Bookings for this Creative:")
            headers = ["booking_id", "status", "created_at", "marketer_name"]
            _print_rows(history, headers)

            # Open portfolio if available
            if creative.get("portfolio_links"):
                print(f"\nOpening portfolio: {creative['portfolio_links']}")
                webbrowser.open(creative["portfolio_links"])
            else:
                print("\nNo portfolio link found.")

            # Insert new booking
            # Choose booking date: show next 30 days and mark dates already booked
            # Ensure bookings table has 'scheduled_date' column (add if missing)
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='bookings' AND column_name='scheduled_date'")
                col = cur.fetchone()
                if not col:
                    try:
                        cur.execute("ALTER TABLE bookings ADD COLUMN scheduled_date DATE")
                        con.commit()
                    except Exception:
                        # if alter fails, continue; we'll attempt inserts without scheduled_date
                        pass
            except Exception:
                pass

            # If creative has global availability flag false, block booking
            cur.execute("SELECT availability FROM creative_profiles WHERE user_id=%s", (creative_id,))
            av = cur.fetchone()
            if av and not av.get('availability', True):
                print("This creative is currently marked unavailable.")
                return

            # Build next 30 days list
            days = [date.today() + timedelta(days=i) for i in range(0, 30)]
            end_date = days[-1]

            # Query existing bookings for this creative with scheduled_date in the next 30 days
            cur.execute("SELECT scheduled_date FROM bookings WHERE creative_id=%s AND status IN ('pending','accepted') AND scheduled_date IS NOT NULL", (creative_id,))
            taken = {r['scheduled_date'] for r in cur.fetchall() if r.get('scheduled_date')}

            # Display calendar(s) for the months covering the next 30 days
            print("\nSelect a date for the booking (dates marked ' X' are unavailable)")
            months = []
            start_month = date.today().replace(day=1)
            # collect unique (year, month) pairs covering the range
            ym = set((d.year, d.month) for d in days)
            months = sorted(list(ym))

            for (y, m) in months:
                cal = calendar.monthcalendar(y, m)
                month_name = calendar.month_name[m]
                print(f"\n   {month_name} {y}")
                print("Mo Tu We Th Fr Sa Su")
                for week in cal:
                    line_parts = []
                    for daynum in week:
                        if daynum == 0:
                            line_parts.append("   ")
                        else:
                            d = date(y, m, daynum)
                            if d < date.today() or d > end_date:
                                line_parts.append(" . ")
                            elif d in taken:
                                line_parts.append(" X ")
                            else:
                                line_parts.append(str(daynum).rjust(2) + " ")
                    print(" ".join(line_parts))

            # Prompt for a date input in ISO format
            choice_date = input("\nEnter the desired date (YYYY-MM-DD) or 0 to cancel: ").strip()
            if choice_date == "0":
                print("Booking cancelled.")
                return
            try:
                scheduled = date.fromisoformat(choice_date)
            except Exception:
                print("Invalid date format. Use YYYY-MM-DD.")
                return

            if scheduled < date.today() or scheduled > end_date:
                print("Selected date is outside the allowed booking window.")
                return
            if scheduled in taken:
                print("Selected date is not available.")
                return

            note = input("\nShort brief for booking (optional): ").strip()

            # Attempt to insert with scheduled_date; if column missing fall back
            try:
                cur.execute("INSERT INTO bookings (marketer_id, creative_id, status, note, created_at, scheduled_date) VALUES (%s, %s, 'pending', %s, %s, %s)", (marketer["id"], creative_id, note, datetime.now(), scheduled))
            except Exception:
                cur.execute("INSERT INTO bookings (marketer_id, creative_id, status, note, created_at) VALUES (%s, %s, 'pending', %s, %s)", (marketer["id"], creative_id, note, datetime.now()))
            con.commit()
            print(f"Booking request sent for {scheduled.isoformat()} (status: pending).")

        # ---------- Cancellation ----------
        elif choice == "2":
            cur.execute("""
                SELECT b.booking_id, c.name AS creative_name, b.status, b.created_at
                FROM bookings b
                JOIN users1 c ON c.id = b.creative_id
                WHERE b.marketer_id = %s
                ORDER BY b.created_at DESC
            """, (marketer["id"],))
            bookings = cur.fetchall()

            if not bookings:
                print("You have no bookings to cancel.")
                return

            print("\nYour Current Bookings:")
            headers = ["booking_id", "creative_name", "status", "created_at"]
            _print_rows(bookings, headers)

            try:
                booking_id = int(_input_nonempty("\nEnter booking_id to cancel: "))
            except ValueError:
                print("Please enter a valid numeric booking_id.")
                return

            cur.execute("""
                UPDATE bookings SET status='cancelled' 
                WHERE booking_id=%s AND marketer_id=%s
            """, (booking_id, marketer["id"]))
            if cur.rowcount > 0:
                con.commit()
                print(f"Booking {booking_id} cancelled.")
            else:
                print("Invalid booking_id or not your booking.")

        elif choice == "3":
            try:
                creative_id = int(_input_nonempty("\nEnter creative user_id to chat with: "))
            except ValueError:
                print("Please enter a valid numeric user_id.")
                return

            # Validate creative exists and is approved
            cur.execute("""
                SELECT u.id, c.portfolio_links
                FROM users1 u 
                JOIN creative_profiles c ON u.id = c.user_id 
                WHERE u.id=%s AND u.role='creative' AND u.approved=TRUE
            """, (creative_id,))
            creative = cur.fetchone()
            if not creative:
                print("Creative not found or not approved.")
                return

            # Check for existing pending/accepted booking between this marketer and creative
            cur.execute("""
                SELECT booking_id FROM bookings
                WHERE creative_id=%s AND marketer_id=%s AND status IN ('pending','accepted')
                ORDER BY created_at DESC LIMIT 1
            """, (creative_id, marketer["id"]))
            bk = cur.fetchone()
            if bk:
                booking_id = bk["booking_id"]
                try:
                    from chat import chat_interface
                    chat_interface(marketer, booking_id)
                except Exception as e:
                    print("Unable to open chat:", e)
            else:
                do_create = input("No booking exists with this creative. Create a pending booking to enable chat? (y/N): ").strip().lower()
                if do_create == 'y':
                    note = input("Short brief for booking (optional): ").strip()
                    cur.execute("""
                        INSERT INTO bookings (marketer_id, creative_id, status, note, created_at)
                        VALUES (%s, %s, 'pending', %s, %s)
                        RETURNING booking_id
                    """, (marketer["id"], creative_id, note, datetime.now()))
                    newbk = cur.fetchone()
                    con.commit()
                    if newbk:
                        booking_id = newbk["booking_id"]
                        print(f"Pending booking {booking_id} created. Opening chat...")
                        try:
                            from chat import chat_interface
                            chat_interface(marketer, booking_id)
                        except Exception as e:
                            print("Unable to open chat:", e)
                    else:
                        print("Failed to create booking.")
                else:
                    print("Chat cancelled.")

    except psycopg2.Error as e:
        print("Database error:", e)
    finally:
        cur.close()
        con.close()


# ---------- Add Review ----------
def add_review(marketer):
    print("\n-- Add Review --")
    try:
        con = get_connection()
        cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Show completed bookings for this marketer to choose from
        cur.execute("""
            SELECT b.booking_id, u.id AS creative_id, u.name AS creative_name, b.status, b.scheduled_date, b.created_at
            FROM bookings b
            JOIN users1 u ON u.id = b.creative_id
            WHERE b.marketer_id=%s AND b.status='completed'
            ORDER BY b.created_at DESC
        """, (marketer["id"],))
        completed = cur.fetchall()

        if not completed:
            print("You have no completed bookings to review.")
            return

        print("\nYour Completed Bookings:")
        headers = ["booking_id", "creative_id", "creative_name", "status", "scheduled_date", "created_at"]
        _print_rows(completed, headers)

        try:
            booking_id = int(_input_nonempty("Enter completed booking_id to review: "))
        except ValueError:
            print("Please enter a valid numeric booking_id.")
            return

        cur.execute("""
            SELECT booking_id, creative_id, status
            FROM bookings
            WHERE booking_id=%s AND marketer_id=%s
        """, (booking_id, marketer["id"]))
        bk = cur.fetchone()

        if not bk:
            print("Booking not found.")
            return
        if bk["status"] != "completed":
            print("You can review only after the booking is completed.")
            return

        try:
            rating = int(_input_nonempty("Rating (1-5): "))
            if not 1 <= rating <= 5:
                raise ValueError
        except ValueError:
            print("Please enter a number between 1 and 5.")
            return

        comment = input("Comment (optional): ").strip()

        cur.execute("""
            INSERT INTO reviews (booking_id, marketer_id, creative_id, rating, comment, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (booking_id, marketer["id"], bk["creative_id"], rating, comment, datetime.now()))
        con.commit()
        print("Review submitted. Thank you!")

    except psycopg2.Error as e:
        print("Database error:", e)
    finally:
        if 'cur' in locals() and cur:
            cur.close()
        if 'con' in locals() and con:
            con.close()


# ---------- View History ----------
def view_history(marketer):
    print("\n-- Your Booking History --")
    try:
        con = get_connection()
        cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT 
                b.booking_id, b.status, b.created_at,
                u.id AS creative_id, u.name AS creative_name,
                c.category, c.location
            FROM bookings b
            JOIN users1 u ON u.id = b.creative_id
            JOIN creative_profiles c ON c.user_id = u.id
            WHERE b.marketer_id = %s
            ORDER BY b.created_at DESC
        """, (marketer["id"],))
        rows = cur.fetchall()
        headers = ["booking_id", "status", "created_at", "creative_id", "creative_name", "category", "location"]
        _print_rows(rows, headers)
    except psycopg2.Error as e:
        print("Database error:", e)
    finally:
        cur.close()
        con.close()


# ---------- Support ----------
def support(marketer):
    print("\n-- Support --")
    subject = _input_nonempty("Subject: ")
    message = _input_nonempty("Describe your issue: ")

    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            INSERT INTO support_tickets (user_id, subject, message, status, created_at)
            VALUES (%s, %s, %s, 'open', %s)
        """, (marketer["id"], subject, message, datetime.now()))
        con.commit()
        print("Support ticket created. Our team will reach out soon.")
    except psycopg2.Error as e:
        print("Database error:", e)
    finally:
        cur.close()
        con.close()
