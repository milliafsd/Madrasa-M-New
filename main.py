import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import base64
import io
import plotly.express as px
from PIL import Image
import os

# --- Database Setup ---
DB_NAME = 'jamia_millia_v1 (1).db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS teachers 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, password TEXT, phone TEXT, address TEXT, id_card TEXT, photo TEXT, role TEXT DEFAULT 'teacher')''')
    c.execute('''CREATE TABLE IF NOT EXISTS students 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, father_name TEXT, teacher_name TEXT, phone TEXT, address TEXT, id_card TEXT, photo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT, 
                  surah TEXT, a_from TEXT, a_to TEXT, sq_p TEXT, sq_a INTEGER, sq_m INTEGER, 
                  m_p TEXT, m_a INTEGER, m_m INTEGER, attendance TEXT, principal_note TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, a_date DATE, arrival TEXT, departure TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, reason TEXT, start_date DATE, back_date DATE, status TEXT, request_date DATE, l_type TEXT, days INTEGER, notification_seen INTEGER DEFAULT 0)''')
    c.execute("""CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            s_name TEXT, 
            f_name TEXT, 
            para_no INTEGER, 
            start_date TEXT, 
            end_date TEXT,
            q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER, q5 INTEGER,
            total INTEGER, 
            grade TEXT,
            status TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_type TEXT,
            user_name TEXT,
            message TEXT,
            created_date TEXT,
            is_read INTEGER DEFAULT 0)""")
    conn.commit()

    # Add missing columns if needed
    try:
        c.execute("ALTER TABLE teachers ADD COLUMN role TEXT DEFAULT 'teacher'")
    except:
        pass
    try:
        c.execute("ALTER TABLE leave_requests ADD COLUMN days INTEGER")
    except:
        pass
    try:
        c.execute("ALTER TABLE leave_requests ADD COLUMN l_type TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE notifications ADD COLUMN is_read INTEGER DEFAULT 0")
    except:
        pass

    # Ensure admin user exists with role 'admin'
    c.execute("INSERT OR IGNORE INTO teachers (name, password, role) VALUES (?,?,?)", ("admin", "jamia123", "admin"))
    # Ensure admin role is set correctly
    c.execute("UPDATE teachers SET role='admin' WHERE name='admin' AND (role IS NULL OR role != 'admin')")
    conn.commit()

init_db()

# --- Helper Functions ---
def get_base64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

def create_notification(user_type, user_name, message):
    c.execute("INSERT INTO notifications (user_type, user_name, message, created_date) VALUES (?,?,?,?)",
              (user_type, user_name, message, date.today().isoformat()))
    conn.commit()

def get_notifications(user_name):
    notif = c.execute("SELECT id, message, created_date FROM notifications WHERE user_name=? AND is_read=0 ORDER BY created_date DESC", (user_name,)).fetchall()
    return notif

def mark_notification_read(notif_id):
    c.execute("UPDATE notifications SET is_read=1 WHERE id=?", (notif_id,))
    conn.commit()

# --- Custom CSS (safe) ---
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ پورٹل", layout="wide")
try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except FileNotFoundError:
    # Fallback basic styling
    st.markdown("""
    <style>
        body {direction: rtl; text-align: right;}
        .stButton>button {background: #1e5631; color: white; border-radius: 8px; font-weight: bold; width: 100%; border: none; padding: 10px;}
        .stButton>button:hover {background: #143e22;}
        .main-header {text-align: center; color: #1e5631; background-color: #f1f8e9; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-bottom: 4px solid #1e5631;}
    </style>
    """, unsafe_allow_html=True)

# --- Login / Logout Logic ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_type = ""

# --- Main App ---
if not st.session_state.logged_in:
    # Display login form
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.subheader("🔐 لاگ ان پینل")
        u = st.text_input("صارف کا نام (Username)")
        p = st.text_input("پاسورڈ (Password)", type="password")
        if st.button("داخل ہوں"):
            user = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
            if user:
                st.session_state.logged_in = True
                st.session_state.username = u
                # Determine user type from role column
                # user tuple: (id, name, password, phone, address, id_card, photo, role)
                role = user[7] if len(user) > 7 else None
                if role == 'admin':
                    st.session_state.user_type = 'admin'
                elif role == 'teacher':
                    st.session_state.user_type = 'teacher'
                else:
                    # Fallback based on name
                    st.session_state.user_type = 'admin' if u == 'admin' else 'teacher'
                st.rerun()
            else:
                st.error("❌ غلط معلومات، براہ کرم دوبارہ کوشش کریں۔")
else:
    # User is logged in
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/150?text=Logo", width=100)
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown(f"**نوعیت:** {'انتظامیہ' if st.session_state.user_type == 'admin' else 'استاد'}")
        st.divider()
        
        # Notifications
        notifs = get_notifications(st.session_state.username)
        if notifs:
            with st.expander(f"📢 اطلاعیں ({len(notifs)})"):
                for nid, msg, date_ in notifs:
                    col1, col2 = st.columns([5,1])
                    col1.write(f"📅 {date_}: {msg}")
                    if col2.button("✔️", key=f"read_{nid}"):
                        mark_notification_read(nid)
                        st.rerun()
        else:
            st.info("کوئی نئی اطلاع نہیں")
        
        st.divider()
        if st.button("🚪 لاگ آؤٹ کریں"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_type = ""
            st.rerun()
    
    # Menu based on user type
    if st.session_state.user_type == "admin":
        menu_options = {
            "📊 ڈیش بورڈ": "dashboard",
            "📝 تعلیمی ریکارڈ": "hifz",
            "🎓 امتحانی نظام": "exams",
            "📜 ماہانہ رزلٹ": "monthly_result",
            "👨‍🏫 اساتذہ مینجمنٹ": "teachers",
            "👨‍🎓 طلباء مینجمنٹ": "students",
            "🏛️ رخصت کی منظوری": "leave_approval",
            "📈 رپورٹس": "reports",
            "⚙️ سیٹنگز": "settings"
        }
    else:
        menu_options = {
            "📊 ڈیش بورڈ": "dashboard",
            "📝 تعلیمی اندراج": "hifz_entry",
            "🎓 امتحانی درخواست": "exam_request",
            "📩 درخواستِ رخصت": "leave_request",
            "📜 میری رخصتیں": "my_leaves",
            "🕒 میری حاضری": "my_attendance"
        }
    
    choice = st.sidebar.radio("📌 مینو منتخب کریں", list(menu_options.keys()))
    selected = menu_options[choice]
    
    # --- Dashboard ---
    if selected == "dashboard":
        st.markdown("<h1 style='text-align: center;'>📊 جامعہ ڈیش بورڈ</h1>", unsafe_allow_html=True)
        
        if st.session_state.user_type == "admin":
            # Admin dashboard
            total_students = c.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            total_teachers = c.execute("SELECT COUNT(*) FROM teachers WHERE name != 'admin'").fetchone()[0]
            pending_leaves = c.execute("SELECT COUNT(*) FROM leave_requests WHERE status='پینڈنگ (زیرِ غور)'").fetchone()[0]
            pending_exams = c.execute("SELECT COUNT(*) FROM exams WHERE status='پینڈنگ'").fetchone()[0]
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("کل طلباء", total_students)
            col2.metric("کل اساتذہ", total_teachers)
            col3.metric("زیرِ غور رخصتیں", pending_leaves)
            col4.metric("زیرِ غور امتحانات", pending_exams)
            
            # Recent activities
            st.subheader("🕒 حالیہ سرگرمیاں")
            recent_hifz = pd.read_sql_query("SELECT r_date, s_name, t_name FROM hifz_records ORDER BY r_date DESC LIMIT 5", conn)
            if not recent_hifz.empty:
                st.dataframe(recent_hifz, use_container_width=True)
            else:
                st.info("ابھی کوئی سرگرمی نہیں")
                
        else:
            # Teacher dashboard
            st.subheader(f"👋 خوش آمدید، {st.session_state.username}")
            my_students = c.execute("SELECT COUNT(*) FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchone()[0]
            my_leaves_pending = c.execute("SELECT COUNT(*) FROM leave_requests WHERE t_name=? AND status='پینڈنگ (زیرِ غور)'", (st.session_state.username,)).fetchone()[0]
            col1, col2 = st.columns(2)
            col1.metric("میرے طلباء", my_students)
            col2.metric("زیرِ غور رخصتیں", my_leaves_pending)
            
            # Recent student performance
            st.subheader("📈 طلباء کی کارکردگی")
            perf = pd.read_sql_query(f"SELECT s_name, AVG(sq_m) as avg_sq, AVG(m_m) as avg_m FROM hifz_records WHERE t_name='{st.session_state.username}' GROUP BY s_name", conn)
            if not perf.empty:
                fig = px.bar(perf, x='s_name', y=['avg_sq', 'avg_m'], barmode='group', title="اوسط غلطیاں (سبقی و منزل)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("ابھی کوئی ڈیٹا نہیں")
    
    # --- Hifz Records (Admin) ---
    elif selected == "hifz":
        st.markdown("<h1 style='text-align: center;'>📝 تعلیمی ریکارڈ</h1>", unsafe_allow_html=True)
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            start_date = st.date_input("آغاز", date.today().replace(day=1))
        with col2:
            end_date = st.date_input("اختتام", date.today())
        with col3:
            teachers = ["تمام"] + [t[0] for t in c.execute("SELECT DISTINCT t_name FROM hifz_records").fetchall()]
            teacher_filter = st.selectbox("استاد", teachers)
        
        query = "SELECT * FROM hifz_records WHERE r_date BETWEEN ? AND ?"
        params = [start_date, end_date]
        if teacher_filter != "تمام":
            query += " AND t_name = ?"
            params.append(teacher_filter)
        
        df = pd.read_sql_query(query, conn, params=params)
        if df.empty:
            st.warning("کوئی ریکارڈ نہیں ملا۔")
        else:
            st.data_editor(df, num_rows="dynamic", use_container_width=True)
            if st.button("💾 تبدیلیاں محفوظ کریں"):
                try:
                    c.execute(f"DELETE FROM hifz_records WHERE r_date BETWEEN '{start_date}' AND '{end_date}'" + 
                              (f" AND t_name='{teacher_filter}'" if teacher_filter != "تمام" else ""))
                    df.to_sql('hifz_records', conn, if_exists='append', index=False)
                    st.success("✅ تبدیلیاں محفوظ ہو گئیں!")
                    st.rerun()
                except Exception as e:
                    st.error(f"ایرر: {e}")
    
    # --- Hifz Entry (Teacher) ---
    elif selected == "hifz_entry":
        st.markdown("<h1 style='text-align: center;'>📝 تعلیمی اندراج</h1>", unsafe_allow_html=True)
        surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
        paras = [f"پارہ {i}" for i in range(1, 31)]
        
        sel_date = st.date_input("تاریخ", date.today())
        students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
        if not students:
            st.warning("آپ کی کلاس میں کوئی طالب علم نہیں۔")
        else:
            for s, f in students:
                with st.expander(f"👤 {s} ولد {f}"):
                    att = st.radio(f"حاضری", ["حاضر", "غیر حاضر (ناغہ)", "رخصت"], key=f"att_{s}", horizontal=True)
                    if att == "حاضر":
                        # New lesson
                        st.subheader("📖 نیا سبق")
                        sabq = st.text_input("سبق", key=f"sabq_{s}")
                        # Sabqi
                        st.subheader("🔄 سبقی")
                        sq_count = st.number_input("تعداد سبقی", min_value=0, max_value=10, value=1, key=f"sq_count_{s}")
                        sq_data = []
                        sq_errors = 0
                        for i in range(sq_count):
                            col1, col2, col3, col4 = st.columns([2,1,1,1])
                            para = col1.selectbox(f"پارہ {i+1}", paras, key=f"sq_para_{s}_{i}")
                            amount = col2.selectbox(f"مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sq_amount_{s}_{i}")
                            errors = col3.number_input(f"غلطی", 0, key=f"sq_err_{s}_{i}")
                            atkan = col4.number_input(f"اٹکن", 0, key=f"sq_atk_{s}_{i}")
                            sq_data.append(f"{para}:{amount}(غ:{errors},ا:{atkan})")
                            sq_errors += errors
                        # Manzil
                        st.subheader("🏠 منزل")
                        m_count = st.number_input("تعداد منزل", min_value=0, max_value=10, value=1, key=f"m_count_{s}")
                        m_data = []
                        m_errors = 0
                        for j in range(m_count):
                            col1, col2, col3, col4 = st.columns([2,1,1,1])
                            para = col1.selectbox(f"پارہ {j+1}", paras, key=f"m_para_{s}_{j}")
                            amount = col2.selectbox(f"مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"m_amount_{s}_{j}")
                            errors = col3.number_input(f"غلطی", 0, key=f"m_err_{s}_{j}")
                            atkan = col4.number_input(f"اٹکن", 0, key=f"m_atk_{s}_{j}")
                            m_data.append(f"{para}:{amount}(غ:{errors},ا:{atkan})")
                            m_errors += errors
                        if st.button(f"محفوظ کریں: {s}", key=f"save_{s}"):
                            # Check duplicate
                            existing = c.execute("SELECT 1 FROM hifz_records WHERE r_date=? AND s_name=? AND f_name=?", (sel_date, s, f)).fetchone()
                            if existing:
                                st.error("آج کا ریکارڈ پہلے موجود ہے!")
                            else:
                                c.execute("""INSERT INTO hifz_records 
                                          (r_date, s_name, f_name, t_name, surah, sq_p, sq_m, m_p, m_m, attendance)
                                          VALUES (?,?,?,?,?,?,?,?,?,?)""",
                                          (sel_date, s, f, st.session_state.username, sabq, " | ".join(sq_data), sq_errors, " | ".join(m_data), m_errors, att))
                                conn.commit()
                                st.success(f"✅ {s} کا ریکارڈ محفوظ ہو گیا۔")
                    else:
                        if st.button(f"حاضری لگائیں: {s}", key=f"att_{s}"):
                            existing = c.execute("SELECT 1 FROM hifz_records WHERE r_date=? AND s_name=? AND f_name=?", (sel_date, s, f)).fetchone()
                            if existing:
                                st.error("آج کا ریکارڈ پہلے موجود ہے!")
                            else:
                                c.execute("""INSERT INTO hifz_records (r_date, s_name, f_name, t_name, attendance, surah, sq_p, m_p) 
                                          VALUES (?,?,?,?,?,?,?,?)""", (sel_date, s, f, st.session_state.username, att, "ناغہ", "ناغہ", "ناغہ"))
                                conn.commit()
                                st.success(f"✅ {s} کی حاضری لگ گئی۔")
    
    # --- Exams System ---
    elif selected == "exams":
        st.markdown("<h1 style='text-align: center;'>🎓 امتحانی نظام</h1>", unsafe_allow_html=True)
        if st.session_state.user_type == "admin":
            tab1, tab2 = st.tabs(["📥 پینڈنگ امتحانات", "📜 مکمل شدہ"])
            with tab1:
                pending = c.execute("SELECT id, s_name, f_name, para_no, start_date FROM exams WHERE status='پینڈنگ'").fetchall()
                if not pending:
                    st.info("کوئی امتحان زیر غور نہیں۔")
                else:
                    for eid, sn, fn, pn, sd in pending:
                        with st.expander(f"{sn} ولد {fn} (پارہ {pn}) - درخواست: {sd}"):
                            q1 = st.number_input("سوال 1", 0, 20, key=f"q1_{eid}")
                            q2 = st.number_input("سوال 2", 0, 20, key=f"q2_{eid}")
                            q3 = st.number_input("سوال 3", 0, 20, key=f"q3_{eid}")
                            q4 = st.number_input("سوال 4", 0, 20, key=f"q4_{eid}")
                            q5 = st.number_input("سوال 5", 0, 20, key=f"q5_{eid}")
                            total = q1+q2+q3+q4+q5
                            if total >= 90:
                                grade = "ممتاز"
                            elif total >= 80:
                                grade = "جید جدا"
                            elif total >= 70:
                                grade = "جید"
                            elif total >= 60:
                                grade = "مقبول"
                            else:
                                grade = "ناکام"
                            st.write(f"کل نمبر: {total} | گریڈ: {grade}")
                            if st.button("کلیئر کریں", key=f"clear_{eid}"):
                                c.execute("""UPDATE exams SET q1=?, q2=?, q3=?, q4=?, q5=?, total=?, grade=?, status=?, end_date=? WHERE id=?""",
                                          (q1, q2, q3, q4, q5, total, grade, "مکمل", date.today().isoformat(), eid))
                                conn.commit()
                                st.success("امتحان کلیئر ہو گیا!")
                                st.rerun()
            with tab2:
                completed = pd.read_sql_query("SELECT s_name, f_name, para_no, total, grade, end_date FROM exams WHERE status='مکمل'", conn)
                if not completed.empty:
                    st.dataframe(completed, use_container_width=True)
                    st.download_button("ایکسل ڈاؤن لوڈ", convert_df_to_excel(completed), "exams.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.info("کوئی مکمل شدہ امتحان نہیں۔")
        else:
            # Teacher: send exam request
            students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
            if not students:
                st.warning("آپ کی کلاس میں کوئی طالب علم نہیں۔")
            else:
                with st.form("exam_request"):
                    selected_student = st.selectbox("طالب علم", [f"{s[0]} ولد {s[1]}" for s in students])
                    para = st.number_input("پارہ نمبر", 1, 30)
                    start_date = st.date_input("تاریخ آغاز", date.today())
                    if st.form_submit_button("درخواست بھیجیں"):
                        s_name, f_name = selected_student.split(" ولد ")
                        existing = c.execute("SELECT 1 FROM exams WHERE s_name=? AND f_name=? AND para_no=? AND status='پینڈنگ'", (s_name, f_name, para)).fetchone()
                        if existing:
                            st.error("پہلے سے درخواست موجود ہے!")
                        else:
                            c.execute("INSERT INTO exams (s_name, f_name, para_no, start_date, status) VALUES (?,?,?,?,?)",
                                      (s_name, f_name, para, start_date.isoformat(), "پینڈنگ"))
                            conn.commit()
                            create_notification("admin", "admin", f"استاد {st.session_state.username} نے {s_name} کا پارہ {para} کا امتحان بھیجا۔")
                            st.success("درخواست بھیج دی گئی!")
    
    # --- Monthly Result ---
    elif selected == "monthly_result":
        st.markdown("<h1 style='text-align: center;'>📜 ماہانہ رزلٹ کارڈ</h1>", unsafe_allow_html=True)
        students = c.execute("SELECT name FROM students").fetchall()
        if not students:
            st.warning("کوئی طالب علم نہیں۔")
        else:
            student = st.selectbox("طالب علم", [s[0] for s in students])
            month = st.date_input("ماہ", date.today().replace(day=1))
            start_month = month.replace(day=1)
            end_month = (month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            data = pd.read_sql_query(f"SELECT r_date, sq_m, m_m FROM hifz_records WHERE s_name='{student}' AND r_date BETWEEN '{start_month}' AND '{end_month}'", conn)
            if not data.empty:
                avg_sq = data['sq_m'].mean()
                avg_m = data['m_m'].mean()
                col1, col2 = st.columns(2)
                col1.metric("اوسط سبقی غلطی", f"{avg_sq:.1f}")
                col2.metric("اوسط منزل غلطی", f"{avg_m:.1f}")
                fig = px.line(data, x='r_date', y=['sq_m', 'm_m'], title="غلطیوں کا رجحان")
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(data, use_container_width=True)
            else:
                st.info("اس ماہ کا کوئی ریکارڈ نہیں۔")
    
    # --- Teachers Management ---
    elif selected == "teachers":
        st.markdown("<h1 style='text-align: center;'>👨‍🏫 اساتذہ مینجمنٹ</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["نیا استاد", "موجودہ اساتذہ"])
        with tab1:
            with st.form("add_teacher"):
                name = st.text_input("نام")
                password = st.text_input("پاسورڈ", type="password")
                phone = st.text_input("فون")
                address = st.text_area("پتہ")
                submitted = st.form_submit_button("شامل کریں")
                if submitted:
                    if name and password:
                        try:
                            c.execute("INSERT INTO teachers (name, password, phone, address, role) VALUES (?,?,?,?,?)", (name, password, phone, address, 'teacher'))
                            conn.commit()
                            st.success("استاد شامل ہو گیا!")
                        except sqlite3.IntegrityError:
                            st.error("نام پہلے سے موجود ہے!")
                    else:
                        st.error("نام اور پاسورڈ ضروری ہیں۔")
        with tab2:
            teachers = pd.read_sql_query("SELECT id, name, phone, address FROM teachers WHERE name != 'admin'", conn)
            if not teachers.empty:
                edited = st.data_editor(teachers, num_rows="dynamic", use_container_width=True, hide_index=True)
                if st.button("اپ ڈیٹ کریں"):
                    for idx, row in edited.iterrows():
                        c.execute("UPDATE teachers SET name=?, phone=?, address=? WHERE id=?", (row['name'], row['phone'], row['address'], row['id']))
                    conn.commit()
                    st.success("اپ ڈیٹ ہو گیا!")
                    st.rerun()
            else:
                st.info("کوئی استاد نہیں۔")
    
    # --- Students Management ---
    elif selected == "students":
        st.markdown("<h1 style='text-align: center;'>👨‍🎓 طلباء مینجمنٹ</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["نیا طالب علم", "موجودہ طلباء"])
        with tab1:
            with st.form("add_student"):
                name = st.text_input("نام")
                father = st.text_input("والد کا نام")
                teacher = st.selectbox("استاد", [t[0] for t in c.execute("SELECT name FROM teachers WHERE name != 'admin'").fetchall()])
                phone = st.text_input("فون")
                address = st.text_area("پتہ")
                submitted = st.form_submit_button("داخل کریں")
                if submitted:
                    if name and father and teacher:
                        c.execute("INSERT INTO students (name, father_name, teacher_name, phone, address) VALUES (?,?,?,?,?)", (name, father, teacher, phone, address))
                        conn.commit()
                        st.success("طالب علم شامل ہو گیا!")
                    else:
                        st.error("نام، والد کا نام، اور استاد ضروری ہیں۔")
        with tab2:
            students = pd.read_sql_query("SELECT id, name, father_name, teacher_name, phone, address FROM students", conn)
            if not students.empty:
                edited = st.data_editor(students, num_rows="dynamic", use_container_width=True, hide_index=True)
                if st.button("اپ ڈیٹ کریں"):
                    for idx, row in edited.iterrows():
                        c.execute("UPDATE students SET name=?, father_name=?, teacher_name=?, phone=?, address=? WHERE id=?", (row['name'], row['father_name'], row['teacher_name'], row['phone'], row['address'], row['id']))
                    conn.commit()
                    st.success("اپ ڈیٹ ہو گیا!")
                    st.rerun()
            else:
                st.info("کوئی طالب علم نہیں۔")
    
    # --- Leave Approval ---
    elif selected == "leave_approval":
        st.markdown("<h1 style='text-align: center;'>🏛️ رخصت کی منظوری</h1>", unsafe_allow_html=True)
        leaves = c.execute("SELECT id, t_name, l_type, reason, start_date, days, status FROM leave_requests WHERE status='پینڈنگ (زیرِ غور)'").fetchall()
        if not leaves:
            st.info("کوئی زیر غور رخصت نہیں۔")
        else:
            for lid, tname, ltype, reason, sdate, days, status in leaves:
                with st.expander(f"{tname} - {ltype} - {sdate} ({days} دن)"):
                    st.write(f"وجہ: {reason}")
                    col1, col2 = st.columns(2)
                    if col1.button("✅ منظور", key=f"app_{lid}"):
                        c.execute("UPDATE leave_requests SET status='منظور شدہ ✅' WHERE id=?", (lid,))
                        conn.commit()
                        create_notification("teacher", tname, f"آپ کی {days} دن کی رخصت منظور کر لی گئی۔")
                        st.rerun()
                    if col2.button("❌ مسترد", key=f"rej_{lid}"):
                        c.execute("UPDATE leave_requests SET status='مسترد شدہ ❌' WHERE id=?", (lid,))
                        conn.commit()
                        create_notification("teacher", tname, f"آپ کی {days} دن کی رخصت مسترد کر دی گئی۔")
                        st.rerun()
    
    # --- Reports ---
    elif selected == "reports":
        st.markdown("<h1 style='text-align: center;'>📈 رپورٹس</h1>", unsafe_allow_html=True)
        report_type = st.selectbox("رپورٹ کی قسم", ["حاضری", "تعلیمی کارکردگی", "رخصتیں"])
        if report_type == "حاضری":
            start = st.date_input("آغاز", date.today().replace(day=1))
            end = st.date_input("اختتام", date.today())
            att_df = pd.read_sql_query(f"SELECT r_date, t_name, attendance FROM hifz_records WHERE r_date BETWEEN '{start}' AND '{end}'", conn)
            if not att_df.empty:
                st.dataframe(att_df, use_container_width=True)
                st.download_button("ایکسل ڈاؤن لوڈ", convert_df_to_excel(att_df), "attendance.xlsx")
            else:
                st.info("کوئی ڈیٹا نہیں۔")
        elif report_type == "تعلیمی کارکردگی":
            student = st.selectbox("طالب علم", [s[0] for s in c.execute("SELECT name FROM students").fetchall()])
            perf_df = pd.read_sql_query(f"SELECT r_date, sq_m, m_m FROM hifz_records WHERE s_name='{student}'", conn)
            if not perf_df.empty:
                st.dataframe(perf_df, use_container_width=True)
                fig = px.line(perf_df, x='r_date', y=['sq_m', 'm_m'])
                st.plotly_chart(fig)
            else:
                st.info("کوئی ڈیٹا نہیں۔")
        else:
            leaves_df = pd.read_sql_query("SELECT t_name, l_type, start_date, days, status FROM leave_requests", conn)
            if not leaves_df.empty:
                st.dataframe(leaves_df, use_container_width=True)
            else:
                st.info("کوئی ڈیٹا نہیں۔")
    
    # --- Settings ---
    elif selected == "settings":
        st.markdown("<h1 style='text-align: center;'>⚙️ سیٹنگز</h1>", unsafe_allow_html=True)
        st.subheader("پروفائل")
        user_data = c.execute("SELECT name, phone, address FROM teachers WHERE name=?", (st.session_state.username,)).fetchone()
        if user_data:
            with st.form("profile_form"):
                name = st.text_input("نام", user_data[0])
                phone = st.text_input("فون", user_data[1])
                address = st.text_area("پتہ", user_data[2])
                if st.form_submit_button("اپ ڈیٹ کریں"):
                    c.execute("UPDATE teachers SET name=?, phone=?, address=? WHERE name=?", (name, phone, address, st.session_state.username))
                    conn.commit()
                    st.success("پروفائل اپ ڈیٹ ہو گیا!")
                    st.rerun()
    
    # --- Teacher: Leave Request ---
    elif selected == "leave_request":
        st.markdown("<h1 style='text-align: center;'>📩 درخواستِ رخصت</h1>", unsafe_allow_html=True)
        with st.form("leave_form"):
            l_type = st.selectbox("نوعیت", ["ضروری کام", "بیماری", "ہنگامی", "دیگر"])
            start_date = st.date_input("تاریخ آغاز", date.today())
            days = st.number_input("دنوں کی تعداد", 1, 15)
            reason = st.text_area("وجہ")
            if st.form_submit_button("بھیجیں"):
                if reason:
                    c.execute("""INSERT INTO leave_requests (t_name, l_type, start_date, days, reason, status, notification_seen) 
                              VALUES (?,?,?,?,?,?,?)""", (st.session_state.username, l_type, start_date, days, reason, "پینڈنگ (زیرِ غور)", 0))
                    conn.commit()
                    create_notification("admin", "admin", f"استاد {st.session_state.username} نے {days} دن کی رخصت کی درخواست دی۔")
                    st.success("درخواست بھیج دی گئی!")
                else:
                    st.error("وجہ ضروری ہے۔")
    
    # --- Teacher: My Leaves ---
    elif selected == "my_leaves":
        st.markdown("<h1 style='text-align: center;'>📜 میری رخصتیں</h1>", unsafe_allow_html=True)
        leaves = pd.read_sql_query(f"SELECT start_date, days, l_type, status FROM leave_requests WHERE t_name='{st.session_state.username}'", conn)
        if not leaves.empty:
            st.dataframe(leaves, use_container_width=True)
        else:
            st.info("کوئی ریکارڈ نہیں۔")
    
    # --- Teacher: My Attendance ---
    elif selected == "my_attendance":
        st.markdown("<h1 style='text-align: center;'>🕒 میری حاضری</h1>", unsafe_allow_html=True)
        if st.button("✅ آمد"):
            c.execute("INSERT INTO t_attendance (t_name, a_date, arrival) VALUES (?,?,?)", (st.session_state.username, date.today(), datetime.now().strftime("%I:%M %p")))
            conn.commit()
            st.success("آمد ریکارڈ ہو گئی!")
        if st.button("🚪 رخصت"):
            c.execute("UPDATE t_attendance SET departure=? WHERE t_name=? AND a_date=? AND departure IS NULL", (datetime.now().strftime("%I:%M %p"), st.session_state.username, date.today()))
            conn.commit()
            st.success("رخصت ریکارڈ ہو گئی!")
        attendance = pd.read_sql_query(f"SELECT a_date, arrival, departure FROM t_attendance WHERE t_name='{st.session_state.username}' ORDER BY a_date DESC", conn)
        if not attendance.empty:
            st.dataframe(attendance, use_container_width=True)
