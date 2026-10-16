from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class AnalyzePublicUrlRequest(BaseModel):
    url: str = Field(..., description="Instagram Reel URL, post URL, or public video link")
    declared_views: Optional[int] = Field(None, ge=0, description="Optional creator-reported views if scrape is private")
    declared_likes: Optional[int] = Field(None, ge=0, description="Optional creator-reported likes")
    declared_comments: Optional[int] = Field(None, ge=0, description="Optional creator-reported comments")
    declared_shares: Optional[int] = Field(None, ge=0, description="Optional creator-reported shares")
    declared_saves: Optional[int] = Field(None, ge=0, description="Optional creator-reported saves")


class AnalyzeConnectedReelRequest(BaseModel):
    media_id: str = Field(..., description="Official Instagram Media ID from connected professional account")
    title: Optional[str] = Field(None, description="Optional title or label for the Reel")
    caption: Optional[str] = Field(None, description="Reel caption")
    media_url: Optional[str] = Field(None, description="Direct video media URL from Graph API")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail or cover image URL")


class ReelAnalysisJobResponse(BaseModel):
    id: str
    workspace_id: str
    analysis_mode: str
    input_type: str
    status: str
    progress_percent: int
    stage_message: str
    error_message: Optional[str] = None
    source_url: Optional[str] = None
    source_media_id: Optional[str] = None
    report_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MetricItem(BaseModel):
    name: str
    value: Optional[float] = None
    formatted: str
    numerator: str
    denominator: str
    time_window: str
    source: str
    benchmark: Optional[str] = None
    benchmark_status: Optional[str] = "N/A"  # ABOVE_AVERAGE, AVERAGE, BELOW_AVERAGE, N/A
    limitations: str


class ScoreComponent(BaseModel):
    name: str
    score: float
    weight: float
    status: str  # EXCELLENT, GOOD, NEEDS_IMPROVEMENT, POOR
    details: str


class ScoreDetail(BaseModel):
    score: float
    rating: str  # EXCEPTIONAL, STRONG, MODERATE, UNDERPERFORMING
    confidence: float
    methodology: str
    components: List[ScoreComponent]
    evidence_summary: str


class ScoreOverview(BaseModel):
    creative_quality: ScoreDetail
    performance: ScoreDetail
    growth_conversion: ScoreDetail
    viral_potential: ScoreDetail


class TimelineFinding(BaseModel):
    id: str
    timestamp_start_seconds: float
    timestamp_end_seconds: float
    time_range_formatted: str
    category: str  # HOOK, PACING, VISUAL_CLARITY, AUDIO_SPEECH, SUBTITLES, STRUCTURE, CTA
    severity: str  # CRITICAL, WARNING, OPPORTUNITY, STRENGTH
    observation: str
    evidence: str
    recommendation: str
    proposed_edit: str
    is_heuristic_risk: bool = True


class ActionPlanItem(BaseModel):
    priority: int
    area: str
    what_worked: str
    what_underperformed: str
    why_it_happened: str
    supporting_evidence: str
    what_to_change: str
    how_to_implement: str
    follow_up_test_metric: str


class CreativeAlternatives(BaseModel):
    alternative_hooks: List[Dict[str, str]]
    thumbnail_concepts: List[Dict[str, str]]
    caption_suggestions: List[Dict[str, str]]
    cta_variations: List[Dict[str, str]]
    revised_script: Dict[str, Any]


class ReelReportResponse(BaseModel):
    id: str
    workspace_id: str
    job_id: str
    title: str
    caption: Optional[str] = None
    analysis_mode: str
    thumbnail_url: Optional[str] = None
    duration_seconds: float
    scores: ScoreOverview
    calculated_metrics: Dict[str, MetricItem]
    video_intelligence: Dict[str, Any]
    timeline_findings: List[TimelineFinding]
    prioritized_action_plan: List[ActionPlanItem]
    creative_alternatives: CreativeAlternatives
    provenance: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReelReportSummary(BaseModel):
    id: str
    workspace_id: str
    job_id: str
    title: str
    analysis_mode: str
    thumbnail_url: Optional[str] = None
    duration_seconds: float
    creative_quality_score: float
    performance_score: float
    growth_conversion_score: float
    viral_potential_estimate: float
    views_count: Optional[int] = 0
    likes_count: Optional[int] = 0
    engagement_rate: Optional[float] = 0.0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReelComparisonRequest(BaseModel):
    report_ids: List[str] = Field(..., min_length=2, max_length=5, description="2 to 5 Report IDs to compare")


class ReelComparisonResponse(BaseModel):
    id: str
    workspace_id: str
    report_ids: List[str]
    reports: List[ReelReportResponse]
    comparison_matrix: Dict[str, Any]
    comparative_takeaways: List[str]
    winner_id: Optional[str] = None
    created_at: datetime
