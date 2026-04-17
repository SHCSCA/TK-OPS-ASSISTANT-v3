from __future__ import annotations

import asyncio

import services.ai_capability_service as ai_capability_module
from schemas.ai_capabilities import AICapabilityConfigDto, AICapabilitySettingsDto
from services.ai_capability_service import AICapabilityService


class BroadcastingAICapabilityService(AICapabilityService):
    def update_capabilities(
        self,
        items: list[AICapabilityConfigDto],
    ) -> AICapabilitySettingsDto:
        previous = {
            item.capabilityId: item for item in self.get_settings().capabilities
        }
        result = super().update_capabilities(items)
        changed_capability_ids = sorted(
            item.capabilityId
            for item in items
            if previous.get(item.capabilityId) != item
        )
        asyncio.run(
            ai_capability_module.ws_manager.broadcast(
                {
                    "type": "ai-capability.changed",
                    "payload": {
                        "capabilityIds": changed_capability_ids,
                    },
                }
            )
        )
        return result
