"""epubcheck(W3C EPUB 적합성 검사기)를 tools/ 아래에 설치한다.

epubcheck는 EPUB 명세 적합성을 판정하는 공식 도구다 (DAISY Consortium / W3C).
자바 실행 환경이 따로 필요하다 — JDK 17 이상.

사용법:
    python setup_epubcheck.py              # 최신 릴리스
    python setup_epubcheck.py --tag v5.4.0 # 버전 지정
"""
import argparse
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
TOOLS = ROOT / "tools"
API_LATEST = "https://api.github.com/repos/w3c/epubcheck/releases/latest"
API_TAG = "https://api.github.com/repos/w3c/epubcheck/releases/tags/{tag}"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "User-Agent": "auto-book/0.1",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", help="릴리스 태그 (예: v5.4.0). 생략하면 최신")
    args = ap.parse_args()

    if shutil.which("java") is None:
        print("경고: 자바를 찾지 못했습니다. 설치는 진행하지만 실행하려면 JDK 17 이상이 필요합니다.")
        print("      winget install Microsoft.OpenJDK.17\n")

    url = API_TAG.format(tag=args.tag) if args.tag else API_LATEST
    try:
        release = fetch_json(url)
    except Exception as exc:
        sys.exit(f"릴리스 정보를 받지 못했습니다: {exc}")

    tag = release["tag_name"]
    asset = next((a for a in release.get("assets", [])
                  if a["name"].endswith(".zip")), None)
    if asset is None:
        sys.exit(f"{tag} 릴리스에 zip 자산이 없습니다.")

    dest_dir = TOOLS / Path(asset["name"]).stem
    if (dest_dir / "epubcheck.jar").exists():
        print(f"이미 설치되어 있습니다: {dest_dir / 'epubcheck.jar'}")
        return

    TOOLS.mkdir(exist_ok=True)
    zip_path = TOOLS / asset["name"]
    print(f"{tag} 내려받는 중… ({asset['size'] / 1024 / 1024:.1f} MB)")

    req = urllib.request.Request(asset["browser_download_url"],
                                 headers={"User-Agent": "auto-book/0.1"})
    with urllib.request.urlopen(req, timeout=300) as resp, zip_path.open("wb") as f:
        shutil.copyfileobj(resp, f)

    with zipfile.ZipFile(zip_path) as z:
        z.extractall(TOOLS)
    zip_path.unlink()

    jar = dest_dir / "epubcheck.jar"
    if not jar.exists():
        sys.exit(f"설치했지만 jar을 찾지 못했습니다: {dest_dir}")

    print(f"설치 완료: {jar}")
    print("이제 python verify.py 가 명세 적합성 검사까지 수행합니다.")


if __name__ == "__main__":
    main()
