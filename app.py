import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import io
from datetime import datetime
import requests
import os 
import time


st.set_page_config(page_title="Job Portal", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }

    /* Hide default Streamlit elements for a clean app feel */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Clean background */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Input fields styling */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        border-radius: 8px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
        padding: 10px 14px !important;
        font-size: 14px !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus, .stSelectbox>div>div>div:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
    }
    
    /* Global Buttons */
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        background-color: #ffffff !important;
        color: #334155 !important;
        border: 1px solid #cbd5e1 !important;
        padding: 8px 16px !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
    }
    .stButton>button:hover {
        background-color: #f8fafc !important;
        border-color: #94a3b8 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        color: #0f172a !important;
    }
    /* Primary buttons */
    button[kind="primary"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border: 1px solid #1d4ed8 !important;
    }
    button[kind="primary"]:hover {
        background-color: #1d4ed8 !important;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2) !important;
        color: #ffffff !important;
    }
    
    /* Advanced Custom Cards */
    .custom-card {
        background: #ffffff;
        padding: 24px;
        border-radius: 12px !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
        margin-bottom: 24px;
        transition: box-shadow 0.2s ease, transform 0.2s ease;
    }
    .custom-card:hover {
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
        transform: translateY(-2px);
    }
    
    /* Fallback Card-like containers for Streamlit Forms */
    div[data-testid="stForm"] {
        border-radius: 12px !important;
        background: white !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1) !important;
        padding: 24px !important;
        border: 1px solid #e2e8f0 !important;
    }
    
    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #0f172a;
        font-weight: 600;
        letter-spacing: -0.025em;
    }
    
    p {
        color: #475569;
    }
    
    /* Disable Mobile Pull-to-Refresh */
    body, html, .stApp {
        overscroll-behavior-y: none !important;
        overscroll-behavior: none !important;
    }
</style>
""", unsafe_allow_html=True)

#DATABASE
@st.cache_resource
def init_db():
    conn = sqlite3.connect('job_portal.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        mobile TEXT PRIMARY KEY, role TEXT, name TEXT, aadhar TEXT DEFAULT '',
        skills TEXT DEFAULT '', experience TEXT DEFAULT '', location TEXT DEFAULT '',
        work_image BLOB, password TEXT, created_at TEXT DEFAULT (datetime('now'))
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, creator TEXT, title TEXT,
        skills TEXT DEFAULT '', salary TEXT DEFAULT '', location TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1_mobile TEXT, user2_mobile TEXT,
        job_id INTEGER,
        message TEXT,
        sender_mobile TEXT,
        timestamp TEXT DEFAULT (datetime('now')),
        is_read INTEGER DEFAULT 0
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        creator_mobile TEXT,
        seeker_mobile TEXT,
        rating INTEGER,
        review TEXT,
        work_image BLOB,
        timestamp TEXT DEFAULT (datetime('now'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS hires (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        seeker_mobile TEXT,
        status TEXT DEFAULT 'hired',
        timestamp TEXT DEFAULT (datetime('now'))
    )''')
    
    c.execute("SELECT COUNT(*) FROM users WHERE mobile='9999999999'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users VALUES ('9999999999','Admin','Super Admin','','','','',NULL,'admin123',datetime('now'))")
    conn.commit()
    return conn

conn = init_db()

#TRANSLATIONS
TRANSLATIONS = {
    "eng": {
        "title": "Job Connect", "lang_title": "Language", "english": "English", "tamil": "தமிழ்",
        "menu": "Menu", "login": "Login", "register": "Register", "job_seeker": "Job Seeker", 
        "job_creator": "Job Creator", "admin": "Admin", "name": "Full Name", "org_name": "Organization Name",
        "mobile": "Mobile Number", "aadhar": "Aadhar Number", "skills": "Skills", "experience": "Experience",
        "location": "Location", "password": "Password", "send_otp": "Send OTP", "enter_otp": "Enter OTP (123456)",
        "complete_reg": "Complete Registration", "work_photo": "Work Photo", "post_job": "Post Job",
        "matching": "Matching", "my_matches": "My Matches", "profile": "Profile", 
        "my_profile": "My Profile", "edit_profile": "Edit Profile", "chat": "Chat",
        "profile_photo": "Profile Photo", "personal_details": "Personal Details", "role_label": "Role",
        "mobile_label": "Mobile", "location_label": "Location", "aadhar_label": "Aadhar", "joined": "Joined",
        "score": "Match Score", "posted_by": "Posted by", "no_matches": "No matches yet!", "welcome": "Welcome",
        "perfect_matches": "Perfect Matches!", "add_skills": "Add skills", "add_experience": "Add experience",
        "total_users": "Total Users", "total_jobs": "Total Jobs", "admin_dashboard": "Admin Dashboard", 
        "logout": "Logout", "login_btn": "Login", "job_title": "Job Title", "salary": "Salary", 
        "skills_req": "Required Skills", "users": "Users", "recent_jobs": "Recent Jobs", "preview": "Preview",
        "my_posted_jobs": "My Posted Jobs", "matched_seekers": "Matched Seekers", "job_posted": "Job Posted!",
        "seeker_reg": "Seeker Registered!", "creator_reg": "Creator Registered!", "logged_out": "Logged out!",
        "invalid_credentials": "Invalid credentials", "admin_login": "Admin: 9999999999/admin123",
        "user_exists": "User exists! Login instead.", "no_jobs": "No jobs posted yet!", "apply": "Apply Now",
        "update_success": "Profile updated successfully!", "contact": "***", "no_seekers": "No seekers matched yet!",
        "type_message": "Type a message...", "send": "Send", "no_chat": "No messages yet. Say Hi! ","gov_schemes": "Government Schemes", 
        "add_scheme": "Add Scheme", "scheme_name": "Scheme Name", "trade": "Trade/Skill", 
        "description": "Description", "benefits": "Benefits", "delete": "Delete", 
        "search_schemes": "Search Schemes", "no_schemes": "No schemes found!", 
        "all_schemes": "All Schemes","filter_module": "Filter Matches","Hii":"Hii","day":"day"

    },
    "tam": {
        "title": "வேலைவாய்ப்பு தளம்", "lang_title": "மொழி", "english": "ஆங்கிலம்", "tamil": "தமிழ்",
        "menu": "மெனு", "login": "உள்நுழையவும்", "register": "பதிவு", "job_seeker": "வேலை தேடுபவர்", 
        "job_creator": "வேலை வழங்குபவர்", "admin": "நிர்வாகி", "name": "முழு பெயர்", "org_name": "நிறுவன பெயர்",
        "mobile": "மொபைல்", "aadhar": "ஆதார்", "skills": "திறன்கள்", "experience": "அனுபவம்",
        "location": "இடம்", "password": "கடவுச்சொல்", "send_otp": "OTP அனுப்பு", "enter_otp": "OTP உள்ளிடு (123456)",
        "complete_reg": "பதிவு முடி", "work_photo": "பணி படம்", "post_job": "வேலை விளம்பரம்",
        "matching": "புத்திசாலி பொருத்தம்", "my_matches": "எனது பொருத்தங்கள்", "profile": "சுயவிவரம்", 
        "my_profile": "எனது சுயவிவரம்", "edit_profile": "சுயவிவரம் திருத்து", "chat": "உரையாடல்",
        "profile_photo": "சுயவிவர படம்", "personal_details": "தனிப்பட்ட விவரங்கள்", "role_label": "பாத்திரம்",
        "mobile_label": "மொபைல்", "location_label": "இடம்", "aadhar_label": "ஆதார்", "joined": "உறுப்பினர்",
        "score": "பொருத்தம்", "posted_by": "விளம்பரம் செய்தவர்", "no_matches": "பொருத்தங்கள் இல்லை!",
        "welcome": "வரவேற்கிறோம்", "perfect_matches": "முழுமையான பொருத்தங்கள்!", "add_skills": "திறன்கள் சேர்",
        "add_experience": "அனுபவம் சேர்", "total_users": "மொத்த பயனர்கள்", "total_jobs": "மொத்த வேலைகள்",
        "admin_dashboard": "நிர்வாக மேலாண்மை", "logout": "வெளியேறு", "login_btn": "உள்நுழையவும்",
        "job_title": "வேலை தலைப்பு", "salary": "ஊதியம்", "skills_req": "தேவை திறன்கள்",
        "users": "பயனர்கள்", "recent_jobs": "சமீப வேலைகள்", "preview": "முன்னோட்டம்",
        "my_posted_jobs": "எனது விளம்பரங்கள்", "matched_seekers": "பொருத்த வேலை தேடுபவர்கள்",
        "job_posted": "வேலை பதிவிடப்பட்டது!", "seeker_reg": "வேலை தேடுபவர் பதிவு!", 
        "creator_reg": "வேலை வழங்குபவர் பதிவு!", "logged_out": "வெளியேறினீர்கள்!",
        "invalid_credentials": "தவறான விவரங்கள்", "admin_login": "நிர்வாகி: 9999999999/admin123",
        "user_exists": "பயனர் உள்ளார்! உள்நுழையவும்.", "no_jobs": "வேலைகள் இல்லை!", "apply": "விண்ணப்பி",
        "update_success": "சுயவிவரம் மேம்படுத்தப்பட்டது!", "contact": "***", "no_seekers": "இன்னும் பொருத்த வேலை தேடுபவர்கள் இல்லை!",
        "type_message": "செய்தி டைப் செய்யுங்கள்...", "send": "அனுப்பு", "no_chat": "இன்னும் செய்திகள் இல்லை. ஹாய் சொல்லுங்கள்! ","gov_schemes": "அரசு திட்டங்கள்", "add_scheme": "திட்டம் சேர்", "scheme_name": "திட்ட பெயர்", 
        "trade": "தொழில்/திறன்", "description": "விளக்கம்", "benefits": "நன்மைகள்", 
        "delete": "அழி", "search_schemes": "திட்டங்கள் தேடு", "no_schemes": "திட்டங்கள் இல்லை!", 
        "all_schemes": "எல்லா திட்டங்களும்","filter_module": "வடிகட்டுக","Hii":"வணக்கம்","day":"நாள்"

    }
}

def t(key):
    lang = st.session_state.get('lang', 'eng')
    return TRANSLATIONS.get(lang, TRANSLATIONS['eng']).get(key, key)



def mask_contact(mobile):
    if not mobile or len(mobile) < 10: return mobile
    return mobile[:3] + "***"

def mask_aadhar(aadhar):
    if not aadhar or len(aadhar) < 12: return aadhar
    return aadhar[:4] + "****"

#CHAT FUNCTIONS
def save_message(user1_mobile, user2_mobile, job_id, message, sender_mobile):
    pd.DataFrame([{
        'user1_mobile': str(user1_mobile),
        'user2_mobile': str(user2_mobile),
        'job_id': int(job_id),
        'message': message,
        'sender_mobile': str(sender_mobile),
        'timestamp': datetime.now()
    }]).to_sql('chats', conn, if_exists='append', index=False)
    conn.commit()

def get_chat_history(user1_mobile, user2_mobile, job_id, current_user_mobile):
    user1_mobile, user2_mobile = str(user1_mobile), str(user2_mobile)
    job_id = int(job_id)
    current_user_mobile = str(current_user_mobile)
    
    # First, mark any unread messages from the other user as read
    conn.cursor().execute("""
        UPDATE chats SET is_read=1 
        WHERE ((user1_mobile=? AND user2_mobile=?) OR (user1_mobile=? AND user2_mobile=?))
        AND job_id=? AND sender_mobile!=? AND is_read=0
    """, (user1_mobile, user2_mobile, user2_mobile, user1_mobile, job_id, current_user_mobile))
    conn.commit()

    query = """
    SELECT * FROM chats 
    WHERE ((user1_mobile=? AND user2_mobile=?) OR (user1_mobile=? AND user2_mobile=?))
    AND job_id=? ORDER BY timestamp ASC
    """
    df = pd.read_sql(query, conn, params=[user1_mobile, user2_mobile, user2_mobile, user1_mobile, job_id])
    return df.to_dict('records')

def check_unread_messages(mobile):
    query = """
    SELECT sender_mobile, job_id FROM chats 
    WHERE (user1_mobile=? OR user2_mobile=?) AND sender_mobile!=? AND is_read=0
    ORDER BY timestamp DESC
    """
    df = pd.read_sql(query, conn, params=(mobile, mobile, mobile))
    if df.empty:
        return 0, None
    latest_msg = df.iloc[0]
    return len(df), {'sender_mobile': latest_msg['sender_mobile'], 'job_id': latest_msg['job_id']}

#CORE FUNCTIONS
def hire_seeker(job_id, seeker_mobile):
    pd.DataFrame([{'job_id': job_id, 'seeker_mobile': seeker_mobile, 'status': 'hired'}]).to_sql('hires', conn, if_exists='append', index=False)
    conn.commit()

def finish_job_status(job_id, seeker_mobile):
    conn.cursor().execute("UPDATE hires SET status='finished' WHERE job_id=? AND seeker_mobile=?", (job_id, seeker_mobile))
    conn.commit()

def get_hired_status(job_id, seeker_mobile):
    df = pd.read_sql("SELECT status FROM hires WHERE job_id=? AND seeker_mobile=? ORDER BY id DESC LIMIT 1", conn, params=(job_id, seeker_mobile))
    if not df.empty:
        return df.iloc[0]['status']
    return None

def is_seeker_hired_elsewhere(seeker_mobile, current_job_id):
    df = pd.read_sql("SELECT * FROM hires WHERE seeker_mobile=? AND status='hired' AND job_id!=?", conn, params=(seeker_mobile, current_job_id))
    return not df.empty
def get_smart_matches(current_user):
    role = current_user['role']
    matches = []
    
    if role == 'Job Seeker':
        jobs_df = pd.read_sql("SELECT * FROM jobs", conn)
        seeker_profile = f"{current_user.get('skills', '')} {current_user.get('experience', '')} {current_user.get('location', '')}"
        for _, job in jobs_df.iterrows():
            creator = find_user(job['creator'])
            if creator:
                score = calculate_match_score(seeker_profile, f"{job['skills']} {job['title']} {job['location']}")
                if score > 0.2:
                    matches.append({'type': 'job', 'job': job.to_dict(), 'creator': creator, 'score': f"{score*100:.1f}%"})
    else:
        users_df = pd.read_sql("SELECT * FROM users WHERE role='Job Seeker'", conn)
        creator_jobs_df = pd.read_sql("SELECT skills, title FROM jobs WHERE creator=?", conn, params=(current_user['mobile'],))
        creator_jobs = " ".join([f"{job['skills']} {job['title']}" for _, job in creator_jobs_df.iterrows()])
        if not creator_jobs: creator_jobs = current_user.get('skills', '')
        for _, seeker in users_df.iterrows():
            score = calculate_match_score(creator_jobs, f"{seeker['skills']} {seeker['experience']} {seeker['location']}")
            if score > 0.2:
                matches.append({'type': 'seeker', 'seeker': seeker.to_dict(), 'score': f"{score*100:.1f}%"})
    return sorted(matches, key=lambda x: float(x['score'][:-1]), reverse=True)[:10]

def get_job_creator_matches(creator_mobile):
    jobs_df = pd.read_sql("SELECT * FROM jobs WHERE creator=?", conn, params=(creator_mobile,))
    all_matches = []
    
    for _, job in jobs_df.iterrows():
        job_profile = f"{job['skills']} {job['title']} {job['location']}"
        seekers_df = pd.read_sql("SELECT * FROM users WHERE role='Job Seeker'", conn)
        
        for _, seeker in seekers_df.iterrows():
            if is_seeker_hired_elsewhere(seeker['mobile'], job['id']):
                continue
            seeker_profile = f"{seeker['skills']} {seeker['experience']} {seeker['location']}"
            score = calculate_match_score(job_profile, seeker_profile)
            if score > 0.2:
                all_matches.append({
                    'job': job.to_dict(),
                    'seeker': seeker.to_dict(),
                    'score': f"{score*100:.1f}%"
                })
    
    job_matches = {}
    for match in all_matches:
        job_id = match['job']['id']
        if job_id not in job_matches:
            job_matches[job_id] = {'job': match['job'], 'seekers': []}
        job_matches[job_id]['seekers'].append({
            'seeker': match['seeker'],
            'score': match['score']
        })
    
    return list(job_matches.values())

def get_posted_jobs(creator_mobile):
    return pd.read_sql("SELECT * FROM jobs WHERE creator=? ORDER BY created_at DESC", conn, params=(creator_mobile,))

def delete_job(job_id, creator_mobile):
    """Bulletproof job deletion with proper row count checking"""
    try:
        
        job_check = pd.read_sql("SELECT creator FROM jobs WHERE id=? AND creator=?", 
                               conn, params=(job_id, creator_mobile))
        
        if job_check.empty:
            return False, "❌ Job not found or you don't own it"
        
        
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chats WHERE job_id=?", (job_id,))
        chats_deleted = cursor.rowcount  
        
        
        cursor.execute("DELETE FROM jobs WHERE id=? AND creator=?", (job_id, creator_mobile))
        jobs_deleted = cursor.rowcount   
        
        conn.commit()
        
        if jobs_deleted > 0:
            return True, f"✅ Job deleted! ({chats_deleted} chats cleared)"
        else:
            return False, "❌ Failed to delete job (already deleted?)"
            
    except Exception as e:
        conn.rollback()  
        return False, f"❌ Delete failed: {str(e)}"
def calculate_match_score(profile1, profile2):
    try:
        vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1,2))
        texts = [profile1.lower(), profile2.lower()]
        tfidf = vectorizer.fit_transform(texts)
        return cosine_similarity(tfidf[0:1], tfidf[1:])[0][0]
    except:
        return 0.0

def export_users_to_excel():
    try:
        users_df = pd.read_sql("SELECT mobile, role, name, aadhar, skills, experience, location, created_at FROM users", conn)
        seekers_df = users_df[users_df['role'] == 'Job Seeker']
        creators_df = users_df[users_df['role'] == 'Job Creator']
        
        with pd.ExcelWriter('users_data.xlsx', engine='openpyxl') as writer:
            seekers_df.to_excel(writer, sheet_name='Job Seekers', index=False)
            creators_df.to_excel(writer, sheet_name='Job Creators', index=False)
    except Exception as e:
        pass

def find_user(mobile):
    try:
        df = pd.read_sql("SELECT * FROM users WHERE mobile=?", conn, params=(mobile,))
        return df.to_dict('records')[0] if not df.empty else None
    except:
        return None

def save_user(data):
    df = pd.read_sql("SELECT * FROM users WHERE mobile=?", conn, params=(data['mobile'],))
    if not df.empty:
        st.warning(t("user_exists"))
        return False
    
    required = {'skills': '', 'experience': '', 'location': '', 'aadhar': '', 'work_image': None}
    for k, v in required.items(): data.setdefault(k, v)
    pd.DataFrame([data]).to_sql('users', conn, if_exists='append', index=False)
    conn.commit()
    export_users_to_excel()
    return True

def update_user(mobile, data):
    try:
        current_user = find_user(mobile)
        if not current_user: return False
        
        update_fields = ['name', 'skills', 'experience', 'location', 'work_image']
        update_query = "UPDATE users SET "
        params = []
        
        for field in update_fields:
            if field in data:
                update_query += f"{field}=?, "
                params.append(data[field])
        
        update_query = update_query.rstrip(', ') + " WHERE mobile=?"
        params.append(mobile)
        
        pd.read_sql_query(update_query, conn, params=params)
        conn.commit()
        export_users_to_excel()
        return True
    except:
        return False

def save_job(data):
    required = {'skills': '', 'salary': '', 'location': ''}
    for k, v in required.items(): data.setdefault(k, v)
    pd.DataFrame([data]).to_sql('jobs', conn, if_exists='append', index=False)
    conn.commit()
    return True

@st.cache_data
def load_schemes():
    try:
        df = pd.read_excel('government_schemes.xlsx')
        return df
    except:
        default_schemes = pd.DataFrame({
            'name': [
                'PM Vishwakarma Yojana', 'e-Shram Card', 'PM Shram Yogi Maan-dhan (PM-SYM)', 'MGNREGA', 'PM SVANidhi',
                'Aam Admi Bima Yojana', 'Atal Pension Yojana', 'PM Jeevan Jyoti Bima Yojana (PMJJBY)', 'PM Suraksha Bima Yojana (PMSBY)', 'Ayushman Bharat (PM-JAY)',
                'PM Awas Yojana (PMAY)', 'BOCW Welfare Scheme', 'DAY-NULM', 'DDU-GKY', 'PM Kaushal Vikas Yojana (PMKVY)',
                'PMEGP', 'Stand Up India Scheme', 'Mudra Yojana (PMMY)', 'NSKFDC Schemes', 'Antyodaya Anna Yojana (AAY)',
                'Ujjwala Yojana (PMUY)', 'Garib Kalyan Rojgar Abhiyaan', 'Skill India Mission', 'Swachh Bharat Mission (Grameen)', 'Jal Jeevan Mission'
            ],
            'trade': [
                'Carpenter,Tailor,Mason,Others', 'All Unorganized Workers', 'All Daily Wage Workers', 'Rural Unskilled Workers', 'Street Vendors',
                'Landless Households', 'Unorganized Sector', 'All Citizens', 'All Citizens', 'Poor & Vulnerable',
                'Economically Weaker Section', 'Construction Workers', 'Urban Poor', 'Rural Youth', 'All Skills',
                'All Trades', 'SC/ST/Women Entrepreneurs', 'Small Business Owners', 'Safai Karamcharis', 'Poorest of Poor',
                'BPL Households', 'Migrant Workers', 'All Trades', 'Rural Sanitation Workers', 'Plumbers/Rural Workers'
            ],
            'description': [
                'Support for traditional artisans and craftspeople', 'National database of unorganized workers', 'Pension scheme for unorganized sector', '100 days of guaranteed wage employment', 'Micro-credit facility for street vendors',
                'Social security for rural landless households', 'Pension scheme focused on unorganized sector', 'Life insurance scheme', 'Accident insurance scheme', 'Health insurance coverage',
                'Housing for all', 'Welfare for building and other construction workers', 'National Urban Livelihoods Mission', 'Rural youth skill training', 'Skill certification scheme',
                'Employment generation programme', 'Loans for SC/ST and women', 'Micro business loans', 'Financial assistance for sanitation workers', 'Highly subsidized food grains',
                'LPG connections for BPL households', 'Employment for migrant workers', 'Skill training and certification', 'Sanitation infrastructure', 'Piped water supply'
            ],
            'benefits': [
                'Toolkit incentive up to ₹15,000, credit support', 'Accident insurance cover of ₹2 Lakhs', 'Assured pension of ₹3000/month after 60', 'Guaranteed 100 days work', 'Working capital loan up to ₹10,000',
                'Life and disability cover', 'Guaranteed minimum pension', 'Life cover of ₹2 Lakhs', 'Accident cover of ₹2 Lakhs', 'Health cover up to ₹5 Lakhs per family',
                'Financial assistance for house construction', 'Health, education, maternity, and pension benefits', 'Skill training, self-employment support', 'Free training and placement', 'Free skill training and certification',
                'Loan up to ₹25 Lakh for manufacturing', 'Bank loans between ₹10 Lakh and ₹1 Crore', 'Loans up to ₹10 Lakhs', 'Loans and skill training', '35 kg of food grains per month',
                'Free LPG connection', 'Employment and infrastructure creation', 'Industry-relevant skill training', 'Incentives for toilet construction', 'Employment in water supply works'
            ]
        })
        default_schemes.to_excel('government_schemes.xlsx', index=False)
        return default_schemes

def save_scheme(df):
    df.to_excel('government_schemes.xlsx', index=False)

def find_schemes(search_term, df):
    search_term = search_term.lower()
    matches = df[df['trade'].str.contains(search_term, case=False, na=False) | 
                df['name'].str.contains(search_term, case=False, na=False)]
    return matches

#SESSION STATE
if 'user' not in st.session_state: st.session_state.user = None
if 'otp_store' not in st.session_state: st.session_state.otp_store = {}
if 'lang' not in st.session_state: st.session_state.lang = 'eng'
if 'current_chat' not in st.session_state: st.session_state.current_chat = None
if "job_chat_state" not in st.session_state:
    st.session_state.job_chat_state = {"messages": [], "waiting_for_chat": False, "selected_match": None}

#LANGUAGE SELECTOR
col1, col2 = st.columns([3,1])
with col1:
    st.title(t("title"))
with col2:
    lang_options = [TRANSLATIONS['eng']['english'], TRANSLATIONS['tam']['tamil']]
    selected_idx = 0 if st.session_state.lang == 'eng' else 1
    selected_lang = st.selectbox(t("lang_title"), lang_options, index=selected_idx)
    
    if selected_lang == TRANSLATIONS['tam']['tamil'] and st.session_state.lang != 'tam':
        st.session_state.lang = 'tam'
        st.rerun()
    elif selected_lang == TRANSLATIONS['eng']['english'] and st.session_state.lang != 'eng':
        st.session_state.lang = 'eng'
        st.rerun()

#LOGIN/REGISTER
if not st.session_state.user:
    st.sidebar.title(t("menu"))
    menu = st.sidebar.radio("", [t("login"), t("register")])
    
    if menu == t("login"):
        _, col2, _ = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"<h2 style='text-align:center;'>Welcome!</h2>", unsafe_allow_html=True)
            with st.form("login_form"):
                mobile = st.text_input(t("mobile"))
                password = st.text_input(t("password"), type="password")
                
                submitted = st.form_submit_button(t("login_btn"), use_container_width=True)
                if submitted:
                    user = find_user(mobile)
                    if user and user['password'] == password:
                        st.session_state.user = user
                        st.success(f"{t('welcome')} {user['name']}!")
                        st.rerun()
                    else:
                        st.error(t("invalid_credentials"))
        
    
    elif menu == t("register"):
        _, col2, _ = st.columns([1, 3, 1])
        with col2:
            st.markdown(f"<h2 style='text-align:center;'>Create an Account</h2>", unsafe_allow_html=True)
            role_choice = st.radio("Register as:", [t("job_seeker"), t("job_creator")], horizontal=True)
            
            if role_choice == t("job_seeker"):
                with st.form("seeker_form"):
                    c1, c2 = st.columns(2)
                    with c1:
                        name = st.text_input(t("name"))
                        mobile = st.text_input(t("mobile"))
                        aadhar = st.text_input(t("aadhar"))
                    with c2:
                        skills = st.text_input(t("skills"))
                        location = st.text_input(t("location"))
                        experience = st.text_area(t("experience"), height=68)
                    
                    work_photo = st.file_uploader(t("work_photo"), type=['jpg','png','jpeg'])
                    if work_photo:
                        st.image(work_photo, caption=t("preview"), width=200)
                    
                    password = st.text_input(t("password"), type="password")
                    
                    c1, c2 = st.columns([2, 1])
                    with c1: otp = st.text_input(t("enter_otp"))
                    with c2: send_otp = st.form_submit_button(t("send_otp"), use_container_width=True)
                    
                    submitted = st.form_submit_button(t("complete_reg"), use_container_width=True)
                    
                    if send_otp and len(mobile)==10 and mobile.isdigit():
                        st.session_state.otp_store[mobile] = "123456"
                        st.success("OTP sent! (Use **123456**)")
                    
                    if submitted and otp == "123456":
                        work_image = work_photo.read() if work_photo else None
                        if save_user({
                            'mobile': mobile, 'role': 'Job Seeker', 'name': name,
                            'aadhar': aadhar, 'skills': skills, 'experience': experience,
                            'location': location, 'work_image': work_image, 'password': password
                        }):
                            st.success(t("seeker_reg"))
                            st.rerun()
        
            else:
                with st.form("creator_form"):
                    c1, c2 = st.columns(2)
                    with c1: org_name = st.text_input(t("org_name"))
                    with c2: mobile = st.text_input(t("mobile"))
                    location = st.text_input(t("location"))
                    password = st.text_input(t("password"), type="password")
                    
                    c1, c2 = st.columns([2, 1])
                    with c1: otp = st.text_input(t("enter_otp"))
                    with c2: send_otp = st.form_submit_button(t("send_otp"), use_container_width=True)
                    
                    submitted = st.form_submit_button(t("complete_reg"), use_container_width=True)
                    
                    if send_otp and len(mobile)==10 and mobile.isdigit():
                        st.session_state.otp_store[mobile] = "123456"
                        st.success("OTP sent! (Use **123456**)")
                    
                    if submitted and otp == "123456":
                        if save_user({
                            'mobile': mobile, 'role': 'Job Creator', 'name': org_name,
                            'location': location, 'password': password
                        }):
                            st.success(t("creator_reg"))
                            st.rerun()

#DASHBOARD
else:
    st.sidebar.title(f"{t('Hii')} {st.session_state.user['name']}")
    st.sidebar.markdown(f"**{t('role_label')}:** {st.session_state.user['role']}")
    st.sidebar.markdown("---")
    if st.sidebar.button(t('logout'), use_container_width=True):
        st.session_state.user = None
        st.session_state.current_chat = None
        st.rerun()
    
    role = st.session_state.user['role']
    
    if role == "Admin":
        menu = st.sidebar.radio("", [t("admin_dashboard"), t("filter_module"), t("gov_schemes")])
    elif role == "Job Creator":
        menu = st.sidebar.radio("", [t("profile"), t("post_job"), t("my_matches"), t("filter_module"), t("my_posted_jobs"), t("gov_schemes")])
    else:  # Job Seeker
        menu = st.sidebar.radio("", [t("matching"), t("profile"), t("gov_schemes")])
    
    st.session_state.user = find_user(st.session_state.user['mobile'])
    
    unread_count, latest_msg = check_unread_messages(st.session_state.user['mobile'])
    if unread_count > 0:
        if st.sidebar.button(f"{unread_count} New Message(s)", type="primary", use_container_width=True):
            other_user = find_user(latest_msg['sender_mobile'])
            job_df = pd.read_sql("SELECT title FROM jobs WHERE id=?", conn, params=(int(latest_msg['job_id']),))
            job_title = job_df.iloc[0]['title'] if not job_df.empty else "Job Chat"
            
            st.session_state.current_chat = {
                'other_user': other_user,
                'job_id': int(latest_msg['job_id']),
                'job_title': job_title
            }
            st.rerun()

    #CHAT INTERFACE 
    if st.session_state.current_chat:
        st.markdown("""
        <style>
        [data-testid="stSidebar"] {display: none !important;}
        </style>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:20px;border-radius:0 0 20px 20px;color:white;text-align:center'>
            <h1 style='margin:0'>{t('chat')} - {st.session_state.current_chat.get('job_title', 'Chat')}</h1>
        </div>
        """, unsafe_allow_html=True)
        col1, col2 = st.columns([1, 8])
        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state.current_chat = None
                st.rerun()
    
        current_user = st.session_state.user
        other_user = st.session_state.current_chat.get('other_user')
        job_id = st.session_state.current_chat.get('job_id')
    
        if not other_user or not other_user.get('mobile'):
            st.error("Invalid chat partner!")
            st.session_state.current_chat = None
            st.rerun()
            st.stop()
        st.markdown(f"""
        <div style='background:#f8f9fa;padding:15px;border-radius:15px;border-left:5px solid #667eea;margin:20px 0'>
            <h3>**{other_user.get('name', 'Unknown')}**</h3>
            <p>{mask_contact(other_user.get('mobile'))} | {other_user.get('location', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)
    
        #CHAT HISTORY
        chat_container = st.container(height=450)

        @st.fragment(run_every="3s")
        def render_chat_history():
            chat_history = get_chat_history(current_user['mobile'], other_user['mobile'], job_id, current_user['mobile'])
            if chat_history:
                for msg in chat_history:
                    if msg.get('sender_mobile') == current_user['mobile']:
                        st.markdown(f"""
                        <div style='background:#dcf8c6;padding:12px 16px;margin:8px 10px 8px 50px;
                        border-radius:18px 18px 4px 18px;float:right;max-width:65%;word-wrap:break-word;box-shadow:0 2px 8px rgba(0,0,0,0.1)'>
                            <div style='font-size:11px;color:#666;margin-bottom:4px'>{msg.get('timestamp', '00:00')[-8:-3]}</div>
                            <div style='font-size:14px;line-height:1.4'>{msg.get('message', '')}</div>
                        </div><div style='clear:both;'></div>""", unsafe_allow_html=True)
                    else:   
                        st.markdown(f"""
                        <div style='background:#ffffff;padding:12px 16px;margin:8px 50px 8px 10px;
                        border-radius:18px 18px 18px 4px;float:left;max-width:65%;word-wrap:break-word;box-shadow:0 2px 8px rgba(0,0,0,0.1)'>
                            <div style='font-size:11px;color:#666;margin-bottom:4px'>{msg.get('timestamp', '00:00')[-8:-3]}</div>
                            <div style='font-size:14px;line-height:1.4'>{msg.get('message', '')}</div>
                        </div><div style='clear:both;'></div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style='height:350px;display:flex;align-items:center;justify-content:center;color:#666;text-align:center'>
                    <div><h3>{t('no_chat')}</h3></div>
                </div>""", unsafe_allow_html=True)

        col_clear, _ = st.columns([1, 4])
        with col_clear:
            if st.button("Clear Chat", use_container_width=True):
                current_user = st.session_state.user
                other_user = st.session_state.current_chat.get('other_user')
                job_id = st.session_state.current_chat.get('job_id')
        
                pd.read_sql_query("""
                    DELETE FROM chats WHERE 
                    ((user1_mobile=? AND user2_mobile=?) OR (user1_mobile=? AND user2_mobile=?))
                    AND job_id=?
                """, conn, params=[current_user['mobile'], other_user['mobile'], 
                          other_user['mobile'], current_user['mobile'], job_id])
                conn.commit()
                st.success("Chat cleared!")
                st.rerun()

        with chat_container:
            render_chat_history()
    
        st.markdown("---")
        # Use Streamlit's native chat input for reliable messaging (handles 'Enter' to send automatically)
        message = st.chat_input(t("type_message"), max_chars=200)
        if message and message.strip():
            save_message(current_user['mobile'], other_user['mobile'], job_id, message.strip(), current_user['mobile']) 
            st.rerun()

        if current_user['role'] == 'Job Creator':
            st.markdown("---")
            with st.expander("Mark Job Complete & Review Seeker"):
                with st.form("review_form"):
                    st.write(f"Review for {other_user.get('name', 'Seeker')}")
                    rating = st.slider("Rating", 1, 5, 5)
                    review_text = st.text_area("Review Comments", max_chars=300)
                    completed_image = st.file_uploader("Work Image (Optional)", type=['jpg','png','jpeg'])
                    
                    if st.form_submit_button("Submit Review"):
                        img_data = completed_image.read() if completed_image else None
                        pd.DataFrame([{
                            'job_id': job_id,
                            'creator_mobile': current_user['mobile'],
                            'seeker_mobile': other_user['mobile'],
                            'rating': rating,
                            'review': review_text,
                            'work_image': img_data,
                            'timestamp': datetime.now()
                        }]).to_sql('reviews', conn, if_exists='append', index=False)
                        conn.commit()
                        st.success("Review saved successfully!")
                        st.rerun()
        st.stop()
    
    #PROFILE
    if menu == t("profile"):
        st.header(t("my_profile"))
        
        tab1, tab2 = st.tabs([t("profile"), t("edit_profile")])
        
        with tab1:
            user = st.session_state.user
            
            if role == "Job Seeker":
                col1, col2 = st.columns([1,2])
                with col1:
                    st.markdown("### " + t("profile_photo"))
                    if user.get('work_image'):
                        st.image(io.BytesIO(user['work_image']), width=250)
                    else:
                        st.markdown("""
                        <div style='width:250px;height:250px;background:#e3f2fd;border-radius:20px;
                        display:flex;align-items:center;justify-content:center;font-size:60px;color:#1976d2'>
                        </div>""", unsafe_allow_html=True)
                
                with col2:
                    st.markdown("### " + t("personal_details"))
                    st.markdown(f"""
                    <div style='background:#e3f2fd;padding:25px;border-radius:15px;box-shadow:0 8px 32px rgba(0,0,0,0.1);'>
                        <h3 style='color:#1976d2'>{user.get('name', 'N/A')}</h3>
                        <p><strong>{t('role_label')}:</strong> <span style='color:#4caf50'>{user.get('role')}</span></p>
                        <p><strong>{t('mobile_label')}:</strong> <span style='color:#f44336'>{mask_contact(user.get('mobile'))}</span></p>
                        <p><strong>{t('location_label')}:</strong> {user.get('location', 'N/A')}</p>
                        <p><strong>{t('aadhar_label')}:</strong> <span style='color:#f44336'>{mask_aadhar(user.get('aadhar', 'N/A'))}</span></p>
                        <p><strong>{t('joined')}:</strong> {user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A'}</p>
                    </div>""", unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### " + t("skills"))
                    skills = user.get('skills', '')
                    if skills:
                        for skill in [s.strip() for s in skills.split(',')][:10]:
                            st.markdown(f"• **{skill}**")
                    else:
                        st.warning(t("add_skills"))
                
                    st.markdown("### " + t("experience"))
                    exp = user.get('experience', '')
                    st.markdown(f"**{exp[:400]}**..." if exp else t("add_experience"))

                st.markdown("---")
                st.markdown("### Ratings & Reviews")
                reviews_df = pd.read_sql("SELECT rating, review, timestamp, creator_mobile FROM reviews WHERE seeker_mobile=?", conn, params=(user['mobile'],))
                if not reviews_df.empty:
                    avg_rating = reviews_df['rating'].mean()
                    st.markdown(f"**Average Rating:** {'★' * int(avg_rating)} ({avg_rating:.1f}/5.0 from {len(reviews_df)} reviews)")
                    
                    for _, row in reviews_df.iterrows():
                        creator = find_user(row['creator_mobile'])
                        creator_name = creator['name'] if creator else "Unknown Creator"
                        st.markdown(f"""
                        <div style='background:#f9f9f9;padding:15px;border-radius:10px;margin-bottom:10px;border-left:4px solid #ffc107'>
                            <strong>{creator_name}</strong> - {'★' * int(row['rating'])}<br>
                            <em>{row['review']}</em><br>
                            <small style='color:gray'>{row['timestamp'][:10]}</small>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No reviews yet!")
            
            else:
                col1, col2 = st.columns([1,3])
                with col1:
                    st.markdown("### " + t("profile_photo"))
                    st.markdown("<div style='width:250px;height:250px;background:#f3e5f5;border-radius:20px;display:flex;align-items:center;justify-content:center;font-size:60px;color:#7b1fa2'></div>", unsafe_allow_html=True)
                
                with col2:
                    st.markdown("### " + t("personal_details"))
                    st.markdown(f"""
                    <div style='background:#f3e5f5;padding:25px;border-radius:15px;box-shadow:0 8px 32px rgba(0,0,0,0.1);'>
                        <h3 style='color:#7b1fa2'>{user.get('name', 'N/A')}</h3>
                        <p><strong>{t('role_label')}:</strong> <span style='color:#4caf50'>{user.get('role')}</span></p>
                        <p><strong>{t('mobile_label')}:</strong> <span style='color:#f44336'>{mask_contact(user.get('mobile'))}</span></p>
                        <p><strong>{t('location_label')}:</strong> {user.get('location', 'N/A')}</p>
                    </div>""", unsafe_allow_html=True)
        
        with tab2:
            st.subheader(t("edit_profile"))
            user = st.session_state.user
            if role == "Job Seeker":
                with st.form("edit_seeker_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_name = st.text_input(t("name"), value=user.get('name', ''))
                        new_skills = st.text_input(t("skills"), value=user.get('skills', ''), placeholder="Python, Java, Testing...")
                        new_location = st.text_input(t("location"), value=user.get('location', ''))
                    with col2:
                        new_experience = st.text_area(t("experience"), value=user.get('experience', ''), placeholder="2 years experience...")
                    
                    new_work_photo = st.file_uploader(t("work_photo"), type=['jpg','png','jpeg'])
                    if new_work_photo:
                        st.image(new_work_photo, caption=t("preview"), width=200)
                    
                    submitted = st.form_submit_button(t("update_success"), use_container_width=True)
                    
                    if submitted:
                        update_data = {
                            'name': new_name,
                            'skills': new_skills,
                            'experience': new_experience,
                            'location': new_location
                        }
                        if new_work_photo:
                            update_data['work_image'] = new_work_photo.read()
                        
                        if update_user(user['mobile'], update_data):
                            st.success(t("update_success"))
                            st.session_state.user = find_user(user['mobile'])
                            st.rerun()
                           
            else:
                with st.form("edit_creator_form"):
                    col1, col2 = st.columns(2)
                    with col1: new_name = st.text_input(t("org_name"), value=user.get('name', ''))
                    with col2: new_location = st.text_input(t("location"), value=user.get('location', ''))
                    
                    submitted = st.form_submit_button("💾 " + t("update_success"), use_container_width=True)
                    
                    if submitted:
                        if update_user(user['mobile'], {
                            'name': new_name,
                            'location': new_location
                        }):
                            st.success(t("update_success"))
                            st.session_state.user = find_user(user['mobile'])
                            st.rerun()
                            

    #JOB SEEKER MATCHING
    elif menu == t("matching") and role == "Job Seeker":
        st.header(t("matching"))
        matches = get_smart_matches(st.session_state.user)
        
        if matches:
            st.success(f"**{len(matches)} {t('perfect_matches')}**")
            for i, match in enumerate(matches):
                if match['type'] == 'job':
                    job = match['job']
                    creator = match['creator']
                    skills_html = " ".join([f"<span class='skill-tag'>{s.strip()}</span>" for s in job['skills'].split(',') if s.strip()])
                    
                    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
                    col1, col2 = st.columns([3,1])
                    with col1:
                        st.markdown(f"<h3 style='margin:0;'>{job['title']}</h3>", unsafe_allow_html=True)
                        st.markdown(f"<p style='color:gray; font-size:14px;'> {creator.get('name', 'Unknown')}</p>", unsafe_allow_html=True)
                        st.markdown(f"**{job['location']}** &nbsp;|&nbsp; **{job['salary']}**")
                        st.markdown(f"<div style='margin-top:10px;'>{skills_html}</div>", unsafe_allow_html=True)
                    with col2:
                        st.metric(t("score"), match['score'])
                        if creator and creator.get('mobile'):
                            if st.button(t('chat'), key=f"chat_job_seeker_{i}", use_container_width=True):
                                st.session_state.current_chat = {
                                    'other_user': creator,
                                    'job_id': job['id'],
                                    'job_title': job['title']
                                }
                                st.rerun()
                        else:
                            st.warning("Invalid creator")
                    st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info(t("no_matches"))

    if st.session_state.get('reviewing_job'):
        r_job_id = st.session_state.reviewing_job['job_id']
        r_seeker = st.session_state.reviewing_job['seeker']

        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.markdown("### Job Completion & Review")
        with st.form("completion_review_form"):
            st.write(f"Please provide a review for **{r_seeker.get('name', 'Seeker')}** to mark this job as finished.")
            rating = st.slider("Rating (1-5)", 1, 5, 5)
            review_text = st.text_area("Review Comments", max_chars=300)
            completed_image = st.file_uploader("Work Image (Optional)", type=['jpg','png','jpeg'])
            
            col1, col2 = st.columns(2)
            with col1: submitted = st.form_submit_button("Submit Review & Finish", use_container_width=True)
            with col2: cancel = st.form_submit_button("Cancel", use_container_width=True)
            
            if submitted:
                img_data = completed_image.read() if completed_image else None
                pd.DataFrame([{
                    'job_id': r_job_id, 'creator_mobile': st.session_state.user['mobile'],
                    'seeker_mobile': r_seeker['mobile'], 'rating': rating,
                    'review': review_text, 'work_image': img_data,
                    'timestamp': datetime.now()
                }]).to_sql('reviews', conn, if_exists='append', index=False)
                finish_job_status(r_job_id, r_seeker['mobile'])
                st.session_state.reviewing_job = None
                st.success("Job Finished and Review saved successfully!")
                st.rerun()
            if cancel:
                st.session_state.reviewing_job = None
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    #FILTER MODULE
    elif menu == t("filter_module") and role == "Job Creator":
        st.header(t("filter_module"))
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            filter_location = st.text_input("Filter Location (e.g. Chennai)")
        with f_col2:
            filter_skills = st.text_input("Filter Skills (e.g. Plumber)")

        query = "SELECT mobile, name, skills, experience, location FROM users WHERE role='Job Seeker'"
        params = []
        if filter_location:
            query += " AND location LIKE ?"
            params.append(f"%{filter_location}%")
        if filter_skills:
            query += " AND skills LIKE ?"
            params.append(f"%{filter_skills}%")
            
        seekers_df = pd.read_sql(query, conn, params=params)
        my_jobs = pd.read_sql("SELECT id, title FROM jobs WHERE creator=?", conn, params=(st.session_state.user['mobile'],))
        
        if not seekers_df.empty:
            st.success(f"**Found {len(seekers_df)} Job Seekers!**")
            
            for seeker_idx, seeker_row in seekers_df.iterrows():
                seeker = seeker_row.to_dict()
                st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([1,4,3])
                with col1:
                    st.markdown("<div style='font-size:40px;text-align:center;'></div>", unsafe_allow_html=True)
                with col2:
                    st.markdown(f"**{seeker.get('name', 'Unknown')}** | {mask_contact(seeker.get('mobile'))}<br>{seeker.get('location', 'N/A')} | {seeker.get('skills', 'N/A')[:50]}", unsafe_allow_html=True)
                
                with col3:
                    if st.button("Chat", key=f"chat_glb_{seeker_idx}", use_container_width=True):
                        st.session_state.current_chat = {
                            'other_user': seeker, 
                            'job_id': 0, 
                            'job_title': 'Direct Message'
                        }
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("No job seekers found matching your criteria.")

    #JOB CREATOR MATCHES
    elif menu == t("my_matches") and role == "Job Creator":
        st.header(t("my_matches"))
        job_matches = get_job_creator_matches(st.session_state.user['mobile'])
        
        if job_matches:
            st.success(f"**{len(job_matches)} {t('perfect_matches')}**")
            for job_idx, job_match in enumerate(job_matches):
                job = job_match['job']
                seekers = job_match['seekers']
                skills_html = " ".join([f"<span class='skill-tag'>{s.strip()}</span>" for s in job['skills'].split(',') if s.strip()])
                
                st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
                st.markdown(f"<h3 style='margin:0;'>{job['title']}</h3>", unsafe_allow_html=True)
                st.markdown(f"**{job['location']}** &nbsp;|&nbsp; **{job['salary']}**")
                st.markdown(f"<div style='margin-top:10px;'>{skills_html}</div>", unsafe_allow_html=True)
                
                st.markdown(f"#### **{len(seekers)} {t('matched_seekers')}**")
                for seeker_idx, seeker_match in enumerate(seekers):
                    seeker = seeker_match['seeker']
                    score = seeker_match['score']
                    hired_status = get_hired_status(job['id'], seeker['mobile'])
                    
                    c1, c2, c3 = st.columns([1,4,2])
                    with c1: st.markdown("<div style='font-size:40px;text-align:center;'></div>", unsafe_allow_html=True)
                    with c2: 
                        st.markdown(f"**{seeker.get('name', 'Unknown')}** | {mask_contact(seeker.get('mobile'))}")
                        if hired_status == 'hired':
                            st.markdown("<span style='color:#10b981;font-weight:bold;background:#d1fae5;padding:3px 8px;border-radius:5px;'>Hired for this Job</span>", unsafe_allow_html=True)
                        elif hired_status == 'finished':
                            st.markdown("<span style='color:#f59e0b;font-weight:bold;background:#fef3c7;padding:3px 8px;border-radius:5px;'>Job Completed</span>", unsafe_allow_html=True)
                            
                    with c3:
                        st.metric(t("score"), score)
                        
                        if not hired_status:
                            c_btn1, c_btn2 = st.columns(2)
                            with c_btn1:
                                if st.button("Hire", key=f"hire_my_{job['id']}_{seeker_idx}", use_container_width=True):
                                    hire_seeker(job['id'], seeker['mobile'])
                                    st.rerun()
                            with c_btn2:
                                if st.button("Chat", key=f"chat_my_{job['id']}_{seeker_idx}", use_container_width=True):
                                    st.session_state.current_chat = {'other_user': seeker, 'job_id': job['id'], 'job_title': job['title']}
                                    st.rerun()
                        elif hired_status == 'hired':
                            c_btn1, c_btn2 = st.columns(2)
                            with c_btn1:
                                if st.button("Finish", key=f"fin_my_{job['id']}_{seeker_idx}", use_container_width=True):
                                    st.session_state.reviewing_job = {'job_id': job['id'], 'seeker': seeker}
                                    st.rerun()
                            with c_btn2:
                                if st.button("Chat", key=f"chat_hired_my_{job['id']}_{seeker_idx}", use_container_width=True):
                                    st.session_state.current_chat = {'other_user': seeker, 'job_id': job['id'], 'job_title': job['title']}
                                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info(t("no_seekers"))

    #MY POSTED JOBS
    elif menu == t("my_posted_jobs") and role == "Job Creator":
        st.header(t("my_posted_jobs"))
        jobs = get_posted_jobs(st.session_state.user['mobile'])
        if not jobs.empty:
            for idx, job in jobs.iterrows():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"""
                    <div style='background:#fff3e0;padding:20px;border-radius:15px;margin:10px 0;border-left:5px solid #ff9800;box-shadow:0 4px 12px rgba(0,0,0,0.1)'>
                    <h4><strong>{job['title']}</strong></h4>
                    <p><strong>{t('salary')}</strong> {job['salary']} | <strong>{t('location')}</strong> {job['location']}</p>
                    <p><strong>{t('skills_req')}</strong> {job['skills']}</p>
                    <small>{job['created_at'][:10]}</small>
                    </div>""", unsafe_allow_html=True)
                with col2:
                    if st.button("Delete", key=f"del_job_{job['id']}", help=t("delete"), use_container_width=True):
                        success, msg = delete_job(job['id'], st.session_state.user['mobile'])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
        else:
            st.info(t("no_jobs"))

    # POST JOB
    elif menu == t("post_job"):
        st.header(t("post_job"))
        with st.form("post_job_form"):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input(t("job_title"), placeholder="Tailor,Carpenter..")
                skills = st.text_input(t("skills_req"),)
            with col2:
                salary = st.text_input(t("salary"), placeholder="1000/{t('day')}")
                location = st.text_input(t("location"), placeholder="Chennai")
            
            submitted = st.form_submit_button(t("post_job"), use_container_width=True)
            if submitted:
                save_job({
                    'creator': st.session_state.user['mobile'],
                    'title': title, 'skills': skills, 'salary': salary, 'location': location
                })
                st.success(t("job_posted"))
                

    #ADMIN FILTER MODULE
    elif menu == t("filter_module") and role == "Admin":
        st.header(t("filter_module"))
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            filter_role = st.selectbox("Role", ["All", "Job Seeker", "Job Creator"])
        with f_col2:
            filter_location = st.text_input("Location (e.g. Chennai)")
        with f_col3:
            filter_skills = st.text_input("Skills/Trade (e.g. Plumber)")
        st.markdown("</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(t("recent_jobs"))
            jobs_query = "SELECT * FROM jobs WHERE 1=1"
            jobs_params = []
            if filter_location:
                jobs_query += " AND location LIKE ?"
                jobs_params.append(f"%{filter_location}%")
            if filter_skills:
                jobs_query += " AND skills LIKE ?"
                jobs_params.append(f"%{filter_skills}%")
            jobs_query += " ORDER BY id DESC LIMIT 50"
            recent_jobs = pd.read_sql(jobs_query, conn, params=jobs_params)
            st.dataframe(recent_jobs, use_container_width=True)
            
        with col2:
            st.subheader(t("users"))
            users_query = "SELECT mobile, name, role, location, skills, experience FROM users WHERE 1=1"
            users_params = []
            if filter_role != "All":
                users_query += " AND role = ?"
                users_params.append(filter_role)
            if filter_location:
                users_query += " AND location LIKE ?"
                users_params.append(f"%{filter_location}%")
            if filter_skills:
                users_query += " AND skills LIKE ?"
                users_params.append(f"%{filter_skills}%")
            
            users_list = pd.read_sql(users_query, conn, params=users_params)
            st.dataframe(users_list, use_container_width=True)

    #ADMIN DASHBOARD
    elif menu == t("admin_dashboard"):
        st.header(t("admin_dashboard"))
        col1, col2, col3 = st.columns(3)
        total_users = len(pd.read_sql("SELECT * FROM users", conn))
        total_jobs = len(pd.read_sql("SELECT * FROM jobs", conn))
        with col1: 
            st.markdown(f"<div class='custom-card' style='text-align:center;border-top-color:#8b5cf6;'><h2>{total_users}</h2><p>{t('total_users')}</p></div>", unsafe_allow_html=True)
        with col2: 
            st.markdown(f"<div class='custom-card' style='text-align:center;border-top-color:#ec4899;'><h2>{total_jobs}</h2><p>{t('total_jobs')}</p></div>", unsafe_allow_html=True)
        with col3: 
            st.markdown(f"<div class='custom-card' style='text-align:center;border-top-color:#10b981;'><h2>Live</h2><p>Matches</p></div>", unsafe_allow_html=True)
            
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(t("recent_jobs"))
            recent_jobs = pd.read_sql("SELECT * FROM jobs ORDER BY id DESC LIMIT 10", conn)
            st.dataframe(recent_jobs, use_container_width=True)
            
        with col2:
            st.subheader("Recent " + t("users"))
            users_list = pd.read_sql("SELECT mobile, name, role, location, skills FROM users ORDER BY created_at DESC LIMIT 10", conn)
            st.dataframe(users_list, use_container_width=True)

    # GOVERNMENT SCHEMES MODULE
    elif menu == t("gov_schemes"):
        schemes_df = load_schemes()
        
        if role == "Admin":
            st.header(t("gov_schemes") + " - Admin Panel")
            
            tab1, tab2 = st.tabs([t("add_scheme"), t("all_schemes")])
            
            with tab1:
                st.subheader(t("add_scheme"))
                with st.form("add_scheme_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        name = st.text_input(t("scheme_name"))
                        trade = st.text_input(t("trade"), placeholder="Carpenter,Tailor,Plumber")
                    with col2:
                        description = st.text_area(t("description"), max_chars=200)
                        benefits = st.text_area(t("benefits"), max_chars=200)
                    
                    submitted = st.form_submit_button("Save Scheme", use_container_width=True)
                    if submitted:
                        new_scheme = pd.DataFrame({
                            'name': [name], 'trade': [trade], 'description': [description], 'benefits': [benefits]
                        })
                        schemes_df = pd.concat([schemes_df, new_scheme], ignore_index=True)
                        save_scheme(schemes_df)
                        st.success("Scheme added successfully!")
                        st.rerun()
            
            with tab2:
                st.subheader(t("all_schemes"))
                cols = st.columns(2)
                for idx, row in schemes_df.iterrows():
                    with cols[idx % 2]:
                        st.markdown(f"""
                        <div class='custom-card'>
                            <h4 style='color:#1976d2;margin-top:0;'>{row['name']}</h4>
                            <p style='margin-bottom:5px;'><strong>{t('trade')}:</strong> {row['trade']}</p>
                            <p style='font-size:14px;'>{row['description']}</p>
                            <div style='background:#f5f5f5;padding:10px;border-radius:8px;font-size:13px;'>
                                <strong>{t('benefits')}:</strong><br>{row['benefits']}
                            </div>
                        </div>""", unsafe_allow_html=True)
                        if st.button(t('delete'), key=f"del_{idx}"):
                            try:
                                schemes_df = schemes_df.drop(idx).reset_index(drop=True)  # ✅ SAFE NOW
                                save_scheme(schemes_df)
                                st.success("Scheme deleted!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Delete failed: {str(e)}")
        
        else:  
            st.header(t("gov_schemes"))
            search_query = st.text_input(t("search_schemes"), placeholder="carpenter, tailor, plumber...")
            
            if search_query:
                matching_schemes = find_schemes(search_query, schemes_df)
                if not matching_schemes.empty:
                    st.success(f"**{len(matching_schemes)}** schemes found!")
                    cols = st.columns(2)
                    for idx, scheme in matching_schemes.reset_index(drop=True).iterrows():
                        with cols[idx % 2]:
                            st.markdown(f"""
                            <div class='custom-card' style='border-top-color:#4caf50;'>
                                <h3 style='color:#388e3c;margin-top:0;'>{scheme['name']}</h3>
                                <p style='margin-bottom:5px;'><span class='skill-tag'>{scheme['trade']}</span></p>
                                <p style='font-size:14px;color:#555;'>{scheme['description']}</p>
                                <div style='background:#e8f5e9;padding:10px;border-radius:8px;font-size:13px;'>
                                    <strong>{t('benefits')}:</strong><br>{scheme['benefits']}
                                </div>
                            </div>""", unsafe_allow_html=True)
                else:
                    st.info(t("no_schemes"))
            else:
                st.info(t("search_schemes") + " " + t("trade") + "...")

