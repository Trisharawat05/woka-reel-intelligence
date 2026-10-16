from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class AutomationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    trigger_type: str = Field(default="COMMENT")  # COMMENT, STORY_REPLY, MENTION
    target_post_type: str = Field(default="ALL_POSTS")  # ALL_POSTS, SPECIFIC_POST
    target_post_id: Optional[str] = None
    target_post_preview_url: Optional[str] = None
    match_type: str = Field(default="CONTAINS_ANY")  # EXACT_MATCH, CONTAINS_ANY, CONTAINS_ALL, ANY_COMMENT
    trigger_keywords: List[str] = Field(default_factory=list)
    dm_message_template: str = Field(min_length=1)
    reply_comment_template: Optional[str] = None
    cooldown_minutes: int = Field(default=60, ge=1)
    is_active: bool = True

class AutomationUpdate(BaseModel):
    name: Optional[str] = None
    trigger_type: Optional[str] = None
    target_post_type: Optional[str] = None
    target_post_id: Optional[str] = None
    target_post_preview_url: Optional[str] = None
    match_type: Optional[str] = None
    trigger_keywords: Optional[List[str]] = None
    dm_message_template: Optional[str] = None
    reply_comment_template: Optional[str] = None
    cooldown_minutes: Optional[int] = None
    is_active: Optional[bool] = None

class AutomationResponse(BaseModel):
    id: str
    workspace_id: str
    ig_account_id: str
    name: str
    trigger_type: str
    target_post_type: str
    target_post_id: Optional[str] = None
    target_post_preview_url: Optional[str] = None
    match_type: str
    trigger_keywords: List[str]
    dm_message_template: str
    reply_comment_template: Optional[str] = None
    is_active: bool
    cooldown_minutes: int
    total_triggered_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AutomationSimulateRequest(BaseModel):
    automation_id: Optional[str] = None
    post_id: Optional[str] = "reel_sample_123"
    comment_text: str = Field(min_length=1)
    comment_author: str = Field(default="creative_fan_99")

class AutomationSimulateResponse(BaseModel):
    matched: bool
    automation_id: Optional[str] = None
    automation_name: Optional[str] = None
    matched_keyword: Optional[str] = None
    dm_message_preview: Optional[str] = None
    reply_comment_preview: Optional[str] = None
    recipient: str
    status: str
    explanation: str

class AutomationLogResponse(BaseModel):
    id: str
    automation_id: str
    automation_name: Optional[str] = None
    recipient_ig_id: str
    recipient_username: str
    trigger_comment_id: Optional[str] = None
    trigger_comment_text: Optional[str] = None
    dm_text_sent: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
