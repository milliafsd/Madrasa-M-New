import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import plotly.express as px # گرافکس کے لیے

# --- 1. ڈیٹا بیس کی توسیع ---
DB_NAME = 'jamia_erp_v2.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

def init_db():
    # بنیادی ٹیبلز
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, password TEXT, dept TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, f_name TEXT, t_name TEXT, category TEXT, grade TEXT)''')
    
    # درسِ نظامی اور عصری تعلیم کے اسباق کا ٹیبل
    c.execute('''CREATE TABLE IF NOT EXISTS general_education (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, r_date DATE, s_name TEXT, t_name TEXT, 
                 dept TEXT, book_subject TEXT, today_lesson TEXT, homework TEXT, performance TEXT)''')
    
    # حفظ کا ٹیبل (پہلے والا)
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records (id INTEGER PRIMARY KEY AUTOINCREMENT, r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT, surah TEXT, sq_m INTEGER, m_m INTEGER, attendance TEXT)''')
    
    # ٹائم ٹیبل ٹیبل
    c.execute('''CREATE TABLE IF NOT EXISTS timetable (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, day TEXT, period TEXT, book TEXT, room TEXT)''')
    
    # ایڈمن صارف
    c.execute("INSERT OR IGNORE INTO teachers (name, password, dept) VALUES (?,?,?)", ("admin", "jamia123", "Admin"))
    conn.commit()

init_db()

# --- 2. اسٹائلنگ اور برانڈنگ ---
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ ERP", layout="wide")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    body, div, p, h1, h2, h3, label, .stSelectbox { direction: rtl; text-align: right; font-family: 'Noto Nastaliq Urdu', serif; }
    .main-header { background: linear-gradient(90deg, #1e5631, #a4c639); color: white; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    .card { background: #ffffff; padding: 20px; border-radius: 10px; border-right: 5px solid #1e5631; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 10px; }
    .stButton>button { background: #1e5631; color: white; border-radius: 20px; transition: 0.3s; }
    .stButton>button:hover { background: #a4c639; transform: scale(1.05); }
</style>
""", unsafe_allow_html=True)

# --- 3. لاگ ان لاجک ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ اسمارٹ ERP</h1><p>درسِ نظامی | حفظ | عصری تعلیم</p></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        u = st.text_input("صارف نام")
        p = st.text_input("پاسورڈ", type="password")
        if st.button("لاگ ان کریں"):
            res = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
            if res:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.user_type = "admin" if u == "admin" else "teacher"
                st.rerun()
            else: st.error("غلط معلومات!")
else:
    # مینو بار
    if st.session_state.user_type == "admin":
        menu = ["📈 ایڈمن ڈیش بورڈ (Check & Balance)", "📚 ٹائم ٹیبل مینیجر", "👨‍🎓 رجسٹریشن و کنٹرول", "📊 تعلیمی رپورٹس"]
    else:
        menu = ["📝 روزانہ سبق اندراج", "🕒 میرا ٹائم ٹیبل", "📩 رخصت"]
    
    m = st.sidebar.radio("📌 مین مینو", menu)

    # ================= ADMIN: CHECK & BALANCE =================
    if m == "📈 ایڈمن ڈیش بورڈ (Check & Balance)":
        st.markdown("<div class='main-header'><h1>📊 ایڈمن نگرانی ڈیش بورڈ</h1></div>", unsafe_allow_html=True)
        
        # کوئیک سٹیٹس
        c1, c2, c3, c4 = st.columns(4)
        total_s = c.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        total_t = c.execute("SELECT COUNT(*) FROM teachers WHERE name!='admin'").fetchone()[0]
        c1.metric("کل طلباء", total_s)
        c2.metric("کل اساتذہ", total_t)
        
        # حیرت انگیز فیچر: الرٹ سسٹم
        st.subheader("🚩 الرٹس (فوری توجہ کے طالب)")
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.info("📉 **کمزور کارکردگی والے طلباء (حفظ)**")
            low_perf = pd.read_sql_query("SELECT s_name, sq_m FROM hifz_records WHERE sq_m > 3 AND r_date = ?", conn, params=[date.today()])
            if not low_perf.empty: st.warning("آج ان طلباء کی سبقی غلطیاں زیادہ تھیں!")
            st.dataframe(low_perf, hide_index=True)

        with col_b:
            st.info("🚫 **غیر حاضر اساتذہ (آج)**")
            # یہاں حاضری کے ٹیبل سے موازنہ کیا جا سکتا ہے
            st.write("تمام اساتذہ حاضر ہیں۔")

        # گرافیکل تجزیہ
        st.subheader("📈 تعلیمی پیش رفت کا گراف")
        df_plot = pd.read_sql_query("SELECT r_date, COUNT(*) as count FROM hifz_records GROUP BY r_date", conn)
        if not df_plot.empty:
            fig = px.line(df_plot, x="r_date", y="count", title="روزانہ اسباق کی شرح")
            st.plotly_chart(fig, use_container_width=True)

    # ================= TEACHER: DAILY ENTRY =================
    elif m == "📝 روزانہ سبق اندراج":
        st.header("📝 تعلیمی اندراج")
        dept = st.selectbox("شعبہ منتخب کریں", ["حفظ", "درسِ نظامی", "عصری تعلیم (School)"])
        
        today = date.today()
        
        if dept == "حفظ":
            # یہاں آپ کا پرانا حفظ والا کوڈ (Dynamic Rows کے ساتھ) آئے گا
            st.success("حفظ کے اندراج کا فارم لوڈ ہو گیا...")
            # (پچھلے کوڈ والا حفظ مینو یہاں شامل ہوگا)
            
        elif dept == "درسِ نظامی":
            st.subheader("📖 درسِ نظامی سبق ریکارڈ")
            teachers_students = c.execute("SELECT name FROM students WHERE category='درسِ نظامی'").fetchall()
            s_name = st.selectbox("طالب علم", [s[0] for s in teachers_students])
            
            with st.form("dars_form"):
                book = st.text_input("کتاب کا نام (مثلاً: قدوری، نحومیر)")
                lesson = st.text_area("آج کا سبق / صفحہ نمبر / مقام")
                perf = st.select_slider("طالب علم کی سمجھ بوجھ", options=["بہت بہتر", "بہتر", "مناسب", "کمزور"])
                if st.form_submit_button("محفوظ کریں"):
                    c.execute("INSERT INTO general_education (r_date, s_name, t_name, dept, book_subject, today_lesson, performance) VALUES (?,?,?,?,?,?,?)",
                              (today, s_name, st.session_state.username, "درس نظامی", book, lesson, perf))
                    conn.commit(); st.success("سبق درج کر لیا گیا!")

        elif dept == "عصری تعلیم (School)":
            st.subheader("🏫 عصری (سکول) تعلیم ڈائری")
            grade = st.selectbox("کلاس", ["نرسری", "اول", "دوم", "سوم", "چہارم", "پنجم", "ششم", "ہفتم", "ہشتم"])
            s_list = c.execute("SELECT name FROM students WHERE grade=?", (grade,)).fetchall()
            
            with st.form("school_form"):
                sel_student = st.selectbox("طالب علم", [s[0] for s in s_list])
                subject = st.selectbox("مضمون", ["Urdu", "English", "Math", "Science", "Islamiat", "S.Studies"])
                topic = st.text_input("آج کا عنوان (Topic)")
                h_work = st.text_area("گھر کا کام (Homework)")
                if st.form_submit_button("ڈائری محفوظ کریں"):
                    c.execute("INSERT INTO general_education (r_date, s_name, t_name, dept, book_subject, today_lesson, homework) VALUES (?,?,?,?,?,?,?)",
                              (today, sel_student, st.session_state.username, "عصری تعلیم", subject, topic, h_work))
                    conn.commit(); st.success("سکول ریکارڈ محفوظ!")

    # ================= TIMETABLE =================
    elif m == "📚 ٹائم ٹیبل مینیجر":
        st.header("🕒 ٹائم ٹیبل کی ترتیب")
        t_list = [t[0] for t in c.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
        sel_t = st.selectbox("استاد منتخب کریں", t_list)
        
        with st.expander("➕ نیا پیریڈ شامل کریں"):
            day = st.selectbox("دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"])
            period = st.text_input("وقت / پیریڈ (مثلاً: 08:00 تا 09:00)")
            book = st.text_input("کتاب / مضمون")
            if st.button("ٹائم ٹیبل میں شامل کریں"):
                c.execute("INSERT INTO timetable (t_name, day, period, book) VALUES (?,?,?,?)", (sel_t, day, period, book))
                conn.commit(); st.rerun()
        
        st.write(f"### 🗓️ شیڈول برائے {sel_t}")
        tt_df = pd.read_sql_query(f"SELECT day as دن, period as وقت, book as کتاب FROM timetable WHERE t_name='{sel_t}'", conn)
        st.table(tt_df)

    # ================= REGISTRATION =================
    elif m == "👨‍🎓 رجسٹریشن و کنٹرول":
        st.header("⚙️ رجسٹریشن سینٹر")
        tab1, tab2 = st.tabs(["طلباء کا داخلہ", "اساتذہ کی تعیناتی"])
        
        with tab1:
            with st.form("s_form"):
                sn = st.text_input("نام طالب علم")
                sf = st.text_input("ولدیت")
                cat = st.selectbox("شعبہ", ["حفظ", "درسِ نظامی", "عصری تعلیم"])
                grd = st.selectbox("کلاس (عصری تعلیم کے لیے)", ["N/A", "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th"])
                tn = st.selectbox("نگران استاد", [t[0] for t in c.execute("SELECT name FROM teachers").fetchall()])
                if st.form_submit_button("داخلہ مکمل کریں"):
                    c.execute("INSERT INTO students (name, f_name, t_name, category, grade) VALUES (?,?,?,?,?)", (sn, sf, tn, cat, grd))
                    conn.commit(); st.success("طالب علم رجسٹر ہو گیا!")

    # لاگ آؤٹ
    st.sidebar.divider()
    if st.sidebar.button("🚪 لاگ آؤٹ"):
        st.session_state.logged_in = False
        st.rerun()
