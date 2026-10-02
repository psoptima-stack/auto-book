"""구텐베르크 원문에서 소설 본문을 챕터/청크 단위로 쪼갠다."""
import re
from dataclasses import dataclass
from pathlib import Path

BODY_START = 6430   # 'CHAPTER I.' (Volume I 첫 챕터)
BODY_END = 41836    # 'A POSTSCRIPT ...' 직후, 주석(NOTE 1~)·용어집 시작 전

CHAPTER_RE = re.compile(r"^\s*(CHAPTER\s+[IVXLC]+\.?|A POSTSCRIPT WHICH SHOULD HAVE BEEN A PREFACE)\s*$")

# 한 청크의 목표 단어 수. 문단 경계에서만 자르므로 실제로는 이 값을 다소 넘길 수 있다.
CHUNK_WORDS = 1200


@dataclass
class Chunk:
    index: int          # 전체 청크 통번호 (0부터)
    chapter_no: int     # 챕터 순번 (1부터)
    chapter_title: str  # 'CHAPTER I.' 등
    part: int           # 챕터 내 몇 번째 조각인지 (1부터)
    parts: int          # 그 챕터의 총 조각 수
    text: str

    @property
    def is_chapter_head(self) -> bool:
        return self.part == 1


def load_body(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[BODY_START:BODY_END]


def split_chapters(body: list[str]) -> list[tuple[str, str]]:
    """[(제목, 본문), ...] 반환."""
    chapters: list[tuple[str, list[str]]] = []
    for line in body:
        if CHAPTER_RE.match(line):
            chapters.append((line.strip(), []))
        elif chapters:
            chapters[-1][1].append(line)
    return [(title, "\n".join(lines).strip()) for title, lines in chapters]


def split_paragraphs(text: str) -> list[str]:
    """빈 줄 기준으로 문단을 나누고, 각 문단의 줄바꿈은 하나로 합친다."""
    paras = re.split(r"\n\s*\n", text)
    return [" ".join(p.split()) for p in paras if p.strip()]


def chunk_chapter(paragraphs: list[str], target: int = CHUNK_WORDS) -> list[str]:
    """문단 경계를 지키면서 target 단어 내외로 묶는다."""
    chunks: list[str] = []
    buf: list[str] = []
    count = 0
    for para in paragraphs:
        n = len(para.split())
        if buf and count + n > target:
            chunks.append("\n\n".join(buf))
            buf, count = [], 0
        buf.append(para)
        count += n
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


def build_chunks(path: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    idx = 0
    for ch_no, (title, text) in enumerate(split_chapters(load_body(path)), start=1):
        pieces = chunk_chapter(split_paragraphs(text))
        for part, piece in enumerate(pieces, start=1):
            chunks.append(Chunk(idx, ch_no, title, part, len(pieces), piece))
            idx += 1
    return chunks


if __name__ == "__main__":
    chunks = build_chunks(Path(__file__).parent / "data" / "raw" / "pg5998.txt")
    chapters = {c.chapter_no for c in chunks}
    words = sum(len(c.text.split()) for c in chunks)
    print(f"챕터 수: {len(chapters)}")
    print(f"청크 수: {len(chunks)}")
    print(f"본문 단어 수: {words:,}")
    print(f"청크 단어 수: 최소 {min(len(c.text.split()) for c in chunks)} / "
          f"최대 {max(len(c.text.split()) for c in chunks)}")
