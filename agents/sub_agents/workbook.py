"""WorkbookAgent — 기사 기반으로 워크북 활동지 2세트를 생성한다."""

import json
import logging
import re
from typing import Callable

import anthropic

from config import CLAUDE_MODEL, SYSTEM_PROMPT, LEVEL_CONFIG
from models import ArticleResult, WorkbookSet, Level

logger = logging.getLogger(__name__)


class WorkbookAgent:
    def __init__(
        self,
        client: anthropic.Anthropic,
        log_callback: Callable[[str], None] | None = None,
    ):
        self._client = client
        self._log = log_callback or (lambda msg: logger.info(msg))

    def run(self, article: ArticleResult, level: Level) -> list[WorkbookSet]:
        self._log("[Workbook] 활동지 2세트 생성 시작")
        cfg = LEVEL_CONFIG[level.value]

        vocab_list = ", ".join(article.vocabulary) if article.vocabulary else "N/A"

        prompt = f"""Create TWO complete sets of workbook activities for the article below.
The activities are for {cfg['newspaper']} students (CEFR {cfg['cefr']}, {cfg['target']}).

Key vocabulary from the article: {vocab_list}

Guidelines for EACH set:
1. Vocabulary Activity
   - Use the key vocabulary words listed above
   - Activities must be educational and appropriately challenging
   - Do NOT reuse the same answers or content across Set 1 and Set 2

2. True/False sentences (4 sentences)
   - Based on the article content
   - Mix of true and false (at least 1 of each)
   - No overlap in content or answers between Set 1 and Set 2

3. Comprehension Questions (3 questions)
   - Must require paragraph-length answers (not one-word or one-fact answers)
   - Questions must ask for explanation, comparison, or inference
   - No overlap in questions between Set 1 and Set 2

4. Discussion Questions (3 questions)
   - Open-ended and thought-provoking
   - At least ONE question must ask for a personal opinion or experience
   - No overlap in questions between Set 1 and Set 2

Before finalizing, double-check all activities for flow, consistency, grammar,
and make sure Set 1 and Set 2 do not overlap in answers or content.

Article:
\"\"\"
{article.text}
\"\"\"

Respond in this exact JSON format:
{{
  "workbook_sets": [
    {{
      "set_number": 1,
      "vocabulary_activity": "Full text of the vocabulary activity for Set 1",
      "true_false": [
        {{"sentence": "...", "answer": "True"}},
        {{"sentence": "...", "answer": "False"}},
        {{"sentence": "...", "answer": "True"}},
        {{"sentence": "...", "answer": "False"}}
      ],
      "comprehension_questions": [
        "Question 1 requiring a detailed answer...",
        "Question 2...",
        "Question 3..."
      ],
      "discussion_questions": [
        "Discussion question 1 (personal angle)...",
        "Discussion question 2...",
        "Discussion question 3..."
      ]
    }},
    {{
      "set_number": 2,
      ...
    }}
  ]
}}"""

        data = self._call_claude(prompt)
        sets = [
            WorkbookSet(
                set_number=s.get("set_number", i + 1),
                vocabulary_activity=s.get("vocabulary_activity", ""),
                true_false=s.get("true_false", []),
                comprehension_questions=s.get("comprehension_questions", []),
                discussion_questions=s.get("discussion_questions", []),
            )
            for i, s in enumerate(data.get("workbook_sets", []))
        ]

        self._log(f"[Workbook] 완료 — {len(sets)}세트 생성")
        return sets

    def _call_claude(self, prompt: str) -> dict:
        message = self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=3000,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        return json.loads(raw)
