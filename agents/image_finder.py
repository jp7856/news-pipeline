"""Agent 3: 이미지 탐색 — Google Custom Search API로 기사 관련 이미지를 찾는다."""

import logging
from typing import Callable

import requests

from config import GOOGLE_CSE_API_KEY, GOOGLE_CSE_ID
from models import Article, ArticleStatus

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.googleapis.com/customsearch/v1"


class ImageFinderAgent:
    def __init__(self, log_callback: Callable[[str], None] | None = None):
        self._log = log_callback or (lambda msg: logger.info(msg))

    def run(self, articles: list[Article]) -> list[Article]:
        """각 기사에 맞는 이미지 URL을 찾아 채운다."""
        self._log(f"[Agent3] 이미지 탐색 시작: {len(articles)}건")
        for article in articles:
            if article.status == ArticleStatus.ERROR:
                continue
            try:
                url = self._find_image(article.title_ko or article.title)
                article.image_url = url or ""
                if url:
                    self._log(f"[Agent3] 이미지 발견: {article.title[:30]}...")
                else:
                    self._log(f"[Agent3] 이미지 없음: {article.title[:30]}...")
                if article.status != ArticleStatus.ERROR:
                    article.status = ArticleStatus.IMAGE_FOUND
            except Exception as e:
                self._log(f"[Agent3] 이미지 오류 ({article.id}): {e}")
        self._log("[Agent3] 이미지 탐색 완료")
        return articles

    # ------------------------------------------------------------------

    def _find_image(self, query: str) -> str | None:
        if not GOOGLE_CSE_API_KEY or not GOOGLE_CSE_ID:
            # API 키 없을 때 빈 문자열 반환 (실패 아님)
            return None

        params = {
            "key": GOOGLE_CSE_API_KEY,
            "cx": GOOGLE_CSE_ID,
            "q": query,
            "searchType": "image",
            "num": 1,
            "safe": "active",
        }
        resp = requests.get(SEARCH_URL, params=params, timeout=10)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if items:
            return items[0].get("link", "")
        return None
