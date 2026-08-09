from __future__ import annotations

CAPABILITY_KEYS = frozenset(
    {
        "topic_generation",
        "script_generation",
        "script_rewrite",
        "storyboard_generation",
        "video_deconstruction",
        "speech_to_text",
        "image_generation",
        "text_to_video",
        "image_to_video",
        "tts",
        "subtitle_alignment",
        "asset_analysis",
        "embedding",
    }
)

PROVIDER_ADAPTER_TYPES = frozenset(
    {
        "direct_api",
        "openai_compatible",
        "comfyui",
        "runninghub",
    }
)

COMPOSITION_TEMPLATE_TYPES = frozenset(
    {
        "slideshow",
        "talking_head",
        "product_showcase",
        "mixed_media",
    }
)

PROVIDER_HEALTH_TASK_TYPE = "provider.health_check"
PROVIDER_MODEL_DISCOVERY_TASK_TYPE = "provider.model_discovery"
MODEL_CAPABILITY_CHECK_TASK_TYPE = "model.capability_check"

SYSTEM_AI_TOPIC = "system:ai"

