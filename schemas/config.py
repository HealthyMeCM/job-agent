"""Configuration file schemas."""

from pydantic import Field

from .base import BaseSchema


# --- Seed Companies Config ---


class SeedCompanyEntry(BaseSchema):
    """Single seed company entry."""

    name: str
    reason: str | None = None
    notes: str | None = None


class SeedCompaniesConfig(BaseSchema):
    """Schema for seed_companies.yaml."""

    liked: list[SeedCompanyEntry] = Field(default_factory=list)
    disliked: list[SeedCompanyEntry] = Field(default_factory=list)
    watchlist: list[SeedCompanyEntry] = Field(default_factory=list)


# --- Target Titles Config ---


class SeniorityKeywords(BaseSchema):
    """Keywords indicating seniority levels."""

    senior: list[str] = Field(default_factory=list)
    founding: list[str] = Field(default_factory=list)
    executive: list[str] = Field(default_factory=list)


class TargetTitlesConfig(BaseSchema):
    """Schema for target_titles.yaml."""

    primary_titles: list[str] = Field(..., min_length=1)
    expanded_titles: list[str] = Field(default_factory=list)
    excluded_titles: list[str] = Field(default_factory=list)
    seniority_keywords: SeniorityKeywords = Field(default_factory=SeniorityKeywords)


# --- Preferences Config ---


class LocationPrefs(BaseSchema):
    """Location preferences."""

    preferred: list[str] = Field(default_factory=list)
    strict: bool = False


class StagePrefs(BaseSchema):
    """Company stage preferences."""

    preferred: list[str] = Field(default_factory=list)
    deprioritized: list[str] = Field(default_factory=list)
    strict: bool = False


class DomainPrefs(BaseSchema):
    """Domain/industry preferences."""

    preferred: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)


class DigestSettings(BaseSchema):
    """Daily digest settings."""

    daily_count: int = Field(default=5, ge=1, le=20)
    min_confidence: float = Field(default=0.6, ge=0, le=1)
    include_signals: bool = True


class RankingWeights(BaseSchema):
    """Ranking component weights."""

    title_match: float = Field(default=0.30, ge=0, le=1)
    location_match: float = Field(default=0.15, ge=0, le=1)
    embedding_similarity: float = Field(default=0.35, ge=0, le=1)
    stage_preference: float = Field(default=0.10, ge=0, le=1)
    freshness: float = Field(default=0.10, ge=0, le=1)


class ExclusionRules(BaseSchema):
    """Hard exclusion rules."""

    company_names: list[str] = Field(default_factory=list)
    description_keywords: list[str] = Field(default_factory=list)
    max_posting_age_days: int = Field(default=60, ge=0)


class PreferencesConfig(BaseSchema):
    """Schema for preferences.yaml."""

    location: LocationPrefs = Field(default_factory=LocationPrefs)
    company_stage: StagePrefs = Field(default_factory=StagePrefs)
    domains: DomainPrefs = Field(default_factory=DomainPrefs)
    digest: DigestSettings = Field(default_factory=DigestSettings)
    ranking_weights: RankingWeights = Field(default_factory=RankingWeights)
    exclusions: ExclusionRules = Field(default_factory=ExclusionRules)


# --- Sources Config ---


class ATSCompanyEntry(BaseSchema):
    """Single ATS company entry."""

    board_id: str
    name: str


class ATSSourceConfig(BaseSchema):
    """Config for an ATS source."""

    enabled: bool = True
    companies: list[ATSCompanyEntry] = Field(default_factory=list)
    rate_limit_seconds: int = Field(default=2, ge=1)


class CustomCareersConfig(BaseSchema):
    """Config for custom careers pages."""

    enabled: bool = True
    companies: list[dict] = Field(default_factory=list)
    rate_limit_seconds: int = Field(default=3, ge=1)


class CuratedBoardEntry(BaseSchema):
    """Single curated board entry."""

    name: str
    url: str
    type: str


class CuratedBoardsConfig(BaseSchema):
    """Config for curated job boards."""

    enabled: bool = False
    sources: list[CuratedBoardEntry] = Field(default_factory=list)


class SignalSourcesConfig(BaseSchema):
    """Config for signal sources."""

    github: dict = Field(default_factory=dict)
    news: dict = Field(default_factory=dict)


class GlobalSourceSettings(BaseSchema):
    """Global source settings."""

    user_agent: str = "JobAgent/1.0 (Personal job search assistant)"
    timeout_seconds: int = Field(default=30, ge=1)
    respect_robots_txt: bool = True
    max_concurrent: int = Field(default=3, ge=1)


class SourcesConfig(BaseSchema):
    """Schema for sources.yaml."""

    ats_sources: dict[str, ATSSourceConfig] = Field(default_factory=dict)
    custom_careers_pages: CustomCareersConfig = Field(default_factory=CustomCareersConfig)
    curated_boards: CuratedBoardsConfig = Field(default_factory=CuratedBoardsConfig)
    signal_sources: SignalSourcesConfig = Field(default_factory=SignalSourcesConfig)
    global_settings: GlobalSourceSettings = Field(
        default_factory=GlobalSourceSettings, alias="global"
    )
