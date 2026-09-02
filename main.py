from core.chat import KiraMessageBatchEvent
from core.plugin import BasePlugin, Priority, logger, on
from core.provider import LLMModelClient


class ModelFallbackPlugin(BasePlugin):
    """Adds configured LLM fallback models to each message batch."""

    FALLBACK_MODEL_KEYS = (
        "fallback_model_1",
        "fallback_model_2",
        "fallback_model_3",
    )

    async def initialize(self):
        configured_count = sum(
            bool(str(self.plugin_cfg.get(key, "")).strip())
            for key in self.FALLBACK_MODEL_KEYS
        )
        self._invalid_model_keys: set[str] = set()
        logger.info(
            f"[model-fallback] initialized with {configured_count} fallback model(s)"
        )

    async def terminate(self):
        pass

    @staticmethod
    def _model_key(model: LLMModelClient) -> tuple[str, str]:
        return model.model.provider_id, model.model.model_id

    @on.im_batch_message(priority=Priority.HIGH)
    async def inject_fallback_models(self, event: KiraMessageBatchEvent):
        """Set the default LLM first, followed by valid configured fallbacks."""
        default_model = self.ctx.get_default_llm_client()
        if default_model is None:
            logger.warning("[model-fallback] Default LLM is unavailable; skipping fallback setup")
            return

        model_group = [default_model]
        model_keys = {self._model_key(default_model)}

        for config_key in self.FALLBACK_MODEL_KEYS:
            model_uuid = str(self.plugin_cfg.get(config_key, "")).strip()
            if not model_uuid:
                continue

            fallback_model = self.ctx.get_llm_client(model_uuid)
            if fallback_model is None:
                if config_key not in self._invalid_model_keys:
                    logger.warning(
                        f"[model-fallback] Ignoring unavailable fallback model "
                        f"configured in {config_key}: {model_uuid}"
                    )
                    self._invalid_model_keys.add(config_key)
                continue

            model_key = self._model_key(fallback_model)
            if model_key in model_keys:
                continue

            model_group.append(fallback_model)
            model_keys.add(model_key)

        event.model_group = model_group
