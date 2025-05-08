import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import datetime
import smtplib
import random
from email.message import EmailMessage
import openai

# --- OpenAI API Key ---
openai.api_key = st.secrets["openai_api_key"]

# --- Email Credentials (Static for Deployment) ---
SENDER_EMAIL = "youremail@example.com"     # You can still use this for 'from' display
SENDER_PASSWORD = "your-email-app-password"  # Not used if deploying on Streamlit Cloud

# --- Utility Functions ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_verification_code(email, code):
    msg = EmailMessage()
    msg['Subject'] = '🔐 HealthHub Password Reset Code'
    msg['From'] = SENDER_EMAIL
    msg['To'] = email
    msg.set_content(f"Your HealthHub password reset code is: {code}")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

def get_diet_suggestion(calories, goal):
    prompt = f"""
    I consumed {calories} calories today and my goal is to {goal.lower()}. 
    Suggest a personalized meal plan and health tips for tomorrow to help me achieve my goal. 
    Include food examples and meal timing.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a certified nutritionist."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"⚠️ Error: {e}"

# --- Database ---
conn = sqlite3.connect('healthhub.db', check_same_thread=False)
c = conn.cursor()

def create_usertable():
    c.execute('CREATE TABLE IF NOT EXISTS userstable(username TEXT, password TEXT, email TEXT)')

def add_userdata(username, password, email):
    c.execute('INSERT INTO userstable(username, password, email) VALUES (?,?,?)', (username, password, email))
    conn.commit()

def login_user(username, password):
    c.execute('SELECT * FROM userstable WHERE username=? AND password=?', (username, password))
    return c.fetchall()

def get_email_by_username(username):
    c.execute('SELECT email FROM userstable WHERE username=?', (username,))
    return c.fetchone()

def update_password(username, new_hashed_password):
    c.execute('UPDATE userstable SET password=? WHERE username=?', (new_hashed_password, username))
    conn.commit()

def create_health_table():
    c.execute('''
        CREATE TABLE IF NOT EXISTS healthdata(
            username TEXT,
            date DATE,
            steps INTEGER,
            water REAL,
            sleep REAL,
            mood TEXT,
            calories INTEGER
        )
    ''')

def add_healthdata(username, date, steps, water, sleep, mood, calories):
    c.execute('''
        INSERT INTO healthdata(username, date, steps, water, sleep, mood, calories)
        VALUES (?,?,?,?,?,?,?)
    ''', (username, date, steps, water, sleep, mood, calories))
    conn.commit()

def get_user_healthdata(username):
    c.execute('SELECT date, steps, water, calories FROM healthdata WHERE username=? ORDER BY date DESC', (username,))
    return c.fetchall()

# --- Dashboard ---
def show_dashboard(username):
    create_health_table()
    st.subheader(f"📊 {username}'s Health Dashboard")

    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""
        st.rerun()

    today = datetime.date.today()
    st.markdown("### 📥 Enter today's data")

    col1, col2 = st.columns(2)

    with col1:
        steps = st.number_input("🚶 Steps Walked", min_value=0, max_value=50000, step=100)
        sleep = st.slider("🛌 Hours Slept", 0.0, 12.0, step=0.5)

    with col2:
        water = st.number_input("💧 Water Intake (liters)", min_value=0.0, max_value=10.0, step=0.1)
        mood = st.selectbox("😊 Mood", ["Happy", "Neutral", "Sad", "Anxious"])

    calories = st.number_input("🔥 Calories Consumed", min_value=0, max_value=6000, step=50)
    goal = st.selectbox("🎯 Your Goal", ["Lose weight", "Maintain weight", "Gain weight"])

    if st.button("Submit Today's Data"):
        add_healthdata(username, today, steps, water, sleep, mood, calories)
        st.success("✅ Data saved!")

    if st.button("Get AI Diet Suggestion"):
        with st.spinner("Generating personalized plan..."):
            suggestion = get_diet_suggestion(calories, goal)
            st.markdown("### 🤖 AI Diet Suggestion")
            st.write(suggestion)

    st.markdown("### 📅 Recent Records")
    records = get_user_healthdata(username)
    if records:
        df = pd.DataFrame(records, columns=["Date", "Steps", "Water Intake (L)", "Calories"])
        st.dataframe(df)
        st.line_chart(df.set_index("Date"))
    else:
        st.info("No records yet. Start by entering today's data!")

# --- Main App ---
def main():
    st.set_page_config(page_title="HealthHub", layout="centered")
    st.title("🏥 HealthHub")

    create_usertable()

    if st.session_state.get("logged_in"):
        show_dashboard(st.session_state['username'])
        return

    menu = ["Login", "Signup", "Forgot Password"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Login":
        st.subheader("🔐 Login to your account")
        username = st.text_input("Username")
        password = st.text_input("Password", type='password')

        if st.button("Login"):
            hashed = make_hashes(password)
            result = login_user(username, hashed)
            if result:
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.rerun()
            else:
                st.error("Incorrect username or password")

    elif choice == "Signup":
        st.subheader("📝 Create a new account")
        new_user = st.text_input("Choose a username")
        new_password = st.text_input("Choose a password", type='password')
        email = st.text_input("Your email address")

        if st.button("Signup"):
            if new_user.strip() and new_password.strip() and email.strip():
                add_userdata(new_user, make_hashes(new_password), email)
                st.success("Account created! Please log in.")
            else:
                st.warning("Please fill in all fields.")

    elif choice == "Forgot Password":
        st.subheader("🔑 Forgot Password")
        username = st.text_input("Enter your username")

        if st.button("Send Code"):
            user_email = get_email_by_username(username)
            if user_email:
                code = str(random.randint(100000, 999999))
                st.session_state.reset_code = code
                st.session_state.reset_user = username
                if send_verification_code(user_email[0], code):
                    st.success(f"Code sent to {user_email[0]}")
            else:
                st.error("Username not found.")

        if 'reset_user' in st.session_state:
            entered_code = st.text_input("Enter the code")
            new_pass = st.text_input("New password", type='password')
            confirm_pass = st.text_input("Confirm password", type='password')

            if st.button("Reset Password"):
                if entered_code != st.session_state.reset_code:
                    st.error("Invalid code.")
                elif new_pass != confirm_pass:
                    st.error("Passwords do not match.")
                else:
                    update_password(st.session_state.reset_user, make_hashes(new_pass))
                    st.success("Password reset successfully!")

# --- Run ---
if __name__ == '__main__':
    main()
