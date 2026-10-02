"""영/한 시집 텍스트 두 개를 읽어 구조화된 poems_<섹션>.json을 만든다.

KO 파일에는 빈 줄이 엉뚱한 자리에 끼어들거나(연이 쪼개짐) 번호 줄이
소문자/한글 표기인 곳이 있다. 그래서 KO의 빈 줄 배치는 신뢰하지 않고,
EN의 연 구조(각 연의 행 수)를 틀로 삼아 KO의 내용 줄을 잘라 맞춘다.

사용법:
    python parse_poems.py 01_life
    python parse_poems.py 02_love
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
NUMERAL_RE = re.compile(r"^[IVXLC]+\.$", re.I)
# 첫 줄: "II. LOVE." / "II. 사랑."
HEADER_RE = re.compile(r"^\s*([IVXLC]+)\.\s*(.+?)\.?\s*$")

ROMAN = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
         (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def to_roman(n: int) -> str:
    out = ""
    for value, sym in ROMAN:
        while n >= value:
            out += sym
            n -= value
    return out


def paths(section: str) -> tuple[Path, Path, Path]:
    en = ROOT / f"emily dickinson_{section}_english.txt"
    ko = ROOT / f"emily dickinson_{section}_korean.txt"
    for p in (en, ko):
        if not p.exists():
            sys.exit(f"파일 없음: {p.name}")
    return en, ko, ROOT / "data" / f"poems_{section}.json"


def split_poems(path: Path) -> tuple[list[str], list[list[str]]]:
    """(머리말 줄, [시별 줄 목록, ...]) — 번호 줄 자체는 제외하고 반환."""
    head: list[str] = []
    poems: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if NUMERAL_RE.match(line.strip()):
            poems.append([])
        elif poems:
            poems[-1].append(line)
        else:
            head.append(line)
    return head, poems


def en_blocks(lines: list[str]) -> list[list[str]]:
    """EN은 빈 줄 배치가 정확하므로 그대로 블록으로 나눈다."""
    out: list[list[str]] = []
    buf: list[str] = []
    for line in lines:
        if line.strip():
            buf.append(line.strip())
        elif buf:
            out.append(buf)
            buf = []
    if buf:
        out.append(buf)
    return out


def content_lines(lines: list[str]) -> list[str]:
    return [l.strip() for l in lines if l.strip()]


def reshape(ko_lines: list[str], shape: list[int]) -> list[list[str]]:
    """KO 내용 줄을 EN의 블록별 행 수(shape)대로 잘라 맞춘다."""
    out: list[list[str]] = []
    pos = 0
    for n in shape:
        out.append(ko_lines[pos:pos + n])
        pos += n
    if pos < len(ko_lines):           # 남는 줄은 마지막 블록에 붙인다
        out[-1].extend(ko_lines[pos:])
    return out


def is_title(block: list[str]) -> bool:
    return len(block) == 1 and len(block[0]) <= 40 and not block[0].startswith("[")


def parse_header(head: list[str], fallback: str) -> tuple[str, str]:
    """머리말 첫 줄에서 (섹션 번호, 섹션 제목)을 뽑는다."""
    lines = content_lines(head)
    if lines and (m := HEADER_RE.match(lines[0])):
        return m.group(1), m.group(2)
    return "", fallback


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("section", help="예: 01_life, 02_love")
    args = ap.parse_args()

    en_path, ko_path, out_path = paths(args.section)
    en_head, en_poems = split_poems(en_path)
    ko_head, ko_poems = split_poems(ko_path)

    if len(en_poems) != len(ko_poems):
        sys.exit(f"시 편수 불일치: EN {len(en_poems)} / KO {len(ko_poems)}")

    sec_num, sec_en = parse_header(en_head, args.section)
    _, sec_ko = parse_header(ko_head, args.section)

    poems: list[dict] = []
    warnings: list[str] = []

    for idx, (en_raw, ko_raw) in enumerate(zip(en_poems, ko_poems)):
        # 번호는 EN 순서대로 다시 매긴다 (KO의 표기 흔들림을 무시).
        numeral = to_roman(idx + 1)
        en_b = en_blocks(en_raw)
        ko_c = content_lines(ko_raw)

        shape = [len(b) for b in en_b]
        if sum(shape) != len(ko_c):
            warnings.append(
                f"{numeral}. 내용 줄 수 불일치: EN {sum(shape)} / KO {len(ko_c)} — 연 구분이 어긋날 수 있음")
        ko_b = reshape(ko_c, shape)

        poem: dict = {"no": idx + 1, "numeral": numeral,
                      "title": None, "note": None, "stanzas": []}

        for k, en_block in enumerate(en_b):
            ko_block = ko_b[k] if k < len(ko_b) else []
            if k == 0 and is_title(en_block):
                poem["title"] = {"en": en_block[0], "ko": ko_block[0] if ko_block else ""}
            elif en_block[0].startswith("["):
                poem["note"] = {"en": " ".join(en_block), "ko": " ".join(ko_block)}
            else:
                poem["stanzas"].append({"en": en_block, "ko": ko_block})

        poems.append(poem)

    prefix = f"{sec_num}. " if sec_num else ""
    data = {
        "meta": {
            "section": args.section,
            "title": {
                "en": f"Poems: Series One — {prefix}{sec_en.title()}",
                "ko": f"시집 제1집 — {prefix}{sec_ko}",
            },
            "author": {"en": "Emily Dickinson", "ko": "에밀리 디킨슨"},
            "source": "Project Gutenberg — Poems by Emily Dickinson, Series One (1890)",
            "rights": "원문 퍼블릭 도메인 (저자 1886년 사망, 초판 1890년)",
            "language": ["en", "ko"],
        },
        "section": {"numeral": sec_num, "en": sec_en, "ko": sec_ko},
        "poems": poems,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[{args.section}] {sec_en} / {sec_ko} — 시 {len(poems)}편 → {out_path.name}")
    print(f"  제목 있는 시 {sum(1 for p in poems if p['title'])}편 / "
          f"주석 {sum(1 for p in poems if p['note'])}편 / "
          f"총 {sum(len(p['stanzas']) for p in poems)}연")
    print(f"  경고 {len(warnings)}건" + (":" if warnings else " — 모든 시가 행 단위로 대응됩니다."))
    for w in warnings:
        print(f"    - {w}")


if __name__ == "__main__":
    main()
