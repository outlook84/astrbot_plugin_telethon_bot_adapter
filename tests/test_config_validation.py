import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path


def _install_astrbot_stubs() -> None:
    astrbot_module = types.ModuleType("astrbot")
    api_module = types.ModuleType("astrbot.api")
    event_module = types.ModuleType("astrbot.api.event")
    platform_module = types.ModuleType("astrbot.api.platform")
    astr_message_event_module = types.ModuleType("astrbot.core.platform.astr_message_event")
    command_filter_module = types.ModuleType("astrbot.core.star.filter.command")
    command_group_filter_module = types.ModuleType("astrbot.core.star.filter.command_group")
    star_module = types.ModuleType("astrbot.core.star.star")
    star_handler_module = types.ModuleType("astrbot.core.star.star_handler")

    class _Logger:
        def info(self, *args, **kwargs):
            return None

        def warning(self, *args, **kwargs):
            return None

        def error(self, *args, **kwargs):
            return None

        def debug(self, *args, **kwargs):
            return None

        def exception(self, *args, **kwargs):
            return None

    class Platform:
        def __init__(self, platform_config, event_queue):
            self.config = platform_config
            self.event_queue = event_queue

        def commit_event(self, event):
            return None

    class PlatformMetadata:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class MessageChain:
        pass

    def register_platform_adapter(*args, **kwargs):
        def decorator(cls):
            return cls

        return decorator

    class MessageSesion:
        pass

    class CommandFilter:
        def __init__(self, command_name="", alias=None, parent_command_names=None):
            self.command_name = command_name
            self.alias = alias or []
            self.parent_command_names = parent_command_names

    class CommandGroupFilter:
        def __init__(self, group_name="", alias=None, parent_group=None):
            self.group_name = group_name
            self.alias = alias or []
            self.parent_group = parent_group

    api_module.logger = _Logger()
    event_module.MessageChain = MessageChain
    platform_module.Platform = Platform
    platform_module.PlatformMetadata = PlatformMetadata
    platform_module.AstrBotMessage = type("AstrBotMessage", (), {})
    platform_module.register_platform_adapter = register_platform_adapter
    astr_message_event_module.MessageSesion = MessageSesion
    command_filter_module.CommandFilter = CommandFilter
    command_group_filter_module.CommandGroupFilter = CommandGroupFilter
    star_module.star_map = {}
    star_handler_module.star_handlers_registry = []

    sys.modules["astrbot"] = astrbot_module
    sys.modules["astrbot.api"] = api_module
    sys.modules["astrbot.api.event"] = event_module
    sys.modules["astrbot.api.platform"] = platform_module
    sys.modules["astrbot.core.platform.astr_message_event"] = astr_message_event_module
    sys.modules["astrbot.core.star.filter.command"] = command_filter_module
    sys.modules["astrbot.core.star.filter.command_group"] = command_group_filter_module
    sys.modules["astrbot.core.star.star"] = star_module
    sys.modules["astrbot.core.star.star_handler"] = star_handler_module


def _install_pydantic_stubs() -> None:
    pydantic_module = types.ModuleType("pydantic")
    pydantic_v1_module = types.ModuleType("pydantic.v1")

    class _PrivateAttr:
        def __init__(self, default=None):
            self.default = default
            self.name = None

        def __set_name__(self, owner, name):
            self.name = name

        def __get__(self, instance, owner=None):
            if instance is None:
                return self
            return instance.__dict__.get(self.name, self.default)

        def __set__(self, instance, value):
            instance.__dict__[self.name] = value

    pydantic_module.PrivateAttr = _PrivateAttr
    pydantic_v1_module.PrivateAttr = _PrivateAttr
    sys.modules["pydantic"] = pydantic_module
    sys.modules["pydantic.v1"] = pydantic_v1_module


def _install_telethon_stubs() -> None:
    telethon_module = types.ModuleType("telethon")
    errors_module = types.ModuleType("telethon.errors")
    errors_common_module = types.ModuleType("telethon.errors.common")
    network_module = types.ModuleType("telethon.network")
    connection_module = types.ModuleType("telethon.network.connection")
    sessions_module = types.ModuleType("telethon.sessions")
    events_module = types.ModuleType("telethon.events")
    functions_module = types.ModuleType("telethon.functions")
    functions_bots_module = types.ModuleType("telethon.functions.bots")
    types_module = types.ModuleType("telethon.types")

    class TelegramClient:
        def __init__(self, *args, **kwargs):
            return None

        async def __call__(self, request):
            return request

    class _EventFactory:
        def __call__(self, *args, **kwargs):
            return ("event", args, kwargs)

    class _NewMessage:
        Event = object

        def __call__(self, *args, **kwargs):
            return ("new_message", args, kwargs)

    class _Raw:
        def __call__(self, *args, **kwargs):
            return ("raw", args, kwargs)

    class MemorySession:
        pass

    class SetBotMenuButtonRequest:
        def __init__(self, user_id, button):
            self.user_id = user_id
            self.button = button

    class SetBotCommandsRequest:
        def __init__(self, scope, lang_code, commands):
            self.scope = scope
            self.lang_code = lang_code
            self.commands = commands

    class BotCommand:
        def __init__(self, command, description):
            self.command = command
            self.description = description

    class BotMenuButtonCommands:
        pass

    class BotMenuButtonDefault:
        pass

    class BotCommandScopeDefault:
        pass

    class InputUserSelf:
        pass

    telethon_module.TelegramClient = TelegramClient
    telethon_module.events = events_module
    telethon_module.errors = errors_module
    telethon_module.functions = functions_module
    telethon_module.types = types_module
    network_module.connection = connection_module
    sessions_module.MemorySession = MemorySession
    events_module.NewMessage = _NewMessage()
    events_module.Raw = _Raw()
    errors_module.common = errors_common_module
    functions_module.bots = functions_bots_module
    functions_bots_module.SetBotMenuButtonRequest = SetBotMenuButtonRequest
    functions_bots_module.SetBotCommandsRequest = SetBotCommandsRequest
    types_module.BotCommand = BotCommand
    types_module.BotMenuButtonCommands = BotMenuButtonCommands
    types_module.BotMenuButtonDefault = BotMenuButtonDefault
    types_module.BotCommandScopeDefault = BotCommandScopeDefault
    types_module.InputUserSelf = InputUserSelf

    sys.modules["telethon"] = telethon_module
    sys.modules["telethon.errors"] = errors_module
    sys.modules["telethon.errors.common"] = errors_common_module
    sys.modules["telethon.network"] = network_module
    sys.modules["telethon.network.connection"] = connection_module
    sys.modules["telethon.sessions"] = sessions_module
    sys.modules["telethon.events"] = events_module
    sys.modules["telethon.functions"] = functions_module
    sys.modules["telethon.functions.bots"] = functions_bots_module
    sys.modules["telethon.types"] = types_module


def _install_local_module_stubs() -> None:
    telethon_event_module = types.ModuleType("telethon_adapter.telethon_event")
    message_converter_module = types.ModuleType("telethon_adapter.message_converter")

    class TelethonMessageConverter:
        def __init__(self, adapter):
            self.adapter = adapter

    telethon_event_module.TelethonEvent = type("TelethonEvent", (), {})
    message_converter_module.TelethonMessageConverter = TelethonMessageConverter
    sys.modules["telethon_adapter.telethon_event"] = telethon_event_module
    sys.modules["telethon_adapter.message_converter"] = message_converter_module


def _load_modules():
    for module_name in list(sys.modules):
        if module_name == "telethon_adapter" or module_name.startswith("telethon_adapter."):
            sys.modules.pop(module_name, None)

    _install_astrbot_stubs()
    _install_pydantic_stubs()
    _install_telethon_stubs()
    _install_local_module_stubs()

    package_name = "telethon_adapter"
    package_path = Path(__file__).resolve().parents[1] / package_name
    package_module = types.ModuleType(package_name)
    package_module.__path__ = [str(package_path)]
    sys.modules[package_name] = package_module

    loaded = {}
    for module_name in ["i18n", "config", "telethon_adapter"]:
        full_name = f"{package_name}.{module_name}"
        module_path = package_path / f"{module_name}.py"
        spec = importlib.util.spec_from_file_location(full_name, module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        sys.modules[full_name] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module
    return loaded["config"], loaded["telethon_adapter"]


class ConfigValidationTests(unittest.TestCase):
    def test_default_template_uses_bot_token(self):
        config_module, _ = _load_modules()

        self.assertIn("bot_token", config_module.DEFAULT_CONFIG_TEMPLATE)
        self.assertNotIn("session_string", config_module.DEFAULT_CONFIG_TEMPLATE)
        self.assertEqual(config_module.DEFAULT_CONFIG_TEMPLATE["menu_button_mode"], "commands")

    def test_adapter_init_parses_bot_config(self):
        _, adapter_module = _load_modules()
        adapter = adapter_module.TelethonPlatformAdapter(
            {
                "api_id": 123,
                "api_hash": "hash",
                "bot_token": "123:abc",
                "reply_to_self_triggers_command": "true",
                "debug_logging": "true",
                "telethon_command_register": "false",
                "telethon_command_auto_refresh": "false",
                "telethon_command_register_interval": "123",
                "menu_button_mode": "commands",
            },
            {},
            asyncio.Queue(),
        )

        self.assertEqual(adapter.bot_token, "123:abc")
        self.assertTrue(adapter.reply_to_self_triggers_command)
        self.assertTrue(adapter.debug_logging)
        self.assertFalse(adapter.sync_bot_commands)
        self.assertFalse(adapter.command_auto_refresh)
        self.assertEqual(adapter.command_refresh_interval, 123)
        self.assertEqual(adapter.menu_button_mode, "commands")
        self.assertEqual(adapter.meta().name, "telethon_bot")
        self.assertEqual(adapter.meta().id, "telethon_bot")

    def test_build_adapter_capability_uses_default_limit_for_bot(self):
        _, adapter_module = _load_modules()
        adapter = adapter_module.TelethonPlatformAdapter(
            {
                "api_id": 123,
                "api_hash": "hash",
                "bot_token": "123:abc",
            },
            {},
            asyncio.Queue(),
        )

        capability = adapter._build_adapter_capability()

        self.assertTrue(capability["supports_spoiler"])
        self.assertEqual(capability["max_items"], 10)
        self.assertEqual(capability["supported_types"], ["image", "video"])
        self.assertEqual(
            capability["upload_constraints"]["max_single_file_bytes"],
            adapter_module.TELEGRAM_MAX_FILE_BYTES_DEFAULT,
        )

    def test_validate_config_requires_bot_token(self):
        config_module, _ = _load_modules()
        adapter = types.SimpleNamespace(
            config={"api_id": 123, "api_hash": "hash", "bot_token": "", "language": "zh-CN"},
            api_id=123,
            api_hash="hash",
            bot_token="",
            language="zh-CN",
            proxy_type="",
            proxy_host="",
            proxy_port=0,
            proxy_secret="",
            command_refresh_interval=300,
            menu_button_mode="disabled",
            media_group_timeout=1.2,
            media_group_max_wait=8.0,
        )

        with self.assertRaises(ValueError) as context:
            config_module.validate_config(adapter)

        self.assertIn("bot token", str(context.exception).lower())

    def test_validate_config_rejects_invalid_menu_button_mode(self):
        config_module, _ = _load_modules()
        adapter = types.SimpleNamespace(
            config={
                "api_id": 123,
                "api_hash": "hash",
                "bot_token": "123:abc",
                "language": "zh-CN",
                "menu_button_mode": "web_app",
            },
            api_id=123,
            api_hash="hash",
            bot_token="123:abc",
            language="zh-CN",
            proxy_type="",
            proxy_host="",
            proxy_port=0,
            proxy_secret="",
            command_refresh_interval=300,
            menu_button_mode="web_app",
            media_group_timeout=1.2,
            media_group_max_wait=8.0,
        )

        with self.assertRaises(ValueError) as context:
            config_module.validate_config(adapter)

        self.assertIn("menu", str(context.exception).lower())

    def test_validate_config_rejects_invalid_command_refresh_interval(self):
        config_module, _ = _load_modules()
        adapter = types.SimpleNamespace(
            config={
                "api_id": 123,
                "api_hash": "hash",
                "bot_token": "123:abc",
                "language": "zh-CN",
                "telethon_command_register_interval": 0,
                "menu_button_mode": "disabled",
            },
            api_id=123,
            api_hash="hash",
            bot_token="123:abc",
            language="zh-CN",
            proxy_type="",
            proxy_host="",
            proxy_port=0,
            proxy_secret="",
            command_refresh_interval=0,
            menu_button_mode="disabled",
            media_group_timeout=1.2,
            media_group_max_wait=8.0,
        )

        with self.assertRaises(ValueError) as context:
            config_module.validate_config(adapter)

        self.assertIn("telethon_command_register_interval", str(context.exception))

    def test_legacy_command_config_names_still_work(self):
        _, adapter_module = _load_modules()
        adapter = adapter_module.TelethonPlatformAdapter(
            {
                "api_id": 123,
                "api_hash": "hash",
                "bot_token": "123:abc",
                "sync_bot_commands": "false",
                "telethon_command_refresh_interval": "456",
            },
            {},
            asyncio.Queue(),
        )

        self.assertFalse(adapter.sync_bot_commands)
        self.assertEqual(adapter.command_refresh_interval, 456)

    def test_collect_commands_includes_top_level_commands_and_groups(self):
        _, adapter_module = _load_modules()
        command_filter_module = sys.modules["astrbot.core.star.filter.command"]
        command_group_filter_module = sys.modules["astrbot.core.star.filter.command_group"]
        star_module = sys.modules["astrbot.core.star.star"]
        star_handler_module = sys.modules["astrbot.core.star.star_handler"]

        star_module.star_map["plugin.enabled"] = types.SimpleNamespace(activated=True)
        star_handler_module.star_handlers_registry[:] = [
            types.SimpleNamespace(
                handler_module_path="plugin.enabled",
                enabled=True,
                desc="Status description",
                event_filters=[
                    command_filter_module.CommandFilter(
                        command_name="status",
                        alias=["state"],
                        parent_command_names=None,
                    ),
                    command_group_filter_module.CommandGroupFilter(
                        group_name="admin",
                        parent_group=None,
                    ),
                    command_filter_module.CommandFilter(
                        command_name="sub",
                        alias=[],
                        parent_command_names=["admin"],
                    ),
                ],
            )
        ]

        adapter = adapter_module.TelethonPlatformAdapter(
            {"api_id": 123, "api_hash": "hash", "bot_token": "123:abc"},
            {},
            asyncio.Queue(),
        )
        commands = adapter._collect_commands()

        self.assertEqual(
            [(command.command, command.description) for command in commands],
            [
                ("admin", "Status description"),
                ("state", "Status description"),
                ("status", "Status description"),
            ],
        )

    def test_collect_commands_truncates_description_like_builtin_adapter(self):
        _, adapter_module = _load_modules()
        long_description = "x" * 40

        description = adapter_module.TelethonPlatformAdapter._build_command_description(
            types.SimpleNamespace(desc=long_description),
            "status",
            is_group=False,
        )

        self.assertEqual(description, ("x" * 30) + "...")

    def test_sync_bot_commands_swallows_client_errors(self):
        _, adapter_module = _load_modules()

        class _FailingClient:
            async def __call__(self, request):
                raise RuntimeError("boom")

        adapter = adapter_module.TelethonPlatformAdapter(
            {"api_id": 123, "api_hash": "hash", "bot_token": "123:abc"},
            {},
            asyncio.Queue(),
        )
        adapter.client = _FailingClient()
        adapter.sync_bot_commands = True
        adapter._collect_commands = lambda: [
            types.SimpleNamespace(command="status", description="desc")
        ]

        async def _run():
            await adapter._sync_bot_commands()

        asyncio.run(_run())

    def test_apply_menu_button_logs_only_on_mode_change(self):
        _, adapter_module = _load_modules()

        class _CapturingLogger:
            def __init__(self):
                self.info_calls = []
                self.error_calls = []

            def info(self, *args, **kwargs):
                self.info_calls.append((args, kwargs))

            def warning(self, *args, **kwargs):
                return None

            def error(self, *args, **kwargs):
                self.error_calls.append((args, kwargs))

            def debug(self, *args, **kwargs):
                return None

            def exception(self, *args, **kwargs):
                return None

        class _CapturingClient:
            def __init__(self):
                self.requests = []

            async def __call__(self, request):
                self.requests.append(request)
                return request

        adapter = adapter_module.TelethonPlatformAdapter(
            {"api_id": 123, "api_hash": "hash", "bot_token": "123:abc"},
            {},
            asyncio.Queue(),
        )
        adapter.client = _CapturingClient()
        adapter.menu_button_mode = "commands"

        original_logger = adapter_module.logger
        capturing_logger = _CapturingLogger()
        adapter_module.logger = capturing_logger

        async def _run():
            await adapter._apply_menu_button()
            await adapter._apply_menu_button()

        try:
            asyncio.run(_run())
        finally:
            adapter_module.logger = original_logger

        self.assertEqual(len(adapter.client.requests), 2)
        self.assertEqual(len(capturing_logger.info_calls), 1)
        self.assertEqual(capturing_logger.error_calls, [])
