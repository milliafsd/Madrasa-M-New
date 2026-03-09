# reports/pdf_generator.py
from reportlab.pdfgen import canvas

def generate_pdf(filename="report.pdf"):
    c = canvas.Canvas(filename)
    c.drawString(100, 750, "Millia Smart Madrasa System - Trial PDF")
    c.save()
    return filename
