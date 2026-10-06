"""결과물을 눈으로 확인할 수 있게 이미지와 브라우저용 파일을 준비한다.

검증(verify.py)은 '명세에 맞는가'만 판정한다. 글자가 겹쳤는지, 줄인 시가 읽히는지,
한글 양쪽 정렬에서 공백이 벌어지는지는 지면을 봐야 안다. 이 스크립트가 그 재료를 만든다.

PDF  — PyMuPDF로 쪽을 PNG로 렌더한다 (브라우저 불필요)
EPUB — 리더가 조판하는 형식이라 압축을 풀어 브라우저로 열 수 있게 둔다
       (Playwright MCP로 스크린샷을 찍는다)

사용법:
    python preview.py 01_life                  # 대표 쪽 자동 선정
    python preview.py 01_life --pages 1,3,31   # 쪽 지정
    python preview.py 01_life --all            # 전체 쪽 (많으니 주의)
    python preview.py 01_life --dpi 200        # 해상도 지정
"""
import argparse
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
PREVIEW = ROOT / "output" / "preview"
DEFAULT_DPI = 120


def load_pagemap(section: str) -> dict | None:
    path = ROOT / "data" / f"pagemap_{section}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def pick_pages(pm: dict) -> list[tuple[int, str]]:
    """확인할 가치가 큰 쪽을 고른다. [(쪽번호, 왜 골랐는지), ...]"""
    picks: dict[int, str] = {1: "표지"}

    if pm.get("front_matter"):
        picks[2] = "앞붙임(저자 소개)"

    poems: dict[str, int] = pm.get("poems", {})

    # 첫 시 — 원문/번역 한 쌍이 제대로 마주 보는지
    if first_en := poems.get("I:en"):
        picks.setdefault(first_en, "첫 시 원문")
        picks.setdefault(first_en + 1, "첫 시 번역")

    # 글자를 줄인 쪽 — 가장 많이 줄인 것부터
    shrunk = sorted(pm.get("shrunk", {}).items(),
                    key=lambda kv: int(kv[1].rstrip("%")))
    for key, pct in shrunk[:2]:
        if page := poems.get(key):
            picks.setdefault(page, f"{key} {pct}로 축소")

    # 두 쪽에 걸친 시 — 분할 지점이 어색하지 않은지 두 쪽 다 본다
    for key in pm.get("spread", [])[:2]:
        if page := poems.get(key):
            picks.setdefault(page, f"{key} 두 쪽 중 1")
            picks.setdefault(page + 1, f"{key} 두 쪽 중 2")

    total = pm.get("pages", 0)
    return sorted((p, why) for p, why in picks.items() if 1 <= p <= total)


def render_pdf(section: str, pages: list[tuple[int, str]], dpi: int) -> list[Path]:
    try:
        import pymupdf
    except ImportError:
        print("pymupdf가 없습니다: pip install pymupdf", file=sys.stderr)
        return []

    pdf = ROOT / "output" / f"dickinson_{section}.pdf"
    if not pdf.exists():
        print(f"PDF 없음: {pdf.name}", file=sys.stderr)
        return []

    out_dir = PREVIEW / section
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("p*.png"):
        old.unlink()

    written: list[Path] = []
    with pymupdf.open(pdf) as doc:
        for page_no, why in pages:
            page = doc[page_no - 1]                 # 0-기반
            pix = page.get_pixmap(dpi=dpi)
            dest = out_dir / f"p{page_no:03d}.png"
            pix.save(dest)
            written.append(dest)
            print(f"  {dest.name}  {pix.width}x{pix.height}  — {why}")
    return written


def unpack_epub(section: str) -> Path | None:
    """EPUB을 풀어 브라우저가 열 수 있게 한다."""
    epub = ROOT / "output" / f"dickinson_{section}.epub"
    if not epub.exists():
        print(f"EPUB 없음: {epub.name}", file=sys.stderr)
        return None

    dest = PREVIEW / section / "epub"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(epub) as z:
        z.extractall(dest)
    return dest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("section")
    ap.add_argument("--pages", help="쉼표로 구분한 쪽 번호 (예: 1,3,31)")
    ap.add_argument("--all", action="store_true", help="전체 쪽 렌더")
    ap.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    ap.add_argument("--no-epub", action="store_true", help="EPUB 압축 해제 생략")
    args = ap.parse_args()

    pm = load_pagemap(args.section)
    if pm is None:
        print(f"쪽 지도가 없습니다. 먼저 python build_pdf.py {args.section}", file=sys.stderr)
        sys.exit(1)

    if args.pages:
        pages = [(int(p), "지정") for p in args.pages.split(",") if p.strip()]
    elif args.all:
        pages = [(i, "전체") for i in range(1, pm["pages"] + 1)]
    else:
        pages = pick_pages(pm)

    print(f"[{args.section}] PDF {pm['pages']}쪽 중 {len(pages)}쪽 렌더 ({args.dpi} dpi)")
    written = render_pdf(args.section, pages, args.dpi)

    if not args.no_epub:
        if unpacked := unpack_epub(args.section):
            nav = unpacked / "OEBPS" / "nav.xhtml"
            first = sorted(unpacked.glob("OEBPS/poem-01-*.xhtml"))
            print(f"\nEPUB 압축 해제: {unpacked}")
            print("브라우저로 열 주소 (Playwright MCP에 그대로 넘긴다):")
            for path in [unpacked / "OEBPS" / "cover.xhtml", nav, *first]:
                if path.exists():
                    print(f"  {path.resolve().as_uri()}")

    if written:
        print(f"\n이미지 {len(written)}개: {PREVIEW / args.section}")
        print("이 파일들을 직접 읽어 지면을 확인한다.")


if __name__ == "__main__":
    main()
