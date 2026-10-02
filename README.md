# auto-book

영어 원문과 한국어 번역 텍스트 한 쌍을 **영한 대역 전자책(EPUB + PDF)** 으로 만드는 파이프라인.

에밀리 디킨슨 『시집 제1집』(Poems: Series One, 1890) 네 섹션을 대상으로 만들었습니다.
시 한 편당 원문 한 쪽, 번역 한 쪽으로 배치합니다.

## 요구 환경

- Python 3.11+
- `reportlab` (PDF), `requests` (원문 내려받기), `pypdf` (검증)

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install reportlab requests pypdf
```

PDF의 한글은 Windows 기본 폰트(`batang.ttc` → `malgun.ttf` → `gulim.ttc`)를 찾아 씁니다.
다른 OS에서는 `build_pdf.py`의 `KO_FONTS` 목록을 고쳐야 합니다.

## 입력 파일

```
emily dickinson_<섹션>_english.txt
emily dickinson_<섹션>_korean.txt
```

섹션 이름(`01_life`, `02_love`, …)이 모든 명령의 인자가 됩니다.
원문 첫 줄은 `II. LOVE.` / `II. 사랑.` 형태여야 하며, 여기서 책 제목을 뽑습니다.

## 사용법

```bash
python fix_numerals.py 02_love            # 1. 번호 진단 (미리보기)
python fix_numerals.py 02_love --write    # 2. 적용 (.bak 백업 생성)
python parse_poems.py  02_love            # 3. 파싱 → data/poems_02_love.json
python build_epub.py   02_love            # 4. → output/dickinson_02_love.epub
python build_pdf.py    02_love            # 5. → output/dickinson_02_love.pdf
python verify.py       02_love            # 6. 검증
```

**3번에서 "경고 0건"이 아니면 빌드하지 않습니다.** 연 구분이 어긋난 책이 만들어집니다.

## 구조

```
입력 txt 2개 ─→ [진단·수정] ─→ [파싱] ─→ poems_<섹션>.json ─┬─→ EPUB
                                                          └─→ PDF
data/front_matter/*.txt ──── 앞붙임(첫 권에만) ─────────────┘
```

중간 JSON을 반드시 거칩니다. 번역문을 고칠 때 조판을 다시 건드리지 않아도 되고,
EPUB과 PDF가 같은 원본에서 나와 내용이 어긋나지 않습니다.

## 스크립트

| 파일 | 역할 |
|---|---|
| `fix_numerals.py` | 번역문의 시 번호를 원문 기준 로마 숫자로 교체 |
| `parse_poems.py` | 두 txt → `data/poems_<섹션>.json` |
| `front_matter.py` | 앞붙임(저자 소개) 로더. `FIRST_SECTION`으로 실을 권을 지정 |
| `build_epub.py` | JSON → EPUB 3 (표준 라이브러리 `zipfile`만 사용) |
| `build_pdf.py` | JSON → PDF (A5, reportlab) |
| `verify.py` | 쪽수·문서 수·EPUB 구조 검증 |
| `check_counts.py` | 쪽수 계산식과 실제 빌드 결과 대조 |
| `diag_align.py`, `diag_numerals.py` | 정렬 상태 상세 진단 |
| `fetch_gutenberg.py` | 구텐베르크에서 원문 내려받기 |
| `to_pdf.py` | 일반 텍스트 파일 → PDF (별도 용도) |
| `structure.py`, `translate.py` | 장편 산문 번역 파이프라인 (별도 용도, 미완성) |

## 설계 메모

번역 txt가 기계번역 결과물이면 아래 문제가 거의 항상 나타납니다. **원문을 기준으로 삼습니다.**

- **시 번호 표기가 제멋대로** — 소문자(`v.`), 한글 서수(`열두 번째.`), `제 13 장.`, 아라비아 숫자(`16.`), 로마자 오타가 한 파일 안에 섞입니다. `fix_numerals.py`가 원문의 번호 줄 **위치**를 기준으로 교체하며, 본문을 덮어쓰지 않도록 "20자 이하 + 앞뒤 빈 줄" 조건을 검사합니다.
- **빈 줄이 엉뚱한 자리에 끼어듦** — 연 중간에 빈 줄이 들어가 한 연이 쪼개집니다. 그래서 번역문의 빈 줄 배치를 신뢰하지 않고, 원문의 연 구조(각 연의 행 수)를 틀로 삼아 번역문 내용 줄을 잘라 맞춥니다. 대가로, 번역문을 손으로 고칠 때 **행 수를 원문과 맞춰야** 합니다.

조판에서 걸렸던 두 가지:

- **reportlab `Frame`의 기본 6pt 패딩** — 0으로 두지 않으면 측정한 가용 높이와 실제 조판 높이가 12pt 어긋나, 글자를 줄여도 쪽수가 줄지 않습니다.
- **EPUB `mimetype`** — zip의 첫 항목이고 무압축이어야 리더가 엽니다.

긴 시는 85%까지만 줄여 한 쪽에 맞추고, 그래도 넘치면 축소 없이 두 쪽에 걸치게 둡니다
(`build_pdf.py`의 `MIN_SCALE`). 쪽 넘침은 추정이 아니라 `wrap()`으로 실제 높이를 측정해 판정합니다.

## Claude Code 설정

- `.claude/skills/bilingual-poetry-ebook/` — 전체 작업 절차와 함정을 담은 skill
- `.claude/skills/translate-ko/` — 영한 번역 skill
- `.claude/agents/poem-align-check.md` — 정렬 진단 에이전트 (읽기 전용)
- `.claude/agents/poem-ebook-build.md` — 전체 빌드 에이전트

## 저작권

디킨슨의 원문은 퍼블릭 도메인입니다 (저자 1886년 사망, 초판 1890년, 출처: Project Gutenberg).
한국어 번역문과 저자 소개 글은 이 저장소 소유자의 작업물입니다.
