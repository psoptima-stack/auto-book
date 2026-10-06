# auto-book

영어 원문 txt와 한국어 번역 txt 한 쌍을 영한 대역 전자책(EPUB + PDF)으로 만드는 파이프라인.
작업 절차와 조판 함정은 `.claude/skills/bilingual-poetry-ebook/SKILL.md`에 있다. 작업 전에 읽는다.

## 실행

```powershell
.\venv\Scripts\Activate.ps1     # 항상 먼저
```

파이프라인 순서 — 섹션 이름(`01_life`, `02_love`, `03_nature`, `04_time_and_eternity`)이 모든 명령의 인자다.

```
fix_numerals → parse_poems → build_epub / build_pdf → verify → preview
```

**`parse_poems.py`가 "경고 0건"이 아니면 빌드하지 않는다.** 연 구분이 어긋난 책이 만들어진다.

`build_*.py` 실행 후에는 `verify.py`가 PostToolUse 훅으로 자동 실행된다(`.claude/settings.json`).

## PowerShell 주의 — 이 함정에 세 번 걸렸다

**`python -c "..."` 에 f-string 중괄호·백슬래시·jq 표현식을 쓰지 않는다.** PowerShell이
`{}`를 해시테이블로, `\`를 이스케이프로 해석해 명령이 깨진다. 증상은 매번 다르다 —
`Unexpected token ':>5'`, `Cannot convert ... to Int32`, `failed to parse jq expression`.

여러 줄 파이썬이 필요하면 **스크립트 파일로 만들어 실행한다.** 우회하려 따옴표를 바꾸지 말 것.

그 밖에:

- `Select-Object -First N`은 파이프를 조기 종료시켜 **종료 코드를 왜곡한다**. 종료 코드를 볼 때는 쓰지 않는다.
- git/java는 stderr로 정상 출력을 낸다. PowerShell이 이를 `NativeCommandError`로 포장하지만 **실패가 아니다.** 결과를 따로 확인한다.
- `gh`는 PATH에 없을 수 있다. `& "C:\Program Files\GitHub CLI\gh.exe"` 로 호출한다.

## 인코딩

콘솔 코드페이지가 cp949라 한글·em-dash 출력에서 `UnicodeEncodeError`가 난다.
`verify.py`·`preview.py`는 stdout을 UTF-8로 재설정하고, `.claude/settings.json`이
`PYTHONIOENCODING=utf-8`을 건다. **새 CLI 스크립트를 만들 때 같은 처리를 넣는다.**

## 원본을 함부로 고치지 않는다

- 번역 txt는 `fix_numerals.py --write`로만 고친다. 직접 편집하지 않는다.
- 번역 내용(오역·표현)은 사용자가 요청하지 않으면 손대지 않는다. 구조 문제만 다룬다.
- `front_matter.py`의 `FIRST_SECTION`은 앞붙임을 실을 권을 정한다. 새 섹션 빌드 시 건드리지 않는다.

## 재생성되는 것

`data/raw/`, `data/poems*.json`, `data/pagemap_*.json`, `output/`, `tools/`, `venv/`는
모두 스크립트로 다시 만들 수 있어 git에서 제외되어 있다. 없다고 당황하지 말고 다시 만든다.

## 에이전트

| 이름 | 용도 |
|---|---|
| `poem-align-check` | 정렬 진단 (읽기 전용) |
| `poem-ebook-build` | 전체 빌드 |
| `poem-visual-check` | 지면을 직접 보고 조판 결함 확인 |

사용자가 요청하지 않으면 에이전트를 띄우지 않는다.
