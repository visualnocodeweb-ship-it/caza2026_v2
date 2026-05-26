import os
import qrcode
from fpdf import FPDF
import tempfile

def test():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Test PDF", ln=True, align='C')
    out = pdf.output()
    print(type(out))
    with open("test.pdf", "wb") as f:
        f.write(out)
    
if __name__ == "__main__":
    test()
