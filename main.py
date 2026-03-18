from typing import Awaitable, Callable, TypeVar

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from .plugin_info import (
    PLUGIN_AUTHOR,
    PLUGIN_DESC,
    PLUGIN_NAME,
    PLUGIN_REPO,
    PLUGIN_VERSION,
)
from .telethon_adapter.i18n import t
from .telethon_adapter.services import (
    TelethonSender,
    TelethonStatusService,
)
from . import telethon_adapter  # noqa: F401  # import for platform adapter registration

T = TypeVar("T")


@register(PLUGIN_NAME, PLUGIN_AUTHOR, PLUGIN_DESC, PLUGIN_VERSION, PLUGIN_REPO)
class TelethonAdapterPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.context = context
        self._status_service = TelethonStatusService(context)
        self._sender = TelethonSender()

    def _log_command_debug(self, event: AstrMessageEvent, command: str, **kwargs: str) -> None:
        if not bool(getattr(event, "telethon_debug_logging", False)):
            return

        extra = " ".join(f"{key}=%r" for key in kwargs)
        suffix = f" {extra}" if extra else ""
        logger.info(
            f"[Telethon][Debug] {command}: session_id=%s sender_id=%s "
            f"platform_id=%s message_str=%r{suffix}",
            getattr(event, "session_id", None),
            getattr(event, "get_sender_id", lambda: "")(),
            getattr(getattr(event, "platform_meta", None), "id", None),
            getattr(event, "message_str", ""),
            *kwargs.values(),
        )

    async def _send_text_result(
        self,
        event: AstrMessageEvent,
        text: str,
        *,
        auto_delete_after: float | None = None,
        link_preview: bool = False,
        **log_kwargs: str,
    ) -> bool:
        try:
            sent_message = await self._sender.send_html_message(
                event,
                text,
                link_preview=link_preview,
            )
        except ValueError:
            event.set_result(text)
            return False
        except Exception as exc:
            logger.exception("[Telethon] Failed to send result", extra=log_kwargs or None)
            event.set_result(t(event, "errors.send_result_failed", error=exc))
            return False
        else:
            if auto_delete_after is not None:
                self._sender.schedule_delete_message(
                    event,
                    sent_message,
                    auto_delete_after,
                )
            return True

    async def _run_query_command(
        self,
        event: AstrMessageEvent,
        *,
        log_name: str,
        failure_key: str,
        execute: Callable[[], Awaitable[T]],
        send_result: Callable[[T], Awaitable[object]],
    ) -> None:
        self._log_command_debug(event, log_name)

        try:
            payload = await execute()
        except ValueError as exc:
            event.set_result(str(exc))
            return
        except Exception as exc:
            logger.exception("[Telethon] Command %s failed", log_name.removeprefix("tg_"))
            event.set_result(t(event, failure_key, error=exc))
            return

        await send_result(payload)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("status")
    async def tg_status(self, event: AstrMessageEvent) -> None:
        """获取当前 AstrBot 进程的运行状态. Show current AstrBot process status. status"""
        async def _execute():
            return await self._status_service.build_status_text(event)

        async def _send(status_text: str) -> bool:
            return await self._send_text_result(event, status_text)

        await self._run_query_command(
            event,
            log_name="tg_status",
            failure_key="errors.status_failed",
            execute=_execute,
            send_result=_send,
        )
