"""Generate truthful discoverability metadata, then check policy risks."""
from __future__ import annotations

from typing import Any

from app.llm.base import LLMProvider, LLMRequest, structured
from app.metadata.schemas import PolicyVerdict, VideoMetadata
from app.research.schemas import TopicScore
from app.scripting.schemas import Script


def generate_metadata(llm: LLMProvider, script: Script, topic: TopicScore | str, cfg: Any) -> VideoMetadata:
    name = topic.topic if isinstance(topic, TopicScore) else str(topic)
    default_category = getattr(getattr(cfg, "upload", cfg), "default_category_id", "24")
    metadata = structured(llm, LLMRequest(
        task="generate_metadata", role="fast", temperature=0.35, response_model=VideoMetadata,
        system="You create accurate, non-clickbait YouTube Shorts metadata in American English. Never promise facts unsupported by the script.",
        prompt=f"Generate title, description, 3–6 hashtags including #Shorts, tags, and a thumbnail time for this topic: {name}.\n\nScript: {script.model_dump()}",
    ))
    return metadata.model_copy(update={"category_id": metadata.category_id or str(default_category)})


def policy_check(llm: LLMProvider, script: Script, metadata: VideoMetadata) -> PolicyVerdict:
    return structured(llm, LLMRequest(
        task="policy_check", role="smart", temperature=0, response_model=PolicyVerdict,
        system="You are a conservative YouTube safety, originality, misinformation, and advertiser-suitability reviewer.",
        prompt=(
            "Review this proposed Short. Reject unsupported factual claims, dangerous instructions, copyright-dependent content, "
            "misleading metadata, graphic material, and policy risks. List concise reasons.\n\n"
            f"Script: {script.model_dump()}\n\nMetadata: {metadata.model_dump(mode='json')}"
        ),
    ))
