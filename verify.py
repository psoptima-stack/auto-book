"""만들어진 EPUB/PDF가 정상인지 확인한다.

사용법:
    python verify.py 01_life 02_love
"""
import sys
import zipfile
from pathlib import Path
from xml.dom import minidom

ROOT = Path(__file__).parent


def check_epub(path: Path) -> None:
    z = zipfile.ZipFile(path)
    names = z.namelist()

    first_ok = names[0] == "mimetype"
    stored_ok = z.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
    zip_ok = z.testzip() is None

    bad = []
    xml_count = 0
    for name in names:
        if name.endswith((".xhtml", ".opf", ".xml")):
            xml_count += 1
            try:
                minidom.parseString(z.read(name))
            except Exception as exc:
                bad.append((name, str(exc)[:50]))

    front = [n for n in names if "front-" in n]
    poems = [n for n in names if "poem-" in n]

    print(f"  EPUB {path.stat().st_size:>8,} bytes")
    print(f"    mimetype 선두 {first_ok} · 무압축 {stored_ok} · zip 무결성 {zip_ok}")
    print(f"    XML {xml_count}개 파싱: " + ("오류 없음" if not bad else str(bad)))
    print(f"    앞붙임 {len(front)}개 · 시 문서 {len(poems)}개")


def check_pdf(path: Path) -> None:
    try:
        from pypdf import PdfReader
    except ImportError:
        print("  PDF  (pypdf 미설치 — 쪽수 확인 생략)")
        return

    reader = PdfReader(str(path))
    pages = len(reader.pages)
    second = reader.pages[1].extract_text().strip().splitlines()
    head = next((l.strip() for l in second if l.strip() and not l.strip().isdigit()), "")

    print(f"  PDF  {path.stat().st_size:>8,} bytes · {pages}쪽")
    print(f"    2쪽 머리: {head[:40]!r}")


def main() -> None:
    sections = sys.argv[1:] or ["01_life", "02_love"]
    for section in sections:
        print(f"[{section}]")
        epub = ROOT / "output" / f"dickinson_{section}.epub"
        pdf = ROOT / "output" / f"dickinson_{section}.pdf"
        if epub.exists():
            check_epub(epub)
        if pdf.exists():
            check_pdf(pdf)
        print()


if __name__ == "__main__":
    main()
