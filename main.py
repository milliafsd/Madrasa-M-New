import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import date, timedelta
import plotly.express as px

# Config for Streamlit Cloud
st.set_page_config(
    page_title="🕌 جامعہ ملیہ اسلامیہ ERP", 
    page_icon="🕌",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
* {font-family: 'Noto Nastaliq Urdu', sans-serif !important; direction: rtl; text-align: right;}
.header {background: linear-gradient(135deg, #1e5631, #2e7d32); color: white; padding: 2rem; border-radius: 20px; text-align: center;}
.card {background: #f8f9fa; border-radius: 15px; padding: 1.5rem; margin: 1rem 0; box-shadow: 0 5px 15px rgba(0,0,0,0.1);}
.btn-primary {background: linear-gradient(135deg, #1e5631, #2e7d32) !important; border-radius: 25px !important;}
</style>
""", unsafe_allow_html=True)

# Database (Streamlit Cloud compatible)
@st.cache_resource
def init_db():
    conn = sqlite3.connect(':memory:')  # In-memory for cloud
    c = conn.cursor()
    
    c.execute('''CREATE TABLE teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        password TEXT,
        dept TEXT
    )''')
    
    c.execute('''CREATE TABLE students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        father_name TEXT,
        teacher_name TEXT
    )''')
    
    c.execute('''CREATE TABLE hifz_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE,
        s_name TEXT,
        f_name TEXT,
        t_name TEXT,
        surah TEXT,
        sq_m INTEGER,
        m_m INTEGER,
        attendance TEXT
    )''')
    
    c.execute('''CREATE TABLE exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        s_name TEXT,
        f_name TEXT,
        from_para INTEGER,
        to_para INTEGER,
        q1 INTEGER DEFAULT 0,
        q2 INTEGER DEFAULT 0,
        q3 INTEGER DEFAULT 0,
        q4 INTEGER DEFAULT 0,
        q5 INTEGER DEFAULT 0,
        total INTEGER,
        grade TEXT,
        status TEXT DEFAULT 'پینڈنگ'
    )''')
    
    # Default admin
    admin_hash = hashlib.sha256("jamia123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO teachers VALUES (1, 'admin', ?, 'Admin')", (admin_hash,))
    conn.commit()
    return conn

db = init_db()

# Session State
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# Header
if st.session_state.logged_in:
    st.markdown("""
    <div class='header'>
        <h1>🕌 جامعہ ملیہ اسلامیہ</h1>
        <p>حفظ قرآن | درسِ نظامی | عصری تعلیم | ERP نظام</p>
    </div>
    """, unsafe_allow_html=True)

# Login Page
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center;color:#1e5631;'>🔐 لاگ ان</h2>", unsafe_allow_html=True)
        
        username = st.text_input("صارف نام", placeholder="admin")
        password = st.text_input("پاس ورڈ", type="password", placeholder="jamia123")
        
        col1, col2 = st.columns([3,1])
        if col2.button("داخل ہوں", key="login_btn"):
            hashed = hashlib.sha256(password.encode()).hexdigest()
            user = pd.read_sql_query("SELECT * FROM teachers WHERE name=? AND password=?", db, params=(username, hashed))
            
            if not user.empty:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_type = "admin" if username == "admin" else "teacher"
                st.success("✅ خوش آمدید!")
                st.rerun()
            else:
                st.error("❌ غلط صارف نام یا پاس ورڈ")
        
        st.markdown("""
        <div style='text-align:center;margin-top:2rem;padding:1rem;background:#e3f2fd;border-radius:10px;'>
            <strong>ڈیمو اکاؤنٹ:</strong><br>admin / jamia123
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# Main App
col1, col2 = st.columns([1,6])
with col1:
    st.markdown("## 👋 خوش آمدید")
    st.markdown(f"**{st.session_state.username}**")
    st.markdown(f"**{st.session_state.user_type}**")

with col2:
    menu = ["📊 ڈیش بورڈ", "📝 یومیہ رپورٹ", "🎓 امتحانات", "👥 طلبہ", "🕒 حاضری"]
    if st.session_state.user_type == "admin":
        menu += ["👨‍🏫 اساتذہ", "📚 ٹائم ٹیبل", "⚙️ ترتیبات"]
    
    selected = st.selectbox("منو", menu)

# Pages
if selected == "📊 ڈیش بورڈ":
    st.markdown("<h2>📊 ڈیش بورڈ</h2>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        students = pd.read_sql_query("SELECT COUNT(*) cnt FROM students", db)['cnt'].iloc[0]
        st.metric("طلبہ", students)
    with col2:
        teachers = pd.read_sql_query("SELECT COUNT(*) cnt FROM teachers WHERE name!='admin'", db)['cnt'].iloc[0]
        st.metric("اساتذہ", teachers)
    with col3:
        today = pd.read_sql_query("SELECT COUNT(*) cnt FROM hifz_records WHERE r_date=?", db, params=(date.today(),))['cnt'].iloc[0]
        st.metric("آج ریکارڈ", today)
    with col4:
        pending = pd.read_sql_query("SELECT COUNT(*) cnt FROM exams WHERE status='پینڈنگ'", db)['cnt'].iloc[0]
        st.metric("پینڈنگ امتحان", pending)

elif selected == "📝 یومیہ رپورٹ":
    st.markdown("<h2>📝 یومیہ تعلیمی رپورٹ</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1: start_date = st.date_input("از تاریخ", date.today()-timedelta(days=30))
    with col2: end_date = st.date_input("تک تاریخ", date.today())
    
    df = pd.read_sql_query("""
        SELECT r_date, s_name نام, f_name والد, t_name استاد, surah سبق,
               sq_m 'سبق_غلطی', m_m 'منزل_غلطی', attendance حاضری
        FROM hifz_records WHERE r_date BETWEEN ? AND ?
    """, db, params=(start_date, end_date))
    
    if not df.empty:
        df['کل_غلطیاں'] = df['سبق_غلطی'].fillna(0) + df['منزل_غلطی'].fillna(0)
        st.dataframe(df)
        
        if st.button("📥 CSV ڈاؤن لوڈ"):
            st.download_button("ڈاؤن لوڈ", df.to_csv(index=False), "daily_report.csv")
    else:
        st.info("کوئی ریکارڈ نہیں")

elif selected == "🎓 امتحانات":
    tab1, tab2 = st.tabs(["📋 پینڈنگ", "✅ مکمل"])
    
    with tab1:
        pending = pd.read_sql_query("SELECT * FROM exams WHERE status='پینڈنگ'", db)
        if not pending.empty:
            for idx, row in pending.iterrows():
                with st.expander(f"{row['s_name']} - {row['from_para']}-{row['to_para']}"):
                    col1, col2, col3, col4, col5 = st.columns(5)
                    q1 = col1.number_input("سوال 1", 0, 20, key=f"q1_{row['id']}")
                    q2 = col2.number_input("سوال 2", 0, 20, key=f"q2_{row['id']}")
                    q3 = col3.number_input("سوال 3", 0, 20, key=f"q3_{row['id']}")
                    q4 = col4.number_input("سوال 4", 0, 20, key=f"q4_{row['id']}")
                    q5 = col5.number_input("سوال 5", 0, 20, key=f"q5_{row['id']}")
                    
                    total = q1+q2+q3+q4+q5
                    col1.metric("کل", total)
                    
                    if st.button("✅ مکمل کریں", key=f"exam_{row['id']}"):
                        grade = "ممتاز" if total >= 90 else "جید" if total >= 80 else "ناکام"
                        pd.read_sql_query("UPDATE exams SET q1=?,q2=?,q3=?,q4=?,q5=?,total=?,grade=?,status='مکمل' WHERE id=?", 
                                        db, params=(q1,q2,q3,q4,q5,total,grade,row['id']))
                        st.success("✅ امتحان مکمل!")
                        st.rerun()
        else:
            st.success("کوئی پینڈنگ امتحان نہیں")
    
    with tab2:
        completed = pd.read_sql_query("SELECT * FROM exams WHERE status='مکمل' ORDER BY id DESC", db)
        st.dataframe(completed)

# Footer
st.markdown("""
<div style='text-align:center;padding:2rem;background:#1e5631;color:white;border-radius:20px;margin-top:3rem;'>
    <h3>جامعہ ملیہ اسلامیہ ERP</h3>
    <p>© 2026 | Deployed on Streamlit Cloud</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 👤 پروفائل")
    st.markdown(f"**{st.session_state.username}**")
    st.markdown(f"**{st.session_state.user_type}**")
    
    if st.button("🚪 لاگ آؤٹ"):
        st.session_state.logged_in = False
        st.rerun()
