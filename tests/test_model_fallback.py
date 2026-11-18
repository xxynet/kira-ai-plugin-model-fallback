import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from core.chat import KiraMessageBatchEvent, Session
from core.plugin import PluginContext
from core.provider import LLMModelClient, ModelType, ProviderManager


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def plugin_class():
    spec = importlib.util.spec_from_file_location(
        "model_fallback_under_test", Path(__file__).resolve().parents[1] / "main.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ModelFallbackPlugin


@pytest.mark.anyio
@pytest.mark.parametrize("selection", [None, "session"])
@pytest.mark.parametrize("global_configured", [True, False])
async def test_fallback_group_uses_stored_session_selection(plugin_class, selection, global_configured):
    clients = {
        name: LLMModelClient(SimpleNamespace(provider_id="provider", model_id=name))
        for name in ("global", "session", "fallback")
    }
    manager = object.__new__(ProviderManager)
    manager.get_model_client = Mock(side_effect=lambda provider, model, kind: clients.get(model))
    manager.get_default_model_info = Mock(return_value=SimpleNamespace(
        provider_id="provider", model_id="global", model_type=ModelType.LLM,
    ))
    if not global_configured:
        manager.get_default_model_info.side_effect = ValueError("default_llm not set")
    context = object.__new__(PluginContext)
    context.provider_mgr = manager
    data = {"llm_model": "provider:session"} if selection else {}
    stored = Session("adapter", "dm", "user", data=data)
    context.session_mgr = SimpleNamespace(resolve_session=AsyncMock(return_value=stored))
    plugin = plugin_class(context, {
        "fallback_model_1": "provider:fallback",
        "fallback_models": ["provider:session", "provider:fallback", "provider:missing"],
    })
    await plugin.initialize()
    event = KiraMessageBatchEvent([], 0, session=Session("adapter", "dm", "user"))

    if selection is None and not global_configured:
        with pytest.raises(ValueError, match="default_llm not set"):
            await plugin.inject_fallback_models(event)
        assert event.model_group == []
    else:
        await plugin.inject_fallback_models(event)
        expected = [clients[selection or "global"], clients["fallback"]]
        if selection is None:
            expected.append(clients["session"])
        assert event.model_group == expected
    context.session_mgr.resolve_session.assert_awaited_once_with(event.sid, include_content=False)
    assert event.session.data == {}


@pytest.mark.anyio
async def test_unavailable_session_selection_is_not_replaced_by_global(plugin_class):
    manager = object.__new__(ProviderManager)
    manager.get_model_client = Mock(return_value=None)
    manager.get_default_model_info = Mock()
    context = object.__new__(PluginContext)
    context.provider_mgr = manager
    stored = Session("adapter", "dm", "user", data={"llm_model": "provider:missing"})
    context.session_mgr = SimpleNamespace(resolve_session=AsyncMock(return_value=stored))
    plugin = plugin_class(context, {})
    await plugin.initialize()
    event = KiraMessageBatchEvent([], 0, session=Session("adapter", "dm", "user"))

    with pytest.raises(ValueError, match="LLM model unavailable"):
        await plugin.inject_fallback_models(event)

    assert event.model_group == []
    manager.get_default_model_info.assert_not_called()


@pytest.mark.anyio
async def test_fallback_group_reads_current_metadata_without_loading_history(plugin_class, tmp_path):
    from core.chat.session_manager import SessionManager
    from core.db.db_mgr import DatabaseManager
    from core.db.service import DatabaseService

    database = DatabaseManager(f"sqlite+aiosqlite:///{(tmp_path / 'sessions.db').as_posix()}")
    await database.init()
    try:
        db = DatabaseService(database)
        await db.init_tables()
        context = object.__new__(PluginContext)
        context.session_mgr = SessionManager(db, {})
        clients = {
            name: LLMModelClient(SimpleNamespace(provider_id="provider", model_id=name))
            for name in ("global", "session", "fallback")
        }
        manager = object.__new__(ProviderManager)
        manager.get_model_client = Mock(side_effect=lambda provider, model, kind: clients.get(model))
        manager.get_default_model_info = Mock(return_value=SimpleNamespace(
            provider_id="provider", model_id="global", model_type=ModelType.LLM,
        ))
        context.provider_mgr = manager
        context.get_default_llm_client = Mock(wraps=context.get_default_llm_client)
        event = KiraMessageBatchEvent([], 0, session=Session("adapter", "dm", "user"))
        content = [[{"role": "user", "content": "existing history"}]]
        await db.save_chat_session(event.sid, content=content, data={"llm_model": "provider:session"})
        plugin = plugin_class(context, {"fallback_model_1": "provider:fallback"})
        await plugin.initialize()

        await plugin.inject_fallback_models(event)

        assert event.model_group == [clients["session"], clients["fallback"]]
        selected_session = context.get_default_llm_client.call_args.args[0]
        assert selected_session.content == []
        assert selected_session.data == {"llm_model": "provider:session"}
        await db.save_chat_session(event.sid, data={})

        await plugin.inject_fallback_models(event)

        assert event.model_group == [clients["global"], clients["fallback"]]
        assert event.session.data == {}
        assert (await db.get_chat_session(event.sid))["content"] == content
    finally:
        await database.dispose()
