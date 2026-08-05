"""후보 페이지를 2.2배율로 렌더링해 PNG 저장 → Read 도구로 Figure/Table 위치 확인용."""
import sys, os
import fitz

PDF = os.path.join(os.path.dirname(__file__), "..", "논문", "EyesOnTheStreet_Quito_2025", "buildings-15-02590.pdf")
OUT = os.path.dirname(__file__)

pages = [int(x) for x in sys.argv[1:]] or [2, 4, 5, 7]
doc = fitz.open(PDF)
for p in pages:
    pix = doc[p - 1].get_pixmap(matrix=fitz.Matrix(2.2, 2.2))
    dst = os.path.join(OUT, f"page{p:02d}.png")
    pix.save(dst)
    print(dst, pix.width, "x", pix.height)
