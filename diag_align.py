"""영/한 시집 파일의 정렬 상태를 진단한다."""
import re
from pathlib import Path

ROOT = Path(__file__).parent
NUM = re.compile(r"^[IVXLC]+\.$", re.I)  # KO 파일에 소문자 'v.', 'x.'가 섞여 있다

EN_FILE = "emily dickinson_01_life_english.txt"
KO_FILE = "emily dickinson_01_life_korean.txt"


def load(name: str) -> list[str]:
    return (ROOT / name).read_text(encoding="utf-8").splitlines()


def numbers(lines: list[str]) -> list[tuple[int, str]]:
    return [(i, l.strip()) for i, l in enumerate(lines) if NUM.match(l.strip())]


def main() -> None:
    en, ko = load(EN_FILE), load(KO_FILE)
    en_n, ko_n = numbers(en), numbers(ko)

    print(f"줄 수    EN {len(en)} / KO {len(ko)}")
    print(f"시 개수  EN {len(en_n)} / KO {len(ko_n)}")

    same_pos = [a[0] for a in en_n] == [b[0] for b in ko_n]
    same_num = [a[1].upper() for a in en_n] == [b[1].upper() for b in ko_n]
    print(f"번호 줄 위치 일치: {same_pos}")
    print(f"번호 순서 일치(대소문자 무시): {same_num}")

    # 대소문자가 원문과 다른 번호
    odd = [(i, n) for i, n in ko_n if n != n.upper()]
    print(f"\nKO 소문자 번호 {len(odd)}개: {odd}")

    # 시별 본문 줄 수 비교 (제목 줄 제외, 빈 줄 제외)
    print("\n시별 비수(非空) 줄 수 — 차이 나는 것만:")
    bounds = [i for i, _ in en_n] + [len(en)]
    mismatch = 0
    for k in range(len(en_n)):
        s, e = bounds[k], bounds[k + 1]
        en_c = sum(1 for l in en[s:e] if l.strip())
        ko_c = sum(1 for l in ko[s:e] if l.strip())
        if en_c != ko_c:
            mismatch += 1
            print(f"  {en_n[k][1]:>7} (줄 {s:3d}): EN {en_c:2d} / KO {ko_c:2d}")
    if not mismatch:
        print("  없음 — 26편 모두 줄 수가 같습니다.")


if __name__ == "__main__":
    main()
