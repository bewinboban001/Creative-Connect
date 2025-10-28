import psycopg2
import psycopg2.extras
from datetime import datetime
import webbrowser

# ---------- Database Config ----------
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "test",
    "user": "postgres",
    "password": "root"
}


# ---------- Connection Function ----------
def get_db_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except psycopg2.Error as e:
        print("Database connection failed:", e)
        return None


# ---------- Admin Login ----------
def admin_login():
    print("\n--- Admin Login ---")
    email = input("Enter admin email: ").strip()
    password = input("Enter admin password: ").strip()

    conn = get_db_connection()
    if not conn:
        print("❌ Cannot connect to database.")
        return

    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT * FROM users1
        WHERE email=%s AND password=%s AND role='admin' AND approved=TRUE
    """, (email, password))
    admin = cur.fetchone()

    if admin:
        print(f"\n✅ Welcome, {admin['name']} (Admin)")
        admin_menu(admin)
    else:
        print("❌ Invalid admin credentials.")

    cur.close()
    conn.close()


# ---------- Admin Menu ----------
def admin_menu(admin):
    while True:
        print("\n--- Admin Panel ---")
        print("1. Approve Users")
        print("2. Manage Categories")
        print("3. View All Users")
        print("4. Logout")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            approve_users()
        elif choice == "2":
            manage_categories()
        elif choice == "3":
            view_all_users()
        elif choice == "4":
            print("Logged out successfully.")
            break
        else:
            print("Invalid choice.")


# ---------- Approve Creative Profiles ----------
def approve_users():
    conn = get_db_connection()
    if not conn:
        print("❌ Cannot connect to database.")
        return

    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Interactive loop: list pending users and allow viewing details/opening portfolio before approving
    while True:
        cur.execute("SELECT id, name, email, role FROM users1 WHERE role IN ('creative','marketer') AND approved=FALSE ORDER BY id")
        pending = cur.fetchall()

        if not pending:
            print("No pending user approvals.")
            break

        print("\nPending User Approvals:")
        for u in pending:
            print(f"{u['id']}. {u['name']} ({u['role']}) - {u['email']}")

        try:
            uid = input("\nEnter user ID to manage (or 0 to exit): ").strip()
            if not uid.isdigit():
                print("Please enter a numeric ID.")
                continue
            uid = int(uid)
            if uid == 0:
                print("Returning to admin menu.")
                break

            # Fetch full details for selected user
            cur.execute("SELECT id, name, email, role, portfolio_link FROM users1 WHERE id=%s AND approved=FALSE", (uid,))
            sel = cur.fetchone()
            if not sel:
                print("No pending user with that ID.")
                continue

            print(f"\nUser details for {sel['name']} (ID: {sel['id']}):")
            print(f"Role: {sel['role']}")
            print(f"Email: {sel['email']}")
            print(f"Portfolio link: {sel.get('portfolio_link')}")

            print("\nOptions: 1. Open portfolio  2. Approve user  3. Back")
            opt = input("Choose: ").strip()
            if opt == '1':
                pl = sel.get('portfolio_link')
                if pl:
                    try:
                        webbrowser.open(pl)
                        print("Opened portfolio in browser.")
                    except Exception as e:
                        print("Failed to open portfolio:", e)
                else:
                    print("No portfolio link provided.")
            elif opt == '2':
                cur.execute("UPDATE users1 SET approved=TRUE WHERE id=%s AND approved=FALSE", (uid,))
                if cur.rowcount == 0:
                    print("No pending user with that ID or already approved.")
                else:
                    conn.commit()
                    print("✅ User approved successfully.")
            elif opt == '3':
                continue
            else:
                print("Invalid option.")

        except Exception:
            print("Invalid input.")

    cur.close()
    conn.close()


# ---------- Manage Categories ----------
def manage_categories():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    while True:
        print("\n--- Category Management ---")
        print("1. View Categories")
        print("2. Add Category")
        print("3. Delete Category")
        print("4. Back")

        ch = input("Choose an option: ")

        if ch == "1":
            cur.execute("SELECT * FROM categories ORDER BY category_id")
            cats = cur.fetchall()
            if cats:
                for c in cats:
                    print(f"{c['category_id']}. {c['name']}")
            else:
                print("No categories found.")

        elif ch == "2":
            name = input("Enter new category name: ").strip()
            if name:
                cur.execute("INSERT INTO categories (name) VALUES (%s)", (name,))
                conn.commit()
                print("✅ Category added successfully.")
            else:
                print("Category name cannot be empty.")

        elif ch == "3":
            # Fetch categories and display a pretty table before deletion
            cur.execute("SELECT category_id, name FROM categories ORDER BY category_id")
            cats = cur.fetchall()
            if not cats:
                print("No categories to delete.")
            else:
                # Calculate column widths
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

                cid = input("Enter category ID to delete (or 0 to cancel): ").strip()
                if cid == "0":
                    print("Cancelled.")
                elif cid.isdigit():
                    cur.execute("DELETE FROM categories WHERE category_id=%s", (int(cid),))
                    if cur.rowcount == 0:
                        print("No category found with that ID.")
                    else:
                        conn.commit()
                        print("✅ Category deleted.")
                else:
                    print("Invalid ID.")

        elif ch == "4":
            break
        else:
            print("Invalid option.")

    cur.close()
    conn.close()


# ---------- View All Users ----------
def view_all_users():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT id, name, email, role, approved FROM users1 ORDER BY id")
    users = cur.fetchall()

    print("\n--- All Users ---")
    for u in users:
        status = "✅ Approved" if u["approved"] else "⏳ Pending"
        print(f"{u['id']}. {u['name']} ({u['role']}) - {u['email']} - {status}")

    cur.close()
    conn.close()


# ---------- Standalone Run ----------
if __name__ == "__main__":
    print("Run admin_login() to access admin panel.")
