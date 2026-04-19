from __future__ import annotations

import hashlib
import sqlite3
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
PAKISTAN_TZ = pytz.timezone("Asia/Karachi")
CLEANLINESS_OPTIONS = ["بہترین", "بہتر", "ناقص"]
ATTENDANCE_OPTIONS = ["حاضر", "غیر حاضر", "رخصت"]
DEPARTMENTS = ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"]
SCHOOL_SUBJECTS = ["اردو", "انگلش", "ریاضی", "سائنس", "اسلامیات", "سماجی علوم"]
PERFORMANCE_OPTIONS = ["بہت بہتر", "بہتر", "مناسب", "کمزور"]
EXAM_TYPES = ["پارہ ٹیسٹ", "ماہانہ", "سہ ماہی", "سالانہ"]
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
PARAS = [f"پارہ {idx}" for idx in range(1, 31)]


@dataclass(frozen=True)
class AppConfig:
    db_path: Path = Path(DB_NAME)
    app_title: str = "جامعہ ملیہ اسلامیہ فیصل آباد"
    app_caption: str = "جدید تعلیمی و انتظامی پورٹل"


CONFIG = AppConfig()


SCHEMA_STATEMENTS = [
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
]


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
    return datetime.now(PAKISTAN_TZ)


def log_audit(user: str, action: str, details: str = "") -> None:
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO audit_log (user, action, timestamp, details) VALUES (?, ?, ?, ?)",
            (user, action, now_pk().isoformat(), details),
        )


def init_db() -> None:
    with db_connection() as conn:
        for statement in SCHEMA_STATEMENTS:
            conn.execute(statement)

        admin_exists = conn.execute("SELECT 1 FROM teachers WHERE name = 'admin'").fetchone()
        if not admin_exists:
            conn.execute(
                "INSERT INTO teachers (name, password, dept) VALUES (?, ?, ?)",
                ("admin", hash_password("jamia123"), "Admin"),
            )


class Repository:
    @staticmethod
    def authenticate(username: str, password: str) -> sqlite3.Row | None:
        hashed = hash_password(password)
        with db_connection() as conn:
            return conn.execute(
                "SELECT * FROM teachers WHERE name = ? AND (password = ? OR password = ?)",
                (username, password, hashed),
            ).fetchone()

    @staticmethod
    def get_students(teacher_name: str | None = None, dept: str | None = None) -> list[sqlite3.Row]:
        query = "SELECT id, name, father_name, dept, roll_no FROM students WHERE 1 = 1"
        params: list[str] = []
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
    def get_dashboard_counts() -> tuple[int, int]:
        with db_connection() as conn:
            student_count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            teacher_count = conn.execute("SELECT COUNT(*) FROM teachers WHERE name != 'admin'").fetchone()[0]
        return student_count, teacher_count

    @staticmethod
    def get_daily_report(start_date: date, end_date: date, teacher: str | None = None) -> pd.DataFrame:
        teacher_clause = ""
        params: list[object] = [start_date, end_date, start_date, end_date, start_date, end_date]
        if teacher and teacher != "تمام":
            teacher_clause = " AND base.teacher = ?"
            params.append(teacher)

        query = f"""
        SELECT * FROM (
            SELECT h.r_date AS تاریخ, s.name AS طالبعلم, s.father_name AS والد, s.roll_no AS رول_نمبر,
                   h.t_name AS teacher, 'حفظ' AS شعبہ, h.surah AS سبق, h.attendance AS حاضری, h.cleanliness AS صفائی
            FROM hifz_records h
            JOIN students s ON s.id = h.student_id
            WHERE h.r_date BETWEEN ? AND ?
            UNION ALL
            SELECT q.r_date, s.name, s.father_name, s.roll_no,
                   q.t_name, 'قاعدہ', q.lesson_no, q.attendance, q.cleanliness
            FROM qaida_records q
            JOIN students s ON s.id = q.student_id
            WHERE q.r_date BETWEEN ? AND ?
            UNION ALL
            SELECT g.r_date, s.name, s.father_name, s.roll_no,
                   g.t_name, g.dept, g.today_lesson, g.attendance, g.cleanliness
            FROM general_education g
            JOIN students s ON s.id = g.student_id
            WHERE g.r_date BETWEEN ? AND ?
        ) AS base
        WHERE 1 = 1 {teacher_clause}
        ORDER BY تاریخ DESC, طالبعلم
        """
        with db_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)

    @staticmethod
    def get_teacher_names() -> list[str]:
        with db_connection() as conn:
            rows = conn.execute("SELECT name FROM teachers ORDER BY name").fetchall()
        return [row["name"] for row in rows]

    @staticmethod
    def add_hifz_record(payload: dict) -> None:
        with db_connection() as conn:
            exists = conn.execute(
                "SELECT 1 FROM hifz_records WHERE r_date = ? AND student_id = ?",
                (payload["r_date"], payload["student_id"]),
            ).fetchone()
            if exists:
                raise ValueError("اس تاریخ کے لیے اس طالبعلم کا ریکارڈ پہلے سے موجود ہے۔")

            conn.execute(
                """
                INSERT INTO hifz_records (
                    r_date, student_id, t_name, surah, a_from, a_to, sq_p, sq_a, sq_m, m_p, m_a, m_m,
                    attendance, principal_note, lines, cleanliness
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["r_date"], payload["student_id"], payload["t_name"], payload["surah"],
                    payload["a_from"], payload["a_to"], payload["sq_p"], payload["sq_a"], payload["sq_m"],
                    payload["m_p"], payload["m_a"], payload["m_m"], payload["attendance"],
                    payload.get("principal_note", ""), payload["lines"], payload["cleanliness"],
                ),
            )

    @staticmethod
    def add_qaida_record(payload: dict) -> None:
        with db_connection() as conn:
            exists = conn.execute(
                "SELECT 1 FROM qaida_records WHERE r_date = ? AND student_id = ?",
                (payload["r_date"], payload["student_id"]),
            ).fetchone()
            if exists:
                raise ValueError("اس تاریخ کے لیے اس طالبعلم کا ریکارڈ پہلے سے موجود ہے۔")
            conn.execute(
                """
                INSERT INTO qaida_records (r_date, student_id, t_name, lesson_no, total_lines, details, attendance, cleanliness)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["r_date"], payload["student_id"], payload["t_name"], payload["lesson_no"],
                    payload["total_lines"], payload["details"], payload["attendance"], payload["cleanliness"],
                ),
            )

    @staticmethod
    def add_general_record(payload: dict) -> None:
        with db_connection() as conn:
            conn.execute(
                """
                INSERT INTO general_education (
                    r_date, student_id, t_name, dept, book_subject, today_lesson, homework, performance, attendance, cleanliness
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["r_date"], payload["student_id"], payload["t_name"], payload["dept"], payload["book_subject"],
                    payload["today_lesson"], payload["homework"], payload["performance"], payload["attendance"],
                    payload["cleanliness"],
                ),
            )

    @staticmethod
    def add_exam_request(payload: dict) -> None:
        with db_connection() as conn:
            conn.execute(
                """
                INSERT INTO exams (
                    student_id, dept, exam_type, from_para, to_para, book_name, amount_read, start_date, end_date, total_days, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["student_id"], payload["dept"], payload["exam_type"], payload["from_para"], payload["to_para"],
                    payload["book_name"], payload["amount_read"], payload["start_date"], payload["end_date"],
                    payload["total_days"], "پینڈنگ",
                ),
            )

    @staticmethod
    def add_leave_request(payload: dict) -> None:
        with db_connection() as conn:
            conn.execute(
                """
                INSERT INTO leave_requests (t_name, reason, start_date, back_date, status, request_date, l_type, days, notification_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    payload["t_name"], payload["reason"], payload["start_date"], payload["back_date"],
                    "پینڈنگ", date.today(), payload["l_type"], payload["days"],
                ),
            )

    @staticmethod
    def get_teacher_attendance(username: str, attendance_date: date) -> sqlite3.Row | None:
        with db_connection() as conn:
            return conn.execute(
                "SELECT * FROM t_attendance WHERE t_name = ? AND a_date = ?",
                (username, attendance_date),
            ).fetchone()

    @staticmethod
    def mark_arrival(username: str, attendance_date: date, arrival_time: str) -> None:
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO t_attendance (t_name, a_date, arrival, actual_arrival) VALUES (?, ?, ?, ?)",
                (username, attendance_date, arrival_time, now_pk().strftime("%I:%M %p")),
            )

    @staticmethod
    def mark_departure(username: str, attendance_date: date, departure_time: str) -> None:
        with db_connection() as conn:
            conn.execute(
                "UPDATE t_attendance SET departure = ?, actual_departure = ? WHERE t_name = ? AND a_date = ?",
                (departure_time, now_pk().strftime("%I:%M %p"), username, attendance_date),
            )

    @staticmethod
    def get_timetable(username: str) -> pd.DataFrame:
        with db_connection() as conn:
            return pd.read_sql_query(
                "SELECT day AS دن, period AS وقت, book AS کتاب, room AS کمرہ FROM timetable WHERE t_name = ?",
                conn,
                params=(username,),
            )


def set_page() -> None:
    st.set_page_config(page_title=CONFIG.app_title, page_icon="📚", layout="wide")
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at top right, rgba(205, 220, 57, 0.14), transparent 25%),
                    linear-gradient(160deg, #f8fbf2 0%, #eef5e7 45%, #fefcf5 100%);
            }
            .hero {
                padding: 1.25rem 1.5rem;
                border-radius: 22px;
                background: linear-gradient(135deg, #123524 0%, #2b5d34 60%, #557c36 100%);
                color: white;
                box-shadow: 0 18px 38px rgba(18, 53, 36, 0.18);
                margin-bottom: 1rem;
            }
            .card {
                background: rgba(255, 255, 255, 0.86);
                border: 1px solid rgba(18, 53, 36, 0.08);
                border-radius: 18px;
                padding: 1rem;
                box-shadow: 0 10px 25px rgba(18, 53, 36, 0.08);
            }
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #133b29 0%, #24563c 100%);
            }
            [data-testid="stSidebar"] * {
                color: white !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_session() -> None:
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("user_type", "")


def require_login() -> None:
    st.markdown(
        f"<div class='hero'><h1>{CONFIG.app_title}</h1><p>{CONFIG.app_caption}</p></div>",
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("لاگ اِن")
        username = st.text_input("صارف نام")
        password = st.text_input("پاسورڈ", type="password")
        if st.button("داخل ہوں", use_container_width=True):
            user = Repository.authenticate(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_type = "admin" if username == "admin" else "teacher"
                log_audit(username, "Login", st.session_state.user_type)
                st.rerun()
            else:
                st.error("غلط صارف نام یا پاسورڈ")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


def render_admin_dashboard() -> None:
    st.markdown("<div class='hero'><h2>ایڈمن ڈیش بورڈ</h2></div>", unsafe_allow_html=True)
    total_students, total_teachers = Repository.get_dashboard_counts()
    col1, col2 = st.columns(2)
    col1.metric("کل طلباء", total_students)
    col2.metric("کل اساتذہ", total_teachers)

    report_df = Repository.get_daily_report(date.today().replace(day=1), date.today())
    if not report_df.empty:
        summary = report_df.groupby("شعبہ").size().reset_index(name="اندراجات")
        chart = px.bar(summary, x="شعبہ", y="اندراجات", color="شعبہ", title="ماہانہ اندراجات")
        st.plotly_chart(chart, use_container_width=True)
        st.dataframe(report_df.head(20), use_container_width=True)
    else:
        st.info("ابھی تک کوئی تعلیمی اندراج موجود نہیں۔")


def render_daily_report() -> None:
    st.subheader("یومیہ تعلیمی رپورٹ")
    col1, col2, col3 = st.columns(3)
    start_date = col1.date_input("تاریخ آغاز", date.today().replace(day=1))
    end_date = col2.date_input("تاریخ اختتام", date.today())
    teacher = col3.selectbox("استاد", ["تمام", *Repository.get_teacher_names()])
    report_df = Repository.get_daily_report(start_date, end_date, teacher)
    if report_df.empty:
        st.warning("منتخب فلٹر کے مطابق کوئی ریکارڈ نہیں ملا۔")
        return
    st.dataframe(report_df, use_container_width=True)
    st.download_button(
        "CSV ڈاؤن لوڈ کریں",
        report_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"daily_report_{start_date}_{end_date}.csv",
        mime="text/csv",
    )


def render_hifz_form(entry_date: date, students: list[sqlite3.Row]) -> None:
    for student in students:
        student_key = f"hifz_{student['id']}"
        st.markdown(f"### {student['name']} ولد {student['father_name'] or '-'}")
        attendance = st.radio("حاضری", ATTENDANCE_OPTIONS, horizontal=True, key=f"{student_key}_att")
        cleanliness = st.selectbox("صفائی", CLEANLINESS_OPTIONS, key=f"{student_key}_clean")
        if attendance != "حاضر":
            if st.button(f"{student['name']} کا غیر حاضر ریکارڈ محفوظ کریں", key=f"{student_key}_save_absent"):
                Repository.add_hifz_record(
                    {
                        "r_date": entry_date, "student_id": student["id"], "t_name": st.session_state.username,
                        "surah": "غائب", "a_from": "", "a_to": "", "sq_p": "غائب", "sq_a": 0, "sq_m": 0,
                        "m_p": "غائب", "m_a": 0, "m_m": 0, "attendance": attendance, "lines": 0, "cleanliness": cleanliness,
                    }
                )
                st.success("ریکارڈ محفوظ ہوگیا")
            st.divider()
            continue

        col1, col2, col3 = st.columns(3)
        surah = col1.selectbox("سورت", SURAHS, key=f"{student_key}_surah")
        ayah_from = col2.text_input("آیت سے", key=f"{student_key}_from")
        ayah_to = col3.text_input("آیت تک", key=f"{student_key}_to")
        lines = st.number_input("کل سطور", min_value=0, value=0, key=f"{student_key}_lines")

        st.caption("سبقی")
        sq_col1, sq_col2, sq_col3 = st.columns(3)
        sq_para = sq_col1.selectbox("پارہ", PARAS, key=f"{student_key}_sq_para")
        sq_amount = sq_col2.selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"{student_key}_sq_amount")
        sq_mistakes = sq_col3.number_input("غلطیاں", min_value=0, value=0, key=f"{student_key}_sq_m")

        st.caption("منزل")
        m_col1, m_col2, m_col3 = st.columns(3)
        m_para = m_col1.selectbox("پارہ ", PARAS, key=f"{student_key}_m_para")
        m_amount = m_col2.selectbox("مقدار ", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"{student_key}_m_amount")
        m_mistakes = m_col3.number_input("منزل غلطیاں", min_value=0, value=0, key=f"{student_key}_m_m")

        if st.button(f"{student['name']} کا ریکارڈ محفوظ کریں", key=f"{student_key}_save"):
            try:
                Repository.add_hifz_record(
                    {
                        "r_date": entry_date,
                        "student_id": student["id"],
                        "t_name": st.session_state.username,
                        "surah": surah,
                        "a_from": ayah_from,
                        "a_to": ayah_to,
                        "sq_p": f"{sq_para}: {sq_amount}",
                        "sq_a": 0,
                        "sq_m": sq_mistakes,
                        "m_p": f"{m_para}: {m_amount}",
                        "m_a": 0,
                        "m_m": m_mistakes,
                        "attendance": attendance,
                        "lines": lines,
                        "cleanliness": cleanliness,
                    }
                )
                log_audit(st.session_state.username, "Hifz Entry", student["name"])
                st.success("حفظ ریکارڈ محفوظ ہوگیا")
            except ValueError as exc:
                st.error(str(exc))
        st.divider()


def render_qaida_form(entry_date: date, students: list[sqlite3.Row]) -> None:
    for student in students:
        student_key = f"qaida_{student['id']}"
        st.markdown(f"### {student['name']} ولد {student['father_name'] or '-'}")
        attendance = st.radio("حاضری", ATTENDANCE_OPTIONS, horizontal=True, key=f"{student_key}_att")
        cleanliness = st.selectbox("صفائی", CLEANLINESS_OPTIONS, key=f"{student_key}_clean")
        lesson = st.text_input("سبق / تختی نمبر", key=f"{student_key}_lesson")
        lines = st.number_input("کل لائنیں", min_value=0, value=0, key=f"{student_key}_lines")
        details = st.text_area("تفصیل", key=f"{student_key}_details")
        if st.button(f"{student['name']} کا ریکارڈ محفوظ کریں", key=f"{student_key}_save"):
            try:
                Repository.add_qaida_record(
                    {
                        "r_date": entry_date,
                        "student_id": student["id"],
                        "t_name": st.session_state.username,
                        "lesson_no": lesson or "غائب",
                        "total_lines": lines if attendance == "حاضر" else 0,
                        "details": details,
                        "attendance": attendance,
                        "cleanliness": cleanliness,
                    }
                )
                log_audit(st.session_state.username, "Qaida Entry", student["name"])
                st.success("قاعدہ ریکارڈ محفوظ ہوگیا")
            except ValueError as exc:
                st.error(str(exc))
        st.divider()


def render_general_form(entry_date: date, students: list[sqlite3.Row], dept: str) -> None:
    with st.form(f"{dept}_form"):
        payloads: list[dict] = []
        for student in students:
            st.markdown(f"### {student['name']} ولد {student['father_name'] or '-'}")
            attendance = st.radio("حاضری", ATTENDANCE_OPTIONS, horizontal=True, key=f"{dept}_{student['id']}_att")
            cleanliness = st.selectbox("صفائی", CLEANLINESS_OPTIONS, key=f"{dept}_{student['id']}_clean")
            if dept == "عصری تعلیم":
                book_subject = st.selectbox("مضمون", SCHOOL_SUBJECTS, key=f"{dept}_{student['id']}_subject")
                homework = st.text_area("ہوم ورک", key=f"{dept}_{student['id']}_hw")
            else:
                book_subject = st.text_input("کتاب", key=f"{dept}_{student['id']}_book")
                homework = ""
            lesson = st.text_area("آج کا سبق", key=f"{dept}_{student['id']}_lesson")
            performance = st.select_slider("کارکردگی", PERFORMANCE_OPTIONS, key=f"{dept}_{student['id']}_perf")
            payloads.append(
                {
                    "r_date": entry_date,
                    "student_id": student["id"],
                    "t_name": st.session_state.username,
                    "dept": dept,
                    "book_subject": book_subject if attendance == "حاضر" else "غائب",
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
                Repository.add_general_record(payload)
            log_audit(st.session_state.username, "General Entries", dept)
            st.success("تمام اندراجات محفوظ ہوگئے")


def render_teacher_lesson_entry() -> None:
    st.subheader("روزانہ سبق اندراج")
    entry_date = st.date_input("تاریخ", date.today())
    dept = st.selectbox("شعبہ منتخب کریں", DEPARTMENTS)
    students = Repository.get_students(st.session_state.username, dept)
    if not students:
        st.info("اس شعبے میں آپ کے نام سے کوئی طالبعلم موجود نہیں۔")
        return
    if dept == "حفظ":
        render_hifz_form(entry_date, students)
    elif dept == "قاعدہ":
        render_qaida_form(entry_date, students)
    else:
        render_general_form(entry_date, students, dept)


def render_exam_request() -> None:
    st.subheader("امتحانی درخواست")
    students = Repository.get_students(st.session_state.username)
    if not students:
        st.warning("آپ کے لیے کوئی طالبعلم موجود نہیں۔")
        return
    labels = {f"{s['name']} ولد {s['father_name'] or '-'} ({s['dept'] or '-'})": s for s in students}
    with st.form("exam_request_form"):
        selected_label = st.selectbox("طالبعلم", list(labels))
        student = labels[selected_label]
        exam_type = st.selectbox("امتحان کی قسم", EXAM_TYPES)
        start_date = st.date_input("تاریخ آغاز", date.today())
        end_date = st.date_input("تاریخ اختتام", date.today() + timedelta(days=7))
        from_para = st.number_input("شروع پارہ", min_value=0, max_value=30, value=1)
        to_para = st.number_input("آخری پارہ", min_value=0, max_value=30, value=max(from_para, 1))
        book_name = st.text_input("کتاب کا نام")
        amount_read = st.text_input("مقدار خواندگی")
        submitted = st.form_submit_button("درخواست بھیجیں", use_container_width=True)
        if submitted:
            Repository.add_exam_request(
                {
                    "student_id": student["id"],
                    "dept": student["dept"],
                    "exam_type": exam_type,
                    "from_para": int(from_para),
                    "to_para": int(to_para),
                    "book_name": book_name,
                    "amount_read": amount_read,
                    "start_date": start_date,
                    "end_date": end_date,
                    "total_days": (end_date - start_date).days + 1,
                }
            )
            log_audit(st.session_state.username, "Exam Requested", selected_label)
            st.success("امتحانی درخواست محفوظ ہوگئی")


def render_leave_request() -> None:
    st.subheader("رخصت کی درخواست")
    with st.form("leave_request_form"):
        leave_type = st.selectbox("رخصت کی نوعیت", ["بیماری", "ضروری کام", "ہنگامی", "دیگر"])
        start_date = st.date_input("شروع تاریخ", date.today())
        days = st.number_input("دن", min_value=1, max_value=30, value=1)
        reason = st.text_area("تفصیلی وجہ")
        if st.form_submit_button("درخواست جمع کریں", use_container_width=True):
            if not reason.strip():
                st.error("براہ کرم وجہ درج کریں۔")
                return
            Repository.add_leave_request(
                {
                    "t_name": st.session_state.username,
                    "reason": reason.strip(),
                    "start_date": start_date,
                    "back_date": start_date + timedelta(days=int(days) - 1),
                    "l_type": leave_type,
                    "days": int(days),
                }
            )
            log_audit(st.session_state.username, "Leave Requested", leave_type)
            st.success("رخصت کی درخواست بھیج دی گئی")


def render_my_attendance() -> None:
    st.subheader("میری حاضری")
    today = date.today()
    attendance = Repository.get_teacher_attendance(st.session_state.username, today)
    if not attendance:
        col1, col2 = st.columns(2)
        selected_date = col1.date_input("تاریخ", today)
        arrival = col2.time_input("آمد کا وقت", datetime.now().time())
        if st.button("آمد درج کریں", use_container_width=True):
            Repository.mark_arrival(st.session_state.username, selected_date, arrival.strftime("%I:%M %p"))
            log_audit(st.session_state.username, "Arrival Marked")
            st.rerun()
        return
    if attendance["departure"] is None:
        st.success(f"آمد: {attendance['arrival']}")
        departure = st.time_input("رخصت کا وقت", datetime.now().time())
        if st.button("رخصت درج کریں", use_container_width=True):
            Repository.mark_departure(st.session_state.username, today, departure.strftime("%I:%M %p"))
            log_audit(st.session_state.username, "Departure Marked")
            st.rerun()
        return
    st.success(f"آمد: {attendance['arrival']} | رخصت: {attendance['departure']}")


def render_timetable() -> None:
    st.subheader("میرا ٹائم ٹیبل")
    timetable_df = Repository.get_timetable(st.session_state.username)
    if timetable_df.empty:
        st.info("ابھی آپ کے لیے کوئی ٹائم ٹیبل درج نہیں۔")
        return
    st.dataframe(timetable_df, use_container_width=True)


def render_notifications() -> None:
    st.subheader("نوٹیفکیشنز")
    with db_connection() as conn:
        notifications = pd.read_sql_query(
            """
            SELECT title AS عنوان, message AS پیغام, target AS وصول_کنندہ, created_at AS وقت
            FROM notifications
            WHERE target IN (?, 'all')
            ORDER BY created_at DESC
            """,
            conn,
            params=(st.session_state.username,),
        )
    if notifications.empty:
        st.info("کوئی نئی نوٹیفکیشن نہیں۔")
        return
    st.dataframe(notifications, use_container_width=True)


def render_password_change() -> None:
    st.subheader("پاسورڈ تبدیل کریں")
    with st.form("password_change_form"):
        old_password = st.text_input("پرانا پاسورڈ", type="password")
        new_password = st.text_input("نیا پاسورڈ", type="password")
        confirm_password = st.text_input("نیا پاسورڈ دوبارہ", type="password")
        if st.form_submit_button("محفوظ کریں", use_container_width=True):
            if new_password != confirm_password:
                st.error("نیا پاسورڈ اور تصدیق ایک جیسے نہیں ہیں۔")
                return
            user = Repository.authenticate(st.session_state.username, old_password)
            if not user:
                st.error("پرانا پاسورڈ درست نہیں۔")
                return
            with db_connection() as conn:
                conn.execute(
                    "UPDATE teachers SET password = ? WHERE name = ?",
                    (hash_password(new_password), st.session_state.username),
                )
            log_audit(st.session_state.username, "Password Changed")
            st.success("پاسورڈ کامیابی سے تبدیل ہوگیا")


def render_sidebar() -> str:
    st.sidebar.markdown(f"## {CONFIG.app_title}")
    st.sidebar.caption(f"خوش آمدید، {st.session_state.username}")
    if st.session_state.user_type == "admin":
        menu = [
            "ایڈمن ڈیش بورڈ",
            "یومیہ تعلیمی رپورٹ",
            "نوٹیفکیشنز",
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
    selected = st.sidebar.radio("مینو", menu)
    st.sidebar.divider()
    if st.sidebar.button("لاگ آؤٹ", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.user_type = ""
        st.rerun()
    return selected


def main() -> None:
    init_db()
    set_page()
    init_session()
    if not st.session_state.logged_in:
        require_login()

    selection = render_sidebar()
    if st.session_state.user_type == "admin":
        if selection == "ایڈمن ڈیش بورڈ":
            render_admin_dashboard()
        elif selection == "یومیہ تعلیمی رپورٹ":
            render_daily_report()
        elif selection == "نوٹیفکیشنز":
            render_notifications()
        elif selection == "پاسورڈ تبدیل کریں":
            render_password_change()
    else:
        if selection == "روزانہ سبق اندراج":
            render_teacher_lesson_entry()
        elif selection == "امتحانی درخواست":
            render_exam_request()
        elif selection == "رخصت کی درخواست":
            render_leave_request()
        elif selection == "میری حاضری":
            render_my_attendance()
        elif selection == "میرا ٹائم ٹیبل":
            render_timetable()
        elif selection == "نوٹیفکیشنز":
            render_notifications()
        elif selection == "پاسورڈ تبدیل کریں":
            render_password_change()


if __name__ == "__main__":
    main()
