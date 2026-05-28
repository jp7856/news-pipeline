"""PlagiarismCheckerAgent — 8개 항목 체크리스트로 표절 위험을 검사한다."""

import logging
from typing import Callable

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, SYSTEM_PROMPT
from models import ArticleResult, PlagiarismReport
from agents.sub_agents.utils import parse_json

logger = logging.getLogger(__name__)

CHECKLIST_PROMPT = """Run the following Plagiarism-Risk Checklist on the article below.

{checklist}

Article to check:
\"\"\"
{article}
\"\"\"

Sources used:
{sources}

For each of the 8 categories, mark whether it PASSES or FAILS, and briefly explain why.
Then give an overall verdict.

Respond in this exact JSON format:
{{
  "passed": true or false,
  "checklist": {{
    "1_sentence_paraphrasing": {{"pass": true/false, "note": "..."}},
    "2_vocabulary_independence": {{"pass": true/false, "note": "..."}},
    "3_information_compression": {{"pass": true/false, "note": "..."}},
    "4_structural_originality": {{"pass": true/false, "note": "..."}},
    "5_quotation_safety": {{"pass": true/false, "note": "..."}},
    "6_tone_purpose_shift": {{"pass": true/false, "note": "..."}},
    "7_source_transparency": {{"pass": true/false, "note": "..."}},
    "8_final_safety_check": {{"pass": true/false, "note": "..."}}
  }},
  "notes": "Overall summary and any red flags"
}}"""

CHECKLIST_TEXT = """1. Sentence-Level Paraphrasing
   - No sentence copies the structure of a source sentence
   - No distinctive phrases from the source are reused
   - Verbs, connectors, and sentence order are reworked

2. Vocabulary Independence
   - Key words are factual (names, places), not stylistic
   - Descriptive language is original
   - No "signature expressions" from the source appear unchanged

3. Information Selection & Compression
   - Only essential facts included
   - Long source explanations are summarized
   - Facts are not presented in the same order as the source

4. Structural Originality
   - Paragraph order differs from the source
   - Content follows an educational outline, not a news flow
   - Headings (if any) are original

5. Quotation Safety
   - Quotes are short and necessary
   - Quotes are clearly attributed
   - No long quotes replacing paraphrasing

6. Tone & Purpose Shift
   - Tone is neutral and explanatory
   - Language fits the student's CEFR level
   - Article serves an educational purpose, not news reproduction

7. Source Transparency
   - All factual claims come from verifiable sources
   - Sources are listed clearly
   - No invented details, dates, or quotes

8. Final Safety Check
   - "If I removed the sources, would this still read like my own explanation?"
   - Yes → Safe / No → Revise"""


class PlagiarismCheckerAgent:
    def __init__(
        self,
        client: anthropic.Anthropic,
        log_callback: Callable[[str], None] | None = None,
    ):
        self._client = client
        self._log = log_callback or (lambda msg: logger.info(msg))

    def run(self, article: ArticleResult) -> PlagiarismReport:
        self._log("[Plagiarism] 표절 검사 시작")

        prompt = CHECKLIST_PROMPT.format(
            checklist=CHECKLIST_TEXT,
            article=article.text,
            sources="\n".join(article.sources) if article.sources else "No sources provided",
        )

        data = self._call_claude(prompt)

        passed = data.get("passed", False)
        failed_items = [
            k for k, v in data.get("checklist", {}).items()
            if not v.get("pass", True)
        ]

        if passed:
            self._log(f"[Plagiarism] 통과 ✓")
        else:
            self._log(f"[Plagiarism] 경고 — 실패 항목: {', '.join(failed_items)}")

        return PlagiarismReport(
            passed=passed,
            checklist=data.get("checklist", {}),
            notes=data.get("notes", ""),
        )

    def _call_claude(self, prompt: str) -> dict:
        message = self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1500,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        return parse_json(message.content[0].text)
