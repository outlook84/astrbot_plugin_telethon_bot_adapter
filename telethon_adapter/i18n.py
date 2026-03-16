from __future__ import annotations

from typing import Any

SUPPORTED_LANGUAGES = ("zh-CN", "en-US")
DEFAULT_LANGUAGE = "zh-CN"

CONFIG_FIELD_TEXTS = {
    "zh-CN": {
        "api_id": {
            "description": "Telegram API ID",
            "hint": "在 my.telegram.org 申请得到的 API ID。",
        },
        "api_hash": {
            "description": "Telegram API Hash",
            "hint": "在 my.telegram.org 申请得到的 API Hash。",
        },
        "bot_token": {
            "description": "Bot Token",
            "hint": "填写从 @BotFather 获取的 bot token。",
        },
        "id": {
            "description": "适配器 ID",
            "hint": "平台实例唯一标识，用于区分多个 Telegram 适配器实例。",
        },
        "language": {
            "description": "界面语言",
            "hint": "控制该适配器实例的运行时回复语言。",
            "labels": ["简体中文", "English"],
        },
        "reply_to_self_triggers_command": {
            "description": "回复自己触发命令",
            "hint": "仅群聊生效。开启后，回复当前 Bot 发出的消息时，也视为一次唤醒。默认关闭。",
        },
        "download_incoming_media": {
            "description": "下载入站媒体",
            "hint": "关闭后，不下载收到的图片、文件、音视频附件。",
        },
        "incoming_media_ttl_seconds": {
            "description": "入站媒体缓存 TTL",
            "hint": "媒体下载到本地后保留的秒数。设为 0 或负数表示仅在适配器退出时清理。",
        },
        "debug_logging": {
            "description": "调试日志",
            "hint": "开启后，输出更详细的 Telethon 事件转换、原始事件与命令调试日志。",
        },
        "telethon_command_register": {
            "description": "同步 Bot Commands",
            "hint": "连接成功后，自动把 AstrBot 已注册命令同步到 Telegram bot commands。",
        },
        "telethon_command_auto_refresh": {
            "description": "自动刷新 Bot Commands",
            "hint": "开启后，运行期间按固定间隔重新同步 commands 和 menu button，行为对齐内置 Telegram 适配器。",
        },
        "telethon_command_register_interval": {
            "description": "Bot Commands 刷新间隔",
            "hint": "自动刷新间隔，单位秒。",
        },
        "menu_button_mode": {
            "description": "菜单按钮模式",
            "hint": "控制 Telegram 私聊输入框左下角 menu button。disabled 为不处理，commands 为显示 bot commands。",
            "labels": ["禁用", "命令"],
        },
        "telethon_media_group_timeout": {
            "description": "媒体组聚合延迟",
            "hint": "媒体组防抖等待时间，单位秒。",
        },
        "telethon_media_group_max_wait": {
            "description": "媒体组最大等待时间",
            "hint": "媒体组聚合的最长等待时间，单位秒。",
        },
        "proxy_type": {
            "description": "代理类型",
            "hint": "支持 socks5、socks4、http、mtproto。",
            "labels": ["直连", "SOCKS5", "SOCKS4", "HTTP", "MTProto"],
        },
        "proxy_host": {
            "description": "代理主机",
            "hint": "代理服务器地址，例如 127.0.0.1。",
        },
        "proxy_port": {
            "description": "代理端口",
            "hint": "代理端口，例如 1080。",
        },
        "proxy_username": {
            "description": "代理用户名",
            "hint": "SOCKS/HTTP 代理可选用户名。",
        },
        "proxy_password": {
            "description": "代理密码",
            "hint": "SOCKS/HTTP 代理可选密码。",
        },
        "proxy_rdns": {
            "description": "代理远程 DNS",
            "hint": "SOCKS/HTTP 代理是否通过代理端进行域名解析，默认开启。",
        },
        "proxy_secret": {
            "description": "MTProto Secret",
            "hint": "仅 MTProto 代理需要填写 secret。",
        },
    },
    "en-US": {
        "api_id": {
            "description": "Telegram API ID",
            "hint": "API ID obtained from my.telegram.org.",
        },
        "api_hash": {
            "description": "Telegram API Hash",
            "hint": "API Hash obtained from my.telegram.org.",
        },
        "bot_token": {
            "description": "Bot Token",
            "hint": "Paste the bot token obtained from @BotFather.",
        },
        "id": {
            "description": "Adapter ID",
            "hint": "Unique platform instance identifier for distinguishing multiple Telegram adapter instances.",
        },
        "language": {
            "description": "Language",
            "hint": "Controls the runtime reply language for this adapter instance.",
            "labels": ["Simplified Chinese", "English"],
        },
        "reply_to_self_triggers_command": {
            "description": "Reply To Self Triggers Command",
            "hint": "Group chats only. When enabled, replying to a message sent by the current bot is also treated as a wake-up trigger. Disabled by default.",
        },
        "download_incoming_media": {
            "description": "Download Incoming Media",
            "hint": "When disabled, received images, files, audio, and video attachments will not be downloaded.",
        },
        "incoming_media_ttl_seconds": {
            "description": "Incoming Media Cache TTL",
            "hint": "How long downloaded media is kept locally in seconds. Set to 0 or negative to clean up only when the adapter exits.",
        },
        "debug_logging": {
            "description": "Debug Logging",
            "hint": "When enabled, output more detailed Telethon event conversion, raw event, and command debug logs.",
        },
        "telethon_command_register": {
            "description": "Sync Bot Commands",
            "hint": "Automatically sync registered AstrBot commands to Telegram bot commands after the bot connects.",
        },
        "telethon_command_auto_refresh": {
            "description": "Auto Refresh Bot Commands",
            "hint": "When enabled, periodically resync commands and menu button during runtime to match the built-in Telegram adapter behavior.",
        },
        "telethon_command_register_interval": {
            "description": "Bot Command Refresh Interval",
            "hint": "Automatic refresh interval in seconds.",
        },
        "menu_button_mode": {
            "description": "Menu Button Mode",
            "hint": "Controls the Telegram private chat menu button. disabled leaves it unchanged, and commands shows bot commands.",
            "labels": ["Disabled", "Commands"],
        },
        "telethon_media_group_timeout": {
            "description": "Media Group Debounce Delay",
            "hint": "Debounce wait time for media group aggregation, in seconds.",
        },
        "telethon_media_group_max_wait": {
            "description": "Media Group Max Wait",
            "hint": "Maximum wait time for media group aggregation, in seconds.",
        },
        "proxy_type": {
            "description": "Proxy Type",
            "hint": "Supported values: socks5, socks4, http, mtproto.",
            "labels": ["Direct", "SOCKS5", "SOCKS4", "HTTP", "MTProto"],
        },
        "proxy_host": {
            "description": "Proxy Host",
            "hint": "Proxy server address, for example 127.0.0.1.",
        },
        "proxy_port": {
            "description": "Proxy Port",
            "hint": "Proxy port, for example 1080.",
        },
        "proxy_username": {
            "description": "Proxy Username",
            "hint": "Optional username for SOCKS/HTTP proxy.",
        },
        "proxy_password": {
            "description": "Proxy Password",
            "hint": "Optional password for SOCKS/HTTP proxy.",
        },
        "proxy_rdns": {
            "description": "Remote DNS via Proxy",
            "hint": "Whether SOCKS/HTTP proxy performs DNS resolution remotely. Enabled by default.",
        },
        "proxy_secret": {
            "description": "MTProto Secret",
            "hint": "Required only for MTProto proxy.",
        },
    },
}

MESSAGES: dict[str, dict[str, str]] = {
    "zh-CN": {
        "config.error": "[Telethon] 配置字段 {field_name} 的当前值为 {current_value!r}。{suggestion}",
        "config.api_id.invalid": "请填写从 my.telegram.org 获取的正整数 API ID。",
        "config.api_hash.invalid": "请填写从 my.telegram.org 获取的 API Hash。",
        "config.bot_token.invalid": "请填写从 @BotFather 获取的有效 bot token。",
        "config.language.invalid": "请从 zh-CN 或 en-US 中选择一个值。",
        "config.menu_button_mode.invalid": "请从 disabled、commands 中选择一个值。",
        "config.command_refresh_interval.invalid": "请填写大于 0 的刷新间隔秒数。",
        "config.proxy_type.invalid": "请从 '', socks5, socks4, http, mtproto 中选择一个值。",
        "config.proxy_host.required": "启用代理时请填写代理主机地址。",
        "config.proxy_port.required": "启用代理时请填写大于 0 的代理端口。",
        "config.proxy_secret.required": "使用 MTProto 代理时请填写 proxy_secret。",
        "config.media_group_timeout.invalid": "请填写大于等于 0 的秒数。",
        "config.media_group_max_wait.invalid": "请填写大于 0 的秒数。",
        "errors.send_result_failed": "发送结果失败: {error}",
        "errors.status_failed": "获取状态失败: {error}",
        "status.title": "运行状态",
        "status.platform": "主机平台",
        "status.python_version": "Python 版本",
        "status.astrbot_version": "AstrBot 版本",
        "status.telethon_version": "Telethon 版本",
        "status.data_center": "数据中心",
        "status.plugin_version": "插件版本",
        "status.adapter_id": "适配器 ID",
        "status.system_cpu": "系统 CPU",
        "status.system_ram": "系统内存",
        "status.swap": "系统 SWAP",
        "status.process_cpu": "进程 CPU",
        "status.process_ram": "进程内存",
        "status.connection_state": "连接状态",
        "status.run_time": "运行时间",
        "status.unknown": "未知",
        "status.connection_state.connected": "已连接",
        "status.connection_state.connecting": "连接中",
        "status.connection_state.reconnecting": "重连退避中",
        "status.connection_state.stopped": "已停止",
        "status.connection_state.unknown": "未知",
        "status.duration.days": "{days}天{hours}小时{minutes}分钟",
        "status.duration.hours": "{hours}小时{minutes}分钟",
        "status.duration.minutes": "{minutes}分钟",
    },
    "en-US": {
        "config.error": "[Telethon] Config field {field_name} currently has value {current_value!r}. {suggestion}",
        "config.api_id.invalid": "Please provide a positive integer API ID from my.telegram.org.",
        "config.api_hash.invalid": "Please provide the API Hash from my.telegram.org.",
        "config.bot_token.invalid": "Please provide a valid bot token from @BotFather.",
        "config.language.invalid": "Please choose either zh-CN or en-US.",
        "config.menu_button_mode.invalid": "Please choose either disabled or commands.",
        "config.command_refresh_interval.invalid": "Please provide a refresh interval greater than 0 seconds.",
        "config.proxy_type.invalid": "Please choose one of '', socks5, socks4, http, or mtproto.",
        "config.proxy_host.required": "Please provide the proxy host when proxy is enabled.",
        "config.proxy_port.required": "Please provide a proxy port greater than 0 when proxy is enabled.",
        "config.proxy_secret.required": "Please provide proxy_secret when using an MTProto proxy.",
        "config.media_group_timeout.invalid": "Please provide a duration in seconds greater than or equal to 0.",
        "config.media_group_max_wait.invalid": "Please provide a duration in seconds greater than 0.",
        "errors.send_result_failed": "Failed to send result: {error}",
        "errors.status_failed": "Failed to get status: {error}",
        "status.title": "Runtime Status",
        "status.platform": "Host Platform",
        "status.python_version": "Python Version",
        "status.astrbot_version": "AstrBot Version",
        "status.telethon_version": "Telethon Version",
        "status.data_center": "Data Center",
        "status.plugin_version": "Plugin Version",
        "status.adapter_id": "Adapter ID",
        "status.system_cpu": "System CPU",
        "status.system_ram": "System RAM",
        "status.swap": "System SWAP",
        "status.process_cpu": "Process CPU",
        "status.process_ram": "Process RAM",
        "status.connection_state": "Connection State",
        "status.run_time": "Uptime",
        "status.unknown": "unknown",
        "status.connection_state.connected": "connected",
        "status.connection_state.connecting": "connecting",
        "status.connection_state.reconnecting": "reconnecting",
        "status.connection_state.stopped": "stopped",
        "status.connection_state.unknown": "unknown",
        "status.duration.days": "{days}d {hours}h {minutes}m",
        "status.duration.hours": "{hours}h {minutes}m",
        "status.duration.minutes": "{minutes}m",
    },
}

DATA_CENTER_LABELS = {
    "zh-CN": {
        1: "🇺🇸 美国迈阿密（DC1）",
        2: "🇳🇱 荷兰阿姆斯特丹（DC2）",
        3: "🇺🇸 美国迈阿密（DC3）",
        4: "🇳🇱 荷兰阿姆斯特丹（DC4）",
        5: "🇸🇬 新加坡（DC5）",
    },
    "en-US": {
        1: "🇺🇸 Miami, United States (DC1)",
        2: "🇳🇱 Amsterdam, Netherlands (DC2)",
        3: "🇺🇸 Miami, United States (DC3)",
        4: "🇳🇱 Amsterdam, Netherlands (DC4)",
        5: "🇸🇬 Singapore (DC5)",
    },
}


def normalize_language(value: Any) -> str:
    language = str(value or "").strip()
    if not language:
        return DEFAULT_LANGUAGE
    lowered = language.lower()
    if lowered.startswith("en"):
        return "en-US"
    if lowered.startswith("zh"):
        return "zh-CN"
    return DEFAULT_LANGUAGE


def get_event_language(event: Any | None) -> str:
    if event is None:
        return DEFAULT_LANGUAGE
    return normalize_language(getattr(event, "telethon_language", None))


def t(language_or_event: Any, key: str, **kwargs: Any) -> str:
    language = (
        get_event_language(language_or_event)
        if not isinstance(language_or_event, str)
        else normalize_language(language_or_event)
    )
    template = MESSAGES.get(language, {}).get(key) or MESSAGES[DEFAULT_LANGUAGE].get(key) or key
    return template.format(**kwargs)


def format_data_center_label(value: Any, language: str = DEFAULT_LANGUAGE) -> str | None:
    normalized = normalize_language(language)
    if value is None or isinstance(value, bool):
        return None
    try:
        dc_id = int(value)
    except (TypeError, ValueError):
        return str(value)
    label_map = DATA_CENTER_LABELS[normalized]
    if normalized == "en-US":
        return label_map.get(dc_id, f"🌐 Unknown Location (DC{dc_id})")
    return label_map.get(dc_id, f"🌐 未知位置（DC{dc_id}）")
