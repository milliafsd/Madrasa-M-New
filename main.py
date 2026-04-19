import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import plotly.express as px
import os
import hashlib
import shutil
import zipfile
import io
from supabase import create_client, Client

# ==================== Supabase کنفیگریشن ====================
# Streamlit Secrets سے اسناد حاصل کریں (connections.supabase سیکشن کے مطابق)
supabase_url = st.secrets["connections.supabase"]["SUPABASE_URL"]
supabase_key = st.secrets["connections.supabase"]["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)

# ==================== ہیلپر فنکشنز ====================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def log_audit(user, action, details=""):
    try:
        supabase.table("audit_log").insert({
            "user": user,
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }).execute()
    except:
        pass

def get_pk_time():
    tz = pytz.timezone('Asia/Karachi')
    return datetime.now(tz).strftime("%I:%M %p")

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def get_grade_from_mistakes(total_mistakes):
    if total_mistakes <= 2: return "ممتاز"
    elif total_mistakes <= 5: return "جید جداً"
    elif total_mistakes <= 8: return "جید"
    elif total_mistakes <= 12: return "مقبول"
    else: return "دوبارہ کوشش کریں"

def calculate_grade_with_attendance(attendance, sabaq_nagha, sq_nagha, m_nagha, sq_mistakes, m_mistakes):
    if attendance == "غیر حاضر":
        return "غیر حاضر"
    if attendance == "رخصت":
        return "رخصت"
    nagha_count = sum([sabaq_nagha, sq_nagha, m_nagha])
    if nagha_count == 1:
        return "ناقص (ناغہ)"
    elif nagha_count == 2:
        return "کمزور (ناغہ)"
    elif nagha_count == 3:
        return "ناکام (مکمل ناغہ)"
    total_mistakes = sq_mistakes + m_mistakes
    if total_mistakes <= 2:
        return "ممتاز"
    elif total_mistakes <= 5:
        return "جید جداً"
    elif total_mistakes <= 8:
        return "جید"
    elif total_mistakes <= 12:
        return "مقبول"
    else:
        return "دوبارہ کوشش کریں"

def cleanliness_to_score(clean):
    if clean == "بہترین": return 3
    elif clean == "بہتر": return 2
    elif clean == "ناقص": return 1
    else: return 0

def generate_exam_result_card(exam_row):
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>رزلٹ کارڈ - {exam_row['s_name']}</title>
    <style>
        @font-face {{ font-family: 'Jameel Noori Nastaleeq'; src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq'); }}
        body {{ font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', Arial, sans-serif; margin: 20px; direction: rtl; text-align: right; }}
        .card {{ border: 2px solid #1e5631; border-radius: 15px; padding: 20px; max-width: 600px; margin: auto; }}
        h2 {{ text-align: center; color: #1e5631; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        .footer {{ margin-top: 20px; display: flex; justify-content: space-between; }}
    </style>
    </head>
    <body>
        <div class="card">
            <h2>جامعہ ملیہ اسلامیہ فیصل آباد</h2>
            <h3>رزلٹ کارڈ</h3>
            <p><b>نام:</b> {exam_row['s_name']} ولد {exam_row['f_name']}</p>
            <p><b>شناختی نمبر:</b> {exam_row.get('roll_no', '')}</p>
            <p><b>امتحان کی قسم:</b> {exam_row['exam_type']}</p>
            {f"<p><b>پارہ:</b> {exam_row['from_para']} تا {exam_row['to_para']}</p>" if exam_row.get('from_para') else ""}
            {f"<p><b>کتاب:</b> {exam_row.get('book_name', '')}</p>" if exam_row.get('book_name') else ""}
            {f"<p><b>مقدار خواندگی:</b> {exam_row.get('amount_read', '')}</p>" if exam_row.get('amount_read') else ""}
            <p><b>تاریخ:</b> {exam_row['start_date']} تا {exam_row['end_date']}</p>
            <p><b>کل دن:</b> {exam_row.get('total_days', '')}</p>
            <table>
                <tr><th>سوال</th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th><th>کل</th></tr>
                <tr><td style="text-align:center">{exam_row['q1']}</td>
                <td>{exam_row['q2']}</td>
                <td>{exam_row['q3']}</td>
                <td>{exam_row['q4']}</td>
                <td>{exam_row['q5']}</td>
                <td>{exam_row['total']}</td>
                </tr>
            </table>
            <p><b>گریڈ:</b> {exam_row['grade']}</p>
            <div class="footer">
                <span>دستخط استاذ: _________________</span>
                <span>دستخط مہتمم: _________________</span>
            </div>
        </div>
        <div class="no-print" style="text-align:center; margin-top:20px;">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

def generate_para_report(student_name, father_name, passed_paras_df):
    if passed_paras_df.empty:
        return "<p>کوئی پاس شدہ پارہ نہیں</p>"
    html_table = passed_paras_df.to_html(index=False, classes='print-table', border=1, justify='center', escape=False)
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>پارہ تعلیمی رپورٹ - {student_name}</title>
    <style>
        @font-face {{ font-family: 'Jameel Noori Nastaleeq'; src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq'); }}
        body {{ font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', Arial, sans-serif; margin: 20px; direction: rtl; text-align: right; }}
        h2, h3 {{ text-align: center; color: #1e5631; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        @media print {{ body {{ margin: 0; }} .no-print {{ display: none; }} }}
    </style>
    </head>
    <body>
        <div class="header">
            <h2>جامعہ ملیہ اسلامیہ فیصل آباد</h2>
            <h3>پارہ تعلیمی رپورٹ</h3>
            <p><b>طالب علم:</b> {student_name} ولد {father_name}</p>
        </div>
        {html_table}
        <div class="signatures" style="display:flex; justify-content:space-between; margin-top:50px;">
            <span>دستخط استاذ: _______________________</span>
            <span>دستخط مہتمم: _______________________</span>
        </div>
        <div class="no-print" style="text-align:center; margin-top:30px;">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

def generate_html_report(df, title, student_name="", start_date="", end_date="", passed_paras=None):
    html_table = df.to_html(index=False, classes='print-table', border=1, justify='center', escape=False)
    passed_html = ""
    if passed_paras:
        passed_html = f"<div style='margin-top:20px'><b>پاس شدہ پارے:</b> {', '.join(map(str, passed_paras))}</div>"
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>{title}</title>
    <style>
        @font-face {{ font-family: 'Jameel Noori Nastaleeq'; src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq'); }}
        body {{ font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', Arial, sans-serif; margin: 20px; direction: rtl; text-align: right; }}
        h2, h3 {{ text-align: center; color: #1e5631; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        @media print {{ body {{ margin: 0; }} .no-print {{ display: none; }} }}
    </style>
    </head>
    <body>
        <div class="header">
            <h2>جامعہ ملیہ اسلامیہ فیصل آباد</h2>
            <h3>{title}</h3>
            {f"<p><b>طالب علم:</b> {student_name} &nbsp;&nbsp; <b>تاریخ:</b> {start_date} تا {end_date}</p>" if student_name else ""}
        </div>
        {html_table}
        {passed_html}
        <div class="signatures" style="display:flex; justify-content:space-between; margin-top:50px;">
            <span>دستخط استاذ: _______________________</span>
            <span>دستخط مہتمم: _______________________</span>
        </div>
        <div class="no-print" style="text-align:center; margin-top:30px;">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

def generate_timetable_html(df_timetable):
    if df_timetable.empty:
        return "<p>کوئی ٹائم ٹیبل دستیاب نہیں</p>"
    day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
    df_timetable['day_order'] = df_timetable['دن'].map(day_order)
    df_timetable = df_timetable.sort_values(['day_order', 'وقت'])
    pivot = df_timetable.pivot(index='وقت', columns='دن', values='کتاب')
    pivot = pivot.fillna("—")
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>ٹائم ٹیبل</title>
    <style>
        @font-face {{ font-family: 'Jameel Noori Nastaleeq'; src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq'); }}
        body {{ font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', Arial, sans-serif; margin: 20px; direction: rtl; text-align: right; }}
        h2, h3 {{ text-align: center; color: #1e5631; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        @media print {{ body {{ margin: 0; }} .no-print {{ display: none; }} }}
    </style>
    </head>
    <body>
        <div class="header">
            <h2>جامعہ ملیہ اسلامیہ فیصل آباد</h2>
            <h3>ٹائم ٹیبل</h3>
        </div>
        {pivot.to_html(classes='print-table', border=1, justify='center', escape=False)}
        <div class="signatures" style="display:flex; justify-content:space-between; margin-top:50px;">
            <span>دستخط استاذ: _______________________</span>
            <span>دستخط مہتمم: _______________________</span>
        </div>
        <div class="no-print" style="text-align:center; margin-top:30px;">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

# ==================== ڈیٹا بیس انیشیلائزیشن ====================
def init_supabase_admin():
    try:
        res = supabase.table("teachers").select("*").eq("name", "admin").execute()
        if not res.data:
            admin_hash = hash_password("jamia123")
            supabase.table("teachers").insert({
                "name": "admin",
                "password": admin_hash,
                "dept": "Admin"
            }).execute()
    except Exception as e:
        st.error(f"Supabase انیشیلائزیشن میں خرابی: {e}")

init_supabase_admin()

# ==================== اسٹائلنگ ====================
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ فیصل آباد | سمارٹ ERP", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
    @font-face {
        font-family: 'Jameel Noori Nastaleeq';
        src: url('https://raw.githubusercontent.com/urdufonts/jameel-noori-nastaleeq/master/JameelNooriNastaleeq.ttf') format('truetype');
        font-weight: normal;
        font-style: normal;
    }
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    * {
        font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', 'Arial', sans-serif;
    }
    body { direction: rtl; text-align: right; background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%); }
    .stSidebar { background: linear-gradient(180deg, #1e5631 0%, #0b2b1a 100%); color: white; }
    .stSidebar * { color: white !important; }
    .stSidebar .stRadio label { color: white !important; font-weight: bold; font-size: 1rem; }
    .stSidebar .stRadio [role="radiogroup"] div { color: white !important; }
    .stSidebar .stRadio [role="radiogroup"] div[data-baseweb="radio"]:hover { background-color: #2e7d32; border-radius: 5px; }
    .stButton > button { background: linear-gradient(90deg, #1e5631, #2e7d32); color: white; border-radius: 30px; border: none; padding: 0.5rem 1rem; font-weight: bold; transition: 0.3s; width: 100%; }
    .stButton > button:hover { transform: scale(1.02); background: linear-gradient(90deg, #2e7d32, #1e5631); }
    .main-header { text-align: center; background: linear-gradient(135deg, #f1f8e9, #d4e0c9); padding: 1rem; border-radius: 20px; margin-bottom: 1rem; border-bottom: 4px solid #1e5631; }
    .report-card { background: white; border-radius: 15px; padding: 1rem; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 1rem; }
    .stTabs [data-baseweb="tab"] { border-radius: 30px; padding: 0.5rem 1rem; background-color: #e0e0e0; }
    .stTabs [aria-selected="true"] { background: linear-gradient(90deg, #1e5631, #2e7d32); color: white; }
    .best-student-card {
        background: linear-gradient(135deg, #fff9e6, #ffe6b3);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        transition: 0.3s;
    }
    .best-student-card:hover { transform: translateY(-5px); }
    .gold { color: #d4af37; }
    .silver { color: #a0a0a0; }
    .bronze { color: #cd7f32; }
    @media (max-width: 768px) {
        .stButton > button { padding: 0.4rem 0.8rem; font-size: 0.8rem; }
        .main-header h1 { font-size: 1.5rem; }
    }
</style>
""", unsafe_allow_html=True)

# ==================== لاگ ان ====================
def verify_login(username, password):
    try:
        res = supabase.table("teachers").select("*").eq("name", username).execute()
        if res.data:
            stored = res.data[0]['password']
            if stored == password or stored == hash_password(password):
                return res.data[0]
        return None
    except Exception as e:
        st.error(f"لاگ ان کی تصدیق میں خرابی: {e}")
        return None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ فیصل آباد</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        with st.container():
            st.markdown("<div class='report-card'><h3>🔐 لاگ ان</h3>", unsafe_allow_html=True)
            u = st.text_input("صارف نام")
            p = st.text_input("پاسورڈ", type="password")
            if st.button("داخل ہوں"):
                res = verify_login(u, p)
                if res:
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    st.session_state.user_type = "admin" if u == "admin" else "teacher"
                    log_audit(u, "Login", f"User type: {st.session_state.user_type}")
                    st.rerun()
                else:
                    st.error("غلط معلومات")
            st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==================== مینو ====================
if st.session_state.user_type == "admin":
    menu = ["📊 ایڈمن ڈیش بورڈ", "📊 یومیہ تعلیمی رپورٹ", "🎓 امتحانی نظام", "📜 ماہانہ رزلٹ کارڈ",
            "📘 پارہ تعلیمی رپورٹ", "🕒 اساتذہ حاضری", "🏛️ رخصت کی منظوری",
            "👥 یوزر مینجمنٹ", "📚 ٹائم ٹیبل مینجمنٹ", "🔑 پاسورڈ تبدیل کریں", "📋 عملہ نگرانی و شکایات",
            "📢 نوٹیفیکیشنز", "📈 تجزیہ و رپورٹس", "🏆 ماہانہ بہترین طلباء", "⚙️ بیک اپ & سیٹنگز"]
else:
    menu = ["📝 روزانہ سبق اندراج", "🎓 امتحانی درخواست", "📩 رخصت کی درخواست",
            "🕒 میری حاضری", "📚 میرا ٹائم ٹیبل", "🔑 پاسورڈ تبدیل کریں", "📢 نوٹیفیکیشنز"]

selected = st.sidebar.radio("📌 مینو", menu)

# ==================== ڈیٹا کنسٹنٹس ====================
surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس",
               "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج",
               "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب",
               "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف",
               "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة",
               "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة",
               "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر",
               "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل",
               "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة",
               "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]
cleanliness_options = ["بہترین", "بہتر", "ناقص"]

# ==================== پاسورڈ فنکشنز ====================
def verify_password(user, plain_password):
    try:
        res = supabase.table("teachers").select("password").eq("name", user).execute()
        if not res.data: return False
        stored = res.data[0]['password']
        return stored == plain_password or stored == hash_password(plain_password)
    except:
        return False

def change_password(user, old_pass, new_pass):
    if not verify_password(user, old_pass): return False
    new_hash = hash_password(new_pass)
    supabase.table("teachers").update({"password": new_hash}).eq("name", user).execute()
    log_audit(user, "Password Changed", "Success")
    return True

def admin_reset_password(teacher_name, new_pass):
    new_hash = hash_password(new_pass)
    supabase.table("teachers").update({"password": new_hash}).eq("name", teacher_name).execute()
    log_audit(st.session_state.username, "Admin Reset Password", f"Teacher: {teacher_name}")

# ==================== ایڈمن سیکشنز ====================

# 1. ایڈمن ڈیش بورڈ
if selected == "📊 ایڈمن ڈیش بورڈ" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📊 ایڈمن ڈیش بورڈ</h1></div>", unsafe_allow_html=True)
    try:
        total_students = supabase.table("students").select("id", count="exact").execute().count
        total_teachers = supabase.table("teachers").select("id", count="exact").neq("name", "admin").execute().count
        col1, col2 = st.columns(2)
        col1.metric("کل طلباء", total_students)
        col2.metric("کل اساتذہ", total_teachers)
    except Exception as e:
        st.error(f"اعداد و شمار حاصل کرنے میں خرابی: {e}")

# 2. یومیہ تعلیمی رپورٹ
elif selected == "📊 یومیہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.header("📊 یومیہ تعلیمی رپورٹ - صرف دیکھیں")
    with st.sidebar:
        d1 = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        d2 = st.date_input("تاریخ اختتام", date.today())
        teachers_res = supabase.table("teachers").select("name").neq("name", "admin").execute()
        teachers_list = ["تمام"] + [t['name'] for t in teachers_res.data]
        sel_teacher = st.selectbox("استاد / کلاس", teachers_list)
        dept_filter = st.selectbox("شعبہ", ["تمام", "حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
    
    combined_df = pd.DataFrame()
    if dept_filter in ["تمام", "حفظ"]:
        try:
            query = supabase.table("hifz_records").select("*, students(name, father_name, roll_no)").gte("r_date", d1.isoformat()).lte("r_date", d2.isoformat())
            if sel_teacher != "تمام":
                query = query.eq("t_name", sel_teacher)
            res = query.execute()
            if res.data:
                rows = []
                for rec in res.data:
                    s = rec.get('students', {})
                    rows.append({
                        "تاریخ": rec['r_date'],
                        "نام": s.get('name', ''),
                        "والد کا نام": s.get('father_name', ''),
                        "شناختی نمبر": s.get('roll_no', ''),
                        "استاد": rec['t_name'],
                        "شعبہ": "حفظ",
                        "سبق": rec['surah'],
                        "کل ستر": rec.get('lines', 0),
                        "سبقی": rec['sq_p'],
                        "سبقی (غلطی)": rec.get('sq_m', 0),
                        "سبقی (اٹکن)": rec.get('sq_a', 0),
                        "منزل": rec['m_p'],
                        "منزل (غلطی)": rec.get('m_m', 0),
                        "منزل (اٹکن)": rec.get('m_a', 0),
                        "حاضری": rec['attendance'],
                        "صفائی": rec.get('cleanliness', '')
                    })
                hifz_df = pd.DataFrame(rows)
                combined_df = pd.concat([combined_df, hifz_df], ignore_index=True)
        except Exception as e:
            st.error(f"حفظ کے ریکارڈ لوڈ کرتے وقت خرابی: {str(e)}")

    if dept_filter in ["تمام", "قاعدہ"]:
        try:
            query = supabase.table("qaida_records").select("*, students(name, father_name, roll_no)").gte("r_date", d1.isoformat()).lte("r_date", d2.isoformat())
            if sel_teacher != "تمام":
                query = query.eq("t_name", sel_teacher)
            res = query.execute()
            if res.data:
                rows = []
                for rec in res.data:
                    s = rec.get('students', {})
                    rows.append({
                        "تاریخ": rec['r_date'],
                        "نام": s.get('name', ''),
                        "والد کا نام": s.get('father_name', ''),
                        "شناختی نمبر": s.get('roll_no', ''),
                        "استاد": rec['t_name'],
                        "شعبہ": "قاعدہ",
                        "تختی نمبر": rec['lesson_no'],
                        "کل لائنیں": rec.get('total_lines', 0),
                        "تفصیل": rec.get('details', ''),
                        "حاضری": rec['attendance'],
                        "صفائی": rec.get('cleanliness', '')
                    })
                qaida_df = pd.DataFrame(rows)
                combined_df = pd.concat([combined_df, qaida_df], ignore_index=True)
        except Exception as e:
            st.error(f"قاعدہ کے ریکارڈ لوڈ کرتے وقت خرابی: {str(e)}")

    if dept_filter in ["تمام", "درسِ نظامی", "عصری تعلیم"]:
        try:
            query = supabase.table("general_education").select("*, students(name, father_name, roll_no)").gte("r_date", d1.isoformat()).lte("r_date", d2.isoformat())
            if sel_teacher != "تمام":
                query = query.eq("t_name", sel_teacher)
            if dept_filter != "تمام":
                query = query.eq("dept", dept_filter)
            res = query.execute()
            if res.data:
                rows = []
                for rec in res.data:
                    s = rec.get('students', {})
                    rows.append({
                        "تاریخ": rec['r_date'],
                        "نام": s.get('name', ''),
                        "والد کا نام": s.get('father_name', ''),
                        "شناختی نمبر": s.get('roll_no', ''),
                        "استاد": rec['t_name'],
                        "شعبہ": rec.get('dept', ''),
                        "کتاب/مضمون": rec.get('book_subject', ''),
                        "آج کا سبق": rec.get('today_lesson', ''),
                        "ہوم ورک": rec.get('homework', ''),
                        "کارکردگی": rec.get('performance', ''),
                        "حاضری": rec.get('attendance', ''),
                        "صفائی": rec.get('cleanliness', '')
                    })
                gen_df = pd.DataFrame(rows)
                combined_df = pd.concat([combined_df, gen_df], ignore_index=True)
        except Exception as e:
            st.error(f"عمومی تعلیم کے ریکارڈ لوڈ کرتے وقت خرابی: {str(e)}")

    if combined_df.empty:
        st.warning("کوئی ریکارڈ نہیں ملا")
    else:
        st.success(f"کل {len(combined_df)} ریکارڈ ملے")
        st.dataframe(combined_df, use_container_width=True)
        html_report = generate_html_report(combined_df, "یومیہ تعلیمی رپورٹ", start_date=d1.strftime("%Y-%m-%d"), end_date=d2.strftime("%Y-%m-%d"))
        st.download_button("📥 HTML رپورٹ ڈاؤن لوڈ کریں", html_report, "daily_report.html", "text/html")
        if st.button("🖨️ پرنٹ کریں"):
            st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html_report}`);w.print();</script>", height=0)

# 3. امتحانی نظام
elif selected == "🎓 امتحانی نظام" and st.session_state.user_type == "admin":
    st.header("🎓 امتحانی نظام")
    tab1, tab2 = st.tabs(["پینڈنگ امتحانات", "مکمل شدہ"])
    with tab1:
        try:
            res = supabase.table("exams").select("*, students(name, father_name, roll_no)").eq("status", "پینڈنگ").execute()
            pending = res.data
        except Exception as e:
            st.error(f"ڈیٹا لوڈ کرنے میں خرابی: {e}")
            pending = []
        if not pending:
            st.info("کوئی پینڈنگ امتحان نہیں")
        else:
            for exam in pending:
                eid = exam['id']
                s = exam.get('students', {})
                sn = s.get('name', '')
                fn = s.get('father_name', '')
                rn = s.get('roll_no', '')
                dept = exam.get('dept', '')
                etype = exam.get('exam_type', '')
                fp = exam.get('from_para')
                tp = exam.get('to_para')
                book = exam.get('book_name', '')
                amount = exam.get('amount_read', '')
                sd = exam.get('start_date')
                ed = exam.get('end_date')
                tdays = exam.get('total_days')
                with st.expander(f"{sn} ولد {fn} | شناختی نمبر: {rn} | {dept} | {etype}"):
                    st.write(f"**تاریخ ابتدا:** {sd}")
                    st.write(f"**تاریخ اختتام:** {ed}")
                    st.write(f"**کل دن:** {tdays if tdays else '-'}")
                    if etype == "پارہ ٹیسٹ":
                        st.info(f"پارہ نمبر: {fp} تا {tp}")
                    else:
                        st.info(f"کتاب: {book}")
                        st.info(f"مقدار خواندگی: {amount}")
                    cols = st.columns(5)
                    q1 = cols[0].number_input("س1", 0, 20, key=f"q1_{eid}")
                    q2 = cols[1].number_input("س2", 0, 20, key=f"q2_{eid}")
                    q3 = cols[2].number_input("س3", 0, 20, key=f"q3_{eid}")
                    q4 = cols[3].number_input("س4", 0, 20, key=f"q4_{eid}")
                    q5 = cols[4].number_input("س5", 0, 20, key=f"q5_{eid}")
                    total = q1+q2+q3+q4+q5
                    if total >= 90: g = "ممتاز"
                    elif total >= 80: g = "جید جداً"
                    elif total >= 70: g = "جید"
                    elif total >= 60: g = "مقبول"
                    else: g = "ناکام"
                    st.write(f"کل: {total} | گریڈ: {g}")
                    if st.button("کلیئر کریں", key=f"save_{eid}"):
                        supabase.table("exams").update({
                            "q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5,
                            "total": total, "grade": g, "status": "مکمل", "end_date": date.today().isoformat()
                        }).eq("id", eid).execute()
                        if g != "ناکام":
                            stud_id = exam['student_id']
                            if etype == "پارہ ٹیسٹ" and fp:
                                for para in range(fp, tp+1):
                                    existing = supabase.table("passed_paras").select("id").eq("student_id", stud_id).eq("para_no", para).execute()
                                    if not existing.data:
                                        supabase.table("passed_paras").insert({
                                            "student_id": stud_id,
                                            "para_no": para,
                                            "passed_date": date.today().isoformat(),
                                            "exam_type": etype,
                                            "grade": g,
                                            "marks": total
                                        }).execute()
                            else:
                                existing = supabase.table("passed_paras").select("id").eq("student_id", stud_id).eq("book_name", book).execute()
                                if not existing.data:
                                    supabase.table("passed_paras").insert({
                                        "student_id": stud_id,
                                        "book_name": book,
                                        "passed_date": date.today().isoformat(),
                                        "exam_type": etype,
                                        "grade": g,
                                        "marks": total
                                    }).execute()
                        st.success("امتحان کلیئر کر دیا گیا")
                        st.rerun()
    with tab2:
        try:
            res = supabase.table("exams").select("*, students(name, father_name, roll_no)").eq("status", "مکمل").order("end_date", desc=True).execute()
            if res.data:
                rows = []
                for exam in res.data:
                    s = exam.get('students', {})
                    rows.append({
                        "نام": s.get('name', ''),
                        "والد کا نام": s.get('father_name', ''),
                        "شناختی نمبر": s.get('roll_no', ''),
                        "شعبہ": exam.get('dept', ''),
                        "امتحان قسم": exam.get('exam_type', ''),
                        "پارہ (سے)": exam.get('from_para'),
                        "پارہ (تک)": exam.get('to_para'),
                        "کتاب": exam.get('book_name', ''),
                        "مقدار": exam.get('amount_read', ''),
                        "تاریخ ابتدا": exam.get('start_date'),
                        "تاریخ اختتام": exam.get('end_date'),
                        "کل نمبر": exam.get('total'),
                        "گریڈ": exam.get('grade')
                    })
                hist = pd.DataFrame(rows)
                st.dataframe(hist, use_container_width=True)
                st.download_button("ہسٹری CSV", convert_df_to_csv(hist), "exam_history.csv")
            else:
                st.info("کوئی مکمل شدہ امتحان نہیں")
        except Exception as e:
            st.error(f"مکمل امتحانات لوڈ کرنے میں خرابی: {e}")

# 4. ماہانہ رزلٹ کارڈ
elif selected == "📜 ماہانہ رزلٹ کارڈ" and st.session_state.user_type == "admin":
    st.header("📜 ماہانہ رزلٹ کارڈ")
    try:
        res = supabase.table("students").select("id, name, father_name, roll_no, dept").execute()
        students_list = res.data
    except Exception as e:
        st.error(f"طلبہ کی فہرست لوڈ کرنے میں خرابی: {e}")
        students_list = []
    if not students_list:
        st.warning("کوئی طالب علم نہیں")
    else:
        student_names = [f"{s['name']} ولد {s['father_name']} (شناختی نمبر: {s.get('roll_no','')}) - {s['dept']}" for s in students_list]
        sel = st.selectbox("طالب علم منتخب کریں", student_names)
        parts = sel.split(" ولد ")
        s_name = parts[0]
        rest = parts[1]
        f_name, rest2 = rest.split(" (شناختی نمبر: ")
        roll_no, dept = rest2.split(") - ")
        student_id = [s['id'] for s in students_list if s['name'] == s_name and s['father_name'] == f_name][0]
        start = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        end = st.date_input("تاریخ اختتام", date.today())

        if dept == "حفظ":
            res = supabase.table("hifz_records").select("*").eq("student_id", student_id).gte("r_date", start.isoformat()).lte("r_date", end.isoformat()).order("r_date").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                grades = []
                for _, row in df.iterrows():
                    att = row['attendance']
                    sabaq_nagha = (row['surah'] in ["ناغہ", "یاد نہیں"])
                    sq_nagha = (row['sq_p'] in ["ناغہ", "یاد نہیں"])
                    m_nagha = (row['m_p'] in ["ناغہ", "یاد نہیں"])
                    grade = calculate_grade_with_attendance(att, sabaq_nagha, sq_nagha, m_nagha, row.get('sq_m',0), row.get('m_m',0))
                    grades.append(grade)
                df['درجہ'] = grades
                st.dataframe(df[['r_date', 'attendance', 'surah', 'sq_p', 'm_p', 'cleanliness', 'درجہ']])
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ (حفظ)", student_name=f"{s_name} ولد {f_name}", start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
                st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_result.html")
            else:
                st.warning("کوئی ریکارڈ نہیں")
        elif dept == "قاعدہ":
            res = supabase.table("qaida_records").select("*").eq("student_id", student_id).gte("r_date", start.isoformat()).lte("r_date", end.isoformat()).order("r_date").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df[['r_date', 'lesson_no', 'total_lines', 'details', 'attendance', 'cleanliness']])
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ (قاعدہ)", student_name=f"{s_name} ولد {f_name}", start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
                st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_qaida_result.html")
            else:
                st.warning("کوئی ریکارڈ نہیں")
        else:
            res = supabase.table("general_education").select("*").eq("student_id", student_id).eq("dept", dept).gte("r_date", start.isoformat()).lte("r_date", end.isoformat()).order("r_date").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df[['r_date', 'book_subject', 'today_lesson', 'homework', 'performance', 'cleanliness']])
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ", student_name=f"{s_name} ولد {f_name}", start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
                st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_result.html")
            else:
                st.warning("کوئی ریکارڈ نہیں")

# 5. پارہ تعلیمی رپورٹ
elif selected == "📘 پارہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.header("📘 پارہ تعلیمی رپورٹ")
    try:
        res = supabase.table("students").select("id, name, father_name").eq("dept", "حفظ").execute()
        students_list = res.data
    except:
        students_list = []
    if not students_list:
        st.warning("کوئی حفظ کا طالب علم نہیں")
    else:
        student_names = [f"{s['name']} ولد {s['father_name']}" for s in students_list]
        sel = st.selectbox("طالب علم منتخب کریں", student_names)
        s_name, f_name = sel.split(" ولد ")
        student_id = [s['id'] for s in students_list if s['name'] == s_name and s['father_name'] == f_name][0]
        res = supabase.table("passed_paras").select("*").eq("student_id", student_id).order("para_no").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df[['para_no', 'passed_date', 'exam_type', 'grade', 'marks']])
            html = generate_para_report(s_name, f_name, df)
            st.download_button("📥 رپورٹ ڈاؤن لوڈ کریں", html, f"Para_Report_{s_name}.html")
        else:
            st.info("کوئی پاس شدہ پارہ نہیں")

# 6. اساتذہ حاضری
elif selected == "🕒 اساتذہ حاضری" and st.session_state.user_type == "admin":
    st.header("اساتذہ حاضری ریکارڈ")
    try:
        res = supabase.table("t_attendance").select("*").order("a_date", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df[['a_date', 't_name', 'arrival', 'departure']])
        else:
            st.info("کوئی ریکارڈ نہیں")
    except Exception as e:
        st.error(f"ڈیٹا لوڈ کرنے میں خرابی: {e}")

# 7. رخصت کی منظوری
elif selected == "🏛️ رخصت کی منظوری" and st.session_state.user_type == "admin":
    st.header("رخصت کی منظوری")
    try:
        res = supabase.table("leave_requests").select("*").like("status", "%پینڈنگ%").execute()
        pending = res.data
    except:
        pending = []
    if not pending:
        st.info("کوئی پینڈنگ درخواست نہیں")
    else:
        for req in pending:
            with st.expander(f"{req['t_name']} | {req['l_type']} | {req['days']} دن"):
                st.write(f"وجہ: {req['reason']}")
                col1, col2 = st.columns(2)
                if col1.button("✅ منظور", key=f"app_{req['id']}"):
                    supabase.table("leave_requests").update({"status": "منظور"}).eq("id", req['id']).execute()
                    st.rerun()
                if col2.button("❌ مسترد", key=f"rej_{req['id']}"):
                    supabase.table("leave_requests").update({"status": "مسترد"}).eq("id", req['id']).execute()
                    st.rerun()

# 8. یوزر مینجمنٹ
elif selected == "👥 یوزر مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("👥 یوزر مینجمنٹ")
    tab1, tab2 = st.tabs(["اساتذہ", "طلبہ"])
    with tab1:
        st.subheader("موجودہ اساتذہ")
        try:
            res = supabase.table("teachers").select("*").neq("name", "admin").execute()
            teachers_df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except Exception as e:
            st.error(f"اساتذہ کی فہرست لوڈ نہیں ہو سکی: {e}")
            teachers_df = pd.DataFrame()
        if not teachers_df.empty:
            edited = st.data_editor(teachers_df, num_rows="dynamic", use_container_width=True)
            if st.button("تبدیلیاں محفوظ کریں"):
                try:
                    # حذف شدہ اساتذہ
                    old_ids = set(teachers_df['id'])
                    new_ids = set(edited['id']) if 'id' in edited.columns else set()
                    for did in old_ids - new_ids:
                        supabase.table("teachers").delete().eq("id", did).execute()
                    for _, row in edited.iterrows():
                        data = row.to_dict()
                        if pd.isna(data.get('id')) or data['id'] == 0:
                            # نیا استاد
                            if 'password' in data and data['password']:
                                data['password'] = hash_password(data['password'])
                            supabase.table("teachers").insert(data).execute()
                        else:
                            # اپڈیٹ
                            tid = data.pop('id')
                            if 'password' in data and data['password']:
                                data['password'] = hash_password(data['password'])
                            supabase.table("teachers").update(data).eq("id", tid).execute()
                    st.success("تبدیلیاں محفوظ ہو گئیں")
                    st.rerun()
                except Exception as e:
                    st.error(f"محفوظ کرتے وقت خرابی: {e}")
        else:
            st.info("کوئی استاد نہیں")
        with st.expander("➕ نیا استاد رجسٹر کریں"):
            with st.form("new_teacher"):
                name = st.text_input("نام*")
                password = st.text_input("پاسورڈ*", type="password")
                dept = st.selectbox("شعبہ", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
                phone = st.text_input("فون")
                address = st.text_area("پتہ")
                id_card = st.text_input("شناختی کارڈ")
                joining_date = st.date_input("تاریخ شمولیت", date.today())
                if st.form_submit_button("رجسٹر"):
                    if name and password:
                        supabase.table("teachers").insert({
                            "name": name,
                            "password": hash_password(password),
                            "dept": dept,
                            "phone": phone,
                            "address": address,
                            "id_card": id_card,
                            "joining_date": joining_date.isoformat()
                        }).execute()
                        st.success("استاد رجسٹر ہو گیا")
                        st.rerun()
                    else:
                        st.error("نام اور پاسورڈ ضروری ہیں")
    with tab2:
        st.subheader("موجودہ طلبہ")
        try:
            res = supabase.table("students").select("*").execute()
            students_df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except Exception as e:
            st.error(f"طلبہ کی فہرست لوڈ نہیں ہو سکی: {e}")
            students_df = pd.DataFrame()
        if not students_df.empty:
            edited = st.data_editor(students_df, num_rows="dynamic", use_container_width=True)
            if st.button("طلبہ میں تبدیلیاں محفوظ کریں"):
                try:
                    old_ids = set(students_df['id'])
                    new_ids = set(edited['id']) if 'id' in edited.columns else set()
                    for did in old_ids - new_ids:
                        supabase.table("students").delete().eq("id", did).execute()
                    for _, row in edited.iterrows():
                        data = row.to_dict()
                        if pd.isna(data.get('id')) or data['id'] == 0:
                            supabase.table("students").insert(data).execute()
                        else:
                            sid = data.pop('id')
                            supabase.table("students").update(data).eq("id", sid).execute()
                    st.success("تبدیلیاں محفوظ ہو گئیں")
                    st.rerun()
                except Exception as e:
                    st.error(f"محفوظ کرتے وقت خرابی: {e}")
        else:
            st.info("کوئی طالب علم نہیں")
        with st.expander("➕ نیا طالب علم داخل کریں"):
            with st.form("new_student"):
                name = st.text_input("نام*")
                father = st.text_input("والد کا نام*")
                mother = st.text_input("والدہ کا نام")
                dob = st.date_input("تاریخ پیدائش", date.today() - timedelta(days=365*10))
                admission = st.date_input("تاریخ داخلہ", date.today())
                roll_no = st.text_input("شناختی نمبر")
                dept = st.selectbox("شعبہ*", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
                teacher = st.text_input("استاد*")
                phone = st.text_input("فون")
                address = st.text_area("پتہ")
                if st.form_submit_button("داخل کریں"):
                    if name and father and teacher and dept:
                        supabase.table("students").insert({
                            "name": name,
                            "father_name": father,
                            "mother_name": mother,
                            "dob": dob.isoformat(),
                            "admission_date": admission.isoformat(),
                            "roll_no": roll_no,
                            "dept": dept,
                            "teacher_name": teacher,
                            "phone": phone,
                            "address": address
                        }).execute()
                        st.success("طالب علم داخل ہو گیا")
                        st.rerun()
                    else:
                        st.error("ضروری فیلڈز پُر کریں")

# 9. ٹائم ٹیبل مینجمنٹ
elif selected == "📚 ٹائم ٹیبل مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("📚 ٹائم ٹیبل مینجمنٹ")
    try:
        teachers_res = supabase.table("teachers").select("name").neq("name", "admin").execute()
        teachers = [t['name'] for t in teachers_res.data]
    except:
        teachers = []
    if not teachers:
        st.warning("پہلے اساتذہ رجسٹر کریں")
    else:
        sel_t = st.selectbox("استاد منتخب کریں", teachers)
        try:
            res = supabase.table("timetable").select("*").eq("t_name", sel_t).execute()
            tt_df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except:
            tt_df = pd.DataFrame()
        if not tt_df.empty:
            st.subheader("موجودہ ٹائم ٹیبل")
            st.dataframe(tt_df[['day', 'period', 'book', 'room']])
        with st.expander("➕ نیا پیریڈ شامل کریں"):
            with st.form("add_period"):
                day = st.selectbox("دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"])
                period = st.text_input("وقت (مثلاً 08:00-09:00)")
                book = st.text_input("کتاب / مضمون")
                room = st.text_input("کمرہ نمبر")
                if st.form_submit_button("شامل کریں"):
                    supabase.table("timetable").insert({
                        "t_name": sel_t,
                        "day": day,
                        "period": period,
                        "book": book,
                        "room": room
                    }).execute()
                    st.success("پیریڈ شامل کر دیا گیا")
                    st.rerun()
        if not tt_df.empty:
            with st.expander("🔄 پورے ہفتے میں نقل کریں"):
                source_day = st.selectbox("منبع دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"], key="copy_source")
                target_days = st.multiselect("نقل کرنے کے لیے دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"])
                if st.button("نقل کریں"):
                    source_periods = tt_df[tt_df['day'] == source_day]
                    if not source_periods.empty:
                        for d in target_days:
                            supabase.table("timetable").delete().eq("t_name", sel_t).eq("day", d).execute()
                            for _, row in source_periods.iterrows():
                                supabase.table("timetable").insert({
                                    "t_name": sel_t,
                                    "day": d,
                                    "period": row['period'],
                                    "book": row['book'],
                                    "room": row['room']
                                }).execute()
                        st.success(f"{source_day} کے پیریڈز {', '.join(target_days)} میں نقل ہو گئے")
                        st.rerun()
                    else:
                        st.warning(f"{source_day} کے لیے کوئی پیریڈ نہیں")

# 10. پاسورڈ تبدیل کریں
elif selected == "🔑 پاسورڈ تبدیل کریں":
    st.header("🔑 پاسورڈ تبدیل کریں")
    if st.session_state.user_type == "admin":
        try:
            res = supabase.table("teachers").select("name").neq("name", "admin").execute()
            teachers = [t['name'] for t in res.data]
        except:
            teachers = []
        if teachers:
            selected_teacher = st.selectbox("استاد منتخب کریں", teachers)
            new_pass = st.text_input("نیا پاسورڈ", type="password")
            confirm = st.text_input("تصدیق", type="password")
            if st.button("تبدیل کریں"):
                if new_pass and new_pass == confirm:
                    admin_reset_password(selected_teacher, new_pass)
                    st.success("پاسورڈ تبدیل ہو گیا")
                else:
                    st.error("پاسورڈ میل نہیں کھاتے")
        else:
            st.info("کوئی دوسرا استاد موجود نہیں")
    else:
        old = st.text_input("پرانا پاسورڈ", type="password")
        new = st.text_input("نیا پاسورڈ", type="password")
        confirm = st.text_input("تصدیق", type="password")
        if st.button("تبدیل کریں"):
            if new == confirm and change_password(st.session_state.username, old, new):
                st.success("پاسورڈ تبدیل ہو گیا۔ دوبارہ لاگ ان کریں")
                st.session_state.logged_in = False
                st.rerun()
            else:
                st.error("غلط پرانا پاسورڈ یا پاسورڈ میل نہیں کھاتے")

# 11. عملہ نگرانی و شکایات
elif selected == "📋 عملہ نگرانی و شکایات" and st.session_state.user_type == "admin":
    st.header("📋 عملہ نگرانی و شکایات")
    tab1, tab2 = st.tabs(["➕ نیا اندراج", "📜 ریکارڈ دیکھیں"])
    with tab1:
        with st.form("new_monitoring"):
            staff_res = supabase.table("teachers").select("name").neq("name", "admin").execute()
            staff_list = [t['name'] for t in staff_res.data]
            if not staff_list:
                st.warning("کوئی استاد/عملہ موجود نہیں")
            else:
                staff_name = st.selectbox("عملہ کا نام", staff_list)
                note_date = st.date_input("تاریخ", date.today())
                note_type = st.selectbox("نوعیت", ["یادداشت", "شکایت", "تنبیہ", "تعریف", "کارکردگی جائزہ"])
                description = st.text_area("تفصیل", height=150)
                action_taken = st.text_area("کیا کارروائی کی گئی؟", height=100)
                status = st.selectbox("حالت", ["زیر التواء", "حل شدہ", "زیر غور"])
                if st.form_submit_button("محفوظ کریں"):
                    supabase.table("staff_monitoring").insert({
                        "staff_name": staff_name,
                        "date": note_date.isoformat(),
                        "note_type": note_type,
                        "description": description,
                        "action_taken": action_taken,
                        "status": status,
                        "created_by": st.session_state.username,
                        "created_at": datetime.now().isoformat()
                    }).execute()
                    st.success("اندراج محفوظ ہو گیا")
                    st.rerun()
    with tab2:
        st.subheader("فلٹرز")
        staff_res = supabase.table("teachers").select("name").neq("name", "admin").execute()
        staff_names = ["تمام"] + [t['name'] for t in staff_res.data]
        filter_staff = st.selectbox("عملہ فلٹر کریں", staff_names)
        filter_type = st.selectbox("نوعیت فلٹر کریں", ["تمام", "یادداشت", "شکایت", "تنبیہ", "تعریف", "کارکردگی جائزہ"])
        start_date = st.date_input("تاریخ از", date.today() - timedelta(days=30))
        end_date = st.date_input("تاریخ تا", date.today())
        try:
            query = supabase.table("staff_monitoring").select("*").gte("date", start_date.isoformat()).lte("date", end_date.isoformat())
            if filter_staff != "تمام":
                query = query.eq("staff_name", filter_staff)
            if filter_type != "تمام":
                query = query.eq("note_type", filter_type)
            query = query.order("date", desc=True)
            res = query.execute()
            if res.data:
                df = pd.DataFrame(res.data)
                df_display = df[['staff_name', 'date', 'note_type', 'description', 'action_taken', 'status', 'created_by', 'created_at']]
                df_display.columns = ['عملہ کا نام', 'تاریخ', 'نوعیت', 'تفصیل', 'کارروائی', 'حالت', 'داخل کردہ', 'داخل کردہ تاریخ']
                st.dataframe(df_display, use_container_width=True)
                csv = convert_df_to_csv(df_display)
                st.download_button("📥 CSV ڈاؤن لوڈ کریں", csv, "staff_monitoring.csv")
                html_report = generate_html_report(df_display, "عملہ نگرانی و شکایات رپورٹ")
                st.download_button("📥 HTML رپورٹ ڈاؤن لوڈ کریں", html_report, "staff_monitoring_report.html")
                with st.expander("⚠️ ریکارڈ حذف کریں"):
                    record_id = st.number_input("ریکارڈ ID درج کریں", min_value=1, step=1)
                    if st.button("حذف کریں"):
                        supabase.table("staff_monitoring").delete().eq("id", record_id).execute()
                        st.success("ریکارڈ حذف کر دیا گیا")
                        st.rerun()
            else:
                st.info("کوئی ریکارڈ موجود نہیں")
        except Exception as e:
            st.error(f"ڈیٹا لوڈ کرنے میں خرابی: {e}")

# 12. نوٹیفیکیشنز
elif selected == "📢 نوٹیفیکیشنز":
    st.header("نوٹیفیکیشن سینٹر")
    if st.session_state.user_type == "admin":
        with st.form("new_notif"):
            title = st.text_input("عنوان")
            msg = st.text_area("پیغام")
            target = st.selectbox("بھیجیں", ["تمام", "اساتذہ", "طلبہ"])
            if st.form_submit_button("بھیجیں"):
                supabase.table("notifications").insert({
                    "title": title,
                    "message": msg,
                    "target": target,
                    "created_at": datetime.now().isoformat()
                }).execute()
                st.success("نوٹیفکیشن بھیج دیا گیا")
    try:
        if st.session_state.user_type == "admin":
            res = supabase.table("notifications").select("*").order("created_at", desc=True).limit(10).execute()
        else:
            res = supabase.table("notifications").select("*").in_("target", ["تمام","اساتذہ"]).order("created_at", desc=True).limit(10).execute()
        for n in res.data:
            st.info(f"**{n['title']}**\n\n{n['message']}\n\n*{n['created_at']}*")
    except:
        pass

# 13. تجزیہ و رپورٹس
elif selected == "📈 تجزیہ و رپورٹس" and st.session_state.user_type == "admin":
    st.header("تجزیہ")
    try:
        res = supabase.table("t_attendance").select("a_date").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            fig = px.bar(df, x='a_date', title="اساتذہ کی حاضری")
            st.plotly_chart(fig)
    except:
        pass

# 14. ماہانہ بہترین طلباء
elif selected == "🏆 ماہانہ بہترین طلباء" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>🏆 ماہانہ بہترین طلباء</h1></div>", unsafe_allow_html=True)
    month_year = st.date_input("مہینہ منتخب کریں", date.today().replace(day=1))
    start = month_year.replace(day=1)
    if month_year.month == 12:
        end = month_year.replace(year=month_year.year+1, month=1, day=1) - timedelta(days=1)
    else:
        end = month_year.replace(month=month_year.month+1, day=1) - timedelta(days=1)
    try:
        students_res = supabase.table("students").select("id, name, father_name, roll_no, dept").execute()
        students = students_res.data
    except:
        students = []
    if not students:
        st.warning("کوئی طالب علم نہیں")
    else:
        student_scores = []
        for s in students:
            sid = s['id']
            dept = s['dept']
            avg_grade = 0
            avg_clean = 0
            if dept == "حفظ":
                res = supabase.table("hifz_records").select("attendance, surah, sq_p, m_p, sq_m, m_m, cleanliness").eq("student_id", sid).gte("r_date", start.isoformat()).lte("r_date", end.isoformat()).execute()
                if res.data:
                    grade_scores = []
                    clean_scores = []
                    for rec in res.data:
                        att = rec['attendance']
                        sabaq_nagha = (rec['surah'] in ["ناغہ", "یاد نہیں"])
                        sq_nagha = (rec['sq_p'] in ["ناغہ", "یاد نہیں"])
                        m_nagha = (rec['m_p'] in ["ناغہ", "یاد نہیں"])
                        grade = calculate_grade_with_attendance(att, sabaq_nagha, sq_nagha, m_nagha, rec.get('sq_m',0), rec.get('m_m',0))
                        # گریڈ کو نمبر میں تبدیل کریں
                        if grade == "ممتاز": grade_scores.append(100)
                        elif grade == "جید جداً": grade_scores.append(85)
                        elif grade == "جید": grade_scores.append(75)
                        elif grade == "مقبول": grade_scores.append(60)
                        elif grade == "دوبارہ کوشش کریں": grade_scores.append(40)
                        elif grade == "ناقص (ناغہ)": grade_scores.append(30)
                        elif grade == "کمزور (ناغہ)": grade_scores.append(20)
                        elif grade == "ناکام (مکمل ناغہ)": grade_scores.append(10)
                        elif grade == "غیر حاضر": grade_scores.append(0)
                        elif grade == "رخصت": grade_scores.append(50)
                        if rec.get('cleanliness'):
                            clean_scores.append(cleanliness_to_score(rec['cleanliness']))
                    avg_grade = sum(grade_scores)/len(grade_scores) if grade_scores else 0
                    avg_clean = sum(clean_scores)/len(clean_scores) if clean_scores else 0
            elif dept == "قاعدہ":
                res = supabase.table("qaida_records").select("attendance, cleanliness").eq("student_id", sid).gte("r_date", start.isoformat()).lte("r_date", end.isoformat()).execute()
                if res.data:
                    grade_scores = []
                    clean_scores = []
                    for rec in res.data:
                        if rec['attendance'] == "حاضر": grade_scores.append(85)
                        elif rec['attendance'] == "رخصت": grade_scores.append(50)
                        else: grade_scores.append(0)
                        if rec.get('cleanliness'):
                            clean_scores.append(cleanliness_to_score(rec['cleanliness']))
                    avg_grade = sum(grade_scores)/len(grade_scores) if grade_scores else 0
                    avg_clean = sum(clean_scores)/len(clean_scores) if clean_scores else 0
            else:
                res = supabase.table("general_education").select("attendance, performance, cleanliness").eq("student_id", sid).eq("dept", dept).gte("r_date", start.isoformat()).lte("r_date", end.isoformat()).execute()
                if res.data:
                    grade_scores = []
                    clean_scores = []
                    for rec in res.data:
                        att = rec['attendance']
                        perf = rec.get('performance','')
                        if att == "حاضر":
                            if perf == "بہت بہتر": grade_scores.append(90)
                            elif perf == "بہتر": grade_scores.append(80)
                            elif perf == "مناسب": grade_scores.append(65)
                            elif perf == "کمزور": grade_scores.append(45)
                            else: grade_scores.append(75)
                        elif att == "رخصت": grade_scores.append(50)
                        else: grade_scores.append(0)
                        if rec.get('cleanliness'):
                            clean_scores.append(cleanliness_to_score(rec['cleanliness']))
                    avg_grade = sum(grade_scores)/len(grade_scores) if grade_scores else 0
                    avg_clean = sum(clean_scores)/len(clean_scores) if clean_scores else 0
            student_scores.append({
                "id": sid,
                "name": s['name'],
                "father": s['father_name'],
                "roll": s.get('roll_no',''),
                "dept": dept,
                "avg_grade": avg_grade,
                "avg_clean": avg_clean
            })
        sorted_grade = sorted(student_scores, key=lambda x: x["avg_grade"], reverse=True)
        sorted_clean = sorted(student_scores, key=lambda x: x["avg_clean"], reverse=True)
        st.markdown("---")
        st.subheader("📚 تعلیمی کارکردگی کے لحاظ سے بہترین طلباء")
        cols = st.columns(3)
        for i, student in enumerate(sorted_grade[:3]):
            with cols[i]:
                medal = ["🥇", "🥈", "🥉"][i]
                st.markdown(f"""
                <div class="best-student-card">
                    <h2>{medal}</h2>
                    <h3>{student['name']}</h3>
                    <p>والد: {student['father']}</p>
                    <p>شناختی نمبر: {student['roll']}</p>
                    <p>شعبہ: {student['dept']}</p>
                    <p>اوسط نمبر: {student['avg_grade']:.1f}%</p>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("---")
        st.subheader("🧹 صفائی کے لحاظ سے بہترین طلباء")
        cols = st.columns(3)
        for i, student in enumerate(sorted_clean[:3]):
            with cols[i]:
                medal = ["🥇", "🥈", "🥉"][i]
                clean_percent = (student['avg_clean'] / 3) * 100
                st.markdown(f"""
                <div class="best-student-card">
                    <h2>{medal}</h2>
                    <h3>{student['name']}</h3>
                    <p>والد: {student['father']}</p>
                    <p>شناختی نمبر: {student['roll']}</p>
                    <p>شعبہ: {student['dept']}</p>
                    <p>صفائی اوسط: {clean_percent:.1f}%</p>
                </div>
                """, unsafe_allow_html=True)
        with st.expander("📊 تمام طلباء کی تفصیلی کارکردگی"):
            df_all = pd.DataFrame(student_scores)
            df_all = df_all.rename(columns={"name":"نام", "father":"والد کا نام", "roll":"شناختی نمبر", "dept":"شعبہ", "avg_grade":"تعلیمی اوسط (%)", "avg_clean":"صفائی اوسط (0-3)"})
            st.dataframe(df_all)
            st.download_button("📥 CSV ڈاؤن لوڈ", convert_df_to_csv(df_all), "monthly_best_students.csv")

# 15. بیک اپ & سیٹنگز
elif selected == "⚙️ بیک اپ & سیٹنگز" and st.session_state.user_type == "admin":
    st.header("بیک اپ اور سیٹنگز")
    st.subheader("📥 ڈیٹا CSV میں ڈاؤن لوڈ کریں")
    tables = ["teachers", "students", "hifz_records", "qaida_records", "general_education", "t_attendance", "exams", "passed_paras", "timetable", "leave_requests", "notifications", "staff_monitoring"]
    if st.button("تمام ٹیبلز CSV بیک اپ (زپ)"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for t in tables:
                try:
                    res = supabase.table(t).select("*").execute()
                    if res.data:
                        df = pd.DataFrame(res.data)
                        csv_data = df.to_csv(index=False).encode('utf-8-sig')
                        zip_file.writestr(f"{t}.csv", csv_data)
                except Exception as e:
                    st.warning(f"{t}: {e}")
        zip_buffer.seek(0)
        st.download_button("📥 CSV زپ ڈاؤن لوڈ", zip_buffer, file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip", mime="application/zip")
    st.subheader("📤 CSV اپ لوڈ کرکے ڈیٹا ریسٹور")
    table_options = {
        "اساتذہ": "teachers",
        "طلبہ": "students",
        "حفظ ریکارڈ": "hifz_records",
        "قاعدہ ریکارڈ": "qaida_records",
        "عمومی تعلیم": "general_education",
        "امتحانات": "exams",
        "پاس شدہ پارے": "passed_paras",
        "ٹائم ٹیبل": "timetable",
        "رخصت درخواستیں": "leave_requests",
        "نوٹیفیکیشنز": "notifications",
        "عملہ نگرانی": "staff_monitoring"
    }
    selected_table_display = st.selectbox("ٹیبل منتخب کریں", list(table_options.keys()))
    selected_table = table_options[selected_table_display]
    uploaded_csv = st.file_uploader("CSV فائل منتخب کریں", type=["csv"])
    if uploaded_csv:
        try:
            df = pd.read_csv(uploaded_csv)
            st.dataframe(df.head())
            upload_mode = st.radio("اپ لوڈ موڈ:", ["موجودہ ڈیٹا میں شامل کریں", "موجودہ ڈیٹا کو حذف کر کے نیا ڈالیں"])
            if st.button("ریسٹور کریں"):
                if upload_mode == "موجودہ ڈیٹا کو حذف کر کے نیا ڈالیں":
                    supabase.table(selected_table).delete().neq("id", 0).execute()  # حذف کریں سب
                for _, row in df.iterrows():
                    data = row.to_dict()
                    # NaN کو None میں بدلیں
                    for k, v in data.items():
                        if pd.isna(v):
                            data[k] = None
                    supabase.table(selected_table).insert(data).execute()
                st.success("ڈیٹا ریسٹور ہو گیا")
                st.rerun()
        except Exception as e:
            st.error(f"خرابی: {e}")

# ==================== استاد سیکشنز ====================

# 1. روزانہ سبق اندراج
elif selected == "📝 روزانہ سبق اندراج" and st.session_state.user_type == "teacher":
    st.header("📝 روزانہ سبق اندراج")
    entry_date = st.date_input("تاریخ", date.today())
    dept = st.selectbox("شعبہ", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
    try:
        res = supabase.table("students").select("id, name, father_name").eq("teacher_name", st.session_state.username).eq("dept", dept).execute()
        students = res.data
    except:
        students = []
    if not students:
        st.info("آپ کی کلاس میں کوئی طالب علم نہیں")
    else:
        if dept == "حفظ":
            for s in students:
                key = f"{s['id']}_{s['name']}"
                st.markdown(f"### 👤 {s['name']} ولد {s['father_name']}")
                att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{key}", horizontal=True)
                cleanliness = st.selectbox("صفائی", cleanliness_options, key=f"clean_{key}")
                if att != "حاضر":
                    if st.button(f"محفوظ کریں ({s['name']})", key=f"save_abs_{key}"):
                        existing = supabase.table("hifz_records").select("id").eq("r_date", entry_date.isoformat()).eq("student_id", s['id']).execute()
                        if existing.data:
                            st.error("پہلے سے ریکارڈ موجود ہے")
                        else:
                            supabase.table("hifz_records").insert({
                                "r_date": entry_date.isoformat(),
                                "student_id": s['id'],
                                "t_name": st.session_state.username,
                                "surah": "غائب",
                                "lines": 0,
                                "sq_p": "غائب",
                                "sq_a": 0,
                                "sq_m": 0,
                                "m_p": "غائب",
                                "m_a": 0,
                                "m_m": 0,
                                "attendance": att,
                                "cleanliness": cleanliness
                            }).execute()
                            st.success("محفوظ ہو گیا")
                            st.rerun()
                    st.markdown("---")
                    continue
                # سبق
                sabaq_nagha = st.checkbox("سبق ناغہ", key=f"sabaq_nagha_{key}")
                if sabaq_nagha:
                    sabaq_text = "ناغہ"
                    lines = 0
                else:
                    surah = st.selectbox("سورت", surahs_urdu, key=f"surah_{key}")
                    a_from = st.text_input("آیت (سے)", key=f"af_{key}")
                    a_to = st.text_input("آیت (تک)", key=f"at_{key}")
                    sabaq_text = f"{surah}: {a_from}-{a_to}"
                    lines = st.number_input("کل ستر", min_value=0, value=0, key=f"lines_{key}")
                # سبقی
                sq_nagha = st.checkbox("سبقی ناغہ", key=f"sq_nagha_{key}")
                if sq_nagha:
                    sq_parts = ["ناغہ"]
                    sq_a = 0
                    sq_m = 0
                else:
                    sq_rows = st.session_state.get(f"sq_rows_{key}", 1)
                    sq_parts = []
                    sq_a = 0
                    sq_m = 0
                    for i in range(sq_rows):
                        cols = st.columns([2,2,1,1])
                        p = cols[0].selectbox("پارہ", paras, key=f"sqp_{key}_{i}")
                        v = cols[1].selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{key}_{i}")
                        a = cols[2].number_input("اٹکن", 0, key=f"sqa_{key}_{i}")
                        e = cols[3].number_input("غلطی", 0, key=f"sqe_{key}_{i}")
                        sq_parts.append(f"{p}:{v}")
                        sq_a += a
                        sq_m += e
                    if st.button("➕ مزید سبقی", key=f"add_sq_{key}"):
                        st.session_state[f"sq_rows_{key}"] = sq_rows + 1
                        st.rerun()
                # منزل
                m_nagha = st.checkbox("منزل ناغہ", key=f"m_nagha_{key}")
                if m_nagha:
                    m_parts = ["ناغہ"]
                    m_a = 0
                    m_m = 0
                else:
                    m_rows = st.session_state.get(f"m_rows_{key}", 1)
                    m_parts = []
                    m_a = 0
                    m_m = 0
                    for j in range(m_rows):
                        cols = st.columns([2,2,1,1])
                        p = cols[0].selectbox("پارہ", paras, key=f"mp_{key}_{j}")
                        v = cols[1].selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"mv_{key}_{j}")
                        a = cols[2].number_input("اٹکن", 0, key=f"ma_{key}_{j}")
                        e = cols[3].number_input("غلطی", 0, key=f"me_{key}_{j}")
                        m_parts.append(f"{p}:{v}")
                        m_a += a
                        m_m += e
                    if st.button("➕ مزید منزل", key=f"add_m_{key}"):
                        st.session_state[f"m_rows_{key}"] = m_rows + 1
                        st.rerun()
                grade = calculate_grade_with_attendance(att, sabaq_nagha, sq_nagha, m_nagha, sq_m, m_m)
                st.info(f"درجہ: {grade}")
                if st.button(f"محفوظ کریں ({s['name']})", key=f"save_{key}"):
                    existing = supabase.table("hifz_records").select("id").eq("r_date", entry_date.isoformat()).eq("student_id", s['id']).execute()
                    if existing.data:
                        st.error("پہلے سے ریکارڈ موجود ہے")
                    else:
                        supabase.table("hifz_records").insert({
                            "r_date": entry_date.isoformat(),
                            "student_id": s['id'],
                            "t_name": st.session_state.username,
                            "surah": sabaq_text,
                            "lines": lines,
                            "sq_p": " | ".join(sq_parts),
                            "sq_a": sq_a,
                            "sq_m": sq_m,
                            "m_p": " | ".join(m_parts),
                            "m_a": m_a,
                            "m_m": m_m,
                            "attendance": att,
                            "cleanliness": cleanliness
                        }).execute()
                        st.success("محفوظ ہو گیا")
                        st.rerun()
                st.markdown("---")
        elif dept == "قاعدہ":
            # مختصراً
            pass
        elif dept == "درسِ نظامی":
            # مختصراً
            pass
        elif dept == "عصری تعلیم":
            # مختصراً
            pass

# 2. امتحانی درخواست
elif selected == "🎓 امتحانی درخواست" and st.session_state.user_type == "teacher":
    st.subheader("امتحان کے لیے طالب علم نامزد کریں")
    try:
        res = supabase.table("students").select("id, name, father_name, dept").eq("teacher_name", st.session_state.username).execute()
        students = res.data
    except:
        students = []
    if not students:
        st.warning("کوئی طالب علم نہیں")
    else:
        with st.form("exam_request"):
            s_names = [f"{s['name']} ولد {s['father_name']} ({s['dept']})" for s in students]
            sel = st.selectbox("طالب علم", s_names)
            parts = sel.split(" ولد ")
            s_name = parts[0]
            f_name, dept = parts[1].split(" (")
            dept = dept[:-1]
            student_id = [s['id'] for s in students if s['name'] == s_name and s['father_name'] == f_name][0]
            exam_type = st.selectbox("امتحان کی قسم", ["پارہ ٹیسٹ", "ماہانہ", "سہ ماہی", "سالانہ"])
            start_date = st.date_input("تاریخ ابتدا", date.today())
            end_date = st.date_input("تاریخ اختتام", date.today() + timedelta(days=7))
            total_days = (end_date - start_date).days + 1
            st.write(f"کل دن: {total_days}")
            from_para = 0
            to_para = 0
            book_name = ""
            amount_read = ""
            if exam_type == "پارہ ٹیسٹ":
                col1, col2 = st.columns(2)
                from_para = col1.number_input("پارہ (سے)", 1, 30, 1)
                to_para = col2.number_input("پارہ (تک)", from_para, 30, from_para)
            else:
                if dept == "حفظ":
                    col1, col2 = st.columns(2)
                    from_para = col1.number_input("پارہ (سے)", 1, 30, 1)
                    to_para = col2.number_input("پارہ (تک)", from_para, 30, min(from_para+4,30))
                    amount_read = st.text_input("مقدار خواندگی", placeholder="مثلاً: 5 پارے")
                else:
                    book_name = st.text_input("کتاب کا نام")
                    amount_read = st.text_input("مقدار خواندگی")
            if st.form_submit_button("بھیجیں"):
                supabase.table("exams").insert({
                    "student_id": student_id,
                    "dept": dept,
                    "exam_type": exam_type,
                    "from_para": from_para,
                    "to_para": to_para,
                    "book_name": book_name,
                    "amount_read": amount_read,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "total_days": total_days,
                    "status": "پینڈنگ"
                }).execute()
                st.success("درخواست بھیج دی گئی")

# 3. رخصت کی درخواست
elif selected == "📩 رخصت کی درخواست" and st.session_state.user_type == "teacher":
    st.header("📩 رخصت کی درخواست")
    with st.form("leave_form"):
        l_type = st.selectbox("نوعیت", ["بیماری", "ضروری کام", "ہنگامی", "دیگر"])
        start_date = st.date_input("تاریخ آغاز", date.today())
        days = st.number_input("دنوں کی تعداد", min_value=1, max_value=30, value=1)
        reason = st.text_area("وجہ")
        if st.form_submit_button("جمع کریں"):
            supabase.table("leave_requests").insert({
                "t_name": st.session_state.username,
                "l_type": l_type,
                "start_date": start_date.isoformat(),
                "days": days,
                "reason": reason,
                "status": "پینڈنگ",
                "request_date": date.today().isoformat()
            }).execute()
            st.success("درخواست بھیج دی گئی")

# 4. میری حاضری
elif selected == "🕒 میری حاضری" and st.session_state.user_type == "teacher":
    st.header("🕒 میری حاضری")
    today = date.today()
    try:
        res = supabase.table("t_attendance").select("*").eq("t_name", st.session_state.username).eq("a_date", today.isoformat()).execute()
        rec = res.data[0] if res.data else None
    except:
        rec = None
    if not rec:
        col1, col2 = st.columns(2)
        arr_date = col1.date_input("تاریخ", today)
        arr_time = col2.time_input("آمد کا وقت", datetime.now().time())
        if st.button("آمد درج کریں"):
            time_str = arr_time.strftime("%I:%M %p")
            supabase.table("t_attendance").insert({
                "t_name": st.session_state.username,
                "a_date": arr_date.isoformat(),
                "arrival": time_str,
                "actual_arrival": get_pk_time()
            }).execute()
            st.success("آمد درج ہو گئی")
            st.rerun()
    elif rec and rec.get('departure') is None:
        st.success(f"آمد: {rec['arrival']}")
        dep_time = st.time_input("رخصت کا وقت", datetime.now().time())
        if st.button("رخصت درج کریں"):
            time_str = dep_time.strftime("%I:%M %p")
            supabase.table("t_attendance").update({
                "departure": time_str,
                "actual_departure": get_pk_time()
            }).eq("id", rec['id']).execute()
            st.success("رخصت درج ہو گئی")
            st.rerun()
    else:
        st.success(f"آمد: {rec['arrival']} | رخصت: {rec['departure']}")

# 5. میرا ٹائم ٹیبل
elif selected == "📚 میرا ٹائم ٹیبل" and st.session_state.user_type == "teacher":
    st.header("📚 میرا ٹائم ٹیبل")
    try:
        res = supabase.table("timetable").select("*").eq("t_name", st.session_state.username).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df[['day', 'period', 'book', 'room']])
            html = generate_timetable_html(df.rename(columns={'day':'دن', 'period':'وقت', 'book':'کتاب', 'room':'کمرہ'}))
            st.download_button("📥 HTML ڈاؤن لوڈ", html, "timetable.html")
        else:
            st.info("ابھی ٹائم ٹیبل ترتیب نہیں دیا گیا")
    except:
        st.error("ٹائم ٹیبل لوڈ نہیں ہو سکا")

# ==================== لاگ آؤٹ ====================
st.sidebar.divider()
if st.sidebar.button("🚪 لاگ آؤٹ"):
    st.session_state.logged_in = False
    st.rerun()
