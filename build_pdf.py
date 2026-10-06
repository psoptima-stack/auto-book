"""poems_<섹션>.json으로 PDF 시집을 만든다.

시 한 편당 원문 한 쪽, 번역 한 쪽. 긴 시는 한 쪽에 담기도록 글자 크기를 줄인다.

사용법:
    python build_pdf.py 01_life
    python build_pdf.py 02_love
"""
import argparse
import json
from html import escape
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak,
                                PageTemplate, Paragraph, Spacer)

import front_matter

ROOT = Path(__file__).parent


class MappedDoc(BaseDocTemplate):
    """각 시가 몇 쪽에 실렸는지 기록하는 문서 템플릿.

    번호 Paragraph에 _key를 달아 두면, 조판이 끝난 직후의 self.page를 받아 적는다.
    시각 확인(preview.py)이 '줄인 시'·'두 쪽에 걸친 시'를 정확히 겨냥하는 데 쓴다.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_map: dict[str, int] = {}

    def afterFlowable(self, flowable) -> None:
        key = getattr(flowable, "_key", None)
        if key and key not in self.page_map:
            self.page_map[key] = self.page

KO_FONTS = [
    (r"C:\Windows\Fonts\batang.ttc", "Batang", 0),      # 명조 계열 — 시집에 어울린다
    (r"C:\Windows\Fonts\malgun.ttf", "MalgunGothic", None),
    (r"C:\Windows\Fonts\gulim.ttc", "Gulim", 0),
]

GRAY = HexColor("#888888")
DARK = HexColor("#333333")


def register_ko_font() -> str:
    for path, name, idx in KO_FONTS:
        if not Path(path).exists():
            continue
        try:
            font = TTFont(name, path, subfontIndex=idx) if idx is not None else TTFont(name, path)
            pdfmetrics.registerFont(font)
            return name
        except Exception:
            continue
    print("경고: 한글 폰트를 찾지 못했습니다. 한글이 깨질 수 있습니다.")
    return "Helvetica"


def build(section: str) -> None:
    src = ROOT / "data" / f"poems_{section}.json"
    out = ROOT / "output" / f"dickinson_{section}.pdf"
    if not src.exists():
        raise SystemExit(f"먼저 parse_poems.py 를 실행하세요: {src.name} 없음")

    data = json.loads(src.read_text(encoding="utf-8"))
    meta, poems = data["meta"], data["poems"]
    ko_font = register_ko_font()

    en_line = ParagraphStyle("en", fontName="Times-Roman", fontSize=10,
                             leading=14.5, leftIndent=6 * mm, firstLineIndent=-3 * mm)
    ko_line = ParagraphStyle("ko", fontName=ko_font, fontSize=9.5,
                             leading=15, leftIndent=6 * mm, firstLineIndent=-3 * mm,
                             textColor=DARK)
    numeral = ParagraphStyle("numeral", fontName="Times-Roman", fontSize=8.5,
                             alignment=TA_CENTER, textColor=GRAY, spaceAfter=1.5 * mm)
    title_en = ParagraphStyle("title_en", fontName="Times-Bold", fontSize=11.5,
                              alignment=TA_CENTER, spaceAfter=4 * mm)
    title_ko = ParagraphStyle("title_ko", fontName=ko_font, fontSize=11,
                              alignment=TA_CENTER, spaceAfter=4 * mm)
    note = ParagraphStyle("note", fontName="Times-Italic", fontSize=8,
                          alignment=TA_CENTER, textColor=GRAY, spaceAfter=4 * mm)
    note_ko = ParagraphStyle("note_ko", fontName=ko_font, fontSize=8,
                             alignment=TA_CENTER, textColor=GRAY, spaceAfter=4 * mm)
    cover_t = ParagraphStyle("cover_t", fontName=ko_font, fontSize=20,
                             leading=28, alignment=TA_CENTER, spaceAfter=3 * mm)
    cover_s = ParagraphStyle("cover_s", fontName="Times-Roman", fontSize=11.5,
                             leading=17, alignment=TA_CENTER, textColor=GRAY)
    cover_a = ParagraphStyle("cover_a", fontName=ko_font, fontSize=11.5,
                             leading=18, alignment=TA_CENTER)
    fm_title = ParagraphStyle("fm_title", fontName=ko_font, fontSize=14,
                              leading=20, alignment=TA_CENTER, spaceAfter=3 * mm)
    fm_subtitle = ParagraphStyle("fm_subtitle", fontName=ko_font, fontSize=9.5,
                                 leading=15, alignment=TA_CENTER, textColor=GRAY,
                                 spaceAfter=9 * mm)
    fm_body = ParagraphStyle("fm_body", fontName=ko_font, fontSize=9.5,
                             leading=16, alignment=TA_JUSTIFY, textColor=DARK,
                             firstLineIndent=4 * mm, spaceAfter=2.5 * mm)

    out.parent.mkdir(parents=True, exist_ok=True)
    doc = MappedDoc(
        str(out), pagesize=A5,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=16 * mm,
        title=meta["title"]["ko"], author=meta["author"]["ko"],
    )

    def footer(canvas, doc_):
        if doc_.page == 1:
            return
        canvas.saveState()
        canvas.setFont("Times-Roman", 8)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(A5[0] / 2, 10 * mm, str(doc_.page))
        canvas.restoreState()

    # 패딩을 0으로 둬야 height_of()의 측정값과 실제 조판 가용 높이가 일치한다.
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=footer)])

    story = [
        Spacer(1, 45 * mm),
        Paragraph(escape(meta["title"]["ko"]), cover_t),
        Paragraph(escape(meta["title"]["en"]), cover_s),
        Spacer(1, 8 * mm),
        Paragraph(escape(meta["author"]["ko"]), cover_a),
        Paragraph(escape(meta["author"]["en"]), cover_s),
        Spacer(1, 30 * mm),
        Paragraph(escape(meta["source"]), cover_s),
        Paragraph(escape(meta["rights"]), cover_s),
        PageBreak(),
    ]

    # 앞붙임 — 저자 소개 등. 표지 다음, 본문 앞. 길면 자연스럽게 다음 쪽으로 흐른다.
    front = front_matter.load(section)
    for fm in front:
        story.append(Paragraph(escape(fm.title), fm_title))
        if fm.subtitle:
            story.append(Paragraph(escape(fm.subtitle), fm_subtitle))
        for par in fm.paragraphs:
            story.append(Paragraph(escape(par), fm_body))
        story.append(PageBreak())

    def page_flowables(poem: dict, lang: str, scale: float) -> list:
        """한 쪽 분량의 플로어블 목록을 주어진 배율로 만든다."""
        base = en_line if lang == "en" else ko_line
        head = Paragraph(f'{escape(poem["numeral"])}.', numeral)
        head._key = f'{poem["numeral"]}:{lang}'   # MappedDoc이 쪽 번호를 기록한다
        out = [head]

        if poem["title"] and poem["title"][lang]:
            out.append(Paragraph(escape(poem["title"][lang]),
                                 title_en if lang == "en" else title_ko))
        if poem["note"] and poem["note"][lang]:
            out.append(Paragraph(escape(poem["note"][lang]),
                                 note if lang == "en" else note_ko))

        style = ParagraphStyle(
            f'{base.name}_{poem["no"]}_{scale:.2f}', parent=base,
            fontSize=base.fontSize * scale, leading=base.leading * scale,
        )
        # 연 단위로 묶는다. 묶지 않으면 두 쪽에 걸친 시에서 연이 중간에 끊겨
        # 한 줄만 다음 쪽에 혼자 남는다(고아 줄). 쪽 경계는 연 사이에만 생겨야 한다.
        for stanza in poem["stanzas"]:
            lines = [Paragraph(escape(line), style) for line in stanza[lang]]
            out.append(KeepTogether(lines))
            out.append(Spacer(1, 3.5 * mm * scale))
        return out

    def height_of(flowables: list) -> float:
        """실제 조판 높이 — 줄바꿈으로 늘어나는 분량까지 반영한다.

        KeepTogether는 캔버스 없이 wrap()을 못 하므로 내부 요소를 직접 잰다.
        """
        total = 0.0
        for f in flowables:
            if isinstance(f, KeepTogether):
                total += height_of(f._content)
                continue
            total += f.wrap(doc.width, doc.height)[1]
            total += getattr(f, "getSpaceBefore", lambda: 0)()
            total += getattr(f, "getSpaceAfter", lambda: 0)()
        return total

    # 시 한 편당 원문 한 쪽 + 번역 한 쪽이 기본.
    # 한 쪽을 넘치면 읽을 수 있는 최소 크기(MIN_SCALE)까지만 줄이고,
    # 그래도 안 들어가면 축소하지 않고 두 쪽에 걸쳐 흐르게 둔다.
    MIN_SCALE = 0.85
    tight: list[str] = []
    spread: list[str] = []

    for poem in poems:
        for lang in ("en", "ko"):
            scale = 1.0
            while True:
                flowables = page_flowables(poem, lang, scale)
                if height_of(flowables) <= doc.height:
                    break
                if scale <= MIN_SCALE:
                    # 줄여도 못 담는 시는 원래 크기로 두 쪽에 나눈다.
                    scale = 1.0
                    flowables = page_flowables(poem, lang, scale)
                    spread.append(f'{poem["numeral"]}({lang})')
                    break
                scale -= 0.02

            if scale < 1.0:
                tight.append(f'{poem["numeral"]}({lang}) {scale:.0%}')

            story.extend(flowables)
            story.append(PageBreak())

    doc.build(story)

    # 쪽 지도 — preview.py가 '줄인 시'·'두 쪽에 걸친 시'를 겨냥하는 데 쓴다.
    scales = {t.split("(")[0] + ":" + t.split("(")[1].split(")")[0]: t.split()[-1]
              for t in tight}
    page_map = ROOT / "data" / f"pagemap_{section}.json"
    page_map.parent.mkdir(parents=True, exist_ok=True)
    page_map.write_text(json.dumps({
        "section": section,
        "pages": doc.page,
        "front_matter": len(front),
        "poems": doc.page_map,                                  # "I:en" -> 쪽 번호
        "shrunk": scales,                                       # "X:en" -> "96%"
        "spread": [s.replace("(", ":").rstrip(")") for s in spread],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    if tight:
        print(f"  글자를 줄여 한 쪽에 맞춘 곳 {len(tight)}개: {', '.join(tight)}")
    if spread:
        print(f"  길어서 두 쪽에 걸친 시 {len(spread)}개: {', '.join(spread)}")
    print(f"[{section}] {out.name} ({out.stat().st_size:,} bytes, {doc.page}쪽) "
          f"— 시 {len(poems)}편")
    print(f"  본문 폰트: Times-Roman(원문) / {ko_font}(번역)")
    print(f"  쪽 지도: {page_map.name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("section", help="예: 01_life, 02_love")
    build(ap.parse_args().section)
