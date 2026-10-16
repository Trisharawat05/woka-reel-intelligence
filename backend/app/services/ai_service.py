import random
from typing import List
from app.schemas.ai import (
    CaptionGenerateRequest, CaptionGenerateResponse,
    HookGenerateRequest, HookGenerateResponse,
    HashtagGenerateRequest, HashtagGenerateResponse
)

HOOK_TEMPLATES = {
    "Curiosity Gap": [
        "Nobody is talking about this creator strategy, but it got me 100k views in 48 hours...",
        "If you're still doing {topic} the old way, you are losing 80% of your engagement.",
        "The 1 unwritten rule of {topic} that brands will never tell you.",
        "I stopped doing {topic} for 30 days. Here's the crazy thing that happened.",
        "Stop scrolling if you want to master {topic} before 2027."
    ],
    "Contrarian": [
        "Unpopular opinion: Everything you’ve been told about {topic} is completely backwards.",
        "Why most creators fail at {topic} (and why it's not the algorithm's fault).",
        "Don't start {topic} until you've watched this 30-second breakdown.",
        "The biggest lie in the creator economy right now regarding {topic}."
    ],
    "Step-by-Step": [
        "Here is the exact 3-step framework I use every morning for {topic}:",
        "How to go from zero to consistent results with {topic} in under 15 minutes a day.",
        "Bookmark this video: The ultimate beginner blueprint for {topic}."
    ],
    "Story Hook": [
        "6 months ago, I was completely overwhelmed trying to figure out {topic}...",
        "A brand offered me $5,000 for this exact {topic} setup. Here is how I built it.",
        "The moment I realized I had been wasting 10 hours a week on {topic}."
    ],
    "Warning": [
        "Warning: If you do {topic} without this 1 safety step, your reach will tank.",
        "The 3 silent mistakes that kill your conversion rates in {topic}.",
        "Check your settings right now: Are you making this critical {topic} error?"
    ]
}

def generate_caption(payload: CaptionGenerateRequest) -> CaptionGenerateResponse:
    topic = payload.topic.strip()
    tone = payload.tone
    cta = payload.target_cta
    
    hook_list = HOOK_TEMPLATES.get("Curiosity Gap", HOOK_TEMPLATES["Curiosity Gap"])
    selected_hook = random.choice(hook_list).replace("{topic}", topic)
    
    emojis = "✨ 🚀 💡" if payload.include_emojis else ""
    
    if tone == "Witty":
        body = (
            f"Let's be completely honest about {topic}. We’ve all pretended we have it all figured out, "
            f"while silently panicking behind our ring lights.\n\n"
            f"Here’s the unfiltered truth: Once you streamline your system, the results speak for themselves. "
            f"Work smarter, not harder."
        )
    elif tone == "Storytelling":
        body = (
            f"I remember sitting at my desk late at night wondering if anyone was actually listening. "
            f"That was before I discovered how to approach {topic} intentionally.\n\n"
            f"Fast forward to today: Engagement is up, brand conversations are easier, and creating feels fun again. "
            f"The pivot wasn’t luck—it was having the right workflow."
        )
    elif tone == "Urgent":
        body = (
            f"Do not sleep on this. The creator landscape for {topic} is changing faster than ever.\n\n"
            f"The creators who adapt right now are going to capture the next wave of attention and brand deals. "
            f"Take 2 minutes to apply this today."
        )
    else:  # Engaging / Professional
        body = (
            f"Consistency is king, but clarity is power. When it comes to {topic}, "
            f"focusing on real audience value beats chasing every trend every single time.\n\n"
            f"Here are 3 core pillars to keep in mind:\n"
            f"1. Hook with immediate curiosity\n"
            f"2. Deliver punchy, actionable advice\n"
            f"3. Make your call to action effortless"
        )

    if "Comment" in cta:
        cta_line = f"👇 Drop a comment below with '{topic.upper().split()[0]}' and I'll send the full breakdown straight to your DMs!"
    elif "Save" in cta:
        cta_line = "📌 Tap Save right now so you have this ready when you plan your next piece of content."
    elif "Share" in cta:
        cta_line = "✈️ Send this to a fellow creator who needs to hear this today!"
    else:
        cta_line = "🔗 Tap the link in my bio to get immediate access to the full toolkit."

    hashtags = [
        f"#{topic.replace(' ', '').lower()}",
        "#creatoreconomy",
        "#contentcreator",
        "#instagramgrowth",
        "#socialmediatips",
        "#creatorlife",
        "#digitalcreator"
    ]

    full_caption = f"{selected_hook}\n\n{body}\n\n{cta_line}\n\n{' '.join(hashtags)} {emojis}"

    return CaptionGenerateResponse(
        caption=full_caption,
        suggested_hooks=[
            f"Stop scrolling: The secret to {topic} in 2026",
            f"The 1 mistake you're making with {topic}",
            f"How I automated my workflow for {topic}"
        ],
        suggested_hashtags=hashtags,
        call_to_action=cta_line
    )

def generate_hooks(payload: HookGenerateRequest) -> HookGenerateResponse:
    style_templates = HOOK_TEMPLATES.get(payload.style, HOOK_TEMPLATES["Curiosity Gap"])
    hooks = [tpl.replace("{topic}", payload.topic) for tpl in style_templates]
    return HookGenerateResponse(hooks=hooks)

def generate_hashtags(payload: HashtagGenerateRequest) -> HashtagGenerateResponse:
    base = payload.niche.replace(" ", "").lower()
    high = ["#explorepage", "#viral", "#creators", "#trending", "#instadaily"]
    mid = [f"#{base}tips", f"#{base}community", f"#{base}life", "#contentcreatorlife"]
    niche = [f"#{base}creator", f"#{base}daily", f"#{base}strategy", f"#{base}growth"]
    
    recommended = [f"#{base}"] + niche[:2] + mid[:2] + high[:2]
    return HashtagGenerateResponse(
        high_reach=high,
        mid_tier=mid,
        niche_specific=niche,
        recommended_set=recommended
    )
