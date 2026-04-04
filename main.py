import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import date, timedelta
import plotly.express as px

# Page Config
st.set_page_config(page_title="🕌 جامعہ ملیہ اسلامیہ ERP", page_icon="🕌", layout="wide")

# Modern CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
* {font-family: 'Noto Nastaliq Urdu', sans-serif !important; direction: rtl; text-align: right;}
.header {background: linear-gradient(135deg, #1e5631 0%, #2e7d32 50%, #4caf50 100%); color: white; padding: 2.5rem; border-radius: 25px; text-align: center; box-shadow: 0 10px 30px rgba(30,86,49,0.3);}
.card {background: rgba(255,255,255,0.95); border-radius: 20px; padding: 2rem; margin: 1rem 0; box-shadow: 0 10px 30px rgba(0,0,0,0.1); backdrop-filter: blur(10px);}
.metric-card {background: rgba(255,255,255,0.9); padding: 1.5rem; border-radius: 15px; text-align: center; box-shadow: 0 8px 25px rgba(0,0,0,0.1);}
.btn-login {background: linear-gradient(135deg, #1e5631, #2e7d32) !important; border-radius: 30px !important; font-weight: bold !important;}
</style>
""", unsafe_allow_html=True)

# ==================== STREAMLIT CLOUD COMPATIBLE DB ====================
@st.cache_resource
def get_persistent_db():
    """100% Streamlit Cloud compatible - Session State DB"""
    if 'db_data' not in st.session_state:
        st.session_state.db_data = {
            'teachers': [],
            'students': [],
            'hifz_records': [],
            'exams': []
        }
    
    # Initialize default data if empty
    if not st.session_state.db_data['teachers']:
        admin_hash = hashlib.sha256("jamia123".encode()).hexdigest()
        st.session_state.db_data['teachers'] = [
            {'id': 1, 'name': 'admin', 'password': admin_hash, 'dept': 'Administrator'}
        ]
    
    return st.session_state.db_data

def execute_query(query, params=(), table_name=None, action='select'):
    """Universal DB query executor"""
    db_data = get_persistent_db()
    
    if action == 'select':
        if table_name:
            df = pd.DataFrame(db_data.get(table_name, []))
            if params:
                condition_col, condition_val = params[0]
                df = df[df[condition_col] == condition_val]
            return df
        return pd.DataFrame()
    
    elif action == 'insert':
        if table_name:
            record_id = len(db_data[table_name]) + 1
            new_record = {'id': record_id, **params[0]}
            db_data[table_name].append(new_record)
            st.session_state.db_data = db_data  # Update session
            return True
        return False

# Session State
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_type = ""

# ==================== LOGIN PAGE ====================
if not st.session_state.logged_in:
    st.markdown("""
    <div class='header'>
        <div style='font-size: 4rem;'>🕌</div>
        <h1 style='font-size: 2.5rem; margin: 1rem 0;'>جامعہ ملیہ اسلامیہ</h1>
        <p style='font-size: 1.3rem; opacity: 0.9;'>حفظ قرآن | درسِ نظامی | عصری تعلیم</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center; color:#1e5631; margin-bottom:2rem;'>🔐 سسٹم لاگ ان</h2>", unsafe_allow_html=True)
        
        username = st.text_input("👤 صارف نام", placeholder="admin", help="صارف نام درج کریں")
        password = st.text_input("🔐 پاس ورڈ", type="password", placeholder="jamia123", help="پاس ورڈ درج کریں")
        
        col1, col2 = st.columns([3, 1])
        if col2.button("🚀 داخل ہوں", key="login_btn", help="لاگ ان کریں"):
            # FIXED: Session State based authentication
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            teachers = execute_query("SELECT", table_name='teachers')
            
            user = teachers[(teachers['name'] == username) & (teachers['password'] == hashed_pw)]
            
            if not user.empty:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_type = "admin" if username == "admin" else "teacher"
                st.success(f"✅ خوش آمدید {username}!")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ غلط صارف نام یا پاس ورڈ!")
        
        st.markdown("""
        <div style='text-align:center; margin-top:2rem; padding:1.5rem; background:#e3f2fd; border-radius:15px; border-left:5px solid #1e5631;'>
            <strong>💡 ڈیمو اکاؤنٹ:</strong><br>
            <code style='background:#1e5631;color:white;padding:0.3rem 0.6rem;border-radius:5px;'>admin / jamia123</code>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.stop()

# ==================== MAIN INTERFACE ====================
st.markdown("<div class='header'><h2>خوش آمدید <strong style='color:#fff;'>{}</strong></h2></div>".format(st.session_state.username), unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 👤 پروفائل")
    st.markdown(f"**{st.session_state.username}**")
    st.markdown(f"**{st.session_state.user_type}**")
    st.markdown("---")
    
    menu_options = ["📊 ڈیش بورڈ", "📝 یومیہ رپورٹ", "🎓 امتحانات", "👥 طلبہ"]
    if st.session_state.user_type == "admin":
        menu_options += ["👨‍🏫 اساتذہ", "⚙️ بیک اپ"]
    
    selected_page = st.selectbox("منو:", menu_options)
    
    if st.button("🚪 لاگ آؤٹ"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ==================== DASHBOARD ====================
if selected_page == "📊 ڈیش بورڈ":
    st.markdown("<h2 style='color:#1e5631;'>📊 کنٹرول پینل</h2>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        students = len(execute_query("SELECT", table_name='students'))
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='color:#666;'>👥 طلبہ</h3>
            <h1 style='color:#2196F3;font-size:2.5rem;'>{students}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        teachers = len(execute_query("SELECT", table_name='teachers')) - 1  # Exclude admin
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='color:#666;'>👨‍🏫 اساتذہ</h3>
            <h1 style='color:#FF9800;font-size:2.5rem;'>{teachers}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        today_records = len(execute_query("SELECT", params=('r_date', str(date.today())), table_name='hifz_records'))
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='color:#666;'>📚 آج ریکارڈ</h3>
            <h1 style='color:#4CAF50;font-size:2.5rem;'>{today_records}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        pending = len(execute_query("SELECT", params=('status', 'پینڈنگ'), table_name='exams'))
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='color:#666;'>🎓 پینڈنگ امتحان</h3>
            <h1 style='color:#F44336;font-size:2.5rem;'>{pending}</h1>
        </div>
        """, unsafe_allow_html=True)

# ==================== DAILY REPORT ====================
elif selected_page == "📝 یومیہ رپورٹ":
    st.markdown("<h2>📝 یومیہ تعلیمی رپورٹ</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("از تاریخ", date.today()-timedelta(days=30))
    with col2:
        end_date = st.date_input("تک تاریخ", date.today())
    
    hifz_df = execute_query("SELECT", table_name='hifz_records')
    if not hifz_df.empty:
        hifz_df['r_date'] = pd.to_datetime(hifz_df['r_date'])
        hifz_df = hifz_df[(hifz_df['r_date'] >= start_date) & (hifz_df['r_date'] <= end_date)]
        
        hifz_df['کل_غلطیاں'] = hifz_df['sq_m'].fillna(0) + hifz_df['m_m'].fillna(0)
        st.dataframe(hifz_df[['r_date', 's_name', 'f_name', 't_name', 'surah', 'sq_m', 'm_m', 'کل_غلطیاں', 'attendance']])
        
        # Download
        csv = hifz_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button("📥 CSV Export", csv, "hifz_report.csv", "text/csv")
    else:
        st.info("📭 ابھی کوئی ریکارڈ نہیں - نیا اندراج کریں")

# Footer
st.markdown("""
<div style='text-align:center;padding:2rem;margin-top:3rem;background:rgba(30,86,49,0.9);color:white;border-radius:25px;'>
    <h3 style='margin:0;'>جامعہ ملیہ اسلامیہ ERP</h3>
    <p style='opacity:0.9;'>🔥 Live on Streamlit Cloud | © 2026</p>
</div>
""", unsafe_allow_html=True)
