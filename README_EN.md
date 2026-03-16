# Telethon Bot Adapter

A Telegram Bot adapter for AstrBot built on top of Telethon.

## Features

- Log in with a Telegram `bot_token`
- Receive and send Telegram messages through MTProto protocol, without the 50MB upload limit of non-self-hosted Bot APIs
- Provide the `status` command
- Runtime text supports `zh-CN` and `en-US`

## Notes

- The adapter reports platform type `telethon_bot`.
- Platform-level streaming display is unsupported. If AstrBot has `provider_settings.streaming_response` enabled, please disable it for this adapter.

## Configuration

First, apply for `api_id` and `api_hash` at [my.telegram.org](https://my.telegram.org). If you cannot apply for them, change the egress IP address.

Add a platform adapter in AstrBot and choose `telethon_bot`, then fill in:

- `id`: adapter instance ID, default `telethon_bot`
- `api_id`: Telegram API ID
- `api_hash`: Telegram API Hash
- `bot_token`: bot token from `@BotFather`
- `language`: `zh-CN` or `en-US`
- `reply_to_self_triggers_command`: whether replying to a bot message in groups should continue triggering commands
- `telethon_command_register`: whether to automatically sync registered AstrBot commands to Telegram bot commands after connect
- `menu_button_mode`: `disabled` / `commands`, controls the Telegram private chat menu button
- `download_incoming_media`: whether to download incoming media
- `incoming_media_ttl_seconds`: local TTL for downloaded incoming media
- `telethon_media_group_timeout`: media group debounce delay
- `telethon_media_group_max_wait`: maximum media group wait time
- `proxy_type` / `proxy_host` / `proxy_port` / `proxy_username` / `proxy_password` / `proxy_secret`: optional proxy settings

## Command

`status`

- Show AstrBot runtime status, Telethon connection state, data center, and adapter instance info
