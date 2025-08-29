from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def build_payslip_pdf(emp_name, code, month, year, gross, deductions, net):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, f"Payslip  {month:02d}/{year}")
    c.setFont("Helvetica", 12)
    y = 770
    for k, v in [
        ("Employee", emp_name),
        ("Code", code),
        ("Gross", f"{gross:,.2f}"),
        ("Deductions", f"{deductions:,.2f}"),
        ("Net Pay", f"{net:,.2f}"),
    ]:
        c.drawString(50, y, f"{k}: {v}")
        y -= 20
    c.showPage(); c.save()
    return buf.getvalue()
