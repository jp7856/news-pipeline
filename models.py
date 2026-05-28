from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any


class ArticleStatus(str, Enum):
    COLLECTED = "수집완료"
    TRANSLATED = "번역완료"
    IMAGE_FOUND = "이미지완료"
    SHEET_SAVED = "시트저장완료"
    APPROVED = "검수통과"
    REJECTED = "검수거부"
    PUBLISHED = "발행완료"
    ERROR = "오류"


class Level(str, Enum):
    KINDER = "kinder"    # 유치~초등저학년
    KIDS = "kids"        # 초등고학년~중등
    JUNIOR = "junior"    # 중등
    TIMES = "times"      # 고등이상


class Section(str, Enum):
    POLITICS      = "정치"
    ECONOMY       = "경제"
    BUSINESS      = "비즈니스"
    SOCIETY       = "사회"
    WORLD         = "세계"
    SCIENCE       = "과학"
    TECHNOLOGY    = "기술"
    ENVIRONMENT   = "환경"
    HEALTH        = "건강"
    SPORTS        = "스포츠"
    EDUCATION     = "교육"
    CULTURE       = "문화"
    ENTERTAINMENT = "엔터테인먼트"
    PEOPLE        = "인물"


@dataclass
class Article:
    id: str
    title: str
    url: str
    source: str
    level: Level
    section: Section
    collected_at: datetime = field(default_factory=datetime.now)

    # 원문 본문 (일부)
    content_en: str = ""

    # Agent 2: 번역
    title_ko: str = ""
    summary_en: str = ""
    summary_ko: str = ""

    # Agent 3: 이미지
    image_url: str = ""

    # Agent 5: 검수
    status: ArticleStatus = ArticleStatus.COLLECTED
    review_notes: str = ""

    # Google Sheets 행 번호 (저장 후 업데이트용)
    sheet_row: Optional[int] = None


# ============================================================
# Agent 1 — 콘텐츠 제작 결과 모델
# ============================================================

@dataclass
class ArticleResult:
    """WriterAgent가 생성한 기사"""
    text: str                          # 완성된 기사 본문
    vocabulary: list[str]              # 추출된 핵심 어휘 5~8개
    sources: list[str]                 # 참고 URL 목록
    word_count: int = 0

    def __post_init__(self):
        if not self.word_count and self.text:
            self.word_count = len(self.text.split())


@dataclass
class EditingSuggestion:
    """EditorAgent의 개별 수정 제안"""
    original: str      # 원문 문장/구절
    suggestion: str    # 수정 제안
    reason: str        # 이유


@dataclass
class CrosswordSentencePair:
    """CrosswordAgent가 생성한 어휘별 문장 쌍"""
    word: str
    korean_definition: str
    sentence_b1: str      # B1 수준, 단어 위치에 ______ (6칸)
    sentence_b1_b2: str   # B1-B2 수준, 단어 위치에 ______


@dataclass
class WorkbookSet:
    """WorkbookAgent가 생성한 활동지 1세트"""
    set_number: int                         # 1 또는 2
    vocabulary_activity: str               # 어휘 활동
    true_false: list[dict]                 # [{"sentence":..., "answer": T/F}]
    comprehension_questions: list[str]     # 서술형 이해 문제
    discussion_questions: list[str]        # 토론 문제 (1개 이상 개인 관점)


@dataclass
class PlagiarismReport:
    """PlagiarismCheckAgent의 검사 결과"""
    passed: bool
    checklist: dict[str, Any]   # 8개 항목별 결과
    notes: str = ""             # 문제 있을 경우 상세 메모


@dataclass
class ContentPackage:
    """Agent 1의 최종 출력물"""
    topic: str
    level: Level
    section: Section
    article: ArticleResult
    plagiarism_report: PlagiarismReport
    editing_suggestions: list[EditingSuggestion]
    crossword_sentences: list[CrosswordSentencePair]
    workbook_sets: list[WorkbookSet]       # 반드시 2세트


# ============================================================
# 파이프라인 실행 모델
# ============================================================

@dataclass
class PipelineRun:
    run_id: str
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    articles: list[Article] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.articles)

    @property
    def published(self) -> int:
        return sum(1 for a in self.articles if a.status == ArticleStatus.PUBLISHED)

    @property
    def failed(self) -> int:
        return sum(1 for a in self.articles if a.status == ArticleStatus.ERROR)
