from __future__ import annotations

import base64
import hashlib
import io
import sqlite3
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator

import pandas as pd
import plotly.express as px
import pytz
import streamlit as st


DB_NAME = "jamia_millia_data.db"
TZ = pytz.timezone("Asia/Karachi")
ATTENDANCE_OPTIONS = ["حاضر", "غیر حاضر", "رخصت"]
CLEANLINESS_OPTIONS = ["بہترین", "بہتر", "ناقص"]
DEPARTMENTS = ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"]
EXAM_TYPES = ["پارہ ٹیسٹ", "ماہانہ", "سہ ماہی", "سالانہ"]
SCHOOL_SUBJECTS = ["اردو", "انگلش", "ریاضی", "سائنس", "اسلامیات", "سماجی علوم"]
PERFORMANCE_OPTIONS = ["بہت بہتر", "بہتر", "مناسب", "کمزور"]
LEAVE_TYPES = ["بیماری", "ضروری کام", "ہنگامی", "دیگر"]
WEEK_DAYS = ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات", "جمعہ"]
SURAHS = [
    "الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس",
    "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج",
    "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب",
    "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف",
    "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة",
    "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحريم", "الملك", "القلم", "الحاقة",
    "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القيامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التكوير",
    "الانفطار", "المطففين", "الانشقاق", "البروج", "الطارق", "الأعلى", "الغاشية", "الفجر", "البلد", "الشمس", "الليل",
    "الضحى", "الشرح", "التين", "العلق", "القدر", "البينة", "الزلزلة", "العاديات", "القارعة", "التكاثر", "العصر", "الهمزة",
    "الفيل", "قريش", "الماعون", "الكوثر", "الكافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس",
]
PARAS = [f"پارہ {index}" for index in range(1, 31)]


@dataclass(frozen=True)
class AppConfig:
    db_path: Path = Path(DB_NAME)
    app_title: str = "جامعہ ملیہ اسلامیہ فیصل آباد"
    app_caption: str = "جدید، مکمل، اور بہتر تعلیمی و انتظامی پورٹل"


CONFIG = AppConfig()


SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        dept TEXT,
        phone TEXT,
        address TEXT,
        id_card TEXT,
        photo TEXT,
        joining_date DATE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        father_name TEXT,
        mother_name TEXT,
        dob DATE,
        admission_date DATE,
        exit_date DATE,
        exit_reason TEXT,
        id_card TEXT,
        photo TEXT,
        phone TEXT,
        address TEXT,
        teacher_name TEXT,
        dept TEXT,
        class TEXT,
        section TEXT,
        roll_no TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS hifz_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE NOT NULL,
        student_id INTEGER NOT NULL,
        t_name TEXT NOT NULL,
        surah TEXT,
        a_from TEXT,
        a_to TEXT,
        sq_p TEXT,
        sq_a INTEGER DEFAULT 0,
        sq_m INTEGER DEFAULT 0,
        m_p TEXT,
        m_a INTEGER DEFAULT 0,
        m_m INTEGER DEFAULT 0,
        attendance TEXT,
        principal_note TEXT,
        lines INTEGER DEFAULT 0,
        cleanliness TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS qaida_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE NOT NULL,
        student_id INTEGER NOT NULL,
        t_name TEXT NOT NULL,
        lesson_no TEXT,
        total_lines INTEGER DEFAULT 0,
        details TEXT,
        attendance TEXT,
        principal_note TEXT,
        cleanliness TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS general_education (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE NOT NULL,
        student_id INTEGER NOT NULL,
        t_name TEXT NOT NULL,
        dept TEXT,
        book_subject TEXT,
        today_lesson TEXT,
        homework TEXT,
        performance TEXT,
        attendance TEXT,
        cleanliness TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS t_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT NOT NULL,
        a_date DATE NOT NULL,
        arrival TEXT,
        departure TEXT,
        actual_arrival TEXT,
        actual_departure TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT NOT NULL,
        reason TEXT,
        start_date DATE,
        back_date DATE,
        status TEXT,
        request_date DATE,
        l_type TEXT,
        days INTEGER,
        notification_seen INTEGER DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        dept TEXT,
        exam_type TEXT,
        from_para INTEGER,
        to_para INTEGER,
        book_name TEXT,
        amount_read TEXT,
        start_date TEXT,
        end_date TEXT,
        total_days INTEGER,
        q1 INTEGER,
        q2 INTEGER,
        q3 INTEGER,
        q4 INTEGER,
        q5 INTEGER,
        total INTEGER,
        grade TEXT,
        status TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS passed_paras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        para_no INTEGER,
        book_name TEXT,
        passed_date DATE,
        exam_type TEXT,
        grade TEXT,
        marks INTEGER,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT NOT NULL,
        day TEXT,
        period TEXT,
        book TEXT,
        room TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        message TEXT,
        target TEXT,
        created_at DATETIME,
        seen INTEGER DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        action TEXT,
        timestamp DATETIME,
        details TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS staff_monitoring (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        staff_name TEXT,
        date DATE,
        note_type TEXT,
        description TEXT,
        action_taken TEXT,
        status TEXT,
        created_by TEXT,
        created_at DATETIME
    )
    """,
]

REQUIRED_COLUMNS = {
    "teachers": {
        "dept": "TEXT",
        "phone": "TEXT",
        "address": "TEXT",
        "id_card": "TEXT",
        "photo": "TEXT",
        "joining_date": "DATE",
    },
    "students": {
        "mother_name": "TEXT",
        "dob": "DATE",
        "admission_date": "DATE",
        "exit_date": "DATE",
        "exit_reason": "TEXT",
        "id_card": "TEXT",
        "photo": "TEXT",
        "phone": "TEXT",
        "address": "TEXT",
        "teacher_name": "TEXT",
        "dept": "TEXT",
        "class": "TEXT",
        "section": "TEXT",
        "roll_no": "TEXT",
    },
    "hifz_records": {
        "a_from": "TEXT",
        "a_to": "TEXT",
        "sq_a": "INTEGER DEFAULT 0",
        "sq_m": "INTEGER DEFAULT 0",
        "m_a": "INTEGER DEFAULT 0",
        "m_m": "INTEGER DEFAULT 0",
        "attendance": "TEXT",
        "principal_note": "TEXT",
        "lines": "INTEGER DEFAULT 0",
        "cleanliness": "TEXT",
    },
    "qaida_records": {
        "total_lines": "INTEGER DEFAULT 0",
        "details": "TEXT",
        "attendance": "TEXT",
        "principal_note": "TEXT",
        "cleanliness": "TEXT",
    },
    "general_education": {
        "homework": "TEXT",
        "performance": "TEXT",
        "attendance": "TEXT",
        "cleanliness": "TEXT",
    },
    "leave_requests": {
        "back_date": "DATE",
        "status": "TEXT",
        "request_date": "DATE",
        "l_type": "TEXT",
        "days": "INTEGER",
        "notification_seen": "INTEGER DEFAULT 0",
    },
    "exams": {
        "book_name": "TEXT",
        "amount_read": "TEXT",
        "total_days": "INTEGER",
        "q1": "INTEGER",
        "q2": "INTEGER",
        "q3": "INTEGER",
        "q4": "INTEGER",
        "q5": "INTEGER",
        "total": "INTEGER",
        "grade": "TEXT",
        "status": "TEXT",
    },
    "passed_paras": {
        "book_name": "TEXT",
        "marks": "INTEGER",
    },
}


@contextmanager
def db_connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(CONFIG.db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def now_pk() -> datetime:
    return datetime.now(TZ)


def current_time_label() -> str:
    return now_pk().strftime("%I:%M %p")


def current_ts() -> str:
    return now_pk().strftime("%Y-%m-%d %H:%M:%S")


def init_db() -> None:
    with db_connection() as conn:
        for statement in SCHEMA:
            conn.execute(statement)
        for table, columns in REQUIRED_COLUMNS.items():
            existing_columns = {
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            for column, column_type in columns.items():
                if column not in existing_columns:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
        admin_exists = conn.execute("SELECT 1 FROM teachers WHERE name='admin'").fetchone()
        if not admin_exists:
            conn.execute(
                "INSERT INTO teachers (name, password, dept) VALUES (?, ?, ?)",
                ("admin", hash_password("jamia123"), "Admin"),
            )


def log_audit(user: str, action: str, details: str = "") -> None:
    try:
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO audit_log (user, action, timestamp, details) VALUES (?, ?, ?, ?)",
                (user, action, current_ts(), details),
            )
    except Exception:
        pass


def grade_from_mistakes(total_mistakes: int) -> str:
    if total_mistakes <= 2:
        return "ممتاز"
    if total_mistakes <= 5:
        return "جید جدا"
    if total_mistakes <= 8:
        return "جید"
    if total_mistakes <= 12:
        return "مقبول"
    return "دوبارہ کوشش کریں"


def score_cleanliness(label: str) -> int:
    return {"بہترین": 3, "بہتر": 2, "ناقص": 1}.get(label, 0)


def convert_df_to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def ensure_session() -> None:
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("user_type", "")


def notify(title: str, message: str, target: str = "all") -> None:
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO notifications (title, message, target, created_at, seen) VALUES (?, ?, ?, ?, 0)",
            (title, message, target, current_ts()),
        )


class Repo:
    @staticmethod
    def authenticate(username: str, password: str) -> sqlite3.Row | None:
        hashed = hash_password(password)
        with db_connection() as conn:
            return conn.execute(
                "SELECT * FROM teachers WHERE name = ? AND (password = ? OR password = ?)",
                (username, password, hashed),
            ).fetchone()

    @staticmethod
    def teacher_names(include_admin: bool = False) -> list[str]:
        query = "SELECT name FROM teachers"
        params: tuple = ()
        if not include_admin:
            query += " WHERE name != 'admin'"
        query += " ORDER BY name"
        with db_connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [row["name"] for row in rows]

    @staticmethod
    def students(teacher_name: str | None = None, dept: str | None = None) -> list[sqlite3.Row]:
        query = "SELECT * FROM students WHERE 1=1"
        params: list[object] = []
        if teacher_name:
            query += " AND teacher_name = ?"
            params.append(teacher_name)
        if dept:
            query += " AND dept = ?"
            params.append(dept)
        query += " ORDER BY name"
        with db_connection() as conn:
            return conn.execute(query, params).fetchall()

    @staticmethod
    def dashboard_counts() -> dict[str, int]:
        with db_connection() as conn:
            return {
                "students": conn.execute("SELECT COUNT(*) FROM students").fetchone()[0],
                "teachers": conn.execute("SELECT COUNT(*) FROM teachers WHERE name != 'admin'").fetchone()[0],
                "pending_exams": conn.execute("SELECT COUNT(*) FROM exams WHERE status='پینڈنگ'").fetchone()[0],
                "pending_leaves": conn.execute("SELECT COUNT(*) FROM leave_requests WHERE status='پینڈنگ'").fetchone()[0],
            }

    @staticmethod
    def attendance_record(username: str, a_date: date) -> sqlite3.Row | None:
        with db_connection() as conn:
            return conn.execute(
                "SELECT * FROM t_attendance WHERE t_name = ? AND a_date = ?",
                (username, a_date),
            ).fetchone()

    @staticmethod
    def timetable_for(username: str) -> pd.DataFrame:
        with db_connection() as conn:
            return pd.read_sql_query(
                "SELECT day AS دن, period AS وقت, book AS کتاب, room AS کمرہ FROM timetable WHERE t_name = ? ORDER BY day, period",
                conn,
                params=(username,),
            )

    @staticmethod
    def notifications_for(username: str) -> pd.DataFrame:
        with db_connection() as conn:
            return pd.read_sql_query(
                """
                SELECT title AS عنوان, message AS پیغام, target AS ہدف, created_at AS وقت
                FROM notifications
                WHERE target IN (?, 'all')
                ORDER BY created_at DESC
                """,
                conn,
                params=(username,),
            )


def set_page() -> None:
    st.set_page_config(page_title=CONFIG.app_title, page_icon="📚", layout="wide")
    st.markdown(
        """
        <style>
            html, body, [class*="css"] {
                direction: rtl;
            }
            .stApp {
                background:
                    radial-gradient(circle at top right, rgba(155, 188, 68, 0.18), transparent 24%),
                    linear-gradient(160deg, #f8fbf2 0%, #eef5e8 44%, #fffdf6 100%);
                direction: rtl;
                text-align: right;
            }
            .main .block-container, .stMarkdown, .stText, .stAlert, label, p, h1, h2, h3, h4, h5, h6 {
                direction: rtl;
                text-align: right;
            }
            .hero {
                color: white;
                background: linear-gradient(135deg, #123524 0%, #21513a 45%, #547436 100%);
                padding: 1.3rem 1.5rem;
                border-radius: 24px;
                box-shadow: 0 18px 40px rgba(18, 53, 36, 0.18);
                margin-bottom: 1rem;
            }
            .soft-card {
                background: rgba(255,255,255,0.9);
                padding: 1rem;
                border-radius: 18px;
                border: 1px solid rgba(18,53,36,0.08);
                box-shadow: 0 10px 26px rgba(18,53,36,0.08);
            }
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #123524 0%, #26563b 100%);
                right: 0;
                left: auto !important;
                border-left: 1px solid rgba(255,255,255,0.08);
            }
            [data-testid="stSidebar"] * {
                color: white !important;
                direction: rtl;
                text-align: right;
            }
            [data-testid="stSidebarCollapsedControl"] {
                right: 1rem;
                left: auto !important;
            }
            div[data-testid="stHorizontalBlock"] {
                direction: rtl;
            }
            .metric-box {
                background: rgba(255,255,255,0.92);
                border-radius: 18px;
                padding: 0.8rem 1rem;
                border: 1px solid rgba(18,53,36,0.08);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def extract_db_bytes_from_upload(uploaded_file) -> bytes:
    file_name = uploaded_file.name.lower()
    raw_bytes = uploaded_file.getvalue()
    if file_name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
            db_files = [name for name in archive.namelist() if name.lower().endswith((".db", ".sqlite", ".sqlite3"))]
            if not db_files:
                raise ValueError("ZIP میں database file نہیں ملی۔")
            return archive.read(db_files[0])
    if file_name.endswith((".db", ".sqlite", ".sqlite3")):
        return raw_bytes
    raise ValueError("صرف ZIP یا database file اپلوڈ کریں۔")


def restore_database_from_upload(uploaded_file) -> None:
    new_db_bytes = extract_db_bytes_from_upload(uploaded_file)
    temp_path = CONFIG.db_path.with_suffix(".tmp")
    backup_path = CONFIG.db_path.with_suffix(".pre_restore.bak")

    temp_path.write_bytes(new_db_bytes)
    validation_conn = sqlite3.connect(temp_path)
    try:
        validation_conn.execute("SELECT name FROM sqlite_master LIMIT 1").fetchall()
    finally:
        validation_conn.close()

    if CONFIG.db_path.exists():
        backup_path.write_bytes(CONFIG.db_path.read_bytes())
    temp_path.replace(CONFIG.db_path)
    init_db()


def render_login() -> None:
    st.markdown(
        f"<div class='hero'><h1>{CONFIG.app_title}</h1><p>{CONFIG.app_caption}</p></div>",
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 1.35, 1])
    with col2:
        st.markdown("<div class='soft-card'>", unsafe_allow_html=True)
        st.subheader("لاگ اِن")
        username = st.text_input("صارف نام")
        password = st.text_input("پاسورڈ", type="password")
        if st.button("داخل ہوں", use_container_width=True):
            user = Repo.authenticate(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_type = "admin" if username == "admin" else "teacher"
                log_audit(username, "Login", st.session_state.user_type)
                st.rerun()
            else:
                st.error("صارف نام یا پاسورڈ درست نہیں۔")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


def render_sidebar() -> str:
    st.sidebar.markdown(f"## {CONFIG.app_title}")
    st.sidebar.caption(f"خوش آمدید، {st.session_state.username}")
    if st.session_state.user_type == "admin":
        menu = [
            "ایڈمن ڈیش بورڈ",
            "یومیہ تعلیمی رپورٹ",
            "امتحانی نظام",
            "عملہ نگرانی و شکایات",
            "ماہانہ رزلٹ کارڈ",
            "پارہ تعلیمی رپورٹ",
            "اساتذہ حاضری",
            "رخصت کی منظوری",
            "یوزر مینجمنٹ",
            "ٹائم ٹیبل مینجمنٹ",
            "نوٹیفکیشنز",
            "تجزیہ و رپورٹس",
            "ماہانہ بہترین طلباء",
            "بیک اپ و سیٹنگز",
            "پاسورڈ تبدیل کریں",
        ]
    else:
        menu = [
            "روزانہ سبق اندراج",
            "امتحانی درخواست",
            "رخصت کی درخواست",
            "میری حاضری",
            "میرا ٹائم ٹیبل",
            "نوٹیفکیشنز",
            "پاسورڈ تبدیل کریں",
        ]
    choice = st.sidebar.radio("مینو", menu)
    st.sidebar.divider()
    if st.sidebar.button("لاگ آؤٹ", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.user_type = ""
        st.rerun()
    return choice


def render_admin_dashboard() -> None:
    counts = Repo.dashboard_counts()
    st.markdown("<div class='hero'><h2>ایڈمن ڈیش بورڈ</h2><p>اہم اعداد و شمار ایک نظر میں</p></div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("کل طلباء", counts["students"])
    c2.metric("کل اساتذہ", counts["teachers"])
    c3.metric("پینڈنگ امتحانات", counts["pending_exams"])
    c4.metric("پینڈنگ رخصتیں", counts["pending_leaves"])

    with db_connection() as conn:
        recent = pd.read_sql_query(
            """
            SELECT user AS صارف, action AS کارروائی, timestamp AS وقت, details AS تفصیل
            FROM audit_log ORDER BY id DESC LIMIT 20
            """,
            conn,
        )
        attendance = pd.read_sql_query(
            """
            SELECT attendance AS حاضری, COUNT(*) AS تعداد
            FROM (
                SELECT attendance FROM hifz_records
                UNION ALL SELECT attendance FROM qaida_records
                UNION ALL SELECT attendance FROM general_education
            )
            GROUP BY attendance
            """,
            conn,
        )
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.markdown("<div class='soft-card'>", unsafe_allow_html=True)
        st.subheader("حالیہ سرگرمیاں")
        st.dataframe(recent, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='soft-card'>", unsafe_allow_html=True)
        st.subheader("حاضری تقسیم")
        if not attendance.empty:
            fig = px.pie(attendance, names="حاضری", values="تعداد", hole=0.45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ابھی ڈیٹا موجود نہیں۔")
        st.markdown("</div>", unsafe_allow_html=True)


def fetch_daily_report(start_date: date, end_date: date, teacher: str, dept: str) -> pd.DataFrame:
    teacher_filter = ""
    dept_filter = ""
    params: list[object] = [start_date, end_date, start_date, end_date, start_date, end_date]
    if teacher != "تمام":
        teacher_filter = " AND teacher_name = ?"
        params.append(teacher)
    if dept != "تمام":
        dept_filter = " AND dept_name = ?"
        params.append(dept)
    query = f"""
        SELECT * FROM (
            SELECT
                h.r_date AS report_date,
                s.name AS student_name,
                s.father_name AS father_name,
                s.roll_no AS roll_no,
                h.t_name AS teacher_name,
                'حفظ' AS dept_name,
                h.surah AS lesson,
                h.sq_p AS sabaqi,
                h.m_p AS manzil,
                h.attendance AS attendance_status,
                h.cleanliness AS cleanliness_status
            FROM hifz_records h JOIN students s ON s.id = h.student_id
            WHERE h.r_date BETWEEN ? AND ?
            UNION ALL
            SELECT
                q.r_date,
                s.name,
                s.father_name,
                s.roll_no,
                q.t_name,
                'قاعدہ',
                q.lesson_no,
                q.details,
                '' AS manzil,
                q.attendance,
                q.cleanliness
            FROM qaida_records q JOIN students s ON s.id = q.student_id
            WHERE q.r_date BETWEEN ? AND ?
            UNION ALL
            SELECT
                g.r_date,
                s.name,
                s.father_name,
                s.roll_no,
                g.t_name,
                g.dept,
                g.today_lesson,
                g.book_subject,
                g.homework,
                g.attendance,
                g.cleanliness
            FROM general_education g JOIN students s ON s.id = g.student_id
            WHERE g.r_date BETWEEN ? AND ?
        ) base
        WHERE 1=1 {teacher_filter} {dept_filter}
        ORDER BY report_date DESC, student_name
    """
    with db_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df.rename(
        columns={
            "report_date": "تاریخ",
            "student_name": "نام",
            "father_name": "والد",
            "roll_no": "رول_نمبر",
            "teacher_name": "استاد",
            "dept_name": "شعبہ",
            "lesson": "سبق",
            "sabaqi": "سبقی",
            "manzil": "منزل",
            "attendance_status": "حاضری",
            "cleanliness_status": "صفائی",
        }
    )


def render_daily_report() -> None:
    st.subheader("یومیہ تعلیمی رپورٹ")
    c1, c2, c3, c4 = st.columns(4)
    start_date = c1.date_input("تاریخ آغاز", date.today().replace(day=1))
    end_date = c2.date_input("تاریخ اختتام", date.today())
    teacher = c3.selectbox("استاد", ["تمام", *Repo.teacher_names()])
    dept = c4.selectbox("شعبہ", ["تمام", *DEPARTMENTS])
    df = fetch_daily_report(start_date, end_date, teacher, dept)
    if df.empty:
        st.warning("منتخب فلٹر کے مطابق کوئی ریکارڈ نہیں ملا۔")
        return
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("CSV ڈاؤن لوڈ", convert_df_to_csv(df), "daily_report.csv", "text/csv")


def render_exam_management() -> None:
    st.subheader("امتحانی نظام")
    with db_connection() as conn:
        exams_df = pd.read_sql_query(
            """
            SELECT e.id, s.name AS نام, s.father_name AS والد, s.roll_no AS رول_نمبر, e.dept AS شعبہ,
                   e.exam_type AS امتحان, e.from_para AS شروع, e.to_para AS آخر, e.book_name AS کتاب,
                   e.amount_read AS مقدار, e.start_date AS آغاز, e.end_date AS اختتام, e.total_days AS کل_دن,
                   e.total AS کل_نمبر, e.grade AS گریڈ, e.status AS حیثیت
            FROM exams e JOIN students s ON s.id = e.student_id
            ORDER BY e.id DESC
            """,
            conn,
        )
    tabs = st.tabs(["تمام امتحانات", "نتیجہ درج کریں"])
    with tabs[0]:
        st.dataframe(exams_df, use_container_width=True, hide_index=True)
    with tabs[1]:
        if exams_df.empty:
            st.info("کوئی امتحانی درخواست موجود نہیں۔")
            return
        labels = {
            f"{row['id']} - {row['نام']} ({row['امتحان']}) [{row['حیثیت']}]": row["id"]
            for _, row in exams_df.iterrows()
        }
        with st.form("exam_result_form"):
            selected = st.selectbox("امتحان منتخب کریں", list(labels))
            q1 = st.number_input("سوال 1", min_value=0, max_value=20, value=0)
            q2 = st.number_input("سوال 2", min_value=0, max_value=20, value=0)
            q3 = st.number_input("سوال 3", min_value=0, max_value=20, value=0)
            q4 = st.number_input("سوال 4", min_value=0, max_value=20, value=0)
            q5 = st.number_input("سوال 5", min_value=0, max_value=20, value=0)
            status = st.selectbox("حیثیت", ["منظور", "فیل", "پینڈنگ", "مکمل"])
            if st.form_submit_button("نتیجہ محفوظ کریں", use_container_width=True):
                total = int(q1 + q2 + q3 + q4 + q5)
                grade = grade_from_mistakes(max(0, 20 - total // 5))
                exam_id = labels[selected]
                with db_connection() as conn:
                    conn.execute(
                        """
                        UPDATE exams SET q1=?, q2=?, q3=?, q4=?, q5=?, total=?, grade=?, status=?
                        WHERE id=?
                        """,
                        (q1, q2, q3, q4, q5, total, grade, status, exam_id),
                    )
                log_audit(st.session_state.username, "Exam Evaluated", str(exam_id))
                st.success("امتحانی نتیجہ محفوظ ہوگیا۔")


def render_staff_monitoring() -> None:
    st.subheader("عملہ نگرانی و شکایات")
    with st.form("staff_monitoring_form"):
        staff_name = st.selectbox("عملہ", ["", *Repo.teacher_names(include_admin=True)])
        note_date = st.date_input("تاریخ", date.today())
        note_type = st.selectbox("نوعیت", ["تعریف", "شکایت", "انتباہ", "مشاہدہ"])
        description = st.text_area("تفصیل")
        action_taken = st.text_input("کارروائی")
        status = st.selectbox("حالت", ["اوپن", "زیر غور", "حل شدہ"])
        if st.form_submit_button("اندراج محفوظ کریں", use_container_width=True):
            with db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO staff_monitoring (staff_name, date, note_type, description, action_taken, status, created_by, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (staff_name, note_date, note_type, description, action_taken, status, st.session_state.username, current_ts()),
                )
            st.success("نگرانی نوٹ محفوظ ہوگیا۔")
    with db_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT staff_name AS عملہ, date AS تاریخ, note_type AS قسم, description AS تفصیل,
                   action_taken AS کارروائی, status AS حالت, created_by AS درج_کنندہ
            FROM staff_monitoring ORDER BY id DESC
            """,
            conn,
        )
    st.dataframe(df, use_container_width=True, hide_index=True)


def html_download(name: str, html: str, label: str) -> None:
    st.download_button(label, html.encode("utf-8"), name, "text/html")


def result_card_html(row: dict) -> str:
    return f"""
    <!doctype html>
    <html dir="rtl"><head><meta charset="utf-8"><title>رزلٹ کارڈ</title>
    <style>
        body {{ font-family: Arial, sans-serif; direction: rtl; margin: 24px; }}
        .card {{ border: 2px solid #24563b; padding: 20px; border-radius: 16px; max-width: 720px; margin: auto; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 14px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        h2, h3 {{ text-align: center; color: #24563b; }}
    </style></head><body>
    <div class="card">
        <h2>{CONFIG.app_title}</h2>
        <h3>ماہانہ رزلٹ کارڈ</h3>
        <p><b>نام:</b> {row['نام']} ولد {row['والد']}</p>
        <p><b>رول نمبر:</b> {row['رول_نمبر']}</p>
        <p><b>امتحان:</b> {row['امتحان']}</p>
        <p><b>شعبہ:</b> {row['شعبہ']}</p>
        <table>
            <tr><th>کل نمبر</th><th>گریڈ</th><th>حیثیت</th></tr>
            <tr><td>{row['کل_نمبر']}</td><td>{row['گریڈ']}</td><td>{row['حیثیت']}</td></tr>
        </table>
    </div>
    </body></html>
    """


def render_monthly_result_cards() -> None:
    st.subheader("ماہانہ رزلٹ کارڈ")
    with db_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT e.id, s.name AS نام, s.father_name AS والد, s.roll_no AS رول_نمبر, e.exam_type AS امتحان,
                   e.dept AS شعبہ, COALESCE(e.total, 0) AS کل_نمبر, COALESCE(e.grade, '') AS گریڈ,
                   COALESCE(e.status, '') AS حیثیت
            FROM exams e JOIN students s ON s.id = e.student_id
            WHERE COALESCE(e.total, 0) > 0
            ORDER BY e.id DESC
            """,
            conn,
        )
    if df.empty:
        st.info("ابھی تیار شدہ رزلٹ موجود نہیں۔")
        return
    st.dataframe(df, use_container_width=True, hide_index=True)
    selected = st.selectbox("طالبعلم منتخب کریں", [f"{r['id']} - {r['نام']}" for _, r in df.iterrows()])
    selected_id = int(selected.split(" - ")[0])
    row = df[df["id"] == selected_id].iloc[0].to_dict()
    html_download(f"result_card_{selected_id}.html", result_card_html(row), "HTML رزلٹ کارڈ ڈاؤن لوڈ")


def render_para_report() -> None:
    st.subheader("پارہ تعلیمی رپورٹ")
    with db_connection() as conn:
        student_df = pd.read_sql_query(
            "SELECT id, name AS نام, father_name AS والد FROM students ORDER BY name",
            conn,
        )
    if student_df.empty:
        st.info("طلباء موجود نہیں۔")
        return
    selected = st.selectbox("طالبعلم", [f"{r['id']} - {r['نام']} ولد {r['والد']}" for _, r in student_df.iterrows()])
    student_id = int(selected.split(" - ")[0])
    with db_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT para_no AS پارہ, book_name AS کتاب, passed_date AS تاریخ, exam_type AS امتحان, grade AS گریڈ, marks AS نمبر
            FROM passed_paras WHERE student_id = ? ORDER BY para_no
            """,
            conn,
            params=(student_id,),
        )
    if df.empty:
        st.warning("اس طالبعلم کا پارہ ریکارڈ موجود نہیں۔")
        return
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("CSV ڈاؤن لوڈ", convert_df_to_csv(df), "para_report.csv", "text/csv")


def render_teacher_attendance_admin() -> None:
    st.subheader("اساتذہ حاضری")
    with db_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT t_name AS استاد, a_date AS تاریخ, arrival AS آمد, departure AS رخصت,
                   actual_arrival AS اصل_آمد, actual_departure AS اصل_رخصت
            FROM t_attendance ORDER BY a_date DESC, t_name
            """,
            conn,
        )
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_leave_approvals() -> None:
    st.subheader("رخصت کی منظوری")
    with db_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT id, t_name AS استاد, l_type AS نوعیت, start_date AS آغاز, back_date AS واپسی,
                   days AS دن, reason AS وجہ, status AS حالت, request_date AS درخواست_تاریخ
            FROM leave_requests ORDER BY id DESC
            """,
            conn,
        )
    st.dataframe(df, use_container_width=True, hide_index=True)
    if df.empty:
        return
    options = {f"{r['id']} - {r['استاد']} [{r['حالت']}]": r["id"] for _, r in df.iterrows()}
    col1, col2 = st.columns(2)
    selected = col1.selectbox("درخواست", list(options))
    decision = col2.selectbox("فیصلہ", ["منظور", "مسترد", "پینڈنگ"])
    if st.button("حالت اپڈیٹ کریں", use_container_width=True):
        req_id = options[selected]
        with db_connection() as conn:
            conn.execute("UPDATE leave_requests SET status = ? WHERE id = ?", (decision, req_id))
        st.success("رخصت کی حالت اپڈیٹ ہوگئی۔")


def render_user_management() -> None:
    st.subheader("یوزر مینجمنٹ")
    tab1, tab2, tab3, tab4 = st.tabs(["اساتذہ", "نیا استاد", "طلباء", "نیا طالبعلم"])
    with tab1:
        with db_connection() as conn:
            df = pd.read_sql_query(
                """
                SELECT name AS نام, dept AS شعبہ, phone AS فون, address AS پتہ, id_card AS شناختی_کارڈ, joining_date AS جوائننگ
                FROM teachers ORDER BY name
                """,
                conn,
            )
        st.dataframe(df, use_container_width=True, hide_index=True)
        teachers = Repo.teacher_names()
        if teachers:
            selected_teacher = st.selectbox("پاسورڈ ری سیٹ", teachers)
            new_password = st.text_input("نیا پاسورڈ", key="reset_pass", type="password")
            if st.button("پاسورڈ ری سیٹ کریں"):
                with db_connection() as conn:
                    conn.execute(
                        "UPDATE teachers SET password = ? WHERE name = ?",
                        (hash_password(new_password), selected_teacher),
                    )
                st.success("پاسورڈ ری سیٹ ہوگیا۔")
    with tab2:
        with st.form("teacher_create_form"):
            name = st.text_input("نام")
            dept = st.selectbox("شعبہ", ["Admin", *DEPARTMENTS])
            phone = st.text_input("فون")
            address = st.text_input("پتہ")
            id_card = st.text_input("شناختی کارڈ")
            joining_date = st.date_input("جوائننگ تاریخ", date.today())
            password = st.text_input("ابتدائی پاسورڈ", type="password")
            if st.form_submit_button("استاد محفوظ کریں", use_container_width=True):
                with db_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO teachers (name, password, dept, phone, address, id_card, joining_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (name, hash_password(password), dept, phone, address, id_card, joining_date),
                    )
                st.success("استاد محفوظ ہوگیا۔")
    with tab3:
        with db_connection() as conn:
            df = pd.read_sql_query(
                """
                SELECT name AS نام, father_name AS والد, dept AS شعبہ, class AS کلاس,
                       section AS سیکشن, roll_no AS رول_نمبر, teacher_name AS استاد
                FROM students ORDER BY name
                """,
                conn,
            )
        st.dataframe(df, use_container_width=True, hide_index=True)
    with tab4:
        teacher_options = Repo.teacher_names()
        if not teacher_options:
            st.warning("پہلے کم از کم ایک استاد شامل کریں، پھر طالبعلم assign کریں۔")
            return
        with st.form("student_create_form"):
            name = st.text_input("نام", key="student_name")
            father_name = st.text_input("والد کا نام")
            mother_name = st.text_input("والدہ کا نام")
            dob = st.date_input("تاریخ پیدائش", date.today() - timedelta(days=3650))
            admission_date = st.date_input("داخلہ تاریخ", date.today())
            phone = st.text_input("فون", key="student_phone")
            address = st.text_area("پتہ")
            dept = st.selectbox("شعبہ", DEPARTMENTS, key="student_dept")
            class_name = st.text_input("کلاس")
            section = st.text_input("سیکشن")
            roll_no = st.text_input("رول نمبر")
            teacher_name = st.selectbox("استاد", teacher_options)
            id_card = st.text_input("شناختی نمبر")
            if st.form_submit_button("طالبعلم محفوظ کریں", use_container_width=True):
                with db_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO students (
                            name, father_name, mother_name, dob, admission_date, phone, address,
                            teacher_name, dept, class, section, roll_no, id_card
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            name, father_name, mother_name, dob, admission_date, phone, address,
                            teacher_name, dept, class_name, section, roll_no, id_card,
                        ),
                    )
                st.success("طالبعلم محفوظ ہوگیا۔")


def render_timetable_management() -> None:
    st.subheader("ٹائم ٹیبل مینجمنٹ")
    teacher_options = Repo.teacher_names()
    if not teacher_options:
        st.warning("ٹائم ٹیبل بنانے سے پہلے کم از کم ایک استاد شامل کریں۔")
        return
    with st.form("timetable_form"):
        teacher_name = st.selectbox("استاد", teacher_options)
        day = st.selectbox("دن", WEEK_DAYS)
        period = st.text_input("وقت / پیریڈ")
        book = st.text_input("کتاب / مضمون")
        room = st.text_input("کمرہ")
        if st.form_submit_button("ٹائم ٹیبل محفوظ کریں", use_container_width=True):
            with db_connection() as conn:
                conn.execute(
                    "INSERT INTO timetable (t_name, day, period, book, room) VALUES (?, ?, ?, ?, ?)",
                    (teacher_name, day, period, book, room),
                )
            st.success("ٹائم ٹیبل محفوظ ہوگیا۔")
    with db_connection() as conn:
        df = pd.read_sql_query(
            "SELECT t_name AS استاد, day AS دن, period AS وقت, book AS کتاب, room AS کمرہ FROM timetable ORDER BY t_name, day, period",
            conn,
        )
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_notifications_admin() -> None:
    st.subheader("نوٹیفکیشنز")
    col1, col2 = st.columns([1, 1.2])
    with col1:
        with st.form("notification_form"):
            title = st.text_input("عنوان")
            message = st.text_area("پیغام")
            target = st.selectbox("ہدف", ["all", *Repo.teacher_names(include_admin=True)])
            if st.form_submit_button("نوٹیفکیشن بھیجیں", use_container_width=True):
                notify(title, message, target)
                st.success("نوٹیفکیشن بھیج دی گئی۔")
    with col2:
        with db_connection() as conn:
            df = pd.read_sql_query(
                "SELECT title AS عنوان, message AS پیغام, target AS ہدف, created_at AS وقت FROM notifications ORDER BY id DESC",
                conn,
            )
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_analytics() -> None:
    st.subheader("تجزیہ و رپورٹس")
    with db_connection() as conn:
        teacher_student = pd.read_sql_query(
            "SELECT teacher_name AS استاد, COUNT(*) AS طلباء FROM students GROUP BY teacher_name ORDER BY طلباء DESC",
            conn,
        )
        dept_student = pd.read_sql_query(
            "SELECT dept AS شعبہ, COUNT(*) AS طلباء FROM students GROUP BY dept ORDER BY طلباء DESC",
            conn,
        )
    col1, col2 = st.columns(2)
    with col1:
        if not teacher_student.empty:
            fig = px.bar(teacher_student, x="استاد", y="طلباء", title="استاد کے حساب سے طلباء")
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        if not dept_student.empty:
            fig = px.pie(dept_student, names="شعبہ", values="طلباء", title="شعبہ وار طلباء", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    if not teacher_student.empty:
        st.dataframe(teacher_student, use_container_width=True, hide_index=True)


def render_best_students() -> None:
    st.subheader("ماہانہ بہترین طلباء")
    with db_connection() as conn:
        exams_df = pd.read_sql_query(
            """
            SELECT s.name AS نام, s.father_name AS والد, s.dept AS شعبہ,
                   AVG(COALESCE(e.total, 0)) AS اوسط_نمبر
            FROM students s
            LEFT JOIN exams e ON e.student_id = s.id
            GROUP BY s.id
            ORDER BY اوسط_نمبر DESC, s.name
            LIMIT 10
            """,
            conn,
        )
    if exams_df.empty:
        st.info("کافی امتحانی ڈیٹا موجود نہیں۔")
        return
    st.dataframe(exams_df, use_container_width=True, hide_index=True)


def build_backup_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        db_path = CONFIG.db_path
        if db_path.exists():
            archive.write(db_path, arcname=db_path.name)
        code_path = Path(__file__)
        archive.write(code_path, arcname=code_path.name)
    buffer.seek(0)
    return buffer.read()


def render_backup_settings() -> None:
    st.subheader("بیک اپ و سیٹنگز")
    st.info("یہاں سے آپ backup بنا بھی سکتے ہیں اور پرانا backup upload کر کے restore بھی کر سکتے ہیں۔")
    col1, col2 = st.columns(2)
    with col1:
        backup_bytes = build_backup_zip()
        st.download_button(
            "بیک اپ ZIP ڈاؤن لوڈ",
            backup_bytes,
            file_name=f"jamia_backup_{date.today()}.zip",
            mime="application/zip",
            use_container_width=True,
        )
        db_exists = CONFIG.db_path.exists()
        st.write(f"Database file: `{CONFIG.db_path.resolve()}`")
        st.write(f"موجود ہے: `{'ہاں' if db_exists else 'نہیں'}`")
    with col2:
        uploaded_backup = st.file_uploader(
            "بیک اپ اپلوڈ کریں",
            type=["zip", "db", "sqlite", "sqlite3"],
            help="ZIP یا database file اپلوڈ کریں۔",
        )
        if uploaded_backup is not None and st.button("بیک اپ restore کریں", use_container_width=True):
            try:
                restore_database_from_upload(uploaded_backup)
                st.success("بیک اپ کامیابی سے restore ہوگیا۔ App اب reload ہوگی۔")
                st.rerun()
            except Exception as exc:
                st.error(f"بیک اپ restore نہ ہو سکا: {exc}")


def render_password_change() -> None:
    st.subheader("پاسورڈ تبدیل کریں")
    with st.form("change_pass_form"):
        old_password = st.text_input("پرانا پاسورڈ", type="password")
        new_password = st.text_input("نیا پاسورڈ", type="password")
        confirm = st.text_input("نیا پاسورڈ دوبارہ", type="password")
        if st.form_submit_button("پاسورڈ محفوظ کریں", use_container_width=True):
            if new_password != confirm:
                st.error("نیا پاسورڈ اور تصدیق برابر نہیں ہیں۔")
                return
            user = Repo.authenticate(st.session_state.username, old_password)
            if not user:
                st.error("پرانا پاسورڈ درست نہیں۔")
                return
            with db_connection() as conn:
                conn.execute(
                    "UPDATE teachers SET password = ? WHERE name = ?",
                    (hash_password(new_password), st.session_state.username),
                )
            st.success("پاسورڈ تبدیل ہوگیا۔")


def insert_hifz_record(payload: dict) -> None:
    with db_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM hifz_records WHERE r_date = ? AND student_id = ?",
            (payload["r_date"], payload["student_id"]),
        ).fetchone()
        if exists:
            raise ValueError("اس تاریخ پر یہ ریکارڈ پہلے سے موجود ہے۔")
        conn.execute(
            """
            INSERT INTO hifz_records (
                r_date, student_id, t_name, surah, a_from, a_to, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance, principal_note, lines, cleanliness
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["r_date"], payload["student_id"], payload["t_name"], payload["surah"], payload["a_from"], payload["a_to"],
                payload["sq_p"], payload["sq_a"], payload["sq_m"], payload["m_p"], payload["m_a"], payload["m_m"],
                payload["attendance"], payload.get("principal_note", ""), payload["lines"], payload["cleanliness"],
            ),
        )


def insert_qaida_record(payload: dict) -> None:
    with db_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM qaida_records WHERE r_date = ? AND student_id = ?",
            (payload["r_date"], payload["student_id"]),
        ).fetchone()
        if exists:
            raise ValueError("اس تاریخ پر یہ ریکارڈ پہلے سے موجود ہے۔")
        conn.execute(
            """
            INSERT INTO qaida_records (r_date, student_id, t_name, lesson_no, total_lines, details, attendance, cleanliness)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["r_date"], payload["student_id"], payload["t_name"], payload["lesson_no"], payload["total_lines"],
                payload["details"], payload["attendance"], payload["cleanliness"],
            ),
        )


def insert_general_record(payload: dict) -> None:
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO general_education (r_date, student_id, t_name, dept, book_subject, today_lesson, homework, performance, attendance, cleanliness)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["r_date"], payload["student_id"], payload["t_name"], payload["dept"], payload["book_subject"],
                payload["today_lesson"], payload["homework"], payload["performance"], payload["attendance"], payload["cleanliness"],
            ),
        )


def render_hifz_entry(entry_date: date, students: list[sqlite3.Row]) -> None:
    for student in students:
        key = f"h_{student['id']}"
        st.markdown(f"### {student['name']} ولد {student['father_name'] or '-'}")
        attendance = st.radio("حاضری", ATTENDANCE_OPTIONS, horizontal=True, key=f"{key}_att")
        cleanliness = st.selectbox("صفائی", CLEANLINESS_OPTIONS, key=f"{key}_clean")
        if attendance != "حاضر":
            if st.button(f"{student['name']} محفوظ کریں", key=f"{key}_save_abs"):
                try:
                    insert_hifz_record(
                        {
                            "r_date": entry_date, "student_id": student["id"], "t_name": st.session_state.username,
                            "surah": "غائب", "a_from": "", "a_to": "", "sq_p": "غائب", "sq_a": 0, "sq_m": 0,
                            "m_p": "غائب", "m_a": 0, "m_m": 0, "attendance": attendance, "lines": 0, "cleanliness": cleanliness,
                        }
                    )
                    st.success("ریکارڈ محفوظ ہوگیا۔")
                except ValueError as exc:
                    st.error(str(exc))
            st.divider()
            continue
        c1, c2, c3 = st.columns(3)
        surah = c1.selectbox("سورت", SURAHS, key=f"{key}_surah")
        a_from = c2.text_input("آیت سے", key=f"{key}_from")
        a_to = c3.text_input("آیت تک", key=f"{key}_to")
        lines = st.number_input("کل سطور", min_value=0, value=0, key=f"{key}_lines")
        sq_col1, sq_col2, sq_col3 = st.columns(3)
        sq_p = sq_col1.selectbox("سبقی پارہ", PARAS, key=f"{key}_sqp")
        sq_amount = sq_col2.selectbox("سبقی مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"{key}_sqa")
        sq_m = sq_col3.number_input("سبقی غلطیاں", min_value=0, value=0, key=f"{key}_sqm")
        m_col1, m_col2, m_col3 = st.columns(3)
        m_p = m_col1.selectbox("منزل پارہ", PARAS, key=f"{key}_mp")
        m_amount = m_col2.selectbox("منزل مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"{key}_ma")
        m_m = m_col3.number_input("منزل غلطیاں", min_value=0, value=0, key=f"{key}_mm")
        grade = grade_from_mistakes(int(sq_m + m_m))
        st.info(f"اندازاً درجہ: {grade}")
        if st.button(f"{student['name']} کا ریکارڈ محفوظ کریں", key=f"{key}_save"):
            try:
                insert_hifz_record(
                    {
                        "r_date": entry_date, "student_id": student["id"], "t_name": st.session_state.username,
                        "surah": surah, "a_from": a_from, "a_to": a_to, "sq_p": f"{sq_p}: {sq_amount}",
                        "sq_a": 0, "sq_m": int(sq_m), "m_p": f"{m_p}: {m_amount}", "m_a": 0, "m_m": int(m_m),
                        "attendance": attendance, "lines": int(lines), "cleanliness": cleanliness,
                    }
                )
                st.success("حفظ ریکارڈ محفوظ ہوگیا۔")
            except ValueError as exc:
                st.error(str(exc))
        st.divider()


def render_qaida_entry(entry_date: date, students: list[sqlite3.Row]) -> None:
    for student in students:
        key = f"q_{student['id']}"
        st.markdown(f"### {student['name']} ولد {student['father_name'] or '-'}")
        attendance = st.radio("حاضری", ATTENDANCE_OPTIONS, horizontal=True, key=f"{key}_att")
        cleanliness = st.selectbox("صفائی", CLEANLINESS_OPTIONS, key=f"{key}_clean")
        lesson_no = st.text_input("سبق / تختی نمبر", key=f"{key}_lesson")
        total_lines = st.number_input("کل لائنیں", min_value=0, value=0, key=f"{key}_lines")
        details = st.text_area("تفصیل", key=f"{key}_details")
        if st.button(f"{student['name']} کا ریکارڈ محفوظ کریں", key=f"{key}_save"):
            try:
                insert_qaida_record(
                    {
                        "r_date": entry_date, "student_id": student["id"], "t_name": st.session_state.username,
                        "lesson_no": lesson_no or "غائب", "total_lines": int(total_lines if attendance == 'حاضر' else 0),
                        "details": details, "attendance": attendance, "cleanliness": cleanliness,
                    }
                )
                st.success("قاعدہ ریکارڈ محفوظ ہوگیا۔")
            except ValueError as exc:
                st.error(str(exc))
        st.divider()


def render_general_entry(entry_date: date, students: list[sqlite3.Row], dept: str) -> None:
    with st.form(f"general_{dept}"):
        payloads: list[dict] = []
        for student in students:
            st.markdown(f"### {student['name']} ولد {student['father_name'] or '-'}")
            attendance = st.radio("حاضری", ATTENDANCE_OPTIONS, horizontal=True, key=f"{dept}_{student['id']}_att")
            cleanliness = st.selectbox("صفائی", CLEANLINESS_OPTIONS, key=f"{dept}_{student['id']}_clean")
            if dept == "عصری تعلیم":
                subject = st.selectbox("مضمون", SCHOOL_SUBJECTS, key=f"{dept}_{student['id']}_sub")
                homework = st.text_area("ہوم ورک", key=f"{dept}_{student['id']}_hw")
            else:
                subject = st.text_input("کتاب", key=f"{dept}_{student['id']}_book")
                homework = ""
            lesson = st.text_area("آج کا سبق", key=f"{dept}_{student['id']}_lesson")
            performance = st.select_slider("کارکردگی", PERFORMANCE_OPTIONS, key=f"{dept}_{student['id']}_perf")
            payloads.append(
                {
                    "r_date": entry_date,
                    "student_id": student["id"],
                    "t_name": st.session_state.username,
                    "dept": dept,
                    "book_subject": subject if attendance == "حاضر" else "غائب",
                    "today_lesson": lesson if attendance == "حاضر" else "غائب",
                    "homework": homework if attendance == "حاضر" else "",
                    "performance": performance if attendance == "حاضر" else "غائب",
                    "attendance": attendance,
                    "cleanliness": cleanliness,
                }
            )
            st.divider()
        if st.form_submit_button("تمام ریکارڈ محفوظ کریں", use_container_width=True):
            for payload in payloads:
                insert_general_record(payload)
            st.success("تمام ریکارڈ محفوظ ہوگئے۔")


def render_teacher_daily_entry() -> None:
    st.subheader("روزانہ سبق اندراج")
    entry_date = st.date_input("تاریخ", date.today())
    dept = st.selectbox("شعبہ منتخب کریں", DEPARTMENTS)
    students = Repo.students(st.session_state.username, dept)
    if not students:
        st.info("اس شعبے میں آپ کے طلباء موجود نہیں۔")
        return
    if dept == "حفظ":
        render_hifz_entry(entry_date, students)
    elif dept == "قاعدہ":
        render_qaida_entry(entry_date, students)
    else:
        render_general_entry(entry_date, students, dept)


def render_exam_request() -> None:
    st.subheader("امتحانی درخواست")
    students = Repo.students(st.session_state.username)
    if not students:
        st.warning("آپ کے لیے کوئی طالبعلم موجود نہیں۔")
        return
    labels = {f"{s['id']} - {s['name']} ولد {s['father_name'] or '-'} ({s['dept'] or '-'})": s for s in students}
    with st.form("exam_request"):
        selected = st.selectbox("طالبعلم", list(labels))
        exam_type = st.selectbox("امتحان کی قسم", EXAM_TYPES)
        start_date = st.date_input("تاریخ آغاز", date.today())
        end_date = st.date_input("تاریخ اختتام", date.today() + timedelta(days=7))
        from_para = st.number_input("شروع پارہ", min_value=0, max_value=30, value=1)
        to_para = st.number_input("آخر پارہ", min_value=0, max_value=30, value=5)
        book_name = st.text_input("کتاب")
        amount_read = st.text_input("مقدار خواندگی")
        if st.form_submit_button("درخواست بھیجیں", use_container_width=True):
            student = labels[selected]
            with db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO exams (student_id, dept, exam_type, from_para, to_para, book_name, amount_read, start_date, end_date, total_days, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student["id"], student["dept"], exam_type, int(from_para), int(to_para), book_name,
                        amount_read, start_date, end_date, (end_date - start_date).days + 1, "پینڈنگ",
                    ),
                )
            st.success("امتحانی درخواست محفوظ ہوگئی۔")


def render_teacher_leave_request() -> None:
    st.subheader("رخصت کی درخواست")
    with st.form("leave_request"):
        leave_type = st.selectbox("نوعیت", LEAVE_TYPES)
        start_date = st.date_input("شروع تاریخ", date.today())
        days = st.number_input("دن", min_value=1, max_value=30, value=1)
        reason = st.text_area("وجہ")
        if st.form_submit_button("درخواست جمع کریں", use_container_width=True):
            if not reason.strip():
                st.error("براہ کرم وجہ لکھیں۔")
                return
            with db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO leave_requests (t_name, reason, start_date, back_date, status, request_date, l_type, days, notification_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        st.session_state.username, reason.strip(), start_date,
                        start_date + timedelta(days=int(days) - 1), "پینڈنگ", date.today(), leave_type, int(days),
                    ),
                )
            st.success("رخصت کی درخواست بھیج دی گئی۔")


def render_teacher_attendance() -> None:
    st.subheader("میری حاضری")
    today = date.today()
    rec = Repo.attendance_record(st.session_state.username, today)
    if not rec:
        c1, c2 = st.columns(2)
        a_date = c1.date_input("تاریخ", today)
        arrival = c2.time_input("آمد کا وقت", datetime.now().time())
        if st.button("آمد درج کریں", use_container_width=True):
            with db_connection() as conn:
                conn.execute(
                    "INSERT INTO t_attendance (t_name, a_date, arrival, actual_arrival) VALUES (?, ?, ?, ?)",
                    (st.session_state.username, a_date, arrival.strftime("%I:%M %p"), current_time_label()),
                )
            st.success("آمد درج ہوگئی۔")
            st.rerun()
        return
    if rec["departure"] is None:
        st.success(f"آمد: {rec['arrival']}")
        departure = st.time_input("رخصت کا وقت", datetime.now().time())
        if st.button("رخصت درج کریں", use_container_width=True):
            with db_connection() as conn:
                conn.execute(
                    "UPDATE t_attendance SET departure = ?, actual_departure = ? WHERE t_name = ? AND a_date = ?",
                    (departure.strftime("%I:%M %p"), current_time_label(), st.session_state.username, today),
                )
            st.success("رخصت درج ہوگئی۔")
            st.rerun()
        return
    st.success(f"آمد: {rec['arrival']} | رخصت: {rec['departure']}")


def render_teacher_timetable() -> None:
    st.subheader("میرا ٹائم ٹیبل")
    df = Repo.timetable_for(st.session_state.username)
    if df.empty:
        st.info("ابھی آپ کا ٹائم ٹیبل موجود نہیں۔")
        return
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_teacher_notifications() -> None:
    st.subheader("نوٹیفکیشنز")
    df = Repo.notifications_for(st.session_state.username)
    if df.empty:
        st.info("کوئی نوٹیفکیشن نہیں۔")
        return
    st.dataframe(df, use_container_width=True, hide_index=True)


def route_admin(choice: str) -> None:
    if choice == "ایڈمن ڈیش بورڈ":
        render_admin_dashboard()
    elif choice == "یومیہ تعلیمی رپورٹ":
        render_daily_report()
    elif choice == "امتحانی نظام":
        render_exam_management()
    elif choice == "عملہ نگرانی و شکایات":
        render_staff_monitoring()
    elif choice == "ماہانہ رزلٹ کارڈ":
        render_monthly_result_cards()
    elif choice == "پارہ تعلیمی رپورٹ":
        render_para_report()
    elif choice == "اساتذہ حاضری":
        render_teacher_attendance_admin()
    elif choice == "رخصت کی منظوری":
        render_leave_approvals()
    elif choice == "یوزر مینجمنٹ":
        render_user_management()
    elif choice == "ٹائم ٹیبل مینجمنٹ":
        render_timetable_management()
    elif choice == "نوٹیفکیشنز":
        render_notifications_admin()
    elif choice == "تجزیہ و رپورٹس":
        render_analytics()
    elif choice == "ماہانہ بہترین طلباء":
        render_best_students()
    elif choice == "بیک اپ و سیٹنگز":
        render_backup_settings()
    elif choice == "پاسورڈ تبدیل کریں":
        render_password_change()


def route_teacher(choice: str) -> None:
    if choice == "روزانہ سبق اندراج":
        render_teacher_daily_entry()
    elif choice == "امتحانی درخواست":
        render_exam_request()
    elif choice == "رخصت کی درخواست":
        render_teacher_leave_request()
    elif choice == "میری حاضری":
        render_teacher_attendance()
    elif choice == "میرا ٹائم ٹیبل":
        render_teacher_timetable()
    elif choice == "نوٹیفکیشنز":
        render_teacher_notifications()
    elif choice == "پاسورڈ تبدیل کریں":
        render_password_change()


def main() -> None:
    set_page()
    ensure_session()
    try:
        init_db()
        if not st.session_state.logged_in:
            render_login()
        choice = render_sidebar()
        if st.session_state.user_type == "admin":
            route_admin(choice)
        else:
            route_teacher(choice)
    except Exception as exc:
        st.error("ایک unexpected error آیا ہے۔ میں نے app کو crash ہونے کے بجائے capture کر لیا ہے۔")
        st.exception(exc)


if __name__ == "__main__":
    main()
