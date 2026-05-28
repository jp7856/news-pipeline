"""Agent 1: ContentProducerAgent — NE Times 콘텐츠 제작 파이프라인 코디네이터.

흐름:
  WriterAgent → PlagiarismCheckerAgent → EditorAgent
                                              ↓
                          [병렬] CrosswordAgent + WorkbookAgent
                                              ↓
                                      ContentPackage 반환
"""

import logging
from typing import Callable

import anthropic
import requests
from bs4 import BeautifulSoup

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from models import ContentPackage, Level, Section
from agents.sub_agents import (
    WriterAgent,
    PlagiarismCheckerAgent,
    EditorAgent,
    CrosswordAgent,
    WorkbookAgent,
)

logger = logging.getLogger(__name__)

NETIMES_SAMPLE_URL = "https://www.netimes.co.kr"


class ContentProducerAgent:
    def __init__(self, log_callback: Callable[[str], None] | None = None):
        self._log = log_callback or (lambda msg: logger.info(msg))
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self._reference_format_cache: str = ""

        # 서브에이전트 초기화 (클라이언트 공유)
        self._writer    = WriterAgent(self._client, log_callback=self._log)
        self._plagcheck = PlagiarismCheckerAgent(self._client, log_callback=self._log)
        self._editor    = EditorAgent(self._client, log_callback=self._log)
        self._crossword = CrosswordAgent(self._client, log_callback=self._log)
        self._workbook  = WorkbookAgent(self._client, log_callback=self._log)

    def run(self, topic: str, level: Level, section: Section) -> ContentPackage:
        """
        topic   : 기사 주제 (자유 텍스트) 또는 뉴스 URL
        level   : Level.KINDER / KIDS / JUNIOR / TIMES
        section : Section.SCIENCE / ENVIRONMENT 등
        """
        self._log(f"[Agent1] 콘텐츠 제작 시작 — [{level.value}/{section.value}] {topic[:60]}")

        # NE Times 포맷 참고 (캐시 활용)
        reference = self._get_reference_format()

        # ── Step 1: 기사 작성 ─────────────────────────────────────
        article = self._writer.run(topic, level, section, reference_format=reference)

        # ── Step 2: 표절 검사 ─────────────────────────────────────
        plagiarism_report = self._plagcheck.run(article)

        if not plagiarism_report.passed:
            self._log("[Agent1] 표절 위험 감지 — 기사 재작성 시도")
            revised_topic = (
                f"{topic}\n\n"
                f"[REVISION NOTE] The previous version had plagiarism issues: "
                f"{plagiarism_report.notes}. "
                f"Please rewrite with stronger paraphrasing and structural originality."
            )
            article = self._writer.run(revised_topic, level, section, reference_format=reference)
            plagiarism_report = self._plagcheck.run(article)

        # ── Step 3: 교정 ──────────────────────────────────────────
        editing_suggestions = self._editor.run(article, level)

        # ── Step 4 & 5: 크로스워드 + 워크북 (독립 실행) ──────────
        crossword_sentences = self._crossword.run(article)
        workbook_sets       = self._workbook.run(article, level)

        self._log(
            f"[Agent1] 완료 — "
            f"기사 {article.word_count}단어 / "
            f"표절 {'통과' if plagiarism_report.passed else '경고'} / "
            f"수정제안 {len(editing_suggestions)}건 / "
            f"크로스워드 {len(crossword_sentences)}개 / "
            f"워크북 {len(workbook_sets)}세트"
        )

        return ContentPackage(
            topic=topic,
            level=level,
            section=section,
            article=article,
            plagiarism_report=plagiarism_report,
            editing_suggestions=editing_suggestions,
            crossword_sentences=crossword_sentences,
            workbook_sets=workbook_sets,
        )

    # ------------------------------------------------------------------

    def _get_reference_format(self) -> str:
        """netimes.co.kr에서 샘플 기사 텍스트를 가져온다 (세션 중 1회 캐시)."""
        if self._reference_format_cache:
            return self._reference_format_cache
        try:
            resp = requests.get(
                NETIMES_SAMPLE_URL,
                timeout=8,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            soup = BeautifulSoup(resp.text, "lxml")
            # 기사 본문처럼 보이는 텍스트 추출 (p 태그)
            texts = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 40]
            self._reference_format_cache = "\n".join(texts[:15])
            self._log(f"[Agent1] NE Times 포맷 참고 로드 완료 ({len(texts)}개 단락)")
        except Exception as e:
            self._log(f"[Agent1] NE Times 포맷 로드 실패 (무시하고 계속): {e}")
            self._reference_format_cache = ""
        return self._reference_format_cache
