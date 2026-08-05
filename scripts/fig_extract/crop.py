"""페이지 일부를 4배율 고해상도로 크롭 저장. usage: crop.py <page> <x0> <y0> <x1> <y1> <out.png> (좌표는 0~1 비율)"""
import sys, os
import fitz

PDF = os.path.join(os.path.dirname(__file__), "..", "논문", "EyesOnTheStreet_Quito_2025", "buildings-15-02590.pdf")
OUT = os.path.dirname(__file__)

page, x0, y0, x1, y1, out = sys.argv[1:7]
doc = fitz.open(PDF)
pg = doc[int(page) - 1]
r = pg.rect
clip = fitz.Rect(r.width * float(x0), r.height * float(y0), r.width * float(x1), r.height * float(y1))
pix = pg.get_pixmap(matrix=fitz.Matrix(4, 4), clip=clip)
dst = os.path.join(OUT, out)
pix.save(dst)
print(dst, pix.width, "x", pix.height)
