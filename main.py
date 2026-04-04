import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
import sqlite3
import pytz
import hashlib
import plotly.express as px

# Page config
st.set_page_config(page_title="🕌 جامعہ ملیہ اسلامیہ ERP", layout="wide", page_icon="🕌")

# CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
* {font-family: 'Noto Nastaliq Urdu', Arial, sans-serif !important; direction: rtl;}
.main-header {background: linear-gradient(135deg, #1e5631, #2e7d32); color: white; padding: 2rem; border-radius: 20px; text-align: center;}
.card {background: white; border-radius: 15px; padding: 1.5rem; margin: 1rem 0; box-shadow: 0 10px 30px rgba(0,0,0,0.1);}
.stButton > button {background: linear-gradient(135deg, #1e5631, #2e7d32); color: white; border-radius: 25px; border: none; padding: 0.7rem 2rem;}
</style>
""", unsafe_allow_html=True)

# Database
DB_NAME = 'jamia_millia.db'
def get_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY, name TEXT UNIQUE, password TEXT, dept TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY, name TEXT, father_name TEXT, teacher_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records (id INTEGER PRIMARY KEY, r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT, surah TEXT, sq_m INTEGER, m_m INTEGER, attendance TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS exams (id INTEGER PRIMARY KEY, s_name TEXT, f_name TEXT, from_para INTEGER, to_para INTEGER, q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER, q5 INTEGER, total INTEGER, grade TEXT, status TEXT)''')
    
    # Default admin
    admin_hash = hashlib.sha256("jamia123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO teachers (name, password, dept) VALUES (?, ?, ?)", ("admin", admin_hash, "Admin"))
    conn.commit()
    conn.close()

init_db()

# Session
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# Login
if not st.session_state.logged_in:
    st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ</h1><p>حفظ | درسِ نظامی | عصری تعلیم</p></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1,1])
    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        username = st.text_input("👤 صارف نام")
        password = st.text_input("🔐 پاس ورڈ", type="password")
        
        if st.button("داخل ہوں", key="login"):
            conn = get_db()
            hashed = hashlib.sha256(password.encode()).hexdigest()
            user = conn.execute("SELECT * FROM teachers WHERE name=? AND password=?", (username, hashed)).fetchone()
            conn.close()
            
            if user:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_type = "admin" if username == "admin" else "teacher"
                st.success("✅ خوش آمدید!")
                st.rerun()
            else:
                st.error("❌ غلط صارف نام یا پاس ورڈ")
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.info("**ڈیمو:** admin / jamia123")
    st.stop()

# Main App
st.markdown(f"<div class='main-header'><h1>خوش آمدید {st.session_state.username}</h1></div>", unsafe_allow_html=True)

# Sidebar Menu
if st.session_state.user_type == "admin":
    menu = ["📊 ڈیش بورڈ", "📝 یومیہ رپورٹ", "🎓 امتحانات", "👥 طلبہ", "👨‍🏫 اساتذہ", "🕒 حاضری", "📚 ٹائم ٹیبل"]
else:
    menu = ["📝 یومیہ اندراج", "🎓 امتحانات", "🕒 حاضری"]

selected = st.sidebar.selectbox("منتخب کریں", menu)

# Dashboard
if selected == "📊 ڈیش بورڈ" and st.session_state.user_type == "admin":
    st.markdown("<h2>ایڈمن ڈیش بورڈ</h2>", unsafe_allow_html=True)
    
    conn = get_db()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        st.metric("طلبہ", students)
    with col2:
        teachers = conn.execute("SELECT COUNT(*) FROM teachers WHERE name!='admin'").fetchone()[0]
        st.metric("اساتذہ", teachers)
    with col3:
        today_records = conn.execute("SELECT COUNT(*) FROM hifz_records WHERE r_date=?", (date.today(),)).fetchone()[0]
        st.metric("آج کے ریکارڈ", today_records)
    with col4:
        pending = conn.execute("SELECT COUNT(*) FROM exams WHERE status='پینڈنگ'").fetchone()[0]
        st.metric("پینڈنگ امتحانات", pending)
    conn.close()

# Daily Report
elif "یومیہ" in selected:
    st.markdown("<h2>📊 یومیہ تعلیمی رپورٹ</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1: start_date = st.date_input("ابتدا", date.today()-timedelta(days=30))
    with col2: end_date = st.date_input("اختتام", date.today())
    
    conn = get_db()
    df = pd.read_sql_query("""
        SELECT r_date as 'تاریخ', s_name as 'نام', f_name as 'والد', t_name as 'استاد',
               surah as 'سبق', sq_m as 'سبق_غلطی', m_m as 'منزل_غلطی', attendance as 'حاضری'
        FROM hifz_records WHERE r_date BETWEEN ? AND ?
    """, conn, params=(start_date, end_date))
    conn.close()
    
    if not df.empty:
        df['کل_غلطیاں'] = df['سبق_غلطی'].fillna(0) + df['منزل_غلطی'].fillna(0)
        edited_df = st.data_editor(df, num_rows="dynamic")
        
        if st.button("💾 محفوظ کریں"):
            st.success("محفوظ!")
    else:
        # New entry form
        with st.form("new_entry"):
            col1, col2 = st.columns(2)
            with col1: s_name = st.text_input("طالب علم")
            with col2: f_name = st.text_input("والد")
            with col1: t_name = st.text_input("استاد")
            with col2: surah = st.text_input("سورۃ/سبق")
            with col1: sq_m = st.number_input("سبق_غلطی", 0)
            with col2: m_m = st.number_input("منزل_غلطی", 0)
            attendance = st.selectbox("حاضری", ["حاضر", "غائب"])
            
            if st.form_submit_button("ثبت کریں"):
                conn = get_db()
                conn.execute("INSERT INTO hifz_records (r_date, s_name, f_name, t_name, surah, sq_m, m_m, attendance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (date.today(), s_name, f_name, t_name, surah, sq_m, m_m, attendance))
                conn.commit()
                conn.close()
                st.success("✅ ثبت ہو گیا!")
                st.rerun()

# Exams
elif "امتحانات" in selected:
    st.markdown("<h2>🎓 امتحانی نظام</h2>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["پینڈنگ", "مکمل"])
    
    with tab1:
        conn = get_db()
        pending = pd.read_sql_query("SELECT * FROM exams WHERE status='پینڈنگ'", conn)
        conn.close()
        
        if not pending.empty:
            for idx, exam in pending.iterrows():
                with st.expander(f"{exam['s_name']} - پارہ {exam['from_para']}-{exam['to_para']}"):
                    col1, col2, col3, col4, col5 = st.columns(5)
                    q1 = col1.number_input("س1", key=f"q1_{idx}")
                    q2 = col2.number_input("س2", key=f"q2_{idx}")
                    q3 = col3.number_input("س3", key=f"q3_{idx}")
                    q4 = col4.number_input("س4", key=f"q4_{idx}")
                    q5 = col5.number_input("س5", key=f"q5_{idx}")
                    
                    total = q1+q2+q3+q4+q5
                    if st.button("✅ کلیئر کریں", key=f"clear_{idx}"):
                        conn = get_db()
                        conn.execute("UPDATE exams SET q1=?, q2=?, q3=?, q4=?, q5=?, total=?, grade=?, status=? WHERE id=?",
                                   (q1,q2,q3,q4,q5,total,"ممتاز" if total>=90 else "جید","مکمل", exam['id']))
                        conn.commit()
                        conn.close()
                        st.success("امتحان مکمل!")
                        st.rerun()
        else:
            st.info("کوئی پینڈنگ امتحان نہیں")
    
    with tab2:
        conn = get_db()
        completed = pd.read_sql_query("SELECT * FROM exams WHERE status='مکمل' ORDER BY id DESC", conn)
        conn.close()
        st.dataframe(completed)

# Sidebar logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 لاگ آؤٹ"):
    st.session_state.logged_in = False
    st.rerun()
