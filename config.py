import os
from dotenv import load_dotenv

load_dotenv(override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"

GOOGLE_SHEETS_CREDENTIALS_JSON = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON", "credentials.json")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

GOOGLE_CSE_API_KEY = os.getenv("GOOGLE_CSE_API_KEY", "")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "")

MAX_ARTICLES_PER_RUN = int(os.getenv("MAX_ARTICLES_PER_RUN", "10"))

# ------------------------------------------------------------------
# 오케스트레이터 시스템 페르소나 (모든 서브에이전트 공유 — 프롬프트 캐싱)
# ------------------------------------------------------------------
SYSTEM_PROMPT = """You are a writer and editor of an English education for children and teens. \
You work on four weekly newspapers that are catered to different age and level of students \
who are studying English as a foreign language. \
The lowest is called NE Times Kinder and it is for kindergarteners and early elementary school \
students, and the language level is at CEFR level of A1 or lower. \
The next newspaper is called NE Times Kids and it is for elementary school students studying \
at a CEFR level of around A2 or A1-A2. \
The third newspaper is called NE Times Junior and it is for high elementary and low middle school \
students, and the CEFR level is around A2 or A2-B1. \
The highest is NE Times for high schoolers, and the CEFR level is around B1 or B1-B2.

You have worked in this field for about 15 years, making you highly experienced at both writing \
and editing articles, making suitable workbook activities, as well as choosing appropriate topics. \
You see the value in making English articles and content in that they can be helpful to students \
in increasing English skills, expanding knowledge about the world, indirectly experiencing how \
concepts are explained in English, and being exposed to a variety of information and perspectives."""

# ------------------------------------------------------------------
# 레벨별 신문 설정
# ------------------------------------------------------------------
LEVEL_CONFIG: dict[str, dict] = {
    "kinder": {
        "newspaper":        "NE Times Kinder",
        "cefr":             "A1 or lower",
        "target":           "kindergarteners and early elementary school students (ages 5–8)",
        "word_count_range": "80–120",
        "paragraph_count":  "3–4",
    },
    "kids": {
        "newspaper":        "NE Times Kids",
        "cefr":             "A2 / A1-A2",
        "target":           "elementary school students (ages 9–12)",
        "word_count_range": "150–200",
        "paragraph_count":  "4–5",
    },
    "junior": {
        "newspaper":        "NE Times Junior",
        "cefr":             "A2 / A2-B1",
        "target":           "high elementary and low middle school students (ages 11–14)",
        "word_count_range": "200–280",
        "paragraph_count":  "5–6",
    },
    "times": {
        "newspaper":        "NE Times",
        "cefr":             "B1 / B1-B2",
        "target":           "high school students (ages 15–18)",
        "word_count_range": "280–380",
        "paragraph_count":  "6–7",
    },
}

# ------------------------------------------------------------------
# Google Sheets 컬럼 순서
# ------------------------------------------------------------------
SHEET_COLUMNS = [
    "ID", "생성일시", "레벨", "섹션", "토픽",
    "기사본문", "어휘", "출처",
    "표절검사통과", "수정제안수",
    "크로스워드생성수", "워크북세트수", "상태",
]
