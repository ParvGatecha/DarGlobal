import urllib.request
import json
from typing import List, Optional
from backend.app.core.config import settings
from backend.app.core.logger import logger

# Preferred high-capacity free models on OpenRouter in priority order
PREFERRED_FREE_MODELS = [
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3.5-lightning:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "inclusionai/ling-3.2-flash:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "qwen/qwen-2.5-72b-instruct:free",
]

class ModelSelector:
    """
    Dynamically discovers and selects active free models from OpenRouter.
    """

    def __init__(self):
        self._cached_free_models: List[str] = []
        self._active_model: str = settings.OPENROUTER_MODEL

    def discover_free_models(self) -> List[str]:
        """Queries OpenRouter /api/v1/models and returns available ':free' models."""
        url = f"{settings.OPENROUTER_BASE_URL}/models"
        headers = {"User-Agent": "DarGlobal-Intelligence/1.0"}
        if settings.OPENROUTER_API_KEY:
            headers["Authorization"] = f"Bearer {settings.OPENROUTER_API_KEY}"

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("data", [])
                free_models = [m["id"] for m in models if ":free" in m.get("id", "")]
                logger.info(f"Discovered {len(free_models)} free models on OpenRouter.")
                self._cached_free_models = free_models
                return free_models
        except Exception as e:
            logger.warning(f"Could not reach OpenRouter models endpoint: {e}. Using preferred fallback list.")
            return PREFERRED_FREE_MODELS

    def get_best_model(self) -> str:
        """
        Determines the optimal model to use:
        1. If user set an explicit OPENROUTER_MODEL in env, use that.
        2. Otherwise, pick the highest-priority currently available free model.
        """
        if settings.OPENROUTER_MODEL and settings.OPENROUTER_MODEL != "auto":
            self._active_model = settings.OPENROUTER_MODEL
            return self._active_model

        free_models = self.discover_free_models()
        for preferred in PREFERRED_FREE_MODELS:
            if preferred in free_models:
                self._active_model = preferred
                logger.info(f"Auto-selected free model: {self._active_model}")
                return self._active_model

        if free_models:
            self._active_model = free_models[0]
            logger.info(f"Auto-selected available free model: {self._active_model}")
            return self._active_model

        self._active_model = "google/gemma-4-31b-it:free"
        return self._active_model

    @property
    def active_model(self) -> str:
        return self._active_model

model_selector = ModelSelector()
