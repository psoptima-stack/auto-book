"""만들어진 EPUB/PDF를 검증한다.

EPUB은 두 단계로 본다.
  1) 구조 검사 — mimetype 선두·무압축, zip 무결성 (빠르고, 실패 원인이 분명하다)
  2) epubcheck — EPUB 3.4 명세 적합성 (서점 업로드 가능 여부를 가리는 판정)

epubcheck는 자바와 jar이 있어야 돌아간다. 없으면 그 사실을 밝히고 1)만 수행한다.
jar 설치: tools/epubcheck-<버전>/epubcheck.jar  (python setup_epubcheck.py)

사용법:
    python verify.py                       # 기본 네 섹션
    python verify.py 01_life 02_love
    python verify.py --strict 01_life       # 경고도 실패로 간주
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.dom import minidom

# 훅이나 Git Bash에서 돌면 콘솔 코드페이지가 cp949라 한글·em-dash 출력에서 죽는다.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent
SECTIONS = ["01_life", "02_love", "03_nature", "04_time_and_eternity"]


def find_epubcheck() -> Path | None:
    """tools/ 아래에서 epubcheck.jar을 찾는다. 여러 버전이 있으면 가장 최신."""
    candidates = sorted(ROOT.glob("tools/epubcheck-*/epubcheck.jar"), reverse=True)
    return candidates[0] if candidates else None


def have_java() -> bool:
    return shutil.which("java") is not None


# ── 1단계: 구조 검사 ──────────────────────────────────────────────

def check_structure(path: Path) -> tuple[bool, list[str]]:
    problems: list[str] = []
    z = zipfile.ZipFile(path)
    names = z.namelist()

    if names[0] != "mimetype":
        problems.append(f"mimetype이 첫 항목이 아님 (현재: {names[0]})")
    if z.getinfo("mimetype").compress_type != zipfile.ZIP_STORED:
        problems.append("mimetype이 압축되어 있음 (무압축이어야 함)")
    if (bad := z.testzip()) is not None:
        problems.append(f"zip 무결성 오류: {bad}")

    xml_count = 0
    for name in names:
        if name.endswith((".xhtml", ".opf", ".xml")):
            xml_count += 1
            try:
                minidom.parseString(z.read(name))
            except Exception as exc:
                problems.append(f"XML 파싱 실패 {name}: {str(exc)[:60]}")

    front = len([n for n in names if "front-" in n])
    poems = len([n for n in names if "poem-" in n])
    print(f"    구조      XML {xml_count}개 · 앞붙임 {front}개 · 시 문서 {poems}개")
    return not problems, problems


# ── 2단계: epubcheck ─────────────────────────────────────────────

def run_epubcheck(path: Path, jar: Path, strict: bool) -> bool:
    """EPUB 3.4 적합성 검사. 통과하면 True."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.json"
        # 콘솔 출력은 로케일에 따라 깨질 수 있으므로 JSON으로만 받는다.
        proc = subprocess.run(
            ["java", "-Dfile.encoding=UTF-8", "-jar", str(jar),
             str(path), "--json", str(out), "--quiet"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if not out.exists():
            print(f"    epubcheck 실행 실패 (exit {proc.returncode})")
            if proc.stderr:
                print(f"      {proc.stderr.strip()[:200]}")
            return False

        report = json.loads(out.read_text(encoding="utf-8"))

    checker = report.get("checker", {})
    n_fatal = checker.get("nFatal", 0)
    n_error = checker.get("nError", 0)
    n_warn = checker.get("nWarning", 0)
    n_usage = checker.get("nUsage", 0)
    version = checker.get("checkerVersion", "?")

    pub = report.get("publication", {})
    spines = pub.get("nSpines", "?")
    langs = pub.get("language", "?")

    print(f"    epubcheck {version} · 치명적 {n_fatal} / 오류 {n_error} / "
          f"경고 {n_warn} / 정보 {n_usage}")
    print(f"    메타      spine {spines}개 · 언어 {langs} · "
          f"제목 {pub.get('title', '?')!r}")

    # 메시지는 심각한 것부터 보여준다.
    order = {"FATAL": 0, "ERROR": 1, "WARNING": 2, "USAGE": 3, "INFO": 4}
    messages = sorted(report.get("messages", []),
                      key=lambda m: order.get(m.get("severity", "INFO"), 9))
    for msg in messages[:15]:
        sev = msg.get("severity", "?")
        text = " ".join(str(msg.get("message", "")).split())[:110]
        loc = msg.get("locations") or []
        where = ""
        if loc:
            first = loc[0]
            where = f" [{first.get('path', '')}" \
                    f"{':' + str(first['line']) if first.get('line', -1) > 0 else ''}]"
        print(f"      {sev:<8} {text}{where}")
    if len(messages) > 15:
        print(f"      … 그 외 {len(messages) - 15}건")

    failed = n_fatal + n_error
    if strict:
        failed += n_warn
    return failed == 0


# ── PDF ─────────────────────────────────────────────────────────

def check_pdf(path: Path) -> None:
    try:
        from pypdf import PdfReader
    except ImportError:
        print("    PDF       (pypdf 미설치 — 확인 생략)")
        return

    reader = PdfReader(str(path))
    pages = len(reader.pages)
    lines = reader.pages[1].extract_text().strip().splitlines() if pages > 1 else []
    head = next((l.strip() for l in lines if l.strip() and not l.strip().isdigit()), "")
    print(f"    PDF       {path.stat().st_size:,} bytes · {pages}쪽 · 2쪽 머리 {head[:34]!r}")


# ── 본체 ────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sections", nargs="*", default=None)
    ap.add_argument("--strict", action="store_true", help="경고도 실패로 간주")
    args = ap.parse_args()
    sections = args.sections or SECTIONS

    jar = find_epubcheck()
    java_ok = have_java()

    if jar is None:
        print("알림: epubcheck.jar이 없어 명세 적합성 검사를 건너뜁니다.")
        print("      설치: python setup_epubcheck.py\n")
    elif not java_ok:
        print("알림: 자바가 없어 epubcheck를 건너뜁니다. JDK 17 이상을 설치하세요.\n")

    failures: list[str] = []

    for section in sections:
        epub = ROOT / "output" / f"dickinson_{section}.epub"
        pdf = ROOT / "output" / f"dickinson_{section}.pdf"
        # 빌드가 안 된 섹션을 "통과"로 보고하면 관문 역할을 못 한다.
        missing = [p.name for p in (epub, pdf) if not p.exists()]
        if len(missing) == 2:
            print(f"[{section}] 결과물 없음 — 먼저 빌드하세요\n")
            failures.append(f"{section} (결과물 없음)")
            continue
        if missing:
            print(f"[{section}] 일부 결과물 없음: {', '.join(missing)}")
            failures.append(f"{section} (누락: {', '.join(missing)})")

        print(f"[{section}]")
        if epub.exists():
            print(f"    EPUB      {epub.stat().st_size:,} bytes")
            ok, problems = check_structure(epub)
            for p in problems:
                print(f"      구조 문제: {p}")
            if not ok:
                failures.append(f"{section} (구조)")

            if jar and java_ok:
                if not run_epubcheck(epub, jar, args.strict):
                    failures.append(f"{section} (epubcheck)")

        if pdf.exists():
            check_pdf(pdf)
        print()

    if failures:
        print(f"실패 {len(failures)}건: {', '.join(failures)}")
        sys.exit(1)
    print("모든 검사를 통과했습니다.")


if __name__ == "__main__":
    main()
