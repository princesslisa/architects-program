import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd

# Connect to Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Set up the page title
st.title("Annual Architects Program")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Montserrat:wght@300;400;600&display=swap');

/* Apply Montserrat to the main body text */
html, body, [class*="css"]  {
    font-family: 'Montserrat', sans-serif;
}

/* Apply Cinzel and Gold to all headers */
h1, h2, h3 {
    font-family: 'Cinzel', serif !important;
    color: #D4AF37 !important;
    text-transform: uppercase;
}

/* Recreate the gold gradient export button */
.stButton>button {
    background: linear-gradient(135deg, #D4AF37, #8a701e);
    color: #0a1f1a;
    border: none;
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    border-radius: 4px;
}
</style>
""", unsafe_allow_html=True)

# Check if the user is already logged in
if "user" not in st.session_state:
    st.session_state.user = None


def login():
    st.subheader("Participant Login")
    email = st.text_input("Email Address")
    password = st.text_input("Password", type="password")

    if st.button("Log In"):
        try:
            # Send credentials to Supabase
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = response.user
            st.rerun()
        except Exception as e:
            st.error("Login failed. Please check your email and password.")


def dashboard():
    st.success("You are logged in.")

    if st.button("Log Out"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    st.divider()

    user_id = st.session_state.user.id

    participant_data = supabase.table("participants").select("*").eq("id", user_id).execute()
    logs_data = supabase.table("logs").select("log_date").eq("participant_id", user_id).execute()

    log_dates = [log['log_date'] for log in logs_data.data] if logs_data.data else []
    today = datetime.date.today()

    if participant_data.data:
        p_data = participant_data.data[0]
        st.subheader(f"Welcome, {p_data.get('full_name', 'Participant')}")

        total_checkins = len(log_dates)
        consistency_score = 0

        start_date_str = p_data.get('start_date')
        if start_date_str:
            start_date = datetime.datetime.strptime(str(start_date_str), "%Y-%m-%d").date()
            days_since_start = (today - start_date).days + 1
            if days_since_start > 0:
                consistency_score = round((total_checkins / days_since_start) * 100, 1)

        streak_visual = ""
        for i in range(4, -1, -1):
            check_date = today - datetime.timedelta(days=i)
            if str(check_date) in log_dates:
                streak_visual += "🟩 "
            else:
                streak_visual += "⬜ "

        st.write(f"**Current Streak:** {streak_visual}")

        # Displaying metrics in three columns so they all show up properly
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Check-ins", total_checkins)
        col2.metric("Consistency", f"{consistency_score}%")
        col3.metric("Days Active", len(set(log_dates)))

    st.divider()

    st.subheader("Log Your Progress")
    st.write(f"**Date:** {today.strftime('%B %d, %Y')}")

    level = st.radio("What level did you hit today?", ["Floor", "Baseline", "Ceiling"], horizontal=True)
    notes = st.text_area("Any notes? (Optional)")

    if st.button("Submit Check-in"):
        if str(today) in log_dates:
            st.warning("You have already submitted a log for today.")
        else:
            try:
                log_payload = {
                    "participant_id": user_id,
                    "log_date": str(today),
                    "level": level,
                    "notes": notes
                }
                supabase.table("logs").insert(log_payload).execute()
                st.success("Successfully logged activity for today!")
                st.rerun()
            except Exception as e:
                st.error("Failed to save your log. Please try again.")


def admin_dashboard():
    st.success("Admin Access Granted.")

    if st.button("Log Out"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    st.divider()
    st.header("Admin Controls")

    parts_response = supabase.table("participants").select("*").execute()
    participants = parts_response.data

    if not participants:
        st.info("No participants found.")
        return

    name_to_id = {p["full_name"]: p["id"] for p in participants if p.get("full_name")}

    st.subheader("Log on behalf of a participant")
    selected_name = st.selectbox("Select Participant", list(name_to_id.keys()))
    selected_date = st.date_input("Select Date", datetime.date.today())
    level = st.radio("Level", ["Floor", "Baseline", "Ceiling"], horizontal=True)
    notes = st.text_area("Notes")

    if st.button("Submit Admin Log"):
        participant_id = name_to_id[selected_name]

        check_dup = supabase.table("logs").select("*").eq("participant_id", participant_id).eq("log_date",
                                                                                               str(selected_date)).execute()

        if len(check_dup.data) > 0:
            st.warning(f"{selected_name} already has a log for {selected_date}.")
        else:
            try:
                log_payload = {
                    "participant_id": participant_id,
                    "log_date": str(selected_date),
                    "level": level,
                    "notes": notes
                }
                supabase.table("logs").insert(log_payload).execute()
                st.success(f"Successfully logged activity for {selected_name} on {selected_date}!")
            except Exception as e:
                st.error("Failed to save the log.")

    st.divider()
    st.subheader("Group Leaderboard Overview")

    logs_response = supabase.table("logs").select("*").execute()
    logs_df = pd.DataFrame(logs_response.data)
    parts_df = pd.DataFrame(participants)

    if not logs_df.empty and not parts_df.empty:
        log_counts = logs_df.groupby("participant_id").size().reset_index(name="Total Check-ins")
        leaderboard = pd.merge(parts_df, log_counts, left_on="id", right_on="participant_id", how="left")
        leaderboard["Total Check-ins"] = leaderboard["Total Check-ins"].fillna(0).astype(int)

        # Calculate Consistency Score for the Admin Table
        today = datetime.date.today()

        def get_consistency(row):
            start_str = row.get("start_date")
            if not start_str or pd.isna(start_str):
                return 0
            start_d = datetime.datetime.strptime(str(start_str), "%Y-%m-%d").date()
            days = (today - start_d).days + 1
            if days > 0:
                return round((row["Total Check-ins"] / days) * 100, 1)
            return 0

        leaderboard["Consistency %"] = leaderboard.apply(get_consistency, axis=1)

        # Display the visual chart
        st.write("### Total Check-ins by Participant")
        chart_data = leaderboard.set_index("full_name")["Total Check-ins"]
        st.bar_chart(chart_data)

        # Display the full table
        st.write("### Detailed Stats")
        display_df = leaderboard[["full_name", "track", "Total Check-ins", "Consistency %"]].sort_values(
            by="Consistency %", ascending=False)
        st.dataframe(display_df, use_container_width=True)
    else:
        st.write("Not enough data to display the leaderboard yet.")


# Routing logic to show the right screen
if st.session_state.user is None:
    login()
else:
    # Check if the logged-in email exists in the admins table
    user_email = st.session_state.user.email
    admin_check = supabase.table("admins").select("*").eq("email", user_email).execute()

    if len(admin_check.data) > 0:
        admin_dashboard()
    else:
        dashboard()
