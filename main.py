import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import date, timedelta
import plotly.express as px
import os

# Config
st.set_page_config(page_title="🕌 جامعہ ملیہ اسلامیہ ERP", page_icon="🕌", layout="wide")

# CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
* {font-family: 'Noto Nastaliq Urdu', sans-serif !important; direction: rtl; text-align: right;}
.header {background: linear-gradient(135deg, #1e5631, #2e7d32); color: white; padding: 2rem; border-radius: 20px; text-align: center;}
.card {background: #f8f9fa; border-radius: 15px; padding: 1.5rem; margin: 1rem 0; box-shadow: 0 5px 15px rgba(0,0,0,0.1);}
.btn-primary {background: linear-gradient(135deg, #1e5631, #2e7d32) !important; border-radius: 25px !important;}
.metric {background: white; padding: 1rem; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.08);}
</style>
""", unsafe_allow_html=True)

# FIXED: Persistent Database for Streamlit Cloud
@st.cache_resource
def get_db_connection():
    """Streamlit Cloud compatible persistent DB"""
    if 'db_path' not in st.session_state:
        st.session_state.db_path = '/tmp/jamia_millia.db'  # Persistent path
    
    conn = sqlite3.connect(st.session_state.db_path, check_same_thread=False)
    return conn

def init_db():
    """Initialize complete database"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Teachers
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        dept TEXT,
        status TEXT DEFAULT 'active'
    )''')
    
    # Students
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        father_name TEXT,
        teacher_name TEXT,
        dept TEXT,
        phone TEXT,
        status TEXT DEFAULT 'active'
    )''')
    
    # Hifz Records
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE NOT NULL,
        s_name TEXT NOT NULL,
        f_name TEXT NOT NULL,
        t_name TEXT NOT NULL,
        surah TEXT,
        sq_m INTEGER DEFAULT 0,
        m_m INTEGER DEFAULT 0,
        attendance TEXT DEFAULT 'حاضر',
        lines INTEGER DEFAULT 0
    )''')
    
    # Exams
    c.execute('''CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        s_name TEXT NOT NULL,
        f_name TEXT NOT NULL,
        dept TEXT,
        from_para INTEGER,
        to_para INTEGER,
        q1 INTEGER DEFAULT 0,
        q2 INTEGER DEFAULT 0,
        q3 INTEGER DEFAULT 0,
        q4 INTEGER DEFAULT 0,
        q5 INTEGER DEFAULT 0,
        total INTEGER DEFAULT 0,
        grade TEXT,
        status TEXT DEFAULT 'پینڈنگ',
        exam_date DATE DEFAULT CURRENT_DATE
    )''')
    
    # Default admin (jamia123 hashed)
    admin_hash = hashlib.sha256("jamia123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO teachers (name, password, dept) VALUES (?, ?, ?)", 
              ("admin", admin_hash, "Administrator"))
    
    conn.commit()
    conn.close()
    return True

# Initialize
init_db()

# Session State
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_type = ""

# Header
if st.session_state.logged_in:
    st.markdown("""
    <div class='header'>
        <h1 style='margin:0;'>🕌 جامعہ ملیہ اسلامیہ</h1>
        <p style='margin:0.5rem 0 0 0; opacity:0.9;'>حفظ قرآن | درسِ نظامی | عصری تعلیم | ERP نظام</p>
    </div>
    """, unsafe_allow_html=True)

# ==================== LOGIN PAGE ====================
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='card' style='max-width:400px;margin:auto;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center;color:#1e5631;margin-bottom:2rem;'>🔐 سسٹم لاگ ان</h2>", unsafe_allow_html=True)
        
        username = st.text_input("👤 صارف نام", placeholder="admin", help="صارف نام درج کریں")
        password = st.text_input("🔐 پاس ورڈ", type="password", placeholder="jamia123", help="پاس ورڈ درج کریں")
        
        col1, col2 = st.columns([3, 1])
        if col2.button("🚀 داخل ہوں", key="login_submit"):
            conn = get_db_connection()
            
            # FIXED: Proper SQL execution
            c = conn.cursor()
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (username, hashed_pw))
            user = c.fetchone()
            
            conn.close()
            
            if user:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_type = "admin" if username == "admin" else "teacher"
                st.success(f"✅ خوش آمدید {username}!")
                st.rerun()
            else:
                st.error("❌ غلط صارف نام یا پاس ورڈ!")
                st.info("**ڈیمو اکاؤنٹ:** admin / jamia123")
        
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==================== MAIN DASHBOARD ====================
col1, col2 = st.columns([1, 5])
with col1:
    st.markdown("### 👤 پروفائل")
    st.markdown(f"**{st.session_state.username}**")
    st.markdown(f"**{st.session_state.user_type}**")
    
    if st.button("🚪 لاگ آؤٹ", key="logout"):
        st.session_state = {}
        st.rerun()

menu_options = ["📊 ڈیش بورڈ", "📝 یومیہ رپورٹ", "🎓 امتحانات", "👥 طلبہ رجسٹر"]
if st.session_state.user_type == "admin":
    menu_options += ["👨‍🏫 اساتذہ", "⚙️ بیک اپ"]

with col2:
    selected_page = st.selectbox("منو منتخب کریں:", menu_options)

# ==================== PAGES ====================
if selected_page == "📊 ڈیش بورڈ":
    st.markdown("<h2>📊 کنٹرول پینل</h2>", unsafe_allow_html=True)
    
    # Metrics
    conn = get_db_connection()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        students = pd.read_sql_query("SELECT COUNT(*) cnt FROM students WHERE status='active'", conn)['cnt'].iloc[0]
        st.markdown(f"""
        <div class='metric'>
            <h3>طلبہ</h3>
            <h1 style='color:#2196F3;'>{students}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        teachers = pd.read_sql_query("SELECT COUNT(*) cnt FROM teachers WHERE name!='admin' AND status='active'", conn)['cnt'].iloc[0]
        st.markdown(f"""
        <div class='metric'>
            <h3>اساتذہ</h3>
            <h1 style='color:#FF9800;'>{teachers}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        today_records = pd.read_sql_query("SELECT COUNT(*) cnt FROM hifz_records WHERE r_date=?", conn, params=(date.today(),))['cnt'].iloc[0]
        st.markdown(f"""
        <div class='metric'>
            <h3>آج ریکارڈ</h3>
            <h1 style='color:#4CAF50;'>{today_records}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        pending_exams = pd.read_sql_query("SELECT COUNT(*) cnt FROM exams WHERE status='پینڈنگ'", conn)['cnt'].iloc[0]
        st.markdown(f"""
        <div class='metric'>
            <h3>پینڈنگ امتحان</h3>
            <h1 style='color:#F44336;'>{pending_exams}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    conn.close()

elif selected_page == "📝 یومیہ رپورٹ":
    st.markdown("<h2>📝 یومیہ تعلیمی رپورٹ</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("تاریخ آغاز", date.today()-timedelta(days=30))
    with col2:
        end_date = st.date_input("تاریخ ختم", date.today())
    
    conn = get_db_connection()
    df = pd.read_sql_query("""
        SELECT r_date as 'تاریخ', s_name as 'نام', f_name as 'والد کا نام', 
               t_name as 'استاد', surah as 'سورۃ/سبق', sq_m as 'سبق_غلطی', 
               m_m as 'منزل_غلطی', attendance as 'حاضری'
        FROM hifz_records 
        WHERE r_date BETWEEN ? AND ? 
        ORDER BY r_date DESC
    """, conn, params=(start_date, end_date))
    conn.close()
    
    if not df.empty:
        df['کل غلطیاں'] = df['سبق_غلطی'].fillna(0) + df['منزل_غلطی'].fillna(0)
        st.dataframe(df, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 CSV", df.to_csv(index=False, encoding='utf-8-sig'), "daily_report.csv")
        with col2:
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button("📊 Excel", csv, "daily_report.xlsx", "text/csv")
    else:
        st.info("📭 کوئی ریکارڈ نہیں ملا")

# Footer
st.markdown("""
<hr style='border: 2px solid #1e5631;'>
<div style='text-align:center;padding:1.5rem;background:#f8f9fa;border-radius:15px;'>
    <h3 style='color:#1e5631;'>جامعہ ملیہ اسلامیہ</h3>
    <p>🔥 Deployed on Streamlit Cloud | © 2026</p>
</div>
""", unsafe_allow_html=True)
