"""앞붙임(저자 소개 등) 글을 읽어 온다.

data/front_matter/ 안의 .txt 파일을 파일명 순서대로 읽는다.
파일 하나가 전자책의 한 꼭지가 된다. 형식:

    첫 블록   제목        (예: 저자 소개)
    둘째 블록 부제        (60자 이하일 때만. 아니면 본문으로 취급)
    나머지    본문 문단들  (빈 줄로 구분)

파일명 앞의 숫자는 순서를 정하는 용도이며 출력에는 쓰이지 않는다.

앞붙임은 시리즈 전체에 한 번만 들어간다. FIRST_SECTION으로 지정한 첫 권에만
붙고, 나머지 권에서는 load()가 빈 목록을 돌려준다.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

DIR = Path(__file__).parent / "data" / "front_matter"
SUBTITLE_MAX = 60

# 앞붙임을 실을 권. 시리즈의 첫 권에만 넣고 나머지 권에서는 생략한다.
FIRST_SECTION = "01_life"


@dataclass
class Section:
    title: str
    subtitle: str = ""
    paragraphs: list[str] = field(default_factory=list)


def _blocks(text: str) -> list[str]:
    """빈 줄로 나누고, 각 블록 안의 줄바꿈은 공백 하나로 합친다."""
    out = []
    for block in re.split(r"\n\s*\n", text):
        joined = " ".join(block.split())
        if joined:
            out.append(joined)
    return out


def parse(text: str) -> Section | None:
    blocks = _blocks(text)
    if not blocks:
        return None

    title, rest = blocks[0], blocks[1:]
    subtitle = ""
    if rest and len(rest[0]) <= SUBTITLE_MAX:
        subtitle, rest = rest[0], rest[1:]

    return Section(title=title, subtitle=subtitle, paragraphs=rest)


def load(section: str) -> list[Section]:
    """해당 권의 앞붙임 꼭지들을 파일명 순서대로 반환한다.

    첫 권(FIRST_SECTION)이 아니거나 폴더가 없으면 빈 목록.
    """
    if section != FIRST_SECTION or not DIR.exists():
        return []

    sections = []
    for path in sorted(DIR.glob("*.txt")):
        if parsed := parse(path.read_text(encoding="utf-8")):
            sections.append(parsed)
    return sections


if __name__ == "__main__":
    for name in (FIRST_SECTION, "02_love"):
        items = load(name)
        print(f"[{name}] 앞붙임 {len(items)}개"
              + "".join(f"\n    - {s.title} (문단 {len(s.paragraphs)}개)" for s in items))
