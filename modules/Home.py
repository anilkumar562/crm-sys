import streamlit as st
import psycopg2
import os
import importlib
import time
import uuid
import re
st.set_page_config(page_title="User Management", layout="wide")  # This must be first!

from streamlit_cookies_manager import EncryptedCookieManager
# --- Unified CSS Styling ---
st.markdown("""
    <style>
        section[data-testid="stSidebar"] .css-ng1t4o {
            padding-top: 1rem;
        }
        [data-testid="stSidebarNav"]::before {
            content: "🛠️ Tools";
            font-size: 30px;
            font-weight: bold;
            display: block;
            margin: 10px 0 15px 10px;
            margin-top: -50px;
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        button[data-testid="baseButton-secondary"][title="Delete this user"] {
            background-color: #ff4b4b !important;
            color: white !important;
        }
        section[data-testid="stSidebar"] button {
            border-radius: 0 !important;
            margin: 0 !important;
            width: 100% !important;
            min-width: 100% !important;
            box-sizing: border-box !important;
            text-align: left !important;
            justify-content: flex-start !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div {
            margin: 0 !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- Database Configuration ---
DB_HOST = "localhost"
DB_NAME = "database"
DB_USER = "anil"
DB_PASS = "9409030562"

# --- Database Functions ---
def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

# @st.cache_data
def fetch_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_name, userpass, role, COALESCE(pages, ''), COALESCE(cookie, '') FROM users ORDER BY user_name;")
    users = [
        {
            "user_name": r[0],
            "userpass": r[1],
            "role": r[2],
            "pages": r[3].split(",") if r[3] else [],
            "cookie": r[4]
        }
        for r in cur.fetchall()
    ]
    cur.close()
    conn.close()
    return users

# --- Page and Module Management ---

def get_modules_list():
    modules_dir = os.path.join(os.path.dirname(__file__), "modules")
    if not os.path.exists(modules_dir):
        return []
    module_files = [f for f in os.listdir(modules_dir) if f.endswith(".py")]
    module_names = []
    for fname in module_files:
        # Remove prefix and extension, e.g., "Excel Data Validator.py" -> "Excel Data Validator"
        name = fname
        if name.lower().endswith(".py"):
            name = name[:-3]
        module_names.append(name.strip())
    return module_names

# --- Setup cookies ---
cookies = EncryptedCookieManager(
    prefix="myapp_",  # Change this to your app name
    password="a-very-secret-password"  # Change this to a strong secret in production!
)
if not cookies.ready():
    st.stop()

COOKIE_TIMEOUT = 1800  # 30 minutes

def is_logged_in():
    user = cookies.get("user")
    login_time = cookies.get("login_time")
    if user and login_time:
        if time.time() - float(login_time) < COOKIE_TIMEOUT:
            return user
        else:
            del cookies["user"]
            del cookies["login_time"]
            cookies.save()
    return None

def do_login(username):
    cookies["user"] = username
    cookies["login_time"] = str(time.time())
    cookies.save()

def do_logout():
    del cookies["user"]
    del cookies["login_time"]
    cookies.save()

def set_session_state_from_user(user_obj):
    st.session_state.logged_in = True
    st.session_state.user_name = user_obj["user_name"]
    st.session_state.role = user_obj["role"]
    st.session_state.pages = user_obj.get("pages", [])

def update_user_cookie(user_name, cookie_value):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET cookie=%s WHERE user_name=%s;", (cookie_value, user_name))
    conn.commit()
    cur.close()
    conn.close()

def get_user_by_cookie(cookie_value):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_name, userpass, role, COALESCE(pages, ''), cookie FROM users WHERE cookie=%s;", (cookie_value,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {
            "user_name": row[0],
            "userpass": row[1],
            "role": row[2],
            "pages": row[3].split(",") if row[3] else [],
            "cookie": row[4]
        }
    return None

# --- Simple Authentication ---
cookie_token = cookies.get("session_token")
user_obj = None

if cookie_token:
    user_obj = get_user_by_cookie(cookie_token)

if not user_obj:
    st.title("Sudathi")
    with st.form("login_form"):
        st.subheader("Login")
        login_user = st.text_input("Username")
        login_pass = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login")
        if login_btn:
            users = fetch_users()
            user_obj = next((u for u in users if u["user_name"] == login_user and u["userpass"] == login_pass), None)
            if user_obj:
                # Generate a unique session token and store it
                session_token = str(uuid.uuid4())
                cookies["session_token"] = session_token
                cookies.save()
                update_user_cookie(user_obj["user_name"], session_token)
                set_session_state_from_user(user_obj)
                st.success(f"Welcome, {user_obj['user_name']}!")
                st.rerun()
            else:
                st.error("Invalid username or password.")
    st.stop()
else:
    # User is logged in, set session state if not already set
    if not st.session_state.get("logged_in"):
        set_session_state_from_user(user_obj)

MODULES = get_modules_list()

# --- Sidebar Welcome and Logout ---
user_display_name = st.session_state.user_name.capitalize()
st.sidebar.markdown(
    f"""
    <div style='font-size:22px; font-weight:bold; margin-bottom: 10px;'>
        👋 Welcome, <span style='background:#e5f6fd; color:#222; border-radius:4px; padding:2px 8px;'>{user_display_name}</span>
    </div>
    """,
    unsafe_allow_html=True
)

# Custom CSS for red logout button
st.markdown("""
    <style>
    div[data-testid="stSidebar"] button[title="Logout"], 
    div[data-testid="stSidebar"] button:has-text("Logout") {
        background-color: #ff4b4b !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

if st.sidebar.button("Logout", key="logout_btn", help="Logout"):
    # Remove session token from cookie and DB
    update_user_cookie(user_obj["user_name"], "")
    del cookies["session_token"]
    cookies.save()
    st.session_state.clear()
    st.rerun()

# --- Role-based UI ---
if st.session_state.role == "admin":
    # Admin: show all pages by default
    allowed_pages = MODULES
else:
    # User: only show allowed pages
    def normalize(name):
        return name.replace(" ", "_").replace("-", "_").replace(".py", "").lower()
    user_pages = [normalize(p) for p in st.session_state.pages]
    allowed_pages = [name for name in MODULES if normalize(name) in user_pages]

# --- Sidebar Pages ---
if allowed_pages:
    st.sidebar.header("Pages")
    selected_page = None
    for page in allowed_pages:
        # Remove numbers from the menu name
        button_label = re.sub(r'\d+', '', page)
        button_label = button_label.replace("_", " ").title().strip()
        if st.sidebar.button(button_label, key=f"page_btn_{page}"):
            st.session_state.selected_page = page
    selected_page = st.session_state.get("selected_page", allowed_pages[0] if allowed_pages else None)
    if selected_page:
        try:
            import_name = "modules." + selected_page.replace(" ", "_").replace("-", "_").replace(".py", "").lower()
            module = importlib.import_module(import_name)
            module.show()
        except Exception as e:
            st.error(f"Error loading page: {e}")
else:
    st.info("No pages assigned to your user.")
