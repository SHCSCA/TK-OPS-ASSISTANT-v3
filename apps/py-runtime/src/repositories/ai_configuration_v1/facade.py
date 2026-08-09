from __future__ import annotations

from repositories.ai_configuration_v1.models import (
    ModelCapabilityRepository,
    ModelProfileRepository,
)
from repositories.ai_configuration_v1.prompts import PromptProfileRepository
from repositories.ai_configuration_v1.providers import ProviderProfileRepository
from repositories.ai_configuration_v1.recipes import AccountAIRecipeRepository
from repositories.ai_configuration_v1.revisions import AIConfigRevisionRepository
from repositories.ai_configuration_v1.routes import CapabilityRouteRepository
from repositories.ai_configuration_v1.templates import (
    CompositionTemplateProfileRepository,
)


class AIConfigurationV1Repository:
    """汇总 AI 配置子仓储，不持有或提交 Session。"""

    def __init__(self) -> None:
        self.providers = ProviderProfileRepository()
        self.models = ModelProfileRepository()
        self.capabilities = ModelCapabilityRepository()
        self.routes = CapabilityRouteRepository()
        self.prompts = PromptProfileRepository()
        self.templates = CompositionTemplateProfileRepository()
        self.recipes = AccountAIRecipeRepository()
        self.revisions = AIConfigRevisionRepository()
