"""청크 단위로 Claude API를 호출해 웨이벌리 본문을 한국어로 번역한다.

각 청크 결과는 data/ko/ 아래에 개별 저장하므로, 중간에 끊겨도 다시 실행하면
이미 번역된 청크는 건너뛰고 이어서 진행한다.
"""
import argparse
import sys
import time
from pathlib import Path

import anthropic

from structure import build_chunks

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw" / "pg5998.txt"
KO_DIR = ROOT / "data" / "ko"
OUT = ROOT / "output" / "waverley_ko.txt"

MODEL = "claude-opus-5"

SYSTEM = """\
당신은 19세기 영국 소설을 한국어로 옮기는 전문 번역가다.
대상은 월터 스콧의 『웨이벌리(Waverley, 1814)』다.

번역 원칙:
- 의미 단위로 옮긴다. 영어의 수동태·관계절·긴 명사구는 한국어 어순으로 재구성한다.
- 서술문은 '-다'체 평서형으로 통일한다. 대사는 화자의 신분과 관계에 맞는 한국어 화계를 쓴다.
- 번역투("~에 대해서", "~되어진다", "~을 가진다", "~중의 하나이다")를 쓰지 않는다.
- 스콧 특유의 만연체는 한국어에서 읽히도록 적절히 끊되, 문장을 임의로 삭제하거나 요약하지 않는다.
- 스코틀랜드 방언 대사는 표준 한국어로 옮기되, 구어체 어미로 말투의 결을 살린다.
- 인명·지명은 한국어 음차로 적는다(Waverley→웨이벌리, Bradwardine→브래드와딘, Tully-Veolan→털리비올란).
  한 작품 안에서 같은 이름을 다르게 적지 않는다.
- 라틴어·프랑스어 인용구는 원문을 남기고 괄호 안에 한국어 뜻을 덧붙인다.
- 원문의 문단 구분을 그대로 유지한다. 문단을 합치거나 나누지 않는다.

출력 형식:
- 번역문만 출력한다. 설명, 머리말, 주석, 원문 병기를 붙이지 않는다.
- 마크다운 기호로 감싸지 않는다.
"""


def build_client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def translate_chunk(client: anthropic.Anthropic, chunk, glossary: str) -> tuple[str, object]:
    header = f"[{chunk.chapter_title} — {chunk.part}/{chunk.parts}]"
    user = (
        f"{glossary}\n\n"
        f"다음은 『웨이벌리』 {header} 구간의 원문이다. 한국어로 번역하라.\n\n"
        f"---\n{chunk.text}\n---"
    )
    with client.messages.stream(
        model=MODEL,
        max_tokens=32000,
        system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        messages=[{"role": "user", "content": user}],
    ) as stream:
        message = stream.get_final_message()

    if message.stop_reason == "refusal":
        raise RuntimeError(f"모델이 응답을 거부함: {message.stop_details}")
    text = "\n".join(b.text for b in message.content if b.type == "text").strip()
    if not text:
        raise RuntimeError(f"빈 응답 (stop_reason={message.stop_reason})")
    return text, message.usage


GLOSSARY = """\
고정 역어(반드시 이대로 사용):
Waverley 웨이벌리 / Edward Waverley 에드워드 웨이벌리 / Sir Everard 에버라드 경
Baron of Bradwardine 브래드와딘 남작 / Rose Bradwardine 로즈 브래드와딘
Tully-Veolan 털리비올란 / Fergus Mac-Ivor 퍼거스 맥아이버 / Flora Mac-Ivor 플로라 맥아이버
Highlands 하이랜드 / Lowlands 로랜드 / Jacobite 자코바이트 / Chevalier 슈발리에
Baillie Macwheeble 베일리 맥휘블 / Evan Dhu 에번 두 / Callum Beg 캘럼 벡\
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="앞에서부터 N개 청크만 번역 (시험용)")
    ap.add_argument("--assemble-only", action="store_true", help="번역 없이 합치기만")
    args = ap.parse_args()

    chunks = build_chunks(RAW)
    KO_DIR.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    if not args.assemble_only:
        todo = chunks[: args.limit] if args.limit else chunks
        client = build_client()
        in_tok = out_tok = 0
        started = time.time()

        for chunk in todo:
            dest = KO_DIR / f"{chunk.index:04d}.txt"
            if dest.exists():
                continue
            for attempt in range(1, 4):
                try:
                    text, usage = translate_chunk(client, chunk, GLOSSARY)
                    break
                except (anthropic.APIStatusError, anthropic.APIConnectionError, RuntimeError) as e:
                    if attempt == 3:
                        print(f"[{chunk.index:04d}] 3회 실패: {e}", file=sys.stderr)
                        raise
                    wait = 5 * 2 ** (attempt - 1)
                    print(f"[{chunk.index:04d}] 재시도 {attempt}/2 ({e}) — {wait}s 대기", file=sys.stderr)
                    time.sleep(wait)

            dest.write_text(text, encoding="utf-8")
            in_tok += usage.input_tokens + (usage.cache_read_input_tokens or 0)
            out_tok += usage.output_tokens
            done = len(list(KO_DIR.glob("*.txt")))
            cost = in_tok * 5 / 1e6 + out_tok * 25 / 1e6
            elapsed = time.time() - started
            print(f"[{done}/{len(chunks)}] {chunk.chapter_title} {chunk.part}/{chunk.parts} "
                  f"· 누적 ${cost:.2f} · {elapsed/60:.1f}분")

    # 합치기
    missing = [c.index for c in chunks if not (KO_DIR / f"{c.index:04d}.txt").exists()]
    if missing:
        print(f"경고: 미번역 청크 {len(missing)}개 (예: {missing[:5]})", file=sys.stderr)

    parts: list[str] = []
    parts.append("웨이벌리 — 육십 년 전 이야기\n월터 스콧\n\n"
                 "원문: Project Gutenberg eBook #5998 (Waverley; or, 'Tis Sixty Years Since)\n"
                 f"번역: Claude {MODEL}\n\n" + "=" * 60 + "\n")
    for chunk in chunks:
        src = KO_DIR / f"{chunk.index:04d}.txt"
        if not src.exists():
            continue
        if chunk.is_chapter_head:
            parts.append(f"\n\n{'=' * 60}\n{chunk.chapter_title}\n{'=' * 60}\n")
        parts.append(src.read_text(encoding="utf-8"))

    OUT.write_text("\n\n".join(parts), encoding="utf-8")
    size = OUT.stat().st_size
    print(f"\n완료: {OUT} ({size:,} bytes)")


if __name__ == "__main__":
    main()
