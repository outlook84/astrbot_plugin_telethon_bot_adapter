"""
Fast upload support for local Telethon media sending.

This file includes logic adapted from AIOFastTelethonHelper:
https://github.com/aron1cx/AIOFastTelethonHelper

Original upstream license: MIT
Original copyright:
- Copyright (c) 2021 MiyukiKun
- Copyright (c) 2025 Aron1cX

Changes in this repository:
- inlined only the upload-related pieces needed by this plugin
- removed the external aiofiles-based dependency path
- integrated the upload handle creation into Telethon media-building flow
- added fallback behavior for the plugin's supported Telethon versions

See THIRD_PARTY_NOTICES.md for the bundled third-party license text.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import os
import pathlib
import re
from typing import Any

try:
    from astrbot.api import logger
except Exception:
    import logging

    logger = logging.getLogger(__name__)


def _debug_logging_enabled(client: Any) -> bool:
    return bool(getattr(client, "telethon_debug_logging", False))

try:
    from telethon import helpers, utils
    from telethon.client.uploads import _resize_photo_if_needed
    from telethon.network import MTProtoSender
    from telethon.tl import types
    from telethon.tl.alltlobjects import LAYER
    from telethon.tl.functions import InvokeWithLayerRequest
    from telethon.tl.functions.auth import (
        ExportAuthorizationRequest,
        ImportAuthorizationRequest,
    )
    from telethon.tl.functions.upload import SaveBigFilePartRequest, SaveFilePartRequest
except Exception as exc:
    helpers = None
    utils = None
    _resize_photo_if_needed = None
    MTProtoSender = Any
    types = None
    LAYER = None
    InvokeWithLayerRequest = None
    ExportAuthorizationRequest = None
    ImportAuthorizationRequest = None
    SaveBigFilePartRequest = None
    SaveFilePartRequest = None
    _FAST_UPLOAD_IMPORT_ERROR = exc
else:
    _FAST_UPLOAD_IMPORT_ERROR = None


def should_use_fast_upload(client: Any, file: Any) -> bool:
    if _FAST_UPLOAD_IMPORT_ERROR is not None:
        return False
    if isinstance(file, pathlib.Path):
        file = str(file.absolute())
    if not isinstance(file, str) or not os.path.isfile(file):
        return False
    required_attrs = (
        "_call",
        "_get_dc",
        "_connection",
        "_log",
        "session",
    )
    if any(not hasattr(client, attr) for attr in required_attrs):
        return False
    session = getattr(client, "session", None)
    enabled = bool(
        session is not None
        and hasattr(session, "dc_id")
        and hasattr(session, "auth_key")
    )
    if enabled and _debug_logging_enabled(client):
        logger.info(
            "[Telethon][Debug] fast_upload_available: path=%s",
            file,
        )
    return enabled


if _FAST_UPLOAD_IMPORT_ERROR is None:
    class _UploadSender:
        def __init__(
            self,
            client: Any,
            sender: MTProtoSender,
            file_id: int,
            part_count: int,
            is_large: bool,
            index: int,
            stride: int,
            loop: asyncio.AbstractEventLoop,
        ) -> None:
            self.client = client
            self.sender = sender
            self.stride = stride
            self.loop = loop
            self.previous: asyncio.Task | None = None
            if is_large:
                self.request = SaveBigFilePartRequest(file_id, index, part_count, b"")
            else:
                self.request = SaveFilePartRequest(file_id, index, b"")

        async def next(self, data: bytes) -> None:
            if self.previous is not None:
                await self.previous
            self.previous = self.loop.create_task(self._next(data))

        async def _next(self, data: bytes) -> None:
            self.request.bytes = data
            await self.client._call(self.sender, self.request)
            self.request.file_part += self.stride

        async def disconnect(self) -> None:
            if self.previous is not None:
                await self.previous
            await self.sender.disconnect()


    class _ParallelTransferrer:
        def __init__(self, client: Any, dc_id: int | None = None) -> None:
            self.client = client
            self.loop = getattr(client, "loop", None) or asyncio.get_running_loop()
            self.dc_id = dc_id or self.client.session.dc_id
            self.auth_key = (
                None
                if dc_id and self.client.session.dc_id != dc_id
                else self.client.session.auth_key
            )
            self.senders: list[_UploadSender] | None = None
            self.upload_ticker = 0

        @staticmethod
        def _get_connection_count(
            file_size: int,
            max_count: int = 20,
            full_size: int = 100 * 1024 * 1024,
        ) -> int:
            if file_size <= 0:
                return 1
            if file_size > full_size:
                return max_count
            return max(1, math.ceil((file_size / full_size) * max_count))

        async def _create_sender(self) -> MTProtoSender:
            sender = MTProtoSender(self.auth_key, loggers=self.client._log)
            dc = await self.client._get_dc(self.dc_id)
            await sender.connect(
                self.client._connection(
                    dc.ip_address,
                    dc.port,
                    dc.id,
                    loggers=self.client._log,
                    proxy=getattr(self.client, "_proxy", None),
                )
            )
            if not self.auth_key:
                auth = await self.client(ExportAuthorizationRequest(self.dc_id))
                self.client._init_request.query = ImportAuthorizationRequest(
                    id=auth.id,
                    bytes=auth.bytes,
                )
                request = InvokeWithLayerRequest(LAYER, self.client._init_request)
                await sender.send(request)
                self.auth_key = sender.auth_key
            return sender

        async def init_upload(
            self,
            file_id: int,
            file_size: int,
            part_size_kb: float | None = None,
            connection_count: int | None = None,
        ) -> tuple[int, int, bool]:
            connection_count = connection_count or self._get_connection_count(file_size)
            part_size = (
                int(part_size_kb * 1024)
                if part_size_kb
                else utils.get_appropriated_part_size(file_size) * 1024
            )
            part_count = (file_size + part_size - 1) // part_size
            is_large = file_size > 10 * 1024 * 1024
            self.senders = [
                _UploadSender(
                    self.client,
                    await self._create_sender(),
                    file_id,
                    part_count,
                    is_large,
                    index,
                    connection_count,
                    self.loop,
                )
                for index in range(connection_count)
            ]
            return part_size, part_count, is_large

        async def upload(self, part: bytes) -> None:
            assert self.senders is not None
            await self.senders[self.upload_ticker].next(part)
            self.upload_ticker = (self.upload_ticker + 1) % len(self.senders)

        async def finish_upload(self) -> None:
            if not self.senders:
                return
            await asyncio.gather(*(sender.disconnect() for sender in self.senders))
            self.senders = None


async def _fast_upload_file(
    client: Any,
    file: str,
    *,
    file_size: int | None = None,
    file_name: str | None = None,
    progress_callback: Any = None,
) -> Any:
    if _FAST_UPLOAD_IMPORT_ERROR is not None:
        raise RuntimeError("fast upload is unavailable") from _FAST_UPLOAD_IMPORT_ERROR

    actual_file_size = file_size if file_size is not None else os.path.getsize(file)
    if _debug_logging_enabled(client):
        logger.info(
            "[Telethon][Debug] fast_upload_start: path=%s size=%s",
            file,
            actual_file_size,
        )
    file_id = helpers.generate_random_long()
    resolved_name = file_name or os.path.basename(file)
    transferrer = _ParallelTransferrer(client)
    part_size, part_count, is_large = await transferrer.init_upload(file_id, actual_file_size)
    hash_md5 = hashlib.md5()
    sent = 0

    try:
        with open(file, "rb") as reader:
            while True:
                part = await asyncio.to_thread(reader.read, part_size)
                if not part:
                    break
                sent += len(part)
                if not is_large:
                    hash_md5.update(part)
                await transferrer.upload(part)
                if progress_callback:
                    await helpers._maybe_await(progress_callback(sent, actual_file_size))
    finally:
        await transferrer.finish_upload()

    if is_large:
        return types.InputFileBig(file_id, part_count, resolved_name)
    return types.InputFile(file_id, part_count, resolved_name, hash_md5.hexdigest())


async def build_input_media(
    client: Any,
    file: Any,
    *,
    force_document: bool = False,
    file_size: int | None = None,
    progress_callback: Any = None,
    attributes: list[Any] | None = None,
    thumb: Any = None,
    allow_cache: bool = True,
    voice_note: bool = False,
    video_note: bool = False,
    supports_streaming: bool = False,
    mime_type: str | None = None,
    as_image: bool | None = None,
    ttl: int | None = None,
    nosound_video: bool | None = None,
) -> tuple[Any, Any, Any]:
    file_to_media = getattr(client, "_file_to_media", None)
    if _FAST_UPLOAD_IMPORT_ERROR is not None or not callable(file_to_media):
        if not callable(file_to_media):
            raise RuntimeError("Telethon client does not expose _file_to_media")
        return await file_to_media(
            file,
            force_document=force_document,
            file_size=file_size,
            progress_callback=progress_callback,
            attributes=attributes,
            thumb=thumb,
            allow_cache=allow_cache,
            voice_note=voice_note,
            video_note=video_note,
            supports_streaming=supports_streaming,
            mime_type=mime_type,
            as_image=as_image,
            ttl=ttl,
            nosound_video=nosound_video,
        )

    if isinstance(file, pathlib.Path):
        file = str(file.absolute())

    is_image = utils.is_image(file)
    if as_image is None:
        as_image = is_image and not force_document

    if not isinstance(file, (str, bytes, types.InputFile, types.InputFileBig)) and not hasattr(
        file, "read"
    ):
        try:
            return (
                None,
                utils.get_input_media(
                    file,
                    is_photo=as_image,
                    attributes=attributes,
                    force_document=force_document,
                    voice_note=voice_note,
                    video_note=video_note,
                    supports_streaming=supports_streaming,
                    ttl=ttl,
                ),
                as_image,
            )
        except TypeError:
            return None, None, as_image

    media = None
    file_handle = None

    if isinstance(file, (types.InputFile, types.InputFileBig)):
        file_handle = file
    elif not isinstance(file, str) or os.path.isfile(file):
        upload_target = _resize_photo_if_needed(file, as_image)
        if (
            should_use_fast_upload(client, upload_target)
            and isinstance(upload_target, str)
            and os.path.isfile(upload_target)
        ):
            file_handle = await _fast_upload_file(
                client,
                upload_target,
                file_size=file_size,
                progress_callback=progress_callback,
            )
        else:
            file_handle = await client.upload_file(
                upload_target,
                file_size=file_size,
                progress_callback=progress_callback,
            )
    elif re.match(r"https?://", file):
        if as_image:
            media = types.InputMediaPhotoExternal(file, ttl_seconds=ttl)
        else:
            media = types.InputMediaDocumentExternal(file, ttl_seconds=ttl)
    else:
        bot_file = utils.resolve_bot_file_id(file)
        if bot_file:
            media = utils.get_input_media(bot_file, ttl=ttl)

    if media:
        return file_handle, media, as_image
    if not file_handle:
        raise ValueError(
            f"Failed to convert {file} to media. Not an existing file, an HTTP URL or a valid bot file ID"
        )
    if as_image:
        return file_handle, types.InputMediaUploadedPhoto(file_handle, ttl_seconds=ttl), as_image

    attributes, mime_type = utils.get_attributes(
        file,
        mime_type=mime_type,
        attributes=attributes,
        force_document=force_document and not is_image,
        voice_note=voice_note,
        video_note=video_note,
        supports_streaming=supports_streaming,
        thumb=thumb,
    )

    if thumb:
        if isinstance(thumb, pathlib.Path):
            thumb = str(thumb.absolute())
        thumb = await client.upload_file(thumb, file_size=file_size)
    else:
        thumb = None

    if mime_type.split("/")[0] != "video":
        nosound_video = None

    return (
        file_handle,
        types.InputMediaUploadedDocument(
            file=file_handle,
            mime_type=mime_type,
            attributes=attributes,
            thumb=thumb,
            force_file=force_document and not is_image,
            ttl_seconds=ttl,
            nosound_video=nosound_video,
        ),
        as_image,
    )
