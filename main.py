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
            bool(str(self.plugin_cfg.get(key, "") or "").strip())
            for key in self.FALLBACK_MODEL_KEYS
        )
        configured_count += sum(
            1
            for model_uuid in (self.plugin_cfg.get("fallback_models", []) or [])
            if str(model_uuid or "").strip()
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

        # Build an ordered (source_key, model_uuid) list. The numbered fields
        # hold a single uuid each, while "fallback_models" is a multi_select
        # that already stores a list of uuids as its value.
        candidates: list[tuple[str, str]] = [
            (config_key, str(self.plugin_cfg.get(config_key, "") or "").strip())
            for config_key in self.FALLBACK_MODEL_KEYS
        ]
        more_fallback_models = self.plugin_cfg.get("fallback_models", []) or []
        if isinstance(more_fallback_models, str):
            more_fallback_models = [more_fallback_models]
        candidates.extend(
            ("fallback_models", str(model_uuid or "").strip())
            for model_uuid in more_fallback_models
        )

        for source_key, model_uuid in candidates:
            if not model_uuid:
                continue

            fallback_model = self.ctx.get_llm_client(model_uuid)
            if fallback_model is None:
                cache_key = f"{source_key}:{model_uuid}"
                if cache_key not in self._invalid_model_keys:
                    logger.warning(
                        f"[model-fallback] Ignoring unavailable fallback model "
                        f"configured in {source_key}: {model_uuid}"
                    )
                    self._invalid_model_keys.add(cache_key)
                continue

            model_key = self._model_key(fallback_model)
            if model_key in model_keys:
                continue

            model_group.append(fallback_model)
            model_keys.add(model_key)

        event.model_group = model_group
