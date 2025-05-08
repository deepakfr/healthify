import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import datetime
import smtplib
import random
from email.message import EmailMessage

# --- Email Setup ---
SENDER_EMAIL = "youremail@example.com"
SENDER_PASSWORD = "your-app-password"  # Use app password from Gmail

# --- Utility Functions ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def send_verification_code(email, code):
    msg = EmailMessage()
    msg['Subject'] = 'Your HealthHub Password Reset Code'
    msg['From'] = SENDER_EMAIL
    msg['To'] = email
    msg.set_content(f"Your password reset code is: {code}")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

# --- Database Functions ---
conn = sqlite3.connect('healthhub.db', check_same_thread=False)
c = conn.cursor()

def create_usertable():
    c.execute('CREATE TABLE IF NOT EXISTS userstable(username TEXT, password TEXT, email TEXT)')

def add_userdata(username, password, email):
    c.execute('INSERT INTO userstable(username, password, email) VALUES (?,?,?)', (username, password, email))
    conn.commit()

def login_user(username, password):
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, password))
    return c.fetchall()

def create_health_table():
    c.execute('''CREATE TABLE IF NOT EXISTS healthdata(
        username TEXT,
        date DATE,
        steps INTEGER,
        water REAL,
        sleep REAL,
        mood TEXT
    )''')

def add_healthdata(username, date, steps, water, sleep, mood):
    c.execute('INSERT INTO healthdata(username, date, steps, water, sleep, mood) VALUES (?,?,?,?,?,?)',
              (username, date, steps, water, sleep, mood))
    conn.commit()

def get_user_healthdata(username):
    c.execute('SELECT date, steps, water, sleep, mood FROM healthdata WHERE username=? ORDER BY date DESC', (username,))
    return c.fetchall()

# --- Streamlit App ---
def main():
    st.title("🏥 HealthHub - Your All-in-One Health App")

    create_usertable()

    menu = ["Login", "Signup", "Reset Password"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Login":
        st.subheader("Login to Your Account")

        username = st.text_input("Username")
        password = st.text_input("Password", type='password')

        if st.button("Login"):
            hashed_pswd = make_hashes(password)
            result = login_user(username, hashed_pswd)
            if result:
                st.success(f"Welcome back, {username}!")
                user_dashboard(username)
            else:
                st.error("Incorrect Username or Password")

    elif choice == "Signup":
        st.subheader("Create a New Account")

        new_user = st.text_input("New Username")
        new_password = st.text_input("New Password", type='password')
        new_email = st.text_input("Email")

        if st.button("Signup"):
            if new_user.strip() == "" or new_password.strip() == "" or new_email.strip() == "":
                st.warning("Please provide all fields.")
            else:
                add_userdata(new_user, make_hashes(new_password), new_email)
                st.success("Account created successfully.")

    elif choice == "Reset Password":
        st.subheader("🔐 Reset Your Password")

        username = st.text_input("Your Username")
        if st.button("Send Code"):
            c.execute('SELECT email FROM userstable WHERE username=?', (username,))
            result = c.fetchone()
            if result:
                email = result[0]
                code = str(random.randint(100000, 999999))
                st.session_state['reset_code'] = code
                st.session_state['reset_user'] = username
                if send_verification_code(email, code):
                    st.success(f"A verification code was sent to {email}.")
            else:
                st.error("Username not found.")

        code_input = st.text_input("Enter the code")
        new_password = st.text_input("New Password", type='password')
        confirm_password = st.text_input("Confirm Password", type='password')

        if st.button("Reset Password"):
            if 'reset_code' not in st.session_state or 'reset_user' not in st.session_state:
                st.warning("Please request a code first.")
            elif code_input != st.session_state['reset_code']:
                st.error("Incorrect verification code.")
            elif new_password != confirm_password:
                st.warning("Passwords do not match.")
            else:
                c.execute("UPDATE userstable SET password=? WHERE username=?", 
                          (make_hashes(new_password), st.session_state['reset_user']))
                conn.commit()
                st.success("Password reset successfully.")

def user_dashboard(username):
    create_health_table()
    st.subheader(f"{username}'s Health Dashboard")

    st.sidebar.header("Daily Health Inputs")
    today = datetime.date.today()

    steps = st.sidebar.number_input("🚶 Steps Walked", 0, 50000, step=100)
    water = st.sidebar.number_input("💧 Water Intake (liters)", 0.0, 10.0, step=0.1)
    sleep = st.sidebar.slider("🛌 Hours Slept", 0.0, 12.0, step=0.5)
    mood = st.sidebar.selectbox("😊 Mood Today", ["Happy", "Neutral", "Sad", "Anxious"])

    if st.sidebar.button("Submit Today's Data"):
        add_healthdata(username, today, steps, water, sleep, mood)
        st.sidebar.success("Health data added successfully!")

    health_records = get_user_healthdata(username)
    if health_records:
        df = pd.DataFrame(health_records, columns=['Date', 'Steps', 'Water (L)', 'Sleep (hrs)', 'Mood'])
        st.dataframe(df)

        st.line_chart(df.set_index('Date')[['Steps', 'Water (L)', 'Sleep (hrs)']])

        st.subheader("Recent Mood Trends")
        st.bar_chart(df['Mood'].value_counts())
    else:
        st.info("No health data found. Please input today's data!")

if __name__ == '__main__':
    main()
