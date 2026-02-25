import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import uuid


# The cache command saves this connection so it only runs once
@st.cache_resource
def connect_to_google():
    # Setup Google connection
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # For Streamlit Cloud, you will pull the JSON from st.secrets instead of a file
    google_creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS_JSON"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds_dict, scope)
    gs_client = gspread.authorize(creds)
    return gs_client.open("The Annual Architect (Responses)").worksheet("Logs")


# Call the cached function to get your sheet ready
gs_logs_sheet = connect_to_google()

# Connect to Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Check if a password reset code is in the web address
if "code" in st.query_params:
    recovery_code = st.query_params["code"]
    try:
        # Trade the code for an active login session
        supabase.auth.exchange_code_for_session({"auth_code": recovery_code})

        # Wipe the code from the address bar so it does not run twice
        st.query_params.clear()

        # Refresh the page to load the main dashboard
        st.rerun()
    except Exception as e:
        st.error("That reset link has expired or is invalid. Please request a new one.")

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

    # Add this right below your existing Login button

    with st.expander("Forgot Password?"):
        st.write("Enter your email to receive a secure reset link.")
        reset_email = st.text_input("Account Email", key="reset_email_input")

        if st.button("Send Reset Link"):
            if reset_email:
                try:
                    # Make sure to replace this with your actual live Streamlit URL
                    app_url = "https://your-app-url.streamlit.app"
                    supabase.auth.reset_password_email(
                        reset_email,
                        options={"redirect_to": app_url}
                    )
                    st.success("The reset link has been sent. Please check your inbox.")
                except Exception as e:
                    st.error(f"Failed to send the email: {e}")
            else:
                st.warning("Please enter your email address first.")


def calculate_streak(log_dates, today):
    streak = 0
    current_date = today
    while str(current_date) in log_dates:
        streak += 1
        current_date -= datetime.timedelta(days=1)
    return streak


def dashboard():

    with st.expander("Account Settings & Password Reset"):
        st.write("If you used a recovery link to get here, please set a new password now.")
        new_password = st.text_input("Enter New Password", type="password")

        if st.button("Update Password"):
            if len(new_password) >= 6:
                try:
                    supabase.auth.update_user({"password": new_password})
                    st.success("Your password has been successfully updated.")
                except Exception as e:
                    st.error(f"Failed to update password: {e}")
            else:
                st.warning("Your password must be at least 6 characters long.")

    st.success("You are logged in.")

    if st.button("Log Out"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    st.divider()

    user_id = st.session_state.user.id
    today = datetime.date.today()

    participant_data = supabase.table("participants").select("*").eq("id", user_id).execute()
    p_data = participant_data.data[0] if participant_data.data else {}
    st.subheader(f"Welcome, {p_data.get('full_name', 'Participant')}")

    # Create tabs for the participant view
    tab1, tab2 = st.tabs(["My Tracker", "Group Feed"])

    with tab1:
        logs_data = supabase.table("logs").select("log_date").eq("participant_id", user_id).execute()
        log_dates = [log['log_date'] for log in logs_data.data] if logs_data.data else []

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

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Check-ins", total_checkins)
        col2.metric("Consistency", f"{consistency_score}%")
        col3.metric("Current Streak", calculate_streak(log_dates, today))

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

                    # Generate a random 8-character string to act as the AppSheet Log ID
                    log_id = uuid.uuid4().hex[:8]

                    # We use XLOOKUP combined with ROW() to match the email in Column F to the Participants tab
                    gs_formula = '=XLOOKUP(INDIRECT("F"&ROW()), Participants!J:J, Participants!I:I, "")'

                    new_row = [
                        log_id,  # Col A: Log ID
                        str(today),  # Col B: Date
                        gs_formula,  # Col C: Formula to fetch the old Google Sheet ID
                        level,  # Col D: Level
                        notes,  # Col E: Notes
                        p_data.get('email')  # Col F: Email (Hidden helper column)
                    ]

                    # The USER_ENTERED setting tells Google Sheets to actually run the formula instead of pasting it as text
                    gs_logs_sheet.append_row(new_row, value_input_option="USER_ENTERED")

                    st.success("Successfully logged activity for today!")
                    st.rerun()
                except Exception as e:
                    st.error("Failed to save your log. Please try again.")

    with tab2:
        st.subheader("Today's Check-ins")
        all_logs = supabase.table("logs").select("*").eq("log_date", str(today)).execute()
        all_participants = supabase.table("participants").select("*").execute()

        parts_dict = {p['id']: p for p in all_participants.data}

        if all_logs.data:
            # Open a container to hold the chat feed
            feed_html = "<div style='display: flex; flex-direction: column; gap: 12px; margin-top: 10px;'>"

            for log in all_logs.data:
                pid = log['participant_id']
                if pid in parts_dict:
                    person = parts_dict[pid]
                    name = person.get('full_name', 'Someone')

                    start_str = person.get('start_date')
                    day_number = "XX"
                    if start_str:
                        start_d = datetime.datetime.strptime(str(start_str), "%Y-%m-%d").date()
                        day_number = (today - start_d).days + 1

                    log_level = log.get('level', 'Completed')

                    # Create the individual chat bubble matching your brand colors
                    bubble = f"""<div style='background-color: #15332b; border-radius: 0px 15px 15px 15px; padding: 12px 16px; width: fit-content; min-width: 200px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);'>
<div style='color: #D4AF37; font-weight: bold; margin-bottom: 5px; font-family: "Cinzel", serif; font-size: 14px;'>{name}</div>
<div style='color: #F0F0F0; font-family: "Montserrat", sans-serif; line-height: 1.5; font-size: 15px;'>
Day {day_number}<br>
Done✅<br>
The {log_level}
</div>
</div>"""
                    feed_html += bubble

            feed_html += "</div>"
            st.markdown(feed_html, unsafe_allow_html=True)
        else:
            st.write("No one has checked in yet today. Be the first.")


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
    today = datetime.date.today()

    # Create tabs for the admin view
    admin_tab1, admin_tab2 = st.tabs(["Group Leaderboard", "Individual Tracker"])

    with admin_tab1:
        st.subheader("Group Leaderboard Overview")
        logs_response = supabase.table("logs").select("*").execute()

        if logs_response.data and participants:
            logs_df = pd.DataFrame(logs_response.data)
            parts_df = pd.DataFrame(participants)

            log_counts = logs_df.groupby("participant_id").size().reset_index(name="Total Check-ins")
            leaderboard = pd.merge(parts_df, log_counts, left_on="id", right_on="participant_id", how="left")
            leaderboard["Total Check-ins"] = leaderboard["Total Check-ins"].fillna(0).astype(int)

            def get_consistency(row):
                start_str = row.get("start_date")
                if not start_str or pd.isna(start_str):
                    return 0
                start_d = datetime.datetime.strptime(str(start_str), "%Y-%m-%d").date()
                days = (today - start_d).days + 1
                if days > 0:
                    return round((row["Total Check-ins"] / days) * 100, 1)
                return 0

            def get_streak(row):
                pid = row["id"]
                user_logs = logs_df[logs_df["participant_id"] == pid]["log_date"].tolist()
                return calculate_streak(user_logs, today)

            leaderboard["Consistency %"] = leaderboard.apply(get_consistency, axis=1)
            leaderboard["Current Streak"] = leaderboard.apply(get_streak, axis=1)

            display_df = leaderboard[
                ["full_name", "track", "Total Check-ins", "Current Streak", "Consistency %"]].sort_values(
                by="Consistency %", ascending=False)
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.write("Not enough data to display the leaderboard yet.")

    with admin_tab2:
        st.subheader("Manage Individual Participant")
        selected_name = st.selectbox("Select Participant", list(name_to_id.keys()))
        participant_id = name_to_id[selected_name]

        # Show quick stats for the selected person
        user_logs_response = supabase.table("logs").select("log_date").eq("participant_id", participant_id).execute()
        u_log_dates = [log['log_date'] for log in user_logs_response.data] if user_logs_response.data else []

        st.write(f"**Total Logs:** {len(u_log_dates)} | **Current Streak:** {calculate_streak(u_log_dates, today)}")

        st.write("---")
        st.write("Log on their behalf")
        selected_date = st.date_input("Select Date", today)
        level = st.radio("Level", ["Floor", "Baseline", "Ceiling"], horizontal=True)
        notes = st.text_area("Notes")

        if st.button("Submit Admin Log"):
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
