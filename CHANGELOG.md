# Changelog

## 0.5.0 - 2026-03-20

- 重构日志系统，普通调试日志改为跟随 AstrBot 全局 `DEBUG` 日志级别。
- 移除用户可见的 `debug_logging` 配置项。

- Refactored logging so normal Telethon diagnostics now follow AstrBot's global `DEBUG` log level.
- Removed the user-visible `debug_logging` option.

## 0.4.0 - 2026-03-20

- 增加 `fastupload` 开关，可按需启用或关闭快速上传。
- 改进 `caption` 处理，减少发送媒体时的文案行为不一致问题。

- Added a `fastupload` toggle so fast upload can be enabled or disabled as needed.
- Improved `caption` handling to reduce text behavior inconsistencies when sending media.

## 0.3.0 - 2026-03-18

- 一批细节改进与稳定性增强。

- A round of usability and stability refinements.

## 0.2.0 - 2026-03-17

- 新增 fast upload 支持。
- 移除状态输出中的连接状态信息。

- Fast upload for local files.
- Remove connection state from status output.
