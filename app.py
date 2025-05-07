import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import datetime

# --- Utility Functions ---

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# --- Database Functions ---

conn = sqlite3.connect('healthhub.db', check_same_thread=False)
c = conn.cursor()

def create_usertable():
    c.execute('CREATE TABLE IF NOT EXISTS userstable(username TEXT, password TEXT)')

def add_userdata(username, password):
    c.execute('INSERT INTO userstable(username, password) VALUES (?,?)', (username, password))
    conn.commit()

def login_user(username, password):
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, password))
    data = c.fetchall()
    return data

def view_all_users():
    c.execute('SELECT * FROM userstable')
    data = c.fetchall()
    return data

def create_health_table():
    c.execute('''
    CREATE TABLE IF NOT EXISTS healthdata(
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
    data = c.fetchall()
    return data

# --- Streamlit App ---

def main():
    st.title("🏥 HealthHub - Your All-in-One Health App")

    menu = ["Home", "Login", "Signup"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Home":
        st.subheader("Welcome to HealthHub!")
        st.write("Please login or signup to access your personalized health dashboard.")

    elif choice == "Signup":
        st.subheader("Create a New Account")

        new_user = st.text_input("Username")
        new_password = st.text_input("Password", type='password')

        if st.button("Signup"):
            create_usertable()
            if new_user.strip() == "" or new_password.strip() == "":
                st.warning("Please provide both username and password.")
            else:
                add_userdata(new_user, make_hashes(new_password))
                st.success("Account successfully created!")
                st.info("Go to Login menu to log in.")

    elif choice == "Login":
        st.subheader("Login to Your Account")

        username = st.text_input("Username")
        password = st.text_input("Password", type='password')

        if st.button("Login"):
            create_usertable()
            hashed_pswd = make_hashes(password)
            result = login_user(username, hashed_pswd)
            if result:
                st.success(f"Welcome back, {username}!")
                
                # User-specific dashboard
                user_dashboard(username)
            else:
                st.error("Incorrect Username or Password")

def user_dashboard(username):
    create_health_table()
    st.subheader(f"{username}'s Health Dashboard")

    # Sidebar inputs for daily data
    st.sidebar.header("Daily Health Inputs")
    today = datetime.date.today()

    steps = st.sidebar.number_input("🚶 Steps Walked", 0, 50000, step=100)
    water = st.sidebar.number_input("💧 Water Intake (liters)", 0.0, 10.0, step=0.1)
    sleep = st.sidebar.slider("🛌 Hours Slept", 0.0, 12.0, step=0.5)
    mood = st.sidebar.selectbox("😊 Mood Today", ["Happy", "Neutral", "Sad", "Anxious"])

    if st.sidebar.button("Submit Today's Data"):
        add_healthdata(username, today, steps, water, sleep, mood)
        st.sidebar.success("Health data added successfully!")

    # Display user's historical data
    health_records = get_user_healthdata(username)
    if health_records:
        df = pd.DataFrame(health_records, columns=['Date', 'Steps', 'Water (L)', 'Sleep (hrs)', 'Mood'])
        st.dataframe(df)

        # Simple visualization
        st.line_chart(df.set_index('Date')[['Steps', 'Water (L)', 'Sleep (hrs)']])

        st.subheader("Recent Mood Trends")
        mood_counts = df['Mood'].value_counts()
        st.bar_chart(mood_counts)

    else:
        st.info("No health data found. Please input today's data!")

if __name__ == '__main__':
    main()
