# main.py
import streamlit as st
from modules import admin, teacher, parents
from database import get_connection

st.set_page_config(page_title="Millia Smart Madrasa System", layout="wide")
st.markdown("<h1 style='text-align:center;color:green;'>🕌 Millia Smart Madrasa System</h1>", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    username = st.text_input("صارف کا نام")
    password = st.text_input("پاسورڈ", type="password")
    if st.button("داخل ہوں"):
        conn = get_connection()
        c = conn.cursor(dictionary=True)
        c.execute("SELECT * FROM teachers WHERE name=%s AND password=%s", (username, password))
        res = c.fetchone()
        if res:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.user_type = "admin" if username=="admin" else "teacher"
            st.experimental_rerun()
        else:
            st.error("❌ غلط معلومات")
else:
    st.success(f"خوش آمدید {st.session_state.username}")
    st.subheader("تجرباتی ورژن")
    st.write("یہ ورژن صرف ٹرائل کے لیے ہے۔ مکمل ورژن میں تمام فیچرز دستیاب ہوں گے۔")
