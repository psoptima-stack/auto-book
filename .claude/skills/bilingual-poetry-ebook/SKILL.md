---
name: bilingual-poetry-ebook
description: 영어 원문 txt와 한국어 번역 txt 한 쌍을 대역 전자책(EPUB + PDF)으로 만든다. 사용자가 "english/korean 파일로 전자책 만들어줘", "시집 EPUB/PDF로 만들어줘", "대역본 만들어줘"라고 하거나, `*_english.txt` / `*_korean.txt` 쌍을 주며 전자책·PDF·EPUB을 요청할 때 사용한다. 번호 정렬이 어긋난 번역 파일을 바로잡는 작업에도 사용한다.
---

# 영한 대역 시집 전자책 만들기

원문 txt와 번역 txt 한 쌍을 받아 **EPUB + PDF 대역본**을 만든다.
시 한 편당 원문 한 쪽, 번역 한 쪽으로 배치한다.

## 파일 규칙

```
emily dickinson_01_life_english.txt
emily dickinson_01_life_korean.txt
                └─ 섹션 이름: 01_life
```

모든 스크립트가 `<저자>_<섹션>_english.txt` / `_korean.txt` 규칙으로 짝을 찾는다.
섹션 이름(`01_life`, `02_love`)이 모든 명령의 인자가 된다.

원문 첫 줄은 `II. LOVE.` / `II. 사랑.` 형태의 섹션 제목이어야 하며, 여기서 책 제목을 뽑는다.

## 전체 흐름

```
_english.txt  ─┐
               ├─→ [1] 진단 → [2] 번호 수정 → [3] 파싱 → poems_<섹션>.json ─┬→ EPUB ─┐
_korean.txt   ─┘                                                          └→ PDF  ─┤
                                                                                   ├→ [5] 검증
data/front_matter/*.txt ──────────────────── 앞붙임 (첫 권에만) ───────────────────┘
```

중간 JSON을 반드시 거친다. 번역문을 고칠 때 조판을 다시 건드리지 않아도 되고,
EPUB과 PDF가 같은 원본에서 나와 내용이 어긋나지 않는다.

## 실행 순서

```powershell
# 0. 가상환경 (없으면 생성)
.\venv\Scripts\Activate.ps1        # 필요 패키지: reportlab

# 1. 정렬 진단 — 번호가 몇 개이고 어디가 어긋나는지 본다
python fix_numerals.py 02_love              # 미리보기 (파일을 고치지 않음)

# 2. 번호 수정 — 문제가 있으면 적용 (.bak 백업 자동 생성)
python fix_numerals.py 02_love --write

# 3. 파싱 — 두 txt를 대응시켜 JSON으로
python parse_poems.py 02_love

# 4. 빌드
python build_epub.py 02_love                # → output/dickinson_02_love.epub
python build_pdf.py  02_love                # → output/dickinson_02_love.pdf

# 5. 검증 — 쪽수·문서 수·EPUB 구조 확인
python verify.py 02_love                    # 여러 섹션을 나열해도 된다
```

**3번에서 "경고 0건"이 나올 때까지 진행하지 않는다.** 경고가 있으면 연 구분이 어긋난 채로 책이 만들어진다.

## 번역 파일에서 반복되는 문제

기계번역 결과물에는 아래 패턴이 거의 항상 나타난다. 원문 파일은 대개 깨끗하므로 **원문을 기준으로 삼는다.**

### 1. 시 번호 표기가 제멋대로

한 파일 안에서도 형태가 섞인다. 실제로 나온 것들:

| 형태 | 예 |
|---|---|
| 소문자 | `i.` `v.` `x.` |
| 한글 서수 | `열두 번째.` |
| 제N장 | `제 13 장.` |
| 아라비아 숫자 | `16.` |
| 로마자 오타 | `XIV.` (실제로는 XXIV) |

`fix_numerals.py`가 원문의 번호 줄 **위치**를 기준으로 같은 줄을 교체한다.
본문을 실수로 덮어쓰지 않도록 두 조건을 검사한다 — 그 줄이 20자 이하로 짧을 것, 앞뒤가 빈 줄일 것.
조건에 걸리면 교체하지 않고 목록으로 보고하므로, 보고된 줄은 직접 확인한다.

### 2. 빈 줄이 엉뚱한 자리에 끼어듦

번역 과정에서 연 중간에 빈 줄 3개가 들어가 한 연이 둘로 쪼개지는 일이 잦다.

그래서 **번역문의 빈 줄 배치는 신뢰하지 않는다.** `parse_poems.py`는 원문의 연 구조(각 연의 행 수)를
틀로 삼아 번역문의 내용 줄을 잘라 맞춘다. 빈 줄이 몇 개 끼어들든 결과가 같다.

대가: 번역문을 손으로 고칠 때 **행 수를 원문과 맞춰야 한다.** 한 행을 늘리거나 줄이면
그 시의 연 구분이 밀린다. 파서가 `내용 줄 수 불일치` 경고를 내므로 빌드 시 확인한다.

### 3. 번역 품질

구조와 별개 문제다. 기계번역 티가 나는 곳(문맥을 놓친 동음이의어, 명령형/서술형 혼동 등)은
작업 전에 사용자에게 알리고, 손댈지 그대로 갈지 확인한다. 임의로 번역을 고치지 않는다.

## 앞붙임 (저자 소개 등)

본문 앞에 들어가는 글. `front_matter.py`가 읽어 두 빌더가 공유한다.

```
data/front_matter/
  10_about_author.txt      ← 저자 소개
  20_translator_note.txt   ← 나중에 추가하면 저자 소개 뒤에 붙는다
```

파일 하나가 한 꼭지가 되고, **파일명 순서대로** 배치된다. 앞의 숫자는 순서용이며 출력에는 쓰이지 않는다.

파일 형식 — 빈 줄로 블록을 구분한다.

```
저자 소개                              ← 첫 블록: 제목
에밀리 디킨슨 (1830–1886)               ← 둘째 블록: 부제 (60자 이하일 때만, 아니면 본문)
본문 문단...                           ← 나머지: 문단들
```

### 시리즈 첫 권에만 넣는다

여러 섹션을 한 시리즈로 낼 때 저자 소개가 권마다 반복되면 안 된다.
`front_matter.py`의 상수로 어느 권에 실을지 정한다.

```python
FIRST_SECTION = "01_life"    # 이 권에만 앞붙임을 싣는다
```

`load(section)`은 섹션 이름을 받아, 첫 권이 아니면 **빈 목록**을 돌려준다.
새 섹션을 빌드할 때 이 값을 건드리지 않는다. 사용자가 앞붙임 위치를 바꿔 달라고 할 때만 수정한다.

### 배치

- **PDF** — 표지 다음, 본문 앞. 제목 가운데 14pt, 부제 회색 9.5pt, 본문 9.5pt 양쪽 정렬 + 첫 줄 들여쓰기. 길면 다음 쪽으로 자연스럽게 흐른다(한 쪽에 맞추려 줄이지 않는다)
- **EPUB** — 별도 문서(`front-01.xhtml`)로 만들어 목차 맨 위에 항목이 들어간다

### 알려진 미비점

앞붙임이 **한국어로만** 들어간다. 본문은 대역인데 앞붙임만 단일 언어라 어긋난다.
영문 소개를 나란히 넣을지는 사용자에게 확인한다.

## 조판 규칙

### PDF (`build_pdf.py`)

- A5, 여백 18mm. 원문 Times-Roman 10pt / 번역 Batang 9.5pt
- 시 한 편당 원문 1쪽 + 번역 1쪽. 표지 1쪽
- **긴 시는 글자를 줄여 한 쪽에 맞추되, `MIN_SCALE`(기본 0.85) 아래로는 줄이지 않는다.**
  그보다 더 줄여야 하는 시는 축소 없이 두 쪽에 걸치게 둔다. 읽을 수 없는 크기로 밀어넣는 것보다 낫다.
- 쪽 넘침은 추정하지 않고 `wrap()`으로 **실제 조판 높이를 측정**해서 판정한다

**함정 — Frame 기본 패딩.** reportlab의 `Frame`은 상하좌우에 6pt 패딩을 넣는다.
이걸 0으로 두지 않으면 측정한 가용 높이와 실제 조판 높이가 12pt 어긋나, 글자를 줄여도 쪽수가 안 줄어든다.

```python
Frame(..., leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
```

**한글 폰트.** `C:\Windows\Fonts\batang.ttc`(명조, 시집에 어울림) → `malgun.ttf` → `gulim.ttc` 순으로 찾는다.
`.ttc`는 `subfontIndex=0`이 필요하다. 폰트를 못 찾으면 한글이 깨지므로 경고를 출력한다.

### EPUB (`build_epub.py`)

표준 라이브러리 `zipfile`만 쓴다. 외부 패키지가 필요 없다.

- 원문과 번역을 **별도 문서로 분리**한다 (`poem-01-en.xhtml`, `poem-01-ko.xhtml`).
  리더마다 쪽 개념이 달라서, 한 문서 안에서 `page-break`만으로는 분리가 보장되지 않는다.
- 목차는 앞붙임 꼭지들이 먼저, 그다음 시마다 한 항목(아래에 원문/번역 하위 항목)
- 섹션별로 고정 UUID를 생성한다. 다시 빌드해도 같은 책으로 인식되고, 다른 섹션은 별개 책이 된다

**필수 — mimetype.** `mimetype` 파일이 zip의 **첫 항목**이고 **무압축**이어야 한다. 어기면 리더가 열지 않는다.

```python
z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip",
           compress_type=zipfile.ZIP_STORED)
```

## 검증

`python verify.py <섹션>...` 이 아래를 한 번에 확인한다. 직접 짜지 말고 이걸 쓴다.

**PDF 쪽수** — `1(표지) + 앞붙임 쪽수 + 편수 × 2`

앞붙임이 없는 권은 `1 + 편수 × 2`. 기대값보다 많으면 두 쪽에 걸친 시가 있다는 뜻이며,
어느 시인지는 빌드 로그에 나온다. 정상 동작이므로 문제로 취급하지 않는다.

**EPUB 문서 수** — `2(표지·목차) + 앞붙임 수 + 편수 × 2`

**EPUB 구조** — 아래를 모두 통과해야 한다.

```python
z = zipfile.ZipFile(path)
z.namelist()[0] == "mimetype"                                    # 첫 항목
z.getinfo("mimetype").compress_type == zipfile.ZIP_STORED        # 무압축
z.testzip() is None                                              # zip 무결성
minidom.parseString(z.read(f))                                   # 모든 xhtml/opf/xml 파싱
```

## 스크립트

프로젝트 루트에 있다.

| 파일 | 역할 |
|---|---|
| `fix_numerals.py` | 번역문 번호 줄을 원문 기준 로마 숫자로 교체 (`--write`로 적용, `.bak` 백업) |
| `parse_poems.py` | 두 txt → `data/poems_<섹션>.json` |
| `front_matter.py` | 앞붙임 로더 — 두 빌더가 공유. `FIRST_SECTION`으로 실을 권을 정한다 |
| `build_epub.py` | JSON + 앞붙임 → `output/dickinson_<섹션>.epub` |
| `build_pdf.py` | JSON + 앞붙임 → `output/dickinson_<섹션>.pdf` |
| `verify.py` | 쪽수·문서 수·EPUB 구조 검증 (섹션 여러 개 나열 가능) |
| `diag_align.py` | (보조) 두 파일 정렬 상태 상세 진단 |
| `to_pdf.py` | (별도) 일반 텍스트 파일 → PDF |

빌드는 네 종류의 입력을 받는다 — 원문 txt, 번역 txt, `data/front_matter/*.txt`, 그리고
`front_matter.py`의 `FIRST_SECTION` 설정. 책이 비어 보이거나 앞붙임이 빠졌으면 이 네 가지를 먼저 확인한다.

## 마무리 보고

다음을 보고한다.

- 만든 파일과 크기, PDF 쪽수 / EPUB 문서 수, 시 편수
- 번호를 고친 곳이 있으면 몇 곳을 어떻게 고쳤는지, 백업 위치
- 글자를 줄인 시, 두 쪽에 걸친 시
- 앞붙임이 들어갔는지 — 여러 권을 빌드했다면 어느 권에 들어갔는지 분명히 밝힌다
- 파싱 경고가 남아 있으면 어느 시인지
- 번역 품질 문제를 발견했으면 그대로 두었다는 사실과 예시 한둘
