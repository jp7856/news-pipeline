"""Agent 5: 최종 검수 — Claude API로 기사 품질을 검토하고 발행 여부를 결정한다."""

import json
import logging
from typing import Callable

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from models import Article, ArticleStatus

logger = logging.getLogger(__name__)


class ReviewerAgent:
    def __init__(self, log_callback: Callable[[str], None] | None = None):
        self._log = log_callback or (lambda msg: logger.info(msg))
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def run(self, articles: list[Article]) -> list[Article]:
        """각 기사를 검수하고 통과한 기사만 PUBLISHED 상태로 변경한다."""
        self._log(f"[Agent5] 검수 시작: {len(articles)}건")
        for article in articles:
            if article.status not in (ArticleStatus.SHEET_SAVED, ArticleStatus.IMAGE_FOUND):
                continue
            try:
                passed, notes = self._review(article)
                article.review_notes = notes
                if passed:
                    article.status = ArticleStatus.PUBLISHED
                    self._log(f"[Agent5] 승인: {article.title_ko or article.title}")
                else:
                    article.status = ArticleStatus.REJECTED
                    self._log(f"[Agent5] 거부 ({notes}): {article.title_ko or article.title}")
            except Exception as e:
                self._log(f"[Agent5] 검수 오류 ({article.id}): {e}")
                article.status = ArticleStatus.ERROR
        self._log("[Agent5] 검수 완료")
        return articles

    # ------------------------------------------------------------------

    def _review(self, article: Article) -> tuple[bool, str]:
        prompt = f"""아래 뉴스 기사 데이터를 검수해주세요.

원문 제목: {article.title}
한국어 제목: {article.title_ko}
한국어 요약: {article.summary_ko}
이미지 URL: {article.image_url or "없음"}

다음 기준으로 평가하세요:
1. 한국어 번역이 자연스럽고 정확한가?
2. 요약이 충분히 informative한가? (3문장 이상)
3. 스팸/광고/부적절한 내용이 없는가?

아래 JSON 형식으로만 응답하세요:
{{
  "approved": true 또는 false,
  "reason": "간단한 판단 이유"
}}"""

        message = self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()

        data = json.loads(raw)
        return data.get("approved", False), data.get("reason", "")
