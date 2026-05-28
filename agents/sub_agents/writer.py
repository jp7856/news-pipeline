"""WriterAgent — 토픽을 받아 레벨에 맞는 NE Times 기사를 작성한다."""

import json
import logging
import re
from typing import Callable

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, SYSTEM_PROMPT, LEVEL_CONFIG
from models import ArticleResult, Level, Section

logger = logging.getLogger(__name__)

# NE Times 포맷 참고 URL
NETIMES_URL = "https://www.netimes.co.kr"


class WriterAgent:
    def __init__(
        self,
        client: anthropic.Anthropic,
        log_callback: Callable[[str], None] | None = None,
    ):
        self._client = client
        self._log = log_callback or (lambda msg: logger.info(msg))

    def run(
        self,
        topic: str,
        level: Level,
        section: Section,
        reference_format: str = "",
    ) -> ArticleResult:
        """
        topic : 기사 주제 또는 뉴스 URL
        level : 신문 레벨 (kinder/kids/junior/times)
        section : 섹션 (과학/환경 등)
        reference_format : netimes.co.kr에서 가져온 포맷 샘플 텍스트
        """
        self._log(f"[Writer] 기사 작성 시작 — [{level.value}] {topic[:50]}")
        cfg = LEVEL_CONFIG[level.value]

        format_hint = (
            f"\n\nFormat reference from NE Times:\n{reference_format[:800]}"
            if reference_format
            else ""
        )

        prompt = f"""You are writing an article for {cfg['newspaper']}.

Topic: {topic}
Section: {section.value}
Target readers: {cfg['target']}
CEFR level: {cfg['cefr']}
Target word count: {cfg['word_count_range']} words (Microsoft Word standard)
Paragraphs: {cfg['paragraph_count']} paragraphs of roughly equal size
{format_hint}

Instructions:
1. Search your knowledge for accurate, up-to-date information on this topic.
2. Write an article suitable for the readers' age and comprehension level.
3. Include relevant vocabulary naturally in the text.
4. Add one or two points that spark curiosity or deeper interest.
5. Include background explanations where needed for younger readers.
6. Write in a tone and style appropriate to {cfg['newspaper']}.
7. At the end, list 3–5 key vocabulary words from the article.
8. Provide 3 or more real source URLs used for the information.

Respond in this exact JSON format:
{{
  "article": "<full article text with paragraphs separated by \\n\\n>",
  "vocabulary": ["word1", "word2", "word3", "word4", "word5"],
  "sources": ["https://...", "https://...", "https://..."]
}}"""

        data = self._call_claude(prompt)

        article_text = data.get("article", "")
        vocabulary = data.get("vocabulary", [])
        sources = data.get("sources", [])

        result = ArticleResult(
            text=article_text,
            vocabulary=vocabulary[:8],
            sources=sources,
        )
        self._log(
            f"[Writer] 완료 — {result.word_count}단어 / "
            f"어휘 {len(result.vocabulary)}개 / 출처 {len(result.sources)}개"
        )
        return result

    def _call_claude(self, prompt: str) -> dict:
        message = self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_json(message.content[0].text)


def _parse_json(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    start, end = raw.find("{"), raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]
    return json.loads(raw)
