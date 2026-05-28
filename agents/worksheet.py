"""Agent 4: 워크시트 저장 — Google Sheets에 기사 데이터를 기록한다."""

import logging
from typing import Callable

import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_SHEETS_CREDENTIALS_JSON, GOOGLE_SHEET_ID, SHEET_COLUMNS
from models import Article, ArticleStatus

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class WorksheetAgent:
    def __init__(self, log_callback: Callable[[str], None] | None = None):
        self._log = log_callback or (lambda msg: logger.info(msg))
        self._sheet = None

    def run(self, articles: list[Article]) -> list[Article]:
        """기사 데이터를 Google Sheets에 저장하고 행 번호를 article에 기록한다."""
        self._log("[Agent4] Google Sheets 저장 시작")
        try:
            sheet = self._get_sheet()
            self._ensure_header(sheet)

            for article in articles:
                if article.status == ArticleStatus.ERROR:
                    continue
                try:
                    row = self._article_to_row(article)
                    result = sheet.append_row(row, value_input_option="USER_ENTERED")
                    # 저장된 행 번호 기록
                    updated_range = result.get("updates", {}).get("updatedRange", "")
                    article.sheet_row = self._parse_row_number(updated_range)
                    article.status = ArticleStatus.SHEET_SAVED
                    self._log(f"[Agent4] 저장 완료: {article.title_ko or article.title}")
                except Exception as e:
                    self._log(f"[Agent4] 저장 오류 ({article.id}): {e}")
                    article.status = ArticleStatus.ERROR
        except Exception as e:
            self._log(f"[Agent4] 시트 연결 오류: {e}")

        self._log("[Agent4] 저장 완료")
        return articles

    def update_status(self, article: Article) -> None:
        """Agent 5 검수 후 시트의 '상태' 컬럼을 업데이트한다."""
        if article.sheet_row is None:
            return
        try:
            sheet = self._get_sheet()
            status_col = SHEET_COLUMNS.index("상태") + 1
            sheet.update_cell(article.sheet_row, status_col, article.status.value)
        except Exception as e:
            self._log(f"[Agent4] 상태 업데이트 오류: {e}")

    # ------------------------------------------------------------------

    def _get_sheet(self) -> gspread.Worksheet:
        if self._sheet is None:
            creds = Credentials.from_service_account_file(
                GOOGLE_SHEETS_CREDENTIALS_JSON, scopes=SCOPES
            )
            gc = gspread.authorize(creds)
            spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)
            self._sheet = spreadsheet.sheet1
        return self._sheet

    def _ensure_header(self, sheet: gspread.Worksheet) -> None:
        first_row = sheet.row_values(1)
        if first_row != SHEET_COLUMNS:
            sheet.insert_row(SHEET_COLUMNS, index=1)

    def _article_to_row(self, article: Article) -> list:
        return [
            article.id,
            article.collected_at.strftime("%Y-%m-%d %H:%M:%S"),
            article.level.value,
            article.section.value,
            article.title,
            article.title_ko,
            article.url,
            article.summary_en,
            article.summary_ko,
            article.image_url,
            article.source,
            article.status.value,
        ]

    @staticmethod
    def _parse_row_number(updated_range: str) -> int | None:
        # 예: "시트1!A5:J5" → 5
        try:
            cell_part = updated_range.split("!")[-1]
            import re
            numbers = re.findall(r"\d+", cell_part)
            return int(numbers[0]) if numbers else None
        except Exception:
            return None
