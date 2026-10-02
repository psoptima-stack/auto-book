"""skill에 적은 쪽수·문서 수 계산식이 실제 빌드 결과와 맞는지 대조한다.

PDF  기대 쪽수   = 1(표지) + 앞붙임 + 편수 × 2   (+ 두 쪽에 걸친 시)
EPUB 기대 문서수 = 2(표지·목차) + 앞붙임 + 편수 × 2
"""
import json
import zipfile
from pathlib import Path

import front_matter

ROOT = Path(__file__).parent
SECTIONS = ["01_life", "02_love", "03_nature", "04_time_and_eternity"]


def main() -> None:
    header = ("섹션", "편수", "앞붙임", "PDF기대", "PDF실제", "차이", "EPUB기대", "EPUB실제")
    print("{:<22}{:>5}{:>7}{:>9}{:>9}{:>6}{:>10}{:>10}".format(*header))
    print("-" * 78)

    try:
        from pypdf import PdfReader
    except ImportError:
        PdfReader = None

    for section in SECTIONS:
        js = ROOT / "data" / f"poems_{section}.json"
        epub = ROOT / "output" / f"dickinson_{section}.epub"
        pdf = ROOT / "output" / f"dickinson_{section}.pdf"
        if not (js.exists() and epub.exists()):
            continue

        poems = len(json.loads(js.read_text(encoding="utf-8"))["poems"])
        fm = len(front_matter.load(section))

        pdf_expected = 1 + fm + poems * 2
        pdf_actual = len(PdfReader(str(pdf)).pages) if (PdfReader and pdf.exists()) else 0

        epub_expected = 2 + fm + poems * 2
        names = zipfile.ZipFile(epub).namelist()
        epub_actual = len([n for n in names if n.endswith(".xhtml")])

        diff = pdf_actual - pdf_expected
        print("{:<22}{:>5}{:>7}{:>9}{:>9}{:>+6}{:>10}{:>10}".format(
            section, poems, fm, pdf_expected, pdf_actual, diff,
            epub_expected, epub_actual))

    print("\nPDF 차이는 두 쪽에 걸친 시의 개수여야 한다 (빌드 로그와 대조).")
    print("EPUB 기대/실제는 반드시 같아야 한다.")


if __name__ == "__main__":
    main()
