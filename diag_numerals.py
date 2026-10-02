"""02_love 두 파일의 번호 줄을 훑어 어떤 형태로 어긋나 있는지 진단한다."""
import re
from pathlib import Path

ROOT = Path(__file__).parent
EN = ROOT / "emily dickinson_02_love_english.txt"
KO = ROOT / "emily dickinson_02_love_korean.txt"

STRICT = re.compile(r"^[IVXLC]+\.$")          # EN 기준 정상형
# KO에서 번호 줄일 "가능성이 있는" 짧은 줄을 넓게 잡는다.
LOOSE = re.compile(
    r"^\s*(?:제\s*)?(?:[IVXLCivxlc]+|\d+)\s*(?:장|편|\.|\)|장\.)?\s*\.?\s*$"
)


def scan(path: Path) -> list[tuple[int, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [(i, l.rstrip()) for i, l in enumerate(lines)]


def main() -> None:
    en = scan(EN)
    ko = scan(KO)
    print(f"줄 수  EN {len(en)} / KO {len(ko)}\n")

    en_nums = [(i, l.strip()) for i, l in en if STRICT.match(l.strip())]
    print(f"EN 정상 번호 {len(en_nums)}개")
    print("  ", [n for _, n in en_nums], "\n")

    ko_strict = [(i, l.strip()) for i, l in ko if STRICT.match(l.strip())]
    ko_loose = [(i, l.strip()) for i, l in ko if LOOSE.match(l) and l.strip()]
    print(f"KO 정상형 {len(ko_strict)}개 / 느슨한 매칭 {len(ko_loose)}개")
    print("  느슨한 매칭:", [n for _, n in ko_loose], "\n")

    # EN 번호 줄 위치에 KO는 무엇이 있는지 나란히 본다
    print("EN 번호 위치 대비 KO 같은 줄:")
    print(f"{'줄':>5} | {'EN':<10} | KO")
    print("-" * 40)
    for i, num in en_nums:
        ko_line = ko[i][1].strip() if i < len(ko) else "<파일 끝>"
        mark = "  " if ko_line.upper().rstrip(".") == num.rstrip(".") else "<-"
        print(f"{i:>5} | {num:<10} | {ko_line} {mark}")


if __name__ == "__main__":
    main()
