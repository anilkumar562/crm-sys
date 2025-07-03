import streamlit as st
import psycopg2
import os

# --- Database Configuration (ensure these match your main app) ---
DB_HOST = "localhost"
DB_NAME = "database"
DB_USER = "anil"
DB_PASS = "9409030562"

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

def fetch_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_name, userpass, role, COALESCE(pages, '') FROM users ORDER BY user_name;")
    users = [
        {
            "user_name": r[0],
            "userpass": r[1],
            "role": r[2],
            "pages": r[3].split(",") if r[3] else []
        }
        for r in cur.fetchall()
    ]
    cur.close()
    conn.close()
    return users

def add_user(user_name, userpass, role, pages=None):
    conn = get_connection()
    cur = conn.cursor()
    pages_str = ",".join(pages) if pages else ""
    cur.execute(
        "INSERT INTO users (user_name, userpass, role, pages) VALUES (%s, %s, %s, %s);",
        (user_name, userpass, role, pages_str)
    )
    conn.commit()
    cur.close()
    conn.close()

def update_user(old_user_name, user_name, userpass, role, pages=None):
    conn = get_connection()
    cur = conn.cursor()
    pages_str = ",".join(pages) if pages else ""
    cur.execute(
        "UPDATE users SET user_name=%s, userpass=%s, role=%s, pages=%s WHERE user_name=%s;",
        (user_name, userpass, role, pages_str, old_user_name)
    )
    conn.commit()
    cur.close()
    conn.close()

def delete_user(user_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE user_name=%s;", (user_name,))
    conn.commit()
    cur.close()
    conn.close()

def get_modules_list():
    modules_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modules")
    if not os.path.exists(modules_dir):
        return []
    module_files = [f for f in os.listdir(modules_dir) if f.endswith(".py")]
    module_names = []
    for fname in module_files:
        name = fname
        if name.lower().endswith(".py"):
            name = name[:-3]
        if name.lower() != "user_management":  # Prevent self assignment
            module_names.append(name.strip())
    return module_names

def show():
    st.title("User Management")
    st.write("Manage users, roles, and page/module access.")

    users = fetch_users()
    modules = get_modules_list()

    with st.expander("Add New User"):
        with st.form("add_user_form"):
            user_name = st.text_input("Username", key="add_username")
            userpass = st.text_input("Password", type="password", key="add_password")
            role = st.selectbox("Role", ["user", "admin"], key="add_role")
            pages = st.multiselect("Modules Access", options=modules, key="add_pages")
            submitted = st.form_submit_button("Add User")
            if submitted:
                if not user_name or not userpass:
                    st.error("Username and password are required.")
                elif any(u["user_name"] == user_name for u in users):
                    st.error("Username already exists.")
                else:
                    add_user(user_name, userpass, role, pages)
                    st.success(f"User '{user_name}' added successfully.")
                    # Clear input fields
                    st.session_state["add_username"] = ""
                    st.session_state["add_password"] = ""
                    st.session_state["add_role"] = "user"
                    st.session_state["add_pages"] = []
                    st.rerun()

    st.markdown("---")
    st.subheader("Existing Users")
    for u in users:
        with st.expander(f"{u['user_name']} ({u['role']})"):
            with st.form(f"user_edit_{u['user_name']}"):
                new_user_name = st.text_input("Username", value=u["user_name"], key=f"edit_username_{u['user_name']}")
                new_userpass = st.text_input("Password", value=u["userpass"], type="password", key=f"edit_pass_{u['user_name']}")
                new_role = st.selectbox("Role", options=["user", "admin"], index=["user", "admin"].index(u["role"]), key=f"edit_role_{u['user_name']}")
                new_pages = st.multiselect("Modules Access", options=modules, default=u["pages"], key=f"edit_pages_{u['user_name']}")
                col1, col2 = st.columns([1,1])
                update_btn = col1.form_submit_button("Update")
                delete_btn = col2.form_submit_button("Delete", type="primary")
                if update_btn:
                    update_user(u["user_name"], new_user_name, new_userpass, new_role, new_pages)
                    st.success("User updated.")
                    st.rerun()
                if delete_btn:
                    delete_user(u["user_name"])
                    st.success("User deleted.")
                    st.rerun()