"""오케스트레이터 — 토픽을 받아 Agent 1(콘텐츠 제작)부터 순차적으로 파이프라인을 실행한다.

사용법:
    orchestrator = Orchestrator()
    result = orchestrator.run(
        topic="Climate change and young activists",
        level=Level.JUNIOR,
        section=Section.ENVIRONMENT,
    )
"""

import logging
import uuid
from datetime import datetime
from typing import Callable

from agents import ContentProducerAgent
from agents.translator import TranslatorAgent
from models import ContentPackage, Level, Section

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, log_callback: Callable[[str], None] | None = None):
        self._log = log_callback or (lambda msg: logger.info(msg))

    def run(
        self,
        topic: str,
        level: Level,
        section: Section,
    ) -> ContentPackage:
        """
        단건 콘텐츠 제작 파이프라인을 실행한다.

        Args:
            topic   : 기사 주제 (자유 텍스트 또는 뉴스 URL)
            level   : Level.KINDER / KIDS / JUNIOR / TIMES
            section : Section.SCIENCE / ENVIRONMENT 등
        """
        run_id = str(uuid.uuid4())[:8]
        start = datetime.now()
        self._log(f"=== Pipeline Start (run_id: {run_id}) ===")
        self._log(f"    Topic   : {topic}")
        self._log(f"    Level   : {level.value}")
        self._log(f"    Section : {section.value}")
        self._log("")

        # ── Agent 1: 콘텐츠 제작 ──────────────────────────────────
        producer = ContentProducerAgent(log_callback=self._log)
        package = producer.run(topic, level, section)

        # ── Agent 2: 한국어 번역 ──────────────────────────────────
        translator = TranslatorAgent(log_callback=self._log)
        package = translator.run(package)

        # ── 결과 요약 ─────────────────────────────────────────────
        duration = (datetime.now() - start).seconds
        self._log("")
        self._log(f"=== Pipeline Complete ({duration}s) ===")
        self._log(f"    Article    : {package.article.word_count} words")
        self._log(f"    Vocabulary : {len(package.article.vocabulary)} words")
        self._log(f"    Sources    : {len(package.article.sources)}")
        self._log(f"    Plagiarism : {'PASS' if package.plagiarism_report.passed else 'WARNING'}")
        self._log(f"    Edits      : {len(package.editing_suggestions)} suggestions")
        self._log(f"    Crossword  : {len(package.crossword_sentences)} pairs")
        self._log(f"    Workbook   : {len(package.workbook_sets)} sets")
        self._log(f"    Korean     : {'완료' if package.article.text_ko else '없음'}")

        return package


def print_result(pkg: ContentPackage) -> None:
    """ContentPackage 결과물을 읽기 좋게 출력한다."""
    import sys, io
    # Windows cp949 인코딩 문제 방지
    if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    sep = "-" * 60

    print(f"\n{'=' * 60}")
    print(f"  NE Times Content Package")
    print(f"  Topic   : {pkg.topic}")
    print(f"  Level   : {pkg.level.value}")
    print(f"  Section : {pkg.section.value}")
    print(f"{'=' * 60}")

    # 기사
    print(f"\n[ARTICLE] ({pkg.article.word_count} words)")
    print(sep)
    print(pkg.article.text)
    print(sep)

    # 어휘
    print(f"\n[VOCABULARY] {len(pkg.article.vocabulary)} words")
    for w in pkg.article.vocabulary:
        print(f"  - {w}")

    # 출처
    print(f"\n[SOURCES] {len(pkg.article.sources)} links")
    for s in pkg.article.sources:
        print(f"  - {s}")

    # 표절 검사
    print(f"\n[PLAGIARISM CHECK] {'PASS' if pkg.plagiarism_report.passed else 'WARNING'}")
    for key, val in pkg.plagiarism_report.checklist.items():
        status = "PASS" if val.get("pass") else "FAIL"
        print(f"  [{status}] {key}: {val.get('note', '')[:80]}")

    # 수정 제안
    print(f"\n[EDITING SUGGESTIONS] {len(pkg.editing_suggestions)} items")
    for i, s in enumerate(pkg.editing_suggestions, 1):
        print(f"  {i}. \"{s.original[:60]}...\"")
        print(f"     -> {s.suggestion[:60]}...")
        print(f"     Reason: {s.reason}")

    # 크로스워드
    print(f"\n[CROSSWORD SENTENCES] {len(pkg.crossword_sentences)} pairs")
    for c in pkg.crossword_sentences:
        print(f"  {c.word} ({c.korean_definition})")
        print(f"    B1   : {c.sentence_b1}")
        print(f"    B1-B2: {c.sentence_b1_b2}")

    # 워크북
    for ws in pkg.workbook_sets:
        print(f"\n[WORKBOOK SET {ws.set_number}]")
        print(f"  Vocab Activity: {ws.vocabulary_activity[:100]}...")
        print(f"  T/F: {len(ws.true_false)} items")
        print(f"  Comprehension: {len(ws.comprehension_questions)} questions")
        print(f"  Discussion: {len(ws.discussion_questions)} questions")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    result = Orchestrator().run(
        topic="Climate change and young activists",
        level=Level.JUNIOR,
        section=Section.ENVIRONMENT,
    )
    print_result(result)
