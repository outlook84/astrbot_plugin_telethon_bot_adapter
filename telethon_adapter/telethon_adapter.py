from __future__ import annotations

import asyncio
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any

from astrbot.api import logger
from astrbot.api.event import MessageChain
from astrbot.api.platform import (
    AstrBotMessage,
    Platform,
    PlatformMetadata,
    register_platform_adapter,
)
from astrbot.core.platform.astr_message_event import MessageSesion
try:
    from astrbot.core.star.filter.command import CommandFilter
    from astrbot.core.star.filter.command_group import CommandGroupFilter
    from astrbot.core.star.star import star_map
    from astrbot.core.star.star_handler import star_handlers_registry
except ImportError:
    CommandFilter = None
    CommandGroupFilter = None
    star_map = {}
    star_handlers_registry = []

try:
    from astrbot.core.utils.astrbot_path import get_astrbot_temp_path
except ImportError:
    get_astrbot_temp_path = None
try:
    from python_socks import ProxyType
except ImportError:
    ProxyType = None

from telethon import TelegramClient, events, functions, types
try:
    from telethon import errors as telethon_errors
except ImportError:
    telethon_errors = None
from telethon.network import connection
from telethon.sessions import MemorySession
from .config import (
    DEFAULT_CONFIG_TEMPLATE,
    TELETHON_CONFIG_METADATA,
    TELETHON_I18N_RESOURCES,
    apply_config,
    config_error,
    validate_config,
)
from .message_converter import TelethonMessageConverter
from .telethon_event import TelethonEvent

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TELETHON_AUTO_RECONNECT = True
TELETHON_CONNECTION_RETRIES = 5
TELETHON_RETRY_DELAY_SECONDS = 1
OUTER_RECONNECT_BASE_DELAY_SECONDS = 1.0
OUTER_RECONNECT_MAX_DELAY_SECONDS = 30.0
OUTER_RECONNECT_RESET_AFTER_SECONDS = 300.0
TELEGRAM_MAX_FILE_BYTES_DEFAULT = 2_097_152_000


@register_platform_adapter(
    "telethon_bot",
    "Telethon Bot 适配器",
    logo_path=str(PLUGIN_ROOT / "logo.png"),
    support_streaming_message=False,
    default_config_tmpl=DEFAULT_CONFIG_TEMPLATE,
    config_metadata=TELETHON_CONFIG_METADATA,
    i18n_resources=TELETHON_I18N_RESOURCES,
)
class TelethonPlatformAdapter(Platform):
    def __init__(
        self,
        platform_config: dict,
        platform_settings: dict,
        event_queue: asyncio.Queue,
    ) -> None:
        super().__init__(platform_config, event_queue)
        self.settings = platform_settings

        apply_config(self)

        self.client: TelegramClient | None = None
        self.self_id = ""
        self.self_username = ""
        self._running = False
        self._stop_requested = False
        self._main_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None
        self._profile_sync_task: asyncio.Task | None = None
        self._retry_sleep_task: asyncio.Task | None = None
        self._reconnect_attempt = 0
        self._next_reconnect_at_monotonic: float | None = None
        self._last_disconnect_reason = ""
        self._last_disconnect_at_unix: float | None = None
        self._media_group_cache: dict[tuple[str, int], dict[str, Any]] = {}
        self._recent_event_keys: dict[tuple[str, int], float] = {}
        self._recent_event_keys_cleanup_at = 0.0
        self._downloaded_temp_files: dict[str, float] = {}
        self._media_temp_dir = self._build_media_temp_dir()
        self._message_converter = TelethonMessageConverter(self)
        self._last_command_signature: tuple[tuple[str, str], ...] | None = None
        self._last_applied_menu_button_mode: str | None = None

    def meta(self) -> PlatformMetadata:
        adapter_id = str(self.config.get("id") or "telethon_bot")
        return PlatformMetadata(
            name="telethon_bot",
            description="Telethon Bot Adapter",
            id=adapter_id,
            support_streaming_message=False,
        )

    async def run(self):
        validate_config(self)

        client_kwargs = self._build_client_kwargs()
        retry_attempt = 0

        try:
            self._running = True
            if self.incoming_media_ttl_seconds > 0:
                self._cleanup_task = asyncio.create_task(self._cleanup_temp_files_loop())
            self._stop_requested = False

            while not self._stop_requested:
                loop = asyncio.get_running_loop()
                run_started_at = loop.time()
                disconnected_cleanly = False
                try:
                    await self._run_client_once(client_kwargs)
                    disconnected_cleanly = True
                    if not self._stop_requested:
                        should_retry_clean_disconnect = await self._should_retry_clean_disconnect()
                        if not should_retry_clean_disconnect:
                            raise RuntimeError(
                                "[Telethon] Client disconnected and the current session is no longer authorized."
                            )
                except asyncio.CancelledError:
                    logger.info("[Telethon] Adapter task cancelled")
                    raise
                except Exception as exc:
                    if not self._should_retry_client_error(exc):
                        self._record_disconnect(self._describe_disconnect_reason(exc))
                        raise
                    self._record_disconnect(self._describe_disconnect_reason(exc))
                    logger.exception("[Telethon] Client loop failed; recreating TelegramClient")
                finally:
                    uptime = loop.time() - run_started_at
                    await self._disconnect_current_client()

                if self._stop_requested:
                    break

                if disconnected_cleanly:
                    self._record_disconnect("clean_disconnect")
                    logger.warning(
                        "[Telethon] Client disconnected. Recreating TelegramClient: uptime=%.1fs",
                        uptime,
                    )

                if uptime >= OUTER_RECONNECT_RESET_AFTER_SECONDS:
                    retry_attempt = 0
                retry_attempt += 1
                self._reconnect_attempt = retry_attempt
                delay = self._compute_reconnect_delay(retry_attempt)
                self._next_reconnect_at_monotonic = loop.time() + delay
                logger.warning(
                    "[Telethon] Reconnect attempt #%s scheduled in %.1fs",
                    retry_attempt,
                    delay,
                )
                await self._sleep_before_reconnect(delay)
                self._next_reconnect_at_monotonic = None
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            await self.terminate()

    async def terminate(self) -> None:
        self._stop_requested = True

        if self._retry_sleep_task and not self._retry_sleep_task.done():
            self._retry_sleep_task.cancel()
            try:
                await self._retry_sleep_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._profile_sync_task and not self._profile_sync_task.done():
            self._profile_sync_task.cancel()
            try:
                await self._profile_sync_task
            except asyncio.CancelledError:
                pass

        for entry in self._media_group_cache.values():
            task = entry.get("task")
            if task and not task.done():
                task.cancel()
        self._media_group_cache.clear()
        await self._cleanup_expired_temp_files(force=True)
        self._remove_media_temp_dir_if_empty()
        await self._cleanup_bot_profile()
        await self._disconnect_current_client()

    async def send_by_session(
        self, session: MessageSesion, message_chain: MessageChain
    ) -> None:
        if not self.client:
            raise RuntimeError("[Telethon] Client is not initialized")

        inner_message = AstrBotMessage()
        inner_message.session_id = session.session_id
        inner_message.type = session.message_type
        message_event = TelethonEvent(
            message_str=message_chain.get_plain_text(),
            message_obj=inner_message,
            platform_meta=self.meta(),
            session_id=session.session_id,
            client=self.client,
        )
        message_event.adapter_capability = self._build_adapter_capability()
        message_event.telethon_language = self.language
        await message_event.send(message_chain)
        await super().send_by_session(session, message_chain)

    def get_client(self):
        return self.client

    def get_reconnect_status(self) -> dict[str, Any]:
        next_retry_in_seconds: float | None = None
        if self._next_reconnect_at_monotonic is not None:
            next_retry_in_seconds = max(
                0.0,
                self._next_reconnect_at_monotonic - time.monotonic(),
            )

        state = "stopped"
        if self._retry_sleep_task and not self._retry_sleep_task.done():
            state = "reconnecting"
        elif self.client is not None:
            state = "connected"
        elif self._running:
            state = "connecting"

        return {
            "state": state,
            "retry_attempt": self._reconnect_attempt,
            "next_retry_in_seconds": next_retry_in_seconds,
            "last_disconnect_reason": self._last_disconnect_reason,
            "last_disconnect_at_unix": self._last_disconnect_at_unix,
        }

    async def _run_client_once(self, client_kwargs: dict[str, Any]) -> None:
        self.client = self._create_client(client_kwargs)
        await self.client.start(bot_token=self.bot_token)
        if not await self.client.is_user_authorized():
            raise RuntimeError(
                "[Telethon] The current bot_token is unauthorized. Please check the configured bot token."
            )

        me = await self.client.get_me()
        self.self_id = str(me.id)
        self.self_username = str(getattr(me, "username", "") or "").strip().lower()
        await self._sync_bot_profile()
        self._start_profile_sync_task()

        logger.info(
            "[Telethon] Bot started: %s username=%s "
            "download_incoming_media=%s incoming_media_ttl_seconds=%s "
            "reply_to_self_triggers_command=%s debug_logging=%s proxy_type=%s "
            "proxy_host=%s proxy_port=%s raw_config=%s",
            self.self_id,
            self.self_username,
            self.download_incoming_media,
            self.incoming_media_ttl_seconds,
            self.reply_to_self_triggers_command,
            self.debug_logging,
            self.proxy_type or "direct",
            self.proxy_host or "",
            self.proxy_port or 0,
            {
                "reply_to_self_triggers_command": self.config.get(
                    "reply_to_self_triggers_command"
                ),
                "download_incoming_media": self.config.get("download_incoming_media"),
                "incoming_media_ttl_seconds": self.config.get(
                    "incoming_media_ttl_seconds"
                ),
                "debug_logging": self.config.get("debug_logging"),
                "proxy_type": self.config.get("proxy_type"),
                "proxy_host": self.config.get("proxy_host"),
                "proxy_port": self.config.get("proxy_port"),
                "proxy_rdns": self.config.get("proxy_rdns"),
            },
        )
        self.client.add_event_handler(
            self._on_new_message,
            events.NewMessage(incoming=True, outgoing=False),
        )
        if self.debug_logging:
            self.client.add_event_handler(self._on_raw_event, events.Raw())

        self._main_task = asyncio.create_task(self.client.run_until_disconnected())
        await self._main_task

    async def _sync_bot_profile(self) -> None:
        if not self.client:
            return
        await self._sync_bot_commands()
        await self._apply_menu_button()

    async def _sync_bot_commands(self) -> None:
        if not self.client or not self.sync_bot_commands:
            return

        try:
            commands = self._collect_commands()
            if not commands:
                return

            command_signature = tuple(
                (command.command, command.description) for command in commands
            )
            if command_signature == self._last_command_signature:
                return

            await self.client(
                functions.bots.SetBotCommandsRequest(
                    scope=types.BotCommandScopeDefault(),
                    lang_code="",
                    commands=commands,
                )
            )
            self._last_command_signature = command_signature
            logger.info(
                "[Telethon] Synced %s bot commands to Telegram",
                len(commands),
            )
        except Exception as exc:
            logger.error("[Telethon] Failed to sync bot commands: %s", exc)

    async def _apply_menu_button(self) -> None:
        if not self.client or self.menu_button_mode == "disabled":
            return

        try:
            if self.menu_button_mode == "commands":
                button = types.BotMenuButtonCommands()
            else:
                button = types.BotMenuButtonDefault()

            await self.client(
                functions.bots.SetBotMenuButtonRequest(
                    user_id=types.InputUserSelf(),
                    button=button,
                )
            )
            if self._last_applied_menu_button_mode != self.menu_button_mode:
                logger.info(
                    "[Telethon] Applied menu button mode: %s",
                    self.menu_button_mode,
                )
            self._last_applied_menu_button_mode = self.menu_button_mode
        except Exception as exc:
            logger.error(
                "[Telethon] Failed to apply menu button mode %s: %s",
                self.menu_button_mode,
                exc,
            )

    def _start_profile_sync_task(self) -> None:
        if self._profile_sync_task and not self._profile_sync_task.done():
            self._profile_sync_task.cancel()
        if not self.command_auto_refresh:
            self._profile_sync_task = None
            return
        if not self.sync_bot_commands and self.menu_button_mode == "disabled":
            self._profile_sync_task = None
            return
        self._profile_sync_task = asyncio.create_task(self._profile_sync_loop())

    async def _profile_sync_loop(self) -> None:
        try:
            while not self._stop_requested:
                await asyncio.sleep(self.command_refresh_interval)
                if self._stop_requested or not self.client:
                    break
                await self._sync_bot_profile()
        except asyncio.CancelledError:
            raise

    async def _cleanup_bot_profile(self) -> None:
        if not self.client:
            return

        if self.sync_bot_commands:
            try:
                await self.client(
                    functions.bots.SetBotCommandsRequest(
                        scope=types.BotCommandScopeDefault(),
                        lang_code="",
                        commands=[],
                    )
                )
                self._last_command_signature = None
            except Exception as exc:
                logger.error(
                    "[Telethon] Failed to clear bot commands during shutdown: %s",
                    exc,
                )

        if self.menu_button_mode != "disabled":
            try:
                await self.client(
                    functions.bots.SetBotMenuButtonRequest(
                        user_id=types.InputUserSelf(),
                        button=types.BotMenuButtonDefault(),
                    )
                )
            except Exception as exc:
                logger.error(
                    "[Telethon] Failed to reset menu button during shutdown: %s",
                    exc,
                )
            finally:
                self._last_applied_menu_button_mode = None

    def _collect_commands(self) -> list[types.BotCommand]:
        if CommandFilter is None or CommandGroupFilter is None:
            return []

        command_dict: dict[str, str] = {}
        skip_commands = {"start"}

        for handler_metadata in star_handlers_registry:
            plugin = star_map.get(handler_metadata.handler_module_path)
            if plugin is None or not getattr(plugin, "activated", False):
                continue
            if not getattr(handler_metadata, "enabled", False):
                continue
            for event_filter in getattr(handler_metadata, "event_filters", []):
                for cmd_name, description in self._extract_command_info(
                    event_filter,
                    handler_metadata,
                    skip_commands,
                ):
                    if cmd_name in command_dict:
                        logger.warning(
                            "[Telethon] Duplicate command registration ignored: %s",
                            cmd_name,
                        )
                        continue
                    command_dict[cmd_name] = description

        return [
            types.BotCommand(command=cmd_name, description=command_dict[cmd_name])
            for cmd_name in sorted(command_dict)
        ]

    @staticmethod
    def _extract_command_info(
        event_filter: Any,
        handler_metadata: Any,
        skip_commands: set[str],
    ) -> list[tuple[str, str]]:
        cmd_names: list[str] = []
        is_group = False

        if CommandFilter is not None and isinstance(event_filter, CommandFilter):
            command_name = getattr(event_filter, "command_name", "")
            if not command_name:
                return []
            parent_command_names = getattr(event_filter, "parent_command_names", None)
            if parent_command_names and parent_command_names != [""]:
                return []
            cmd_names = [command_name]
            alias = getattr(event_filter, "alias", None) or []
            cmd_names.extend(alias)
        elif CommandGroupFilter is not None and isinstance(event_filter, CommandGroupFilter):
            if getattr(event_filter, "parent_group", None):
                return []
            group_name = getattr(event_filter, "group_name", "")
            if not group_name:
                return []
            cmd_names = [group_name]
            is_group = True

        result: list[tuple[str, str]] = []
        for cmd_name in cmd_names:
            if not cmd_name or cmd_name in skip_commands:
                continue
            if not re.match(r"^[a-z0-9_]+$", cmd_name) or len(cmd_name) > 32:
                continue
            description = TelethonPlatformAdapter._build_command_description(
                handler_metadata,
                cmd_name,
                is_group=is_group,
            )
            result.append((cmd_name, description))
        return result

    @staticmethod
    def _build_command_description(
        handler_metadata: Any,
        cmd_name: str,
        *,
        is_group: bool,
    ) -> str:
        description = getattr(handler_metadata, "desc", "") or (
            f"Command group: {cmd_name}" if is_group else f"Command: {cmd_name}"
        )
        if len(description) > 30:
            description = description[:30] + "..."
        return description

    def _create_client(self, client_kwargs: dict[str, Any]) -> TelegramClient:
        return TelegramClient(
            MemorySession(),
            self.api_id,
            self.api_hash,
            **client_kwargs,
        )

    async def _disconnect_current_client(self) -> None:
        client = self.client
        task = self._main_task
        self.client = None
        self._main_task = None
        self._last_applied_menu_button_mode = None
        profile_sync_task = self._profile_sync_task
        self._profile_sync_task = None

        if profile_sync_task and not profile_sync_task.done():
            profile_sync_task.cancel()
            try:
                await profile_sync_task
            except asyncio.CancelledError:
                pass

        if client:
            try:
                await client.disconnect()
            except Exception:
                logger.exception("[Telethon] Failed to close connection")

        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    def _should_retry_client_error(self, exc: Exception) -> bool:
        if self._stop_requested:
            return False
        if self._is_fatal_client_error(exc):
            return False
        if isinstance(exc, (OSError, ConnectionError, TimeoutError, asyncio.TimeoutError)):
            return True
        if telethon_errors and isinstance(
            exc,
            self._retryable_telethon_error_types(),
        ):
            return True
        return False

    async def _should_retry_clean_disconnect(self) -> bool:
        if not self.client or self._stop_requested:
            return False
        try:
            return bool(await self.client.is_user_authorized())
        except Exception as exc:
            return self._should_retry_client_error(exc)

    def _is_fatal_client_error(self, exc: Exception) -> bool:
        if isinstance(exc, ValueError):
            return True
        message = str(exc).lower()
        if "unauthorized" in message or "bot_token" in message:
            return True
        if telethon_errors and isinstance(
            exc,
            self._fatal_telethon_error_types(),
        ):
            return True
        return False

    def _retryable_telethon_error_types(self) -> tuple[type[BaseException], ...]:
        if telethon_errors is None:
            return ()
        retryable = [
            getattr(telethon_errors, "ServerError", None),
            getattr(telethon_errors, "TimedOutError", None),
        ]
        return tuple(error_type for error_type in retryable if error_type is not None)

    def _fatal_telethon_error_types(self) -> tuple[type[BaseException], ...]:
        if telethon_errors is None:
            return ()
        common_module = getattr(telethon_errors, "common", None)
        fatal = [
            getattr(telethon_errors, "UnauthorizedError", None),
            getattr(telethon_errors, "AuthKeyError", None),
            getattr(telethon_errors, "BadRequestError", None),
            getattr(telethon_errors, "ForbiddenError", None),
            getattr(telethon_errors, "NotFoundError", None),
            getattr(telethon_errors, "InvalidDCError", None),
            getattr(common_module, "AuthKeyNotFound", None),
            getattr(common_module, "SecurityError", None),
            getattr(common_module, "InvalidBufferError", None),
        ]
        retryable = set(self._retryable_telethon_error_types())
        ordered: list[type[BaseException]] = []
        for error_type in fatal:
            if error_type is None or error_type in retryable or error_type in ordered:
                continue
            ordered.append(error_type)
        return tuple(ordered)

    def _compute_reconnect_delay(self, retry_attempt: int) -> float:
        exponent = max(0, retry_attempt - 1)
        delay = OUTER_RECONNECT_BASE_DELAY_SECONDS * (2 ** exponent)
        return min(delay, OUTER_RECONNECT_MAX_DELAY_SECONDS)

    async def _sleep_before_reconnect(self, delay: float) -> None:
        self._retry_sleep_task = asyncio.create_task(asyncio.sleep(delay))
        try:
            await self._retry_sleep_task
        except asyncio.CancelledError:
            if not self._stop_requested:
                raise
        finally:
            self._retry_sleep_task = None
            self._next_reconnect_at_monotonic = None

    def _record_disconnect(self, reason: str) -> None:
        self._last_disconnect_reason = str(reason or "").strip() or "unknown"
        self._last_disconnect_at_unix = time.time()

    @staticmethod
    def _describe_disconnect_reason(exc: Exception) -> str:
        message = str(exc).strip()
        if message:
            return message
        return exc.__class__.__name__

    def _build_client_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "auto_reconnect": TELETHON_AUTO_RECONNECT,
            "connection_retries": TELETHON_CONNECTION_RETRIES,
            "retry_delay": TELETHON_RETRY_DELAY_SECONDS,
        }
        if not self.proxy_type:
            return kwargs

        if not self.proxy_host or not self.proxy_port:
            raise ValueError("[Telethon] Proxy is configured, but proxy_host or proxy_port is missing")

        if self.proxy_type in {"socks5", "socks4", "http"}:
            if ProxyType is None:
                raise RuntimeError(
                    "[Telethon] SOCKS/HTTP proxy is configured, but python-socks is not installed"
                )
            proxy_type_map = {
                "socks5": ProxyType.SOCKS5,
                "socks4": ProxyType.SOCKS4,
                "http": ProxyType.HTTP,
            }
            kwargs["proxy"] = (
                proxy_type_map[self.proxy_type],
                self.proxy_host,
                self.proxy_port,
                self.proxy_rdns,
                self.proxy_username or None,
                self.proxy_password or None,
            )
            return kwargs

        if self.proxy_type == "mtproto":
            if not self.proxy_secret:
                raise ValueError(
                    "[Telethon] MTProto proxy requires proxy_secret"
                )
            mtproto_connection = getattr(
                connection, "ConnectionTcpMTProxyRandomizedIntermediate", None
            ) or getattr(connection, "ConnectionTcpMTProxyIntermediate", None)
            if mtproto_connection is None:
                raise RuntimeError(
                    "[Telethon] The current Telethon version does not provide an MTProto proxy connection class"
                )
            kwargs["connection"] = mtproto_connection
            kwargs["proxy"] = (
                self.proxy_host,
                self.proxy_port,
                self.proxy_secret,
            )
            return kwargs

        raise ValueError(
            "[Telethon] Unsupported proxy_type. Valid values: socks5, socks4, http, mtproto"
        )

    def _config_error(self, field_name: str, current_value: Any, suggestion: str) -> ValueError:
        return config_error(field_name, current_value, suggestion)

    def _validate_config(self) -> None:
        validate_config(self)

    def _log_unprocessed(self, message: str, *args: Any) -> None:
        if self.debug_logging:
            logger.info(message, *args)

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        if not self._running:
            return
        if not getattr(event, "message", None):
            self._log_unprocessed("[Telethon] Ignoring message: empty event.message")
            return
        if self._message_converter.is_topic_service_message(event.message):
            self._log_unprocessed(
                "[Telethon] Ignoring topic service message: chat_id=%s msg_id=%s action=%s",
                getattr(event, "chat_id", None),
                getattr(event.message, "id", None),
                type(getattr(event.message, "action", None)).__name__,
            )
            return

        event_key = (
            str(getattr(event, "chat_id", "")),
            int(getattr(event.message, "id", 0)),
        )
        loop = asyncio.get_running_loop()
        now = loop.time()
        if now >= self._recent_event_keys_cleanup_at:
            stale_keys = [
                key for key, seen_at in self._recent_event_keys.items() if now - seen_at > 30
            ]
            for key in stale_keys:
                self._recent_event_keys.pop(key, None)
            self._recent_event_keys_cleanup_at = now + 30
        if event_key in self._recent_event_keys:
            self._log_unprocessed("[Telethon] Ignoring message: duplicate event %s", event_key)
            return
        self._recent_event_keys[event_key] = now

        self._log_unprocessed(
            "[Telethon] Received message event: chat_id=%s sender_id=%s out=%s private=%s text=%r",
            getattr(event, "chat_id", None),
            getattr(event, "sender_id", None),
            getattr(event.message, "out", None) if getattr(event, "message", None) else None,
            getattr(event, "is_private", None),
            getattr(event.message, "raw_text", "") if getattr(event, "message", None) else "",
        )
        if self.debug_logging:
            peer = getattr(getattr(event, "message", None), "peer_id", None)
            self._log_unprocessed(
                "[Telethon][Debug] raw_event: chat_id=%s sender_id=%s peer_type=%s "
                "msg_id=%s grouped_id=%s out=%s private=%s",
                getattr(event, "chat_id", None),
                getattr(event, "sender_id", None),
                type(peer).__name__ if peer is not None else None,
                getattr(getattr(event, "message", None), "id", None),
                getattr(getattr(event, "message", None), "grouped_id", None),
                getattr(getattr(event, "message", None), "out", None),
                getattr(event, "is_private", None),
            )
        grouped_id = getattr(event.message, "grouped_id", None)
        if grouped_id:
            await self._handle_grouped_message(
                event,
                self._grouped_message_session_id(event),
                int(grouped_id),
            )
            return

        is_private = self._message_converter.resolve_is_private(
            event.message,
            getattr(event, "is_private", False),
        )

        try:
            abm = await self._convert_message(event, include_reply=True)
        except Exception:
            logger.exception(
                "[Telethon] Failed to convert message: chat_id=%s msg_id=%s sender_id=%s reply_to=%s",
                getattr(event, "chat_id", None),
                getattr(event.message, "id", None),
                getattr(event, "sender_id", None),
                getattr(getattr(event.message, "reply_to", None), "reply_to_msg_id", None),
            )
            return

        logger.info(
            "[Telethon] Committing AstrBot event: session_id=%s type=%s sender=%s text=%r",
            getattr(abm, "session_id", None),
            getattr(abm, "type", None),
            getattr(getattr(abm, "sender", None), "user_id", None),
            getattr(abm, "message_str", ""),
        )
        if self.debug_logging:
            logger.info(
                "[Telethon][Debug] commit_event: platform_id=%s self_id=%s session_id=%s "
                "message_id=%s type=%s text=%r",
                getattr(self.meta(), "id", None),
                getattr(abm, "self_id", None),
                getattr(abm, "session_id", None),
                getattr(abm, "message_id", None),
                getattr(abm, "type", None),
                getattr(abm, "message_str", ""),
            )
        self._commit_abm(abm)

    async def _on_raw_event(self, event: events.Raw) -> None:
        if not self._running:
            return

        update = getattr(event, "update", None)
        if update is None:
            return

        update_name = type(update).__name__
        message = getattr(update, "message", None)
        if message is None:
            return

        peer_id = getattr(message, "peer_id", None)
        from_id = getattr(message, "from_id", None)
        raw_text = getattr(message, "message", "")
        out = getattr(message, "out", None)
        msg_id = getattr(message, "id", None)

        logger.info(
            "[Telethon][Raw] update=%s msg_id=%s out=%s peer_id=%s from_id=%s text=%r",
            update_name,
            msg_id,
            out,
            type(peer_id).__name__ if peer_id else None,
            type(from_id).__name__ if from_id else None,
            raw_text,
        )

    def _commit_abm(self, abm: AstrBotMessage) -> None:
        message_event = TelethonEvent(
            message_str=abm.message_str,
            message_obj=abm,
            platform_meta=self.meta(),
            session_id=abm.session_id,
            client=self.client,
        )
        message_event.adapter_capability = self._build_adapter_capability()
        message_event.telethon_debug_logging = self.debug_logging
        message_event.telethon_language = self.language
        self.commit_event(message_event)

    @staticmethod
    def _build_adapter_capability() -> dict[str, Any]:
        return {
            "supports_media_group": True,
            "supports_spoiler": True,
            "max_items": 10,
            "supported_types": ["image", "video"],
            "supports_mixed_types": True,
            "upload_constraints": {
                "max_single_file_bytes": TELEGRAM_MAX_FILE_BYTES_DEFAULT,
                "max_total_group_bytes": None,
            },
        }

    async def _handle_grouped_message(
        self,
        event: events.NewMessage.Event,
        session_id: str,
        grouped_id: int,
    ) -> None:
        cache_key = (session_id, grouped_id)
        loop = asyncio.get_running_loop()
        now = loop.time()
        entry = self._media_group_cache.get(cache_key)
        if not entry:
            entry = {
                "created_at": now,
                "items": [],
                "task": None,
            }
            self._media_group_cache[cache_key] = entry

        entry["items"].append(event)
        elapsed = now - float(entry["created_at"])
        delay = 0 if elapsed >= self.media_group_max_wait else self.media_group_timeout

        task = entry.get("task")
        if task and not task.done():
            task.cancel()
        entry["task"] = asyncio.create_task(
            self._process_grouped_message(cache_key, delay)
        )

    async def _process_grouped_message(
        self,
        cache_key: tuple[str, int],
        delay: float,
    ) -> None:
        try:
            if delay > 0:
                await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return

        entry = self._media_group_cache.pop(cache_key, None)
        if not entry:
            return

        events_list = entry.get("items", [])
        if not events_list:
            return
        session_id, grouped_id = cache_key
        events_list = sorted(events_list, key=lambda e: int(getattr(e.message, "id", 0)))

        trigger_event = events_list[0]

        try:
            merged = await self._convert_message(trigger_event, include_reply=True)
        except Exception:
            logger.exception(
                "[Telethon] Failed to convert media group primary message: session_id=%s chat_id=%s grouped_id=%s msg_id=%s sender_id=%s reply_to=%s",
                session_id,
                getattr(trigger_event, "chat_id", None),
                grouped_id,
                getattr(trigger_event.message, "id", None),
                getattr(trigger_event, "sender_id", None),
                getattr(
                    getattr(trigger_event.message, "reply_to", None),
                    "reply_to_msg_id",
                    None,
                ),
            )
            return

        for extra_event in events_list:
            if extra_event is trigger_event:
                continue
            try:
                extra = await self._convert_message(extra_event, include_reply=False)
            except Exception:
                logger.exception(
                    "[Telethon] Failed to convert media group child message: session_id=%s chat_id=%s grouped_id=%s msg_id=%s sender_id=%s reply_to=%s",
                    session_id,
                    getattr(extra_event, "chat_id", None),
                    grouped_id,
                    getattr(extra_event.message, "id", None),
                    getattr(extra_event, "sender_id", None),
                    getattr(
                        getattr(extra_event.message, "reply_to", None),
                        "reply_to_msg_id",
                        None,
                    ),
                )
                continue

            merged.message.extend(extra.message)
            if not merged.message_str and extra.message_str:
                merged.message_str = extra.message_str

        if not merged.message_str:
            merged.message_str = "[媒体组]"
        self._commit_abm(merged)

    def _grouped_message_session_id(self, event: events.NewMessage.Event) -> str:
        message = getattr(event, "message", None)
        is_private = self._message_converter.resolve_is_private(
            message,
            getattr(event, "is_private", False),
        )
        chat_id = str(getattr(event, "chat_id", ""))
        thread_id = None if is_private else self._message_converter.extract_thread_id(message)
        return self._message_converter.build_session_id(
            chat_id,
            thread_id,
            is_private=is_private,
        )

    def _get_media_temp_dir(self) -> str:
        os.makedirs(self._media_temp_dir, exist_ok=True)
        return self._media_temp_dir

    def _build_media_temp_dir(self) -> str:
        base_dir = tempfile.gettempdir()
        if get_astrbot_temp_path:
            try:
                base_dir = str(get_astrbot_temp_path())
            except Exception:
                logger.warning(
                    "[Telethon] Failed to get AstrBot temp directory, falling back to the system temp directory: adapter_id=%s",
                    self.config.get("id") or "telethon_bot",
                    exc_info=True,
                )

        adapter_id = str(self.config.get("id") or "telethon_bot").strip() or "telethon_bot"
        safe_adapter_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", adapter_id)
        return os.path.join(base_dir, f"telethon_adapter_{safe_adapter_id}")

    def _register_temp_file(self, path: str) -> None:
        if path:
            expires_at = 0.0
            if self.incoming_media_ttl_seconds > 0:
                expires_at = asyncio.get_running_loop().time() + self.incoming_media_ttl_seconds
            self._downloaded_temp_files[os.path.abspath(path)] = expires_at

    async def _cleanup_temp_files_loop(self) -> None:
        interval = min(max(self.incoming_media_ttl_seconds / 2, 30.0), 300.0)
        try:
            while self._running:
                await asyncio.sleep(interval)
                await self._cleanup_expired_temp_files(force=False)
        except asyncio.CancelledError:
            return

    async def _cleanup_expired_temp_files(self, force: bool) -> None:
        if not self._downloaded_temp_files:
            return

        now = asyncio.get_running_loop().time()
        for path, expires_at in list(self._downloaded_temp_files.items()):
            if not force and expires_at > 0 and now < expires_at:
                continue
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                logger.exception("[Telethon] Failed to clean up temporary media file: %s", path)
                continue
            self._downloaded_temp_files.pop(path, None)
        if force or not self._downloaded_temp_files:
            self._remove_media_temp_dir_if_empty()

    def _remove_media_temp_dir_if_empty(self) -> None:
        if not self._media_temp_dir:
            return
        if not os.path.isdir(self._media_temp_dir):
            return
        try:
            if not os.listdir(self._media_temp_dir):
                os.rmdir(self._media_temp_dir)
        except OSError:
            pass

    async def _convert_message(
        self,
        event: events.NewMessage.Event,
        include_reply: bool = True,
    ) -> AstrBotMessage:
        return await self._message_converter.convert_message(event, include_reply)
