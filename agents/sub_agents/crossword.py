"""CrosswordAgent — 기사 어휘별로 B1/B1-B2 두 수준의 크로스워드 문장 쌍을 생성한다."""

import logging
from typing import Callable

import anthropic

from config import CLAUDE_MODEL, SYSTEM_PROMPT
from models import ArticleResult, CrosswordSentencePair
from agents.sub_agents.utils import parse_json

logger = logging.getLogger(__name__)


class CrosswordAgent:
    def __init__(
        self,
        client: anthropic.Anthropic,
        log_callback: Callable[[str], None] | None = None,
    ):
        self._client = client
        self._log = log_callback or (lambda msg: logger.info(msg))

    def run(self, article: ArticleResult) -> list[CrosswordSentencePair]:
        self._log(f"[Crossword] 문장 생성 시작 — 어휘 {len(article.vocabulary)}개")

        if not article.vocabulary:
            self._log("[Crossword] 어휘 없음 — 건너뜀")
            return []

        vocab_list = "\n".join(
            f"{i+1}. {word}" for i, word in enumerate(article.vocabulary)
        )

        prompt = f"""For each vocabulary word below, write TWO crossword puzzle sentences.

Rules:
- Replace the vocabulary word with exactly 6 underscores: ______
- One sentence must be at B1 level (clear, moderately complex)
- One sentence must be at B1-B2 level (slightly more complex vocabulary/grammar)
- Each sentence must make the meaning of the word clear from context
- Sentences must be original — not copied from the article
- Also provide the Korean definition for each word
- Before finalizing, double-check each sentence for flow, consistency, and grammar

Vocabulary words:
{vocab_list}

Respond in this exact JSON format:
{{
  "crossword_sentences": [
    {{
      "word": "word1",
      "korean_definition": "한국어 뜻",
      "sentence_b1": "The scientists made a major ______ about the cause of the disease.",
      "sentence_b1_b2": "Despite years of research, the ______ transformed how experts understood the phenomenon."
    }}
  ]
}}"""

        data = self._call_claude(prompt)
        pairs = [
            CrosswordSentencePair(
                word=item.get("word", ""),
                korean_definition=item.get("korean_definition", ""),
                sentence_b1=item.get("sentence_b1", ""),
                sentence_b1_b2=item.get("sentence_b1_b2", ""),
            )
            for item in data.get("crossword_sentences", [])
        ]

        self._log(f"[Crossword] 완료 — {len(pairs)}개 어휘 문장 쌍 생성")
        return pairs

    def _call_claude(self, prompt: str) -> dict:
        message = self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        return parse_json(message.content[0].text)
