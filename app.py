import os
import base64
import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import uuid


# 1. Force Python to look in the exact same folder as this script
current_folder = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(current_folder, "logo.png")

def get_base64_image(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return ""


logo_text = get_base64_image(logo_path)


st.set_page_config(page_title="The Annual Architect", layout="wide")


# The cache command saves this connection so it only runs once
@st.cache_resource
def connect_to_google():
    # Setup Google connection
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # For Streamlit Cloud, you will pull the JSON from st.secrets instead of a file
    google_creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS_JSON"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds_dict, scope)
    gs_client = gspread.authorize(creds)

    # Open both documents
    main_doc = gs_client.open("The Annual Architect (Responses)")
    waitlist_doc = gs_client.open("The Annual Architect - Cohort 2")

    return main_doc, waitlist_doc


# Call the cached function to get your sheet ready
gs_document, gs_waitlist_document = connect_to_google()

# Assign the specific tabs to their own variables
gs_logs_sheet = gs_document.worksheet("Logs")
gs_registrations_sheet = gs_document.worksheet("Registrations")
gs_waitlist_sheet = gs_waitlist_document.worksheet("Waitlist")

# Connect to Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Initialize the user session state immediately
if "user" not in st.session_state:
    st.session_state.user = None

# Track which page the user is currently viewing
if "current_page" not in st.session_state:
    st.session_state.current_page = "landing"

# Rehydrate the Supabase client so it remembers the session after a rerun
if "access_token" in st.session_state and "refresh_token" in st.session_state:
    try:
        supabase.auth.set_session(st.session_state["access_token"], st.session_state["refresh_token"])
    except Exception:
        pass

# Check if a token_hash is in the web address BEFORE drawing any screens
if "token_hash" in st.query_params:
    recovery_token = st.query_params["token_hash"]
    try:
        response = supabase.auth.verify_otp({
            "token_hash": recovery_token,
            "type": "recovery"
        })

        st.session_state.user = response.user

        # Save the tokens so the client survives the page refresh
        st.session_state["access_token"] = response.session.access_token
        st.session_state["refresh_token"] = response.session.refresh_token

        st.session_state.show_reset_form = True

        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"That reset link has expired or is invalid. Error: {e}")


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Montserrat:wght@300;400;600&display=swap');

/* Pull the whole page up to reduce empty white space at the top */
.block-container {
    padding-top: 3.5rem !important;
    padding-bottom: 2rem !important;
}
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

/* This draws the dark green background and the faint gold grid */
.stApp {
    background-color: #0a1f1a;
    background-image: 
        linear-gradient(rgba(212, 175, 55, 0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(212, 175, 55, 0.05) 1px, transparent 1px);
    background-size: 40px 40px;
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

# 3. ONLY add the watermark layer if the image was successfully found
if logo_text:
    st.markdown(f"""
    <style>
    .stApp::before {{
        content: "";
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 800px;
        height: 800px;
        background-image: url("data:image/png;base64,{logo_text}");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        opacity: 0.15;
        z-index: 0;
        pointer-events: none;
    }}
    </style>
    """, unsafe_allow_html=True)
else:
    # Show exactly where it is trying to find the file if it fails
    st.error(f"Cannot load logo. Please verify 'logo.png' is placed exactly here: {logo_path}")


def landing_page():
    # --- TOP HEADER BAR ---
    # We create a thin row at the top. The empty left column pushes the buttons to the right.
    head_left, head_login, head_waitlist = st.columns([7, 1, 1.5])

    with head_login:
        if st.button("Log In", key="top_login", width='stretch'):
            st.session_state.current_page = "login"
            st.rerun()

    with head_waitlist:
        # We use a primary button to make the waitlist stand out
        if st.button("Join Waitlist", type="primary", key="top_waitlist", width='stretch'):
            st.session_state.current_page = "waitlist"
            st.rerun()

    # --- HERO SECTION ---
    st.markdown("<center><h1 style='font-size: 3rem; margin-top: 10px;'>The Annual Architect Program</h1></center>",
                unsafe_allow_html=True)
    st.markdown("<center><h3 style='margin-bottom: 2rem; color: #D4AF37;'>Build Systems That Last</h3></center>",
                unsafe_allow_html=True)

    # --- THE PROBLEM SECTION (Withholding the Solution) ---
    intro_left, intro_center, intro_right = st.columns([1, 4, 1])

    with intro_center:
        st.write(
            "Setting a goal is easy, but maintaining the daily routine required to reach it seems incredibly difficult. Most tracking methods fail because they demand absolute perfection.")

        st.markdown("""
        Traditional accountability makes you falls apart as:
        * A single missed day triggers a cycle of guilt that makes high performers abandon their goals entirely.
        * Current applications assume progress is an unbroken line and punish you for taking a rest.
        * Group chats become noisy distractions and end up as "just another WhatsApp group" rather than helpful support networks.
        * People are forced to rely on external motivation, which fades quickly when life gets busy.
        """)

        st.write(
            "We approach human behavior differently. Our program provides a quiet environment and "
            "a strict framework that accounts for normal human error. "
            "We give you the structure required to keep moving forward, especially on the days you feel exhausted.")

    st.divider()

    # --- EXPANDED DATA SECTION ---
    st.markdown("<center><h2 style='color: #D4AF37;'>The Data</h2></center>", unsafe_allow_html=True)

    # Adding more context using HTML to control the paragraph width so it reads well
    data_context = """
    <div style='max-width: 1100px; margin: 0 auto; text-align: center; margin-bottom: 25px; font-size: 1.2rem; line-height: 1.6;'>
        Our tracking system actively protects you from the shame cycle. We have analyzed the daily logs of our current 
        participants, and the numbers show exactly why our approach works.
        <p>Thirty-seven percent of all recorded actions are 'Floor' days. These are the days our members were completely 
        exhausted but used our specific protocol to rescue their habit instead of breaking their streak. </p>
        <p>The graphs below illustrate this cumulative progress and the actual breakdown of user engagement.</p>
    </div>
    """
    st.markdown(data_context, unsafe_allow_html=True)


    graph_col1, graph_col2 = st.columns(2)
    with graph_col1:
        st.image("progress_chart.png", caption="Cumulative progress over 90 days", width='stretch')
    with graph_col2:
        st.image("pie_chart.png", caption="Habit Rescue Breakdown", width='stretch')

    st.divider()

    # --- TWO-ROW TESTIMONIAL SECTION ---
    st.markdown("<center><h2 style='color: #D4AF37;'>Member Experiences</h2></center>", unsafe_allow_html=True)

    data_context = """
        <div style='max-width: 1100px; margin: 0 auto; text-align: center; margin-bottom: 25px; font-size: 1.2rem; line-height: 1.6;'>
            Don't believe it? Hear what the participants have to say...</p>
        </div>
        """
    st.markdown(data_context, unsafe_allow_html=True)

    def create_testimonial_card(quote, author):
        return f"""
        <div style='background-color: #15332b; border-left: 4px solid #D4AF37; padding: 20px; margin-bottom: 20px; border-radius: 4px; height: 100%;'>
            <p style='font-style: italic; color: #F0F0F0;'>"{quote}"</p>
            <p style='color: #D4AF37; font-weight: bold; text-align: right;'>- {author}</p>
        </div>
        """

    # First Row of Testimonials
    row1_col1, row1_col2, row1_col3 = st.columns(3)
    with row1_col1:
        st.markdown(create_testimonial_card(
            "I've fallen in love with studying the word and Jesus. I was addicted to K-dramas. I haven't watched any through out this period. I now wake up and read my Bible first thing in the morning",
            "C.N."
        ), unsafe_allow_html=True)
    with row1_col2:
        st.markdown(create_testimonial_card(
            "Where do I start? It has helped me to maintain a consistent fellowship with God despite my feelings or moods. At the beginning of the year, I usually want to improve my relationship with God but I never make it past the 7th day. I can't believe how well it has been.",
            "U.U"
        ), unsafe_allow_html=True)
    with row1_col3:
        st.markdown(create_testimonial_card(
            "The program has given me a clearer understanding of my personality and generally increased my level of self awareness.",
            "O.E."
        ), unsafe_allow_html=True)

    # Second Row of Testimonials
    row2_col1, row2_col2, row2_col3 = st.columns(3)
    with row2_col1:
        st.markdown(create_testimonial_card(
            "I showed up for an entire week which has been impossible up until this point.",
            "F.A."
        ), unsafe_allow_html=True)
    with row2_col2:
        st.markdown(create_testimonial_card(
            "Regardless of how exhausted I am, I'm able to hit the floor thanks to what we learned during the pre-program sessions. I may get carried away but now I'm so conscious of it I have set reminders and I don't snooze them. I can't believe I've been able to come this far."
            "At the beginning, I didn't think 90 days was possible",
            "O.N."
        ), unsafe_allow_html=True)
    with row2_col3:
        st.markdown(create_testimonial_card(
            "Because of the structure, I have been able to organize my time and set proper schedules as any delay or lazy activity would affect my sleep time and impact my commitment. I started a 30 day challenge of code writing. Previously I wouldn't even get to day 7 but I'm on day 18. It's amazing ",
            "T.S"
        ), unsafe_allow_html=True)

    st.divider()

    # --- BOTTOM CALL TO ACTION ---
    out_left, out_center, out_right = st.columns([1, 2, 1])
    with out_center:
        st.info("Ready to stop starting over and build consistency? Join the waitlist for our next cohort.")
        if st.button("Join the Waitlist", key="bottom_waitlist", width='stretch'):
            st.session_state.current_page = "waitlist"
            st.rerun()

def signup_page():
    # Use the same column ratio to keep the width uniform across pages
    left_margin, center_column, right_margin = st.columns([1, 2, 1])

    with center_column:
        if st.button("← Back to Home"):
            st.session_state.current_page = "landing"
            st.rerun()

        st.subheader("The Annual Architect 1.0 Registration")
        st.write(
            "This is not a casual chat group. This is a community for women ready to build a life of purpose and consistency. We are looking for members who are tired of starting over every January. Please answer honestly.")
        st.write("*Your answers help us ensure this is the right room for you.*")

        name = st.text_input("1. Full Name *")
        whatsapp = st.text_input("2. Whatsapp Number *")
        email = st.text_input("3. Email Address *")
        password = st.text_input("Create a Password for your account *", type="password",
                                 help="You will use this to log in immediately after registering.")

        st.write("### Your 'Why'")
        goal = st.text_area(
            "4. What is the ONE goal you have written down for the last few years but still haven't achieved? *")

        why_not_achieved = st.radio(
            "5. Why do you think you haven't achieved it yet? Be honest. *",
            [
                "I didn't have a plan.",
                "I lost motivation after a few weeks.",
                "I tried to do too much at once.",
                "I didn't have anyone to keep me accountable.",
                "Other"
            ]
        )

        if why_not_achieved == "Other":
            why_not_achieved = st.text_input("Please specify your reason:")

        track = st.selectbox(
            "6. We focus on four core 'tracks' for growth. If you could only improve ONE area in the next 90 days, which would it be?",
            [
                "Physical Well-being (Gym, Nutrition, Sleep)",
                "Intellectual Growth (Reading, Skills, Career)",
                "Spiritual/Purpose Alignment (Quiet time, Clarity, Faith)",
                "Financial Growth (Savings Challenges, Budgeting, Investment)"
            ]
        )

        st.write("### The Commitment")
        commitment = st.slider(
            "7. This program requires daily check-ins. On a scale of 1 to 10, how willing are you to show up even on days when you feel tired or unmotivated? *",
            1, 10, 5
        )

        quick_fix = st.text_area(
            "8. Real growth is often boring. It is about doing the same small things every day. Are you looking for a 'quick fix' or are you ready to build a long-term system? *")

        success_vision = st.text_area(
            "9. The 'Peak Within' philosophy is about looking inward to build outward. What does 'success' look like to you by the end of next year? *")

        if st.button("Submit Registration", width='stretch'):
            if not name or not email or not whatsapp or not password:
                st.warning("Please fill in your name, email, Whatsapp number and password to proceed.")
            elif len(password) < 6:
                st.warning("Your password must be at least 6 characters long.")
            else:
                existing = supabase.table("registrations").select("email").eq("email", email).execute()

                if len(existing.data) > 0:
                    st.error("This email address is already in our system. Please click 'Back to Home' and select Log In.")
                else:
                    try:
                        # 1. Create the actual login account in Supabase Auth
                        auth_response = supabase.auth.sign_up({"email": email, "password": password})

                        current_time = str(datetime.datetime.now())

                        # 2. Save their application to the registrations table
                        reg_payload = {
                            "full_name": name,
                            "whatsapp": whatsapp,
                            "email": email,
                            "goal": goal,
                            "why_not_achieved": why_not_achieved,
                            "core_track": track,
                            "commitment_level": commitment,
                            "growth_mindset": quick_fix,
                            "success_vision": success_vision,
                            "created_at": current_time
                        }
                        supabase.table("registrations").insert(reg_payload).execute()

                        # 3. Save to Google Sheets
                        new_row = [
                            current_time,
                            name,
                            whatsapp,
                            email,
                            goal,
                            why_not_achieved,
                            track,
                            str(commitment),
                            quick_fix,
                            success_vision
                        ]
                        gs_registrations_sheet.append_row(new_row, value_input_option="USER_ENTERED")

                        st.success("Registration successful! Please click 'Back to Home' and log in with your new password to access the pre-program activities.")
                    except Exception as e:
                        st.error(f"Failed to create your account. Error: {e}")


def waitlist_page():
    left, center, right = st.columns([1, 2, 1])

    with center:
        # We also reset the submission state if they click back, just in case
        if st.button("← Back to Home"):
            st.session_state.current_page = "landing"
            st.session_state.waitlist_submitted = False
            st.rerun()

        st.markdown("<h1 style='color: #D4AF37; text-align: center;'>Join the Next Cohort</h1>", unsafe_allow_html=True)

        # 1. Initialize the memory switch
        if "waitlist_submitted" not in st.session_state:
            st.session_state.waitlist_submitted = False

        # 2. If they have not submitted yet, show the form
        if not st.session_state.waitlist_submitted:
            st.write(
                "Enter your details below to secure your spot in line. We will notify you the moment applications open.")

            with st.form("waitlist_form"):
                name = st.text_input("Full Name")
                email = st.text_input("Email Address")
                phone = st.text_input("Phone Number")
                reason = st.text_area("Why do you want to join this program?")

                # Make the button visually distinct using the primary type
                submit = st.form_submit_button("Join Waitlist", type="primary")

                if submit:
                    if name and email and phone and reason:
                        try:
                            current_time = str(datetime.datetime.now())

                            payload = {
                                "full_name": name,
                                "email": email,
                                "phone": phone,
                                "reason": reason,
                                "created_at": current_time
                            }

                            # Keep the returning="minimal" to prevent read errors
                            supabase.table("waitlist_form").insert(payload, returning="minimal").execute()

                            new_row = [current_time, name, email, phone, reason]
                            gs_waitlist_sheet.append_row(new_row)

                            # 3. Flip the switch to true and reload the page
                            st.session_state.waitlist_submitted = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error saving to waitlist: {e}")
                    else:
                        st.warning("Please fill out all fields.")

        # 4. If the switch is true, ONLY show the success message
        else:
            st.success("Thank you! Your spot on the waitlist is secured. We will reach out soon.")

            # Give them a way to submit another person if needed
            if st.button("Submit Another Response"):
                st.session_state.waitlist_submitted = False
                st.rerun()


def login():
    # The 1, 2, 1 ratio creates empty margins on the sides
    left_margin, center_column, right_margin = st.columns([1, 2, 1])

    with center_column:
        if st.button("← Back to Home"):
            st.session_state.current_page = "landing"
            st.rerun()

        st.subheader("Participant Login")
        email = st.text_input("Email Address")
        password = st.text_input("Password", type="password")

        # Added use_container_width=True so the button matches the text boxes
        if st.button("Log In", width='stretch'):
            try:
                response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = response.user
                st.session_state["access_token"] = response.session.access_token
                st.session_state["refresh_token"] = response.session.refresh_token
                st.rerun()
            except Exception as e:
                st.error("Login failed. Please check your email and password.")

        with st.expander("Forgot Password?"):
            st.write("Enter your email to receive a secure reset link.")
            reset_email = st.text_input("Account Email", key="reset_email_input")

            if st.button("Send Reset Link"):
                if reset_email:
                    try:
                        app_url = "https://annual-architects-program.streamlit.app"
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

    # If they have not logged today yet, shift the starting point to yesterday
    if str(current_date) not in log_dates:
        current_date -= datetime.timedelta(days=1)

    # Count backward as long as consecutive days are found
    while str(current_date) in log_dates:
        streak += 1
        current_date -= datetime.timedelta(days=1)

    return streak


def pre_program_page():
    st.markdown("<h2 style='margin-top: -10px;'>Pre-Program Setup</h2>", unsafe_allow_html=True)

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("Log Out", width='stretch'):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.pop("access_token", None)
            st.session_state.pop("refresh_token", None)
            st.rerun()

    st.write(
        "Welcome. Before you gain access to the daily tracker, you must complete the following foundational sessions. Please watch the videos, review the slides, and submit your activities below.")
    st.divider()

    # Using tabs helps separate the work so it is not overwhelming
    tab0, tab1, tab2 = st.tabs(["Session 0", "Session 1", "Session 2"])

    with tab0:
        st.subheader("Session 0: Introduction")
        st.video("https://drive.google.com/file/d/10i4uXLVQZzZIf8EvQsI-H7UFx5ymeQTb/view?usp=sharing")
        st.markdown("[Click here to view the Session 0 Slides](https://drive.google.com/file/d/1ee3949sadbKxF4wz-pxXlz9Grlj_nXFZ/view?usp=sharing)")

        st.write("### Activity 0")
        activity_0 = st.text_area("What is your biggest takeaway from this introduction?", key="act0")
        if st.button("Save Session 0 Activity"):
            # You can build a database save function here later if you want to keep their answers
            st.success("Activity saved. Please proceed to Session 1.")

    with tab1:
        st.subheader("Session 1: The Internal Architect")
        st.video("https://drive.google.com/file/d/1YPesjruwdBSf4TMABN_lmLSkeP7jOcNh/view?usp=sharing")
        st.markdown("[Click here to view the Session 1 Slides](https://drive.google.com/file/d/1IQmAJ9I9iBn1kYUn8QywZsMqlyj26oUT/view?usp=sharing)")

        st.write("### Activity 1")
        activity_1 = st.text_area("Draft your initial system based on the four core tracks.", key="act1")
        if st.button("Save Session 1 Activity"):
            st.success("Activity saved. Please proceed to Session 2.")

    with tab2:
        st.subheader("Session 2: The External Architect")
        st.video("https://drive.google.com/file/d/164csnS-ONgUGRzfYSVB_ppxwGoPniu2O/view?usp=sharing")
        st.markdown("[Click here to view the Session 2 Slides](https://drive.google.com/file/d/11pLoB3UDCh4KxkqCbC-kV6sW4aqZuDBR/view?usp=sharing)")

        st.write("### Final Activity")
        activity_2 = st.text_area("Commit to your daily routine. What exactly will you do every day?", key="act2")

        st.info(
            "Submitting this final activity will officially add you to the active program and open your tracking dashboard.")

        if st.button("Submit Final Activity & Enter Program", type="primary"):
            user_email = st.session_state.user.email
            user_id = st.session_state.user.id

            # Fetch their original registration data
            reg_data = supabase.table("registrations").select("*").eq("email", user_email).execute()

            if reg_data.data:
                person = reg_data.data[0]
                try:
                    # Move them into the active participants table
                    participant_payload = {
                        "id": user_id,
                        "full_name": person.get("full_name"),
                        "email": user_email,
                        "track": person.get("core_track"),
                        "start_date": str(datetime.date.today())
                    }
                    supabase.table("participants").insert(participant_payload).execute()

                    st.success("Congratulations! You are officially in. Loading your dashboard now...")
                    st.rerun()
                except Exception as e:
                    st.error(f"There was an error upgrading your account: {e}")


def dashboard():
    # Create a layout row with two columns (making the left column 4 times wider)
    header_col, logout_col = st.columns([4, 1])

    with header_col:
        # Using h2 makes it smaller than the default title size
        st.markdown("<h2 style='margin-top: -10px;'>Annual Architects Program</h2>", unsafe_allow_html=True)

    with logout_col:
        # The button stretches to fill its column area and pushes to the right
        if st.button("Log Out", width='stretch'):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.pop("access_token", None)
            st.session_state.pop("refresh_token", None)
            st.rerun()

    # Place this directly below your header and logout button columns
    with st.expander("⚙️ Account Settings & Password Reset"):
        st.write("Update your password below to secure your account.")

        # We use keys here so Streamlit does not confuse these text boxes with the login page
        new_password = st.text_input("New Password", type="password", key="dash_new_pass")
        confirm_password = st.text_input("Confirm New Password", type="password", key="dash_confirm_pass")

        if st.button("Update Password", width='stretch', key="dash_update_btn"):
            if not new_password or not confirm_password:
                st.warning("Please fill out both fields.")
            elif new_password != confirm_password:
                st.error("Your passwords do not match. Please try again.")
            elif len(new_password) < 6:
                st.warning("Your new password must be at least 6 characters long.")
            else:
                try:
                    # Supabase command to update the currently logged-in user
                    supabase.auth.update_user({"password": new_password})
                    st.success("Your password has been successfully updated.")
                except Exception as e:
                    st.error(f"Failed to update password. Error: {e}")

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
                        "notes": notes,
                        "logged_by": "Participant"
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
                        p_data.get('email'),  # Col F: Email (Hidden helper column)
                        "Participant"  # Col G: Logged By
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
    header_col, logout_col = st.columns([4, 1])

    with header_col:
        st.markdown("<h2 style='margin-top: -10px;'>Annual Architects Program</h2>", unsafe_allow_html=True)

    with logout_col:
        if st.button("Log Out", width='stretch'):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.pop("access_token", None)
            st.session_state.pop("refresh_token", None)
            st.rerun()

    # Place this directly below your admin header and logout button
    with st.expander("⚙️ Account Settings & Password Reset"):
        st.write("Update your admin password below to secure your account.")

        # The keys here start with 'admin_' to keep them completely separate
        new_password = st.text_input("New Password", type="password", key="admin_new_pass")
        confirm_password = st.text_input("Confirm New Password", type="password", key="admin_confirm_pass")

        if st.button("Update Password", width='stretch', key="admin_update_btn"):
            if not new_password or not confirm_password:
                st.warning("Please fill out both fields.")
            elif new_password != confirm_password:
                st.error("Your passwords do not match. Please try again.")
            elif len(new_password) < 6:
                st.warning("Your new password must be at least 6 characters long.")
            else:
                try:
                    # Supabase updates the password for whoever is currently logged in
                    supabase.auth.update_user({"password": new_password})
                    st.success("Your admin password has been successfully updated.")
                except Exception as e:
                    st.error(f"Failed to update password. Error: {e}")

    st.divider()
    st.header("Admin Controls")

    parts_response = supabase.table("participants").select("*").execute()
    participants = parts_response.data

    # Fetch Waitlist data
    waitlist_response = supabase.table("waitlist").select("*").order("created_at", desc=True).execute()
    waitlist_data = waitlist_response.data

    if not participants:
        st.info("No participants found.")
        return

    name_to_id = {p["full_name"]: p["id"] for p in participants if p.get("full_name")}
    today = datetime.date.today()

    # Create tabs for the admin view, now including a third tab for today
    admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
        "Group Leaderboard",
        "Individual Tracker",
        "Today's Activity",
        "Cohort 2 Waitlist"
    ])

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
            st.dataframe(display_df, width='stretch', hide_index=True)
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
                    # Save to Supabase
                    log_payload = {
                        "participant_id": participant_id,
                        "log_date": str(selected_date),
                        "level": level,
                        "notes": notes,
                        "logged_by": "Admin"
                    }
                    supabase.table("logs").insert(log_payload).execute()

                    # Find the target participant's email for the Google Sheet formula
                    target_participant = next((p for p in participants if p["id"] == participant_id), None)
                    target_email = target_participant.get("email") if target_participant else ""

                    # Save to Google Sheets
                    log_id = uuid.uuid4().hex[:8]
                    gs_formula = '=XLOOKUP(INDIRECT("F"&ROW()), Participants!J:J, Participants!I:I, "")'

                    new_row = [
                        log_id,  # Col A: Log ID
                        str(selected_date),  # Col B: Date
                        gs_formula,  # Col C: Formula to fetch the old Google Sheet ID
                        level,  # Col D: Level
                        notes,  # Col E: Notes
                        target_email,  # Col F: Email (Hidden helper column)
                        "Admin"  # Col G: Logged By
                    ]

                    gs_logs_sheet.append_row(new_row, value_input_option="USER_ENTERED")

                    st.success(
                        f"Successfully logged activity for {selected_name} on {selected_date} and synced to Google Sheets!")
                except Exception as e:
                    st.error(f"Failed to save the log. Error: {e}")

        # Add this completely new block for the third tab
        with admin_tab3:
            st.subheader(f"Activity for {today.strftime('%B %d, %Y')}")

            # Pull all logs specifically for today
            today_logs_response = supabase.table("logs").select("*").eq("log_date", str(today)).execute()

            if today_logs_response.data and participants:
                # Convert the raw data into pandas dataframes
                t_logs_df = pd.DataFrame(today_logs_response.data)
                p_df = pd.DataFrame(participants)

                # Merge the logs with the participant data to get their real names
                today_merged = pd.merge(t_logs_df, p_df, left_on="participant_id", right_on="id", how="left")

                # Pick only the columns we want to show and rename them for the admin view
                display_today = today_merged[["full_name", "level", "notes"]]
                display_today.columns = ["Participant Name", "Level Hit", "Notes"]

                st.write(f"**Total Check-ins Today:** {len(today_logs_response.data)}")
                st.dataframe(display_today, width='stretch', hide_index=True)
            else:
                st.info("No participants have checked in yet today.")

        with admin_tab4:
            st.subheader("Cohort 2 Waitlist Management")

            if waitlist_data:
                # Show a high-level metric for total count
                total_waitlist = len(waitlist_data)
                st.metric("Total People on Waitlist", total_waitlist)

                # Convert to DataFrame for easy viewing
                df_waitlist = pd.DataFrame(waitlist_data)

                # Clean up columns for display
                display_waitlist = df_waitlist[["full_name", "email", "phone", "reason", "created_at"]]
                display_waitlist.columns = ["Name", "Email", "Phone", "Why they want to join", "Signed Up At"]

                st.dataframe(display_waitlist, width='stretch', hide_index=True)

                # Add a button to download the list as a CSV for your records
                csv = display_waitlist.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Waitlist as CSV",
                    data=csv,
                    file_name=f"cohort_2_waitlist_{datetime.date.today()}.csv",
                    mime="text/csv",
                )
            else:
                st.info("No one has joined the waitlist yet. Time to share the link.")


# Routing logic to show the right screen
if st.session_state.user is None:
    if st.session_state.current_page == "landing":
        landing_page()
    elif st.session_state.current_page == "login":
        login()
    elif st.session_state.current_page == "signup":
        signup_page()
    elif st.session_state.current_page == "waitlist":
        waitlist_page()
else:
    # If the trigger is active, show the password form at the very top
    if st.session_state.get("show_reset_form"):
        if st.session_state.get("show_reset_form"):
            st.warning("You used a recovery link. Please set your new password below.")
            new_password = st.text_input("Enter New Password", type="password", key="universal_reset")

            if st.button("Save New Password"):
                if len(new_password) >= 6:
                    try:
                        supabase.auth.update_user({"password": new_password})
                        st.success("Your password has been successfully updated.")

                        # Turn off the trigger so the form hides itself
                        st.session_state.show_reset_form = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to update password: {e}")
                else:
                    st.warning("Your password must be at least 6 characters long.")

            st.divider()

    # Continue loading the correct dashboard underneath
    user_email = st.session_state.user.email
    admin_check = supabase.table("admins").select("*").eq("email", user_email).execute()

    if len(admin_check.data) > 0:
        admin_dashboard()
    else:
        # Check if the user has made it into the active participants table yet
        participant_check = supabase.table("participants").select("*").eq("email", user_email).execute()

        if len(participant_check.data) > 0:
            # They finished the pre-program work
            dashboard()
        else:
            # They are still pending
            pre_program_page()