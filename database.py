# database.py
import mysql.connector
from config import DB_HOST, DB_USER, DB_PASS, DB_NAME

def get_connection():
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )
    return conn
