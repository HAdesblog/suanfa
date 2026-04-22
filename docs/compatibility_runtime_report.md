# 运行时兼容性检查报告

- 时间: 2026-04-22T10:19:22
- 平台: macOS-13.7.8-arm64-arm-64bit
- Python: 3.9.6

| 检查项 | 结果 | 说明 |
|---|---|---|
| 依赖导入 | PASS | PySide6 / cryptography 导入成功 |
| AES 互通 | PASS | AES 加解密互通 |
| 强度评分 | PASS | 评分正常（弱=0, 强=83） |
| Qt 启动 | PASS | Qt 窗口初始化成功（offscreen） |
