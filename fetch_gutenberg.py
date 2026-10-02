"""구텐베르크 프로젝트에서 텍스트를 내려받아 본문만 추출한다."""
import re
import sys
from pathlib import Path

import requests

RAW_DIR = Path(__file__).parent / "data" / "raw"

START_RE = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.I)
END_RE = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.I)


def fetch(book_id: int) -> str:
    """UTF-8 본문을 받아온다. 미러 경로를 순서대로 시도한다."""
    urls = [
        f"https://www.gutenberg.org/ebooks/{book_id}.txt.utf-8",
        f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt",
        f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=60, headers={"User-Agent": "auto-book/0.1"})
        except requests.RequestException:
            continue
        if r.ok and len(r.text) > 10_000:
            r.encoding = "utf-8"
            print(f"[fetch] {url} ({len(r.text):,} chars)", file=sys.stderr)
            return r.text
    raise RuntimeError(f"본문을 받지 못했습니다: book_id={book_id}")


def strip_boilerplate(text: str) -> str:
    """앞뒤 구텐베르크 라이선스 안내를 제거한다."""
    if m := START_RE.search(text):
        text = text[m.end():]
    if m := END_RE.search(text):
        text = text[: m.start()]
    return text.strip()


def main() -> None:
    book_id = int(sys.argv[1]) if len(sys.argv) > 1 else 5998  # 기본: Waverley
    body = strip_boilerplate(fetch(book_id))

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / f"pg{book_id}.txt"
    out.write_text(body, encoding="utf-8")

    words = len(body.split())
    print(f"저장: {out}")
    print(f"글자 수: {len(body):,} / 단어 수: {words:,} / 줄 수: {body.count(chr(10)) + 1:,}")
    print("-" * 60)
    print("[본문 앞부분 미리보기]")
    print(chr(10).join(body.splitlines()[:40]))


if __name__ == "__main__":
    main()
