import streamlit as st
import requests
import json
import os
import base64
import streamlit.components.v1 as components
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="Todo App", page_icon="✅", layout="centered")

# Initialize session state for authentication
if "id_token" not in st.session_state:
    st.session_state.id_token = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# Check for Google Sign-In redirect token
if "token" in st.query_params:
    token = st.query_params["token"]
    st.session_state.id_token = token
    try:
        payload = token.split(".")[1]
        padded = payload + '=' * (4 - len(payload) % 4)
        decoded = base64.b64decode(padded)
        user_info = json.loads(decoded)
        st.session_state.user_email = user_info.get("email", "Google User")
    except Exception:
        st.session_state.user_email = "Google User"
    
    st.query_params.clear()
    st.rerun()


def login_with_email_password(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        st.session_state.id_token = data["idToken"]
        st.session_state.user_email = data["email"]
        st.success("Login successful!")
        st.rerun()
    else:
        try:
            error_msg = response.json().get("error", {}).get("message", "Unknown error")
        except:
            error_msg = response.text
        st.error(f"Login failed: {error_msg}")

def signup_with_email_password(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        st.session_state.id_token = data["idToken"]
        st.session_state.user_email = data["email"]
        st.success("Signup successful!")
        st.rerun()
    else:
        try:
            error_msg = response.json().get("error", {}).get("message", "Unknown error")
        except:
            error_msg = response.text
        st.error(f"Signup failed: {error_msg}")

def logout():
    st.session_state.id_token = None
    st.session_state.user_email = None
    st.rerun()

def get_headers():
    return {"Authorization": f"Bearer {st.session_state.id_token}"}

def fetch_todos():
    try:
        response = requests.get(f"{BACKEND_URL}/todos", headers=get_headers())
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            st.error("Session expired. Please log in again.")
            logout()
        else:
            st.error(f"Failed to fetch todos: {response.text}")
            return []
    except Exception as e:
        st.error(f"Backend connection error. Is FastAPI running on {BACKEND_URL}? Error: {str(e)}")
        return []

def create_todo(title, description):
    payload = {"title": title, "description": description, "completed": False}
    try:
        response = requests.post(f"{BACKEND_URL}/todos", headers=get_headers(), json=payload)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error creating todo: {str(e)}")
        return False

def update_todo(todo_id, title, description, completed):
    payload = {"title": title, "description": description, "completed": completed}
    try:
        response = requests.put(f"{BACKEND_URL}/todos/{todo_id}", headers=get_headers(), json=payload)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error updating todo: {str(e)}")
        return False

def delete_todo(todo_id):
    try:
        response = requests.delete(f"{BACKEND_URL}/todos/{todo_id}", headers=get_headers())
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error deleting todo: {str(e)}")
        return False

# --- Application UI ---

if not st.session_state.id_token:
    st.title("✅ Serverless Todo App")
    st.markdown("Please log in or sign up to continue.")
    
    # Auth Tabs
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        with st.form("login_form"):
            login_email = st.text_input("Email")
            login_password = st.text_input("Password", type="password")
            login_submit = st.form_submit_button("Login")
            if login_submit:
                if not FIREBASE_API_KEY or FIREBASE_API_KEY == "YOUR_API_KEY_HERE":
                    st.error("⚠️ FIREBASE_API_KEY is not set. Please configure the .env file in the frontend directory.")
                elif login_email and login_password:
                    login_with_email_password(login_email, login_password)
                else:
                    st.warning("Please enter both email and password.")
                    
    with tab2:
        with st.form("signup_form"):
            signup_email = st.text_input("Email")
            signup_password = st.text_input("Password", type="password")
            signup_submit = st.form_submit_button("Sign Up")
            if signup_submit:
                if not FIREBASE_API_KEY or FIREBASE_API_KEY == "YOUR_API_KEY_HERE":
                    st.error("⚠️ FIREBASE_API_KEY is not set. Please configure the .env file in the frontend directory.")
                elif signup_email and len(signup_password) >= 6:
                    signup_with_email_password(signup_email, signup_password)
                else:
                    st.warning("Please enter a valid email and a password of at least 6 characters.")
                    
    st.markdown("<div style='text-align: center; margin: 10px 0;'>OR</div>", unsafe_allow_html=True)
    
    if FIREBASE_PROJECT_ID and FIREBASE_PROJECT_ID != "YOUR_PROJECT_ID_HERE":
        login_url = f"{BACKEND_URL}/static/login.html?api_key={FIREBASE_API_KEY}&project_id={FIREBASE_PROJECT_ID}"
        st.markdown(f"""
            <a href="{login_url}" target="_self" style="display: block; width: 100%; text-align: center; padding: 10px; background-color: #4285F4; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold; text-decoration: none;">
                🚀 Continue with Google
            </a>
        """, unsafe_allow_html=True)
    else:
        st.info("⚠️ Set FIREBASE_PROJECT_ID in .env to enable Google Sign-in.")
                    
    st.markdown("---")
    
else:
    # Authenticated Dashboard
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🎯 Your Todo Dashboard")
    with col2:
        st.write("") # spacer
        st.write("") # spacer
        if st.button("Logout"):
            logout()
            
    st.markdown(f"Logged in as: **{st.session_state.user_email}**")
    st.divider()
    
    # Add Todo Section
    st.subheader("➕ Add a New Task")
    with st.form("add_todo_form"):
        new_title = st.text_input("Task Title", placeholder="What needs to be done?")
        new_desc = st.text_area("Task Description (Optional)", placeholder="Add some details...")
        submitted = st.form_submit_button("Add Task")
        if submitted:
            if new_title.strip():
                if create_todo(new_title, new_desc):
                    st.success("Task added successfully!")
                    st.rerun()
                else:
                    st.error("Failed to add task.")
            else:
                st.warning("Title is required.")
                
    st.divider()
    
    # View and Filter Todos
    st.subheader("📋 Your Tasks")
    
    # Advanced Feature: Search / Filter
    col_search, col_filter = st.columns([2, 1])
    with col_search:
        search_query = st.text_input("🔍 Search tasks...", "")
    with col_filter:
        filter_status = st.selectbox("Status", ["All", "Pending", "Completed"])
    
    todos = fetch_todos()
    
    if todos:
        # Filter logic
        filtered_todos = todos
        
        # 1. Status Filter
        if filter_status == "Pending":
            filtered_todos = [t for t in filtered_todos if not t.get("completed", False)]
        elif filter_status == "Completed":
            filtered_todos = [t for t in filtered_todos if t.get("completed", True)]
            
        # 2. Search Filter
        if search_query:
            q = search_query.lower()
            filtered_todos = [t for t in filtered_todos if q in t.get("title", "").lower() or q in t.get("description", "").lower()]
            
        if not filtered_todos:
            st.info("No tasks match your search criteria.")
        else:
            for todo in filtered_todos:
                is_completed = todo.get("completed", False)
                status_icon = "✅" if is_completed else "⏳"
                
                with st.expander(f"{status_icon} {todo.get('title')}", expanded=False):
                    if todo.get("description"):
                        st.markdown(f"**Description:**\n{todo.get('description')}")
                    
                    st.markdown("---")
                    
                    # Update Form
                    col_update, col_delete = st.columns([3, 1])
                    with col_update:
                        new_status = st.checkbox("Mark as Completed", value=is_completed, key=f"check_{todo['id']}")
                        edit_title = st.text_input("Edit Title", value=todo.get("title", ""), key=f"title_{todo['id']}")
                        edit_desc = st.text_area("Edit Description", value=todo.get("description", ""), key=f"desc_{todo['id']}")
                        
                        if st.button("Save Changes", key=f"save_{todo['id']}"):
                            if update_todo(todo["id"], edit_title, edit_desc, new_status):
                                st.success("Task updated!")
                                st.rerun()
                            else:
                                st.error("Failed to update task.")
                                
                    with col_delete:
                        st.write("") # vertical spacing
                        st.write("") # vertical spacing
                        if st.button("🗑️ Delete", key=f"del_{todo['id']}", type="primary"):
                            if delete_todo(todo["id"]):
                                st.success("Task deleted!")
                                st.rerun()
                            else:
                                st.error("Failed to delete task.")
    else:
        st.info("You don't have any tasks yet. Create one above to get started!")
