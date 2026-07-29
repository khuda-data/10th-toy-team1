"""크롭한 그림/표 PNG를 base64로 해설 HTML에 일괄 삽입.

(파일명, 영문 캡션, 한국어 캡션, 앵커 문자열, 폭%) 리스트를 순회하며
앵커가 포함된 feature-card가 끝나는 지점(다음 카드/헤딩 직전)에 fig-block을 넣는다.
여러 번 실행해도 중복 삽입되지 않도록 이미 삽입된 파일은 건너뛴다.
"""
import base64, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "..", "논문", "EyesOnTheStreet_Quito_2025", "[해설] buildings-15-02590.html")

FIGS = [
    ("fig1.png",
     "Figure 1: Conceptual framework.",
     "그림 1. 개념틀. 중앙에 “eyes on the street ↔ street crime”, 이를 매개하는 두 이론(자연적 감시 / 일상활동이론)이 놓이고, 바깥 고리에 밀도·토지이용혼합·접촉기회·접근성 4개 차원과 각 차원의 후보 지표가 배치돼 있다. 이 중 실제 회귀 모형에 투입된 지표는 9개다.",
     "operationalized through measurable morphological indicators",
     100),
    ("fig2.png",
     "Figure 2: Map of the 32 urban parishes of Quito, Ecuador.",
     "그림 2. 에콰도르 키토의 32개 도시 교구 지도. 왼쪽은 에콰도르 전국에서 키토의 위치, 오른쪽은 남북으로 길게 뻗은 키토 도시지역과 교구 경계다.",
     "divided into 32 urban parishes",
     100),
    ("tab1.png",
     "Table 1: Description and calculation of morphological variables.",
     "표 1. 형태 변수의 정의와 계산식. 4개 차원 × 9개 지표가 “차원 / 지표 설명 / 계산식”의 3열로 정리돼 있다. 본문 열거에서 빠진 2C(상업·시설 혼합)가 이 표에는 포함돼 있다.",
     "The indicators were calculated within raster cells measuring",
     100),
    ("tab2.png",
     "Table 2: Binary logistic regression model.",
     "표 2. 이진 로지스틱 회귀 결과. 왼쪽이 모형 계수, 오른쪽이 한계효과(dy/dx)이며 괄호 안은 z값이다. 별표는 유의수준 표기로 보이나 <b>원문에 범례가 실려 있지 않다</b>(관례상 *** p&lt;0.01, ** p&lt;0.05). 관측치 “11.046”은 유럽식 천 단위 표기로 11,046개를 뜻한다.",
     "The marginal effects derived from the logistic probability regression model",
     100),
]

BOUNDARIES = ('<div class="feature-card">', '<h2', '<h3', '<div class="agentnotif-section">')


def main():
    html = open(HTML, encoding="utf-8").read()
    inserted = 0
    for fname, en_cap, ko_cap, anchor, width in FIGS:
        marker = f'alt="{fname}"'
        if marker in html:
            print(f"skip (already inserted): {fname}")
            continue
        pos = html.find(anchor)
        if pos == -1:
            print(f"!! anchor not found for {fname}: {anchor[:40]}")
            continue
        # 앵커가 속한 카드가 끝나는 지점 = 다음 카드/헤딩이 시작하는 위치
        nxt = min((p for p in (html.find(b, pos) for b in BOUNDARIES) if p != -1), default=-1)
        if nxt == -1:
            print(f"!! boundary not found for {fname}")
            continue
        b64 = base64.b64encode(open(os.path.join(HERE, fname), "rb").read()).decode("ascii")
        block = (
            f'  <div class="fig-block"><img src="data:image/png;base64,{b64}" '
            f'style="width:{width}%;max-width:100%;border:1px solid var(--hairline);border-radius:var(--r-lg);" '
            f'alt="{fname}">\n'
            f'  <div class="fig-caption"><b>{en_cap}</b><br>{ko_cap}</div></div>\n\n'
        )
        html = html[:nxt] + block + html[nxt:]
        inserted += 1
        print(f"inserted {fname} at {nxt} ({len(b64)//1024} KB base64)")

    open(HTML, "w", encoding="utf-8").write(html)
    print(f"done: {inserted} figure(s) inserted, file size {len(html)//1024} KB")


if __name__ == "__main__":
    sys.exit(main())
