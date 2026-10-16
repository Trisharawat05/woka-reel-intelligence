from typing import List, Optional
from pydantic import BaseModel, Field

class CaptionGenerateRequest(BaseModel):
    topic: str = Field(min_length=2, description="What the post is about")
    tone: str = Field(default="Engaging", description="Engaging, Witty, Professional, Storytelling, Urgent")
    target_cta: str = Field(default="Comment for Link", description="Comment for Link, Save for Later, Share, Visit Bio")
    include_emojis: bool = True
    niche: Optional[str] = "General"

class CaptionGenerateResponse(BaseModel):
    caption: str
    suggested_hooks: List[str]
    suggested_hashtags: List[str]
    call_to_action: str

class HookGenerateRequest(BaseModel):
    topic: str = Field(min_length=2)
    style: str = Field(default="Curiosity Gap", description="Curiosity Gap, Contrarian, Step-by-Step, Story Hook, Warning")

class HookGenerateResponse(BaseModel):
    hooks: List[str]

class HashtagGenerateRequest(BaseModel):
    niche: str = Field(min_length=2)

class HashtagGenerateResponse(BaseModel):
    high_reach: List[str]
    mid_tier: List[str]
    niche_specific: List[str]
    recommended_set: List[str]
