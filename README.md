# Telethon Bot 适配器

为 AstrBot 增加基于 Telethon 的 Telegram Bot 适配器。

English README: [README_EN.md](README_EN.md)

## 功能

- 使用 `bot_token` 登录 Telegram Bot
- 通过 MTProto 协议收发消息与媒体, 不受非自部署 Bot API 50MB 上传限制约束
- 提供 `status` 命令
- 支持 `zh-CN` / `en-US` 多语言运行时文案

## 注意事项

- 该插件平台类型是 `telethon_bot`。
- 适配器不支持平台级流式展示。如果 AstrBot 开启了 `provider_settingsstreaming_response`，请将“不支持流式回复的平台”设置为“关闭流式回复”。

## 安装

将插件目录放置到 `AstrBot` 的 `data/plugins/` 目录下：

```
data/plugins/astrbot_plugin_telethon_bot_adapter/
```
安装插件后，AstrBot 会自动根据 `requirements.txt` 为插件安装依赖库。

依赖里包含 `cryptg`，用于提升 Telethon 的加解密性能。
- 常见 glibc 发行版通常可以直接安装预编译 wheel。
- Alpine Linux 以及其它使用 musl 库的发行版，需要本地编译 `cryptg` 的编译环境，至少需要 `python3-dev`、`musl-dev`、`gcc`、`linux-headers`、`rust`、`cargo`。

## 配置

先在 [my.telegram.org](https://my.telegram.org) 申请 `api_id` 和 `api_hash`。如果无法申请到，更换代理出口 IP 地址。

在 AstrBot 中新增平台适配器并选择 `telethon_bot`，填入：

- `id`: 适配器实例 ID，默认 `telethon_bot`
- `api_id`: Telegram API ID
- `api_hash`: Telegram API Hash
- `bot_token`: 从 `@BotFather` 获取的 bot token
- `language`: `zh-CN` 或 `en-US`
- `reply_to_self_triggers_command`: 是否允许群聊中“回复 Bot 自己的消息”继续触发
- `telethon_command_register`: 连接成功后是否自动同步 AstrBot 已注册命令到 Telegram bot commands
- `menu_button_mode`: `disabled` / `commands`，用于控制 Telegram 私聊 menu button
- `download_incoming_media`: 是否下载收到的媒体
- `incoming_media_ttl_seconds`: 入站媒体本地缓存时间
- `telethon_media_group_timeout`: 媒体组聚合延迟
- `telethon_media_group_max_wait`: 媒体组最大等待时间
- `proxy_type` / `proxy_host` / `proxy_port` / `proxy_username` / `proxy_password` / `proxy_secret`: 可选代理配置

## 命令

`status`

- 查看当前 AstrBot 进程、Telethon 连接状态、数据中心和适配器实例信息
