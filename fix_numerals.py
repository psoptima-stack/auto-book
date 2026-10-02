"""KO 파일의 시 번호 줄을 EN 파일 기준의 로마 숫자로 맞춘다.

EN의 번호 줄 위치를 기준으로 같은 줄 번호의 KO 줄을 교체한다.
본문을 실수로 덮어쓰지 않도록, 교체 대상은 아래 조건을 모두 만족해야 한다.
  - 짧은 줄 (공백 제외 20자 이하)
  - 앞뒤가 빈 줄 (제목 줄의 특징)
조건에 맞지 않으면 건너뛰고 경고한다.

사용법:
    python fix_numerals.py 02_love            # 미리보기
    python fix_numerals.py 02_love --write    # 실제 수정 (.bak 백업 생성)
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
NUMERAL_RE = re.compile(r"^[IVXLC]+\.$")
MAX_LEN = 20


def paths(section: str) -> tuple[Path, Path]:
    en = ROOT / f"emily dickinson_{section}_english.txt"
    ko = ROOT / f"emily dickinson_{section}_korean.txt"
    for p in (en, ko):
        if not p.exists():
            sys.exit(f"파일 없음: {p.name}")
    return en, ko


def is_blank(lines: list[str], i: int) -> bool:
    return i < 0 or i >= len(lines) or not lines[i].strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("section", help="예: 02_love")
    ap.add_argument("--write", action="store_true", help="실제로 파일을 수정한다")
    args = ap.parse_args()

    en_path, ko_path = paths(args.section)
    en = en_path.read_text(encoding="utf-8").splitlines()
    ko = ko_path.read_text(encoding="utf-8").splitlines()

    en_nums = [(i, l.strip()) for i, l in enumerate(en) if NUMERAL_RE.match(l.strip())]
    print(f"EN 번호 {len(en_nums)}개 / EN {len(en)}줄 · KO {len(ko)}줄\n")

    changes: list[tuple[int, str, str]] = []
    skipped: list[tuple[int, str, str]] = []

    for i, numeral in en_nums:
        if i >= len(ko):
            skipped.append((i, numeral, "<KO 파일 끝을 넘음>"))
            continue

        current = ko[i].strip()
        if current == numeral:
            continue

        safe = len(current) <= MAX_LEN and is_blank(ko, i - 1) and is_blank(ko, i + 1)
        if not safe:
            skipped.append((i, numeral, current))
            continue

        changes.append((i, current, numeral))
        ko[i] = numeral

    if changes:
        print(f"수정 대상 {len(changes)}곳:")
        print(f"{'줄':>5} | {'현재':<14} | 변경")
        print("-" * 40)
        for i, old, new in changes:
            print(f"{i:>5} | {old:<14} | {new}")
    else:
        print("수정할 곳이 없습니다.")

    if skipped:
        print(f"\n건너뜀 {len(skipped)}곳 (안전 조건 불충족 — 직접 확인 필요):")
        for i, numeral, current in skipped:
            print(f"  {i:>5} | EN {numeral} | KO {current!r}")

    if not args.write:
        print("\n미리보기입니다. 실제로 고치려면 --write 를 붙이세요.")
        return

    if changes:
        backup = ko_path.with_suffix(".txt.bak")
        shutil.copy2(ko_path, backup)
        ko_path.write_text("\n".join(ko) + "\n", encoding="utf-8")
        print(f"\n수정 완료: {ko_path.name} ({len(changes)}곳)")
        print(f"백업: {backup.name}")


if __name__ == "__main__":
    main()
