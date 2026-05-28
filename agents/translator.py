"""Agent 2: 번역 — Claude API로 기사를 레벨별 한국어로 번역한다.

레벨별 번역 스타일:
  kinder : 유치~초등저학년, 아주 쉬운 단어, 짧은 문장, 섹션도 AI가 분류
  kids   : 초등고학년~중등, 교과서 수준 어휘
  junior : 중등, 표준 뉴스 문체
  times  : 고등이상, 신문 격식체
"""

import json
import logging
import re
from typing import Callable

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from models import Article, ArticleStatus, Level, Section

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 레벨별 번역 지침
# ------------------------------------------------------------------
_LEVEL_STYLE: dict[str, str] = {
    "kinder": (
        "독자: 유치원~초등 저학년 (6~9세)\n"
        "- 아주 쉬운 단어. 한자어·외래어 최소화.\n"
        "- 한 문장은 15단어 이내로 짧게.\n"
        "- 어려운 개념은 '~(이)란 ~이에요' 형식으로 풀어쓰기.\n"
        "- summary_ko: 2문장."
    ),
    "kids": (
        "독자: 초등 고학년~중학교 1학년 (10~13세)\n"
        "- 중학 교과서 수준 어휘.\n"
        "- 전문 용어는 괄호로 간단히 설명.\n"
        "- summary_ko: 3문장."
    ),
    "junior": (
        "독자: 중학생 (13~16세)\n"
        "- 표준 한국어. 뉴스 기사체.\n"
        "- 전문 용어 그대로 사용.\n"
        "- summary_ko: 3문장."
    ),
    "times": (
        "독자: 고등학생 이상 (16세+)\n"
        "- 격식체 한국어. 신문 기사 문체.\n"
        "- 전문 용어·수치 정확히 유지.\n"
        "- summary_ko: 4문장."
    ),
}

# 14개 섹션 목록 (kinder 섹션 분류용)
_SECTIONS = [s.value for s in Section]

# ------------------------------------------------------------------
# 시스템 프롬프트 (공통 부분 — 프롬프트 캐싱 대상)
# ------------------------------------------------------------------
_SYSTEM_PROMPT = (
    "당신은 영어 뉴스를 한국어로 번역하는 전문 에디터입니다.\n"
    "항상 JSON만 출력하고, 마크다운 코드 블록 없이 순수 JSON만 반환하세요.\n"
    "번역은 원문의 사실과 뉘앙스를 정확히 유지해야 합니다."
)


class TranslatorAgent:
    def __init__(self, log_callback: Callable[[str], None] | None = None):
        self._log = log_callback or (lambda msg: logger.info(msg))
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def run(self, articles: list[Article]) -> list[Article]:
        to_translate = [a for a in articles if a.status != ArticleStatus.ERROR]
        self._log(f"[Agent2] 번역 시작: {len(to_translate)}건")

        for article in to_translate:
            try:
                if article.status == ArticleStatus.TRANSLATED:
                    # 한국어 기사 — 요약만 생성
                    self._summarize_korean(article)
                else:
                    self._translate_english(article)
                self._log(f"[Agent2] 완료 [{article.level.value}]: {article.title[:45]}...")
            except Exception as e:
                self._log(f"[Agent2] 오류 ({article.id}): {e}")
                article.status = ArticleStatus.ERROR

        self._log("[Agent2] 번역 완료")
        return articles

    # ------------------------------------------------------------------
    # 영어 → 한국어 번역
    # ------------------------------------------------------------------

    def _translate_english(self, article: Article) -> None:
        level_str = article.level.value
        style = _LEVEL_STYLE.get(level_str, _LEVEL_STYLE["junior"])
        needs_section = (level_str == "kinder")

        content_block = (
            f"\n본문 (일부):\n{article.content_en}" if article.content_en else ""
        )

        section_instruction = ""
        section_output = ""
        if needs_section:
            section_instruction = (
                f"\n\n기사를 읽고 가장 적합한 섹션을 아래 목록에서 하나 선택하세요:\n"
                f"{', '.join(_SECTIONS)}"
            )
            section_output = '\n  "section": "섹션명",'

        prompt = (
            f"[번역 레벨: {level_str}]\n"
            f"{style}\n"
            f"{section_instruction}\n\n"
            f"제목: {article.title}{content_block}\n\n"
            f"아래 JSON 형식으로만 응답하세요:\n"
            f"{{{section_output}\n"
            f'  "title_ko": "한국어 제목",\n'
            f'  "summary_en": "영어 요약",\n'
            f'  "summary_ko": "한국어 요약"\n'
            f"}}"
        )

        data = self._call_claude(prompt)

        article.title_ko   = data.get("title_ko", "")
        article.summary_en = data.get("summary_en", "")
        article.summary_ko = data.get("summary_ko", "")

        # kinder 섹션 재분류
        if needs_section and "section" in data:
            raw_section = data["section"]
            try:
                article.section = Section(raw_section)
            except ValueError:
                pass  # 알 수 없는 값이면 기존 섹션 유지

        article.status = ArticleStatus.TRANSLATED

    # ------------------------------------------------------------------
    # 한국어 기사 요약 (번역 불필요)
    # ------------------------------------------------------------------

    def _summarize_korean(self, article: Article) -> None:
        prompt = (
            f"다음 한국어 뉴스 기사의 제목을 보고 요약을 작성하세요.\n\n"
            f"제목: {article.title_ko}\n"
            f"{('본문: ' + article.content_en) if article.content_en else ''}\n\n"
            f"아래 JSON 형식으로만 응답하세요:\n"
            f'{{\n  "summary_ko": "3문장 한국어 요약"\n}}'
        )
        data = self._call_claude(prompt)
        if not article.summary_ko:
            article.summary_ko = data.get("summary_ko", "")
        article.status = ArticleStatus.TRANSLATED

    # ------------------------------------------------------------------
    # Claude API 호출 (프롬프트 캐싱 적용)
    # ------------------------------------------------------------------

    def _call_claude(self, user_prompt: str) -> dict:
        message = self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = message.content[0].text.strip()
        return self._parse_json(raw)

    @staticmethod
    def _parse_json(raw: str) -> dict:
        # 마크다운 코드 블록 제거
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        # 중괄호 범위 추출
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        return json.loads(raw)
