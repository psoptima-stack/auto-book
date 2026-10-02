"""텍스트 파일을 읽기 좋은 PDF로 변환한다.

사용법:
    python to_pdf.py data/raw/pg5998.txt
    python to_pdf.py data/raw/pg5998.txt -o output/waverley.pdf --title "Waverley"
"""
import argparse
import re
from html import escape
from pathlib import Path

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer

ROOT = Path(__file__).parent

HEADING_RE = re.compile(
    r"^\s*(CHAPTER\s+[IVXLC]+\.?|VOLUME\s+[IVX]+\.?|NOTE\s+\d+|GLOSSARY|"
    r"A POSTSCRIPT WHICH SHOULD HAVE BEEN A PREFACE)\s*$",
    re.I,
)

# 한글이 섞여 있을 수 있으므로(번역본 PDF에도 같은 스크립트를 쓴다) 한글 지원 폰트를 먼저 찾는다.
KO_FONT_CANDIDATES = [
    (r"C:\Windows\Fonts\malgun.ttf", "MalgunGothic"),
    (r"C:\Windows\Fonts\batang.ttc", "Batang"),
    (r"C:\Windows\Fonts\gulim.ttc", "Gulim"),
]


def pick_font(text: str) -> tuple[str, str]:
    """(본문 폰트, 제목 폰트) 반환. 한글이 있으면 한글 폰트를 등록해 쓴다."""
    if not re.search(r"[\uac00-\ud7a3]", text):
        return "Times-Roman", "Helvetica-Bold"

    for path, name in KO_FONT_CANDIDATES:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name, name
            except Exception:
                continue
    print("경고: 한글 폰트를 찾지 못해 기본 폰트로 진행합니다(한글이 깨질 수 있음).")
    return "Times-Roman", "Helvetica-Bold"


def split_paragraphs(text: str) -> list[tuple[str, str]]:
    """[('heading'|'body', 내용), ...] 반환."""
    out: list[tuple[str, str]] = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        if "\n" not in block and HEADING_RE.match(block):
            out.append(("heading", " ".join(block.split())))
        else:
            out.append(("body", " ".join(block.split())))
    return out


def build(src: Path, dest: Path, title: str) -> None:
    text = src.read_text(encoding="utf-8")
    body_font, head_font = pick_font(text)

    body = ParagraphStyle(
        "body", fontName=body_font, fontSize=10.5, leading=15.5,
        alignment=TA_JUSTIFY, firstLineIndent=5 * mm, spaceAfter=2,
    )
    heading = ParagraphStyle(
        "heading", fontName=head_font, fontSize=14, leading=20,
        alignment=TA_CENTER, spaceBefore=10 * mm, spaceAfter=6 * mm,
    )
    cover_title = ParagraphStyle(
        "cover", fontName=head_font, fontSize=26, leading=34,
        alignment=TA_CENTER, spaceAfter=8 * mm,
    )
    cover_sub = ParagraphStyle(
        "sub", fontName=body_font, fontSize=12, leading=18, alignment=TA_CENTER,
    )

    dest.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(dest), pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm,
        topMargin=22 * mm, bottomMargin=20 * mm,
        title=title, author="Sir Walter Scott",
    )

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont(body_font, 8.5)
        canvas.drawCentredString(A4[0] / 2, 12 * mm, str(doc_.page))
        canvas.restoreState()

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=footer)])

    story = [
        Spacer(1, 60 * mm),
        Paragraph(escape(title), cover_title),
        Paragraph("Sir Walter Scott", cover_sub),
        Spacer(1, 6 * mm),
        Paragraph(f"source: {escape(src.name)} &mdash; Project Gutenberg", cover_sub),
        PageBreak(),
    ]
    for kind, content in split_paragraphs(text):
        story.append(Paragraph(escape(content), heading if kind == "heading" else body))

    print(f"문단 {len(story) - 6:,}개 조판 중...")
    doc.build(story)
    print(f"완료: {dest} ({dest.stat().st_size:,} bytes, {doc.page}쪽)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--title", default="Waverley; or, 'Tis Sixty Years Since")
    args = ap.parse_args()

    dest = args.out or ROOT / "output" / (args.src.stem + ".pdf")
    build(args.src, dest, args.title)


if __name__ == "__main__":
    main()
