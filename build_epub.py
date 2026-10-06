"""poems_<섹션>.json으로 EPUB 3 전자책을 만든다.

시 한 편당 원문 한 쪽, 번역 한 쪽으로 배치한다.
외부 의존성 없이 표준 라이브러리의 zipfile만 사용한다.

사용법:
    python build_epub.py 01_life
    python build_epub.py 02_love
"""
import argparse
import json
import uuid
import zipfile
from html import escape
from pathlib import Path

import front_matter

ROOT = Path(__file__).parent

# 섹션마다 고정된 식별자를 쓴다 (다시 빌드해도 같은 책으로 인식되도록).
ID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

CSS = """\
@charset "utf-8";
body { margin: 1.2em 1em; line-height: 1.7; font-family: serif; }
h1.book { font-size: 1.7em; text-align: center; margin: 3em 0 0.3em; font-weight: normal; }
h2.section { font-size: 1.1em; text-align: center; color: #555; font-weight: normal;
             letter-spacing: 0.1em; margin: 0 0 4em; }
p.author { text-align: center; font-size: 1.05em; color: #444; margin: 0.5em 0 0; }
p.colophon { text-align: center; font-size: 0.8em; color: #777; margin-top: 5em; }

h3.numeral { text-align: center; font-size: 0.95em; color: #888; font-weight: normal;
             letter-spacing: 0.15em; margin: 0 0 0.2em; }
h4.title { text-align: center; font-size: 1.15em; font-weight: normal;
           margin: 0 0 1.4em; }
p.note { font-size: 0.82em; color: #666; text-align: center; font-style: italic;
         margin: -0.8em 0 1.6em; }

div.stanza { margin: 0 0 1.3em; }
p.line { margin: 0; text-indent: 0; }
p.line.turn { padding-left: 1.4em; }   /* 넘친 행 들여쓰기 */

/* 시 한 편당 원문 한 쪽, 번역 한 쪽 — 문서마다 새 쪽에서 시작한다. */
body { page-break-before: always; break-before: page; }
div.ko p.line { font-family: sans-serif; font-size: 0.97em; }

/* 앞붙임 (저자 소개 등) */
h1.fm-title { font-size: 1.35em; font-weight: normal; text-align: center;
              margin: 2em 0 0.6em; }
p.fm-subtitle { text-align: center; font-size: 0.95em; color: #555;
                margin: 0 0 2.2em; }
p.fm-body { text-indent: 1em; margin: 0 0 0.9em; text-align: justify; }
p.fm-body:first-of-type { text-indent: 0; }
"""


def xhtml(title: str, body: str) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"
      lang="ko" xml:lang="ko">
<head>
  <meta charset="utf-8"/>
  <title>{escape(title)}</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
{body}
</body>
</html>
"""


def render_lines(lines: list[str], lang: str) -> str:
    return "\n".join(
        f'      <p class="line" lang="{lang}">{escape(line)}</p>' for line in lines
    )


def render_side(poem: dict, lang: str) -> str:
    """한 쪽(문서) 분량 — 원문 또는 번역 한쪽만 담는다."""
    parts = [f'  <h3 class="numeral">{escape(poem["numeral"])}.</h3>']

    if poem["title"] and poem["title"][lang]:
        parts.append(f'  <h4 class="title" lang="{lang}">{escape(poem["title"][lang])}</h4>')
    if poem["note"] and poem["note"][lang]:
        parts.append(f'  <p class="note" lang="{lang}">{escape(poem["note"][lang])}</p>')

    parts.append(f'  <div class="{lang}">')
    for stanza in poem["stanzas"]:
        parts.append('    <div class="stanza">')
        parts.append(render_lines(stanza[lang], lang))
        parts.append("    </div>")
    parts.append("  </div>")

    return "\n".join(parts)


def poem_label(poem: dict) -> str:
    if poem["title"] and poem["title"]["ko"]:
        return f'{poem["numeral"]}. {poem["title"]["ko"].rstrip(".")}'
    return f'{poem["numeral"]}.'


def build(section: str) -> None:
    src = ROOT / "data" / f"poems_{section}.json"
    out = ROOT / "output" / f"dickinson_{section}.epub"
    if not src.exists():
        raise SystemExit(f"먼저 parse_poems.py 를 실행하세요: {src.name} 없음")

    book_id = f"urn:uuid:{uuid.uuid5(ID_NAMESPACE, 'dickinson-' + section)}"
    data = json.loads(src.read_text(encoding="utf-8"))
    meta, poems = data["meta"], data["poems"]

    files: dict[str, str] = {"OEBPS/style.css": CSS}

    # 표지
    files["OEBPS/cover.xhtml"] = xhtml(meta["title"]["ko"], f"""\
  <h1 class="book" lang="ko">{escape(meta["title"]["ko"])}</h1>
  <h2 class="section" lang="en">{escape(meta["title"]["en"])}</h2>
  <p class="author" lang="ko">{escape(meta["author"]["ko"])}</p>
  <p class="author" lang="en">{escape(meta["author"]["en"])}</p>
  <p class="colophon">{escape(meta["source"])}<br/>{escape(meta["rights"])}</p>
""")

    # 앞붙임 — 저자 소개 등. 표지 다음, 본문 앞.
    spine = ["cover.xhtml"]
    front = front_matter.load(section)
    for n, fm in enumerate(front, start=1):
        name = f"front-{n:02d}.xhtml"
        body = [f'  <h1 class="fm-title">{escape(fm.title)}</h1>']
        if fm.subtitle:
            body.append(f'  <p class="fm-subtitle">{escape(fm.subtitle)}</p>')
        body += [f'  <p class="fm-body">{escape(par)}</p>' for par in fm.paragraphs]
        files[f"OEBPS/{name}"] = xhtml(fm.title, "\n".join(body))
        spine.append(name)

    # 본문 — 시 한 편당 두 문서(원문 한 쪽, 번역 한 쪽).
    for poem in poems:
        for lang in ("en", "ko"):
            name = f'poem-{poem["no"]:02d}-{lang}.xhtml'
            files[f"OEBPS/{name}"] = xhtml(poem_label(poem), render_side(poem, lang))
            spine.append(name)

    # 목차 — 앞붙임 각 꼭지, 그다음 시마다 한 항목(아래에 원문/번역 두 쪽)
    front_items = "\n".join(
        f'        <li><a href="front-{n:02d}.xhtml">{escape(fm.title)}</a></li>'
        for n, fm in enumerate(front, start=1)
    )
    nav_items = "\n".join(
        f'        <li><a href="poem-{p["no"]:02d}-en.xhtml">{escape(poem_label(p))}</a>\n'
        f'          <ol>\n'
        f'            <li><a href="poem-{p["no"]:02d}-en.xhtml">원문</a></li>\n'
        f'            <li><a href="poem-{p["no"]:02d}-ko.xhtml">번역</a></li>\n'
        f'          </ol>\n'
        f'        </li>'
        for p in poems
    )
    files["OEBPS/nav.xhtml"] = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"
      lang="ko" xml:lang="ko">
<head><meta charset="utf-8"/><title>목차</title>
<link rel="stylesheet" type="text/css" href="style.css"/></head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>목차</h1>
    <ol>
        <li><a href="cover.xhtml">{escape(meta["title"]["ko"])}</a></li>
{front_items}
{nav_items}
    </ol>
  </nav>
</body>
</html>
"""
    spine.insert(1, "nav.xhtml")

    manifest = "\n".join(
        f'    <item id="{Path(n).stem}" href="{Path(n).name}" media-type="application/xhtml+xml"'
        + (' properties="nav"' if n.endswith("nav.xhtml") else "") + "/>"
        for n in files if n.endswith(".xhtml")
    )
    itemrefs = "\n".join(f'    <itemref idref="{Path(n).stem}"/>' for n in spine)

    files["OEBPS/content.opf"] = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id"
         xml:lang="ko">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">{book_id}</dc:identifier>
    <dc:title>{escape(meta["title"]["ko"])}</dc:title>
    <dc:creator>{escape(meta["author"]["ko"])}</dc:creator>
    <!-- 주 언어만 선언한다. dc:language를 여러 개 두면 epubcheck와 일부 서점이
         마지막 값을 대표 언어로 잡아, 한국어 책이 영어로 등록된다.
         원문 영어는 각 요소의 xml:lang="en"으로 표시한다. -->
    <dc:language>ko</dc:language>
    <dc:source>{escape(meta["source"])}</dc:source>
    <dc:rights>{escape(meta["rights"])}</dc:rights>
    <meta property="dcterms:modified">2026-09-11T00:00:00Z</meta>
  </metadata>
  <manifest>
{manifest}
    <item id="css" href="style.css" media-type="text/css"/>
  </manifest>
  <spine>
{itemrefs}
  </spine>
</package>
"""

    files["META-INF/container.xml"] = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w") as z:
        # mimetype은 반드시 첫 항목이고 무압축이어야 한다.
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip",
                   compress_type=zipfile.ZIP_STORED)
        for name, content in files.items():
            z.writestr(name, content, compress_type=zipfile.ZIP_DEFLATED)

    print(f"[{section}] {out.name} ({out.stat().st_size:,} bytes) "
          f"— 시 {len(poems)}편 / 문서 {len(spine)}개")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("section", help="예: 01_life, 02_love")
    build(ap.parse_args().section)
