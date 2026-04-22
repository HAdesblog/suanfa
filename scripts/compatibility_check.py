"""Runtime compatibility check for Mima Guard."""

from __future__ import annotations

import platform
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _check_imports() -> tuple[bool, str]:
    try:
        import PySide6  # noqa: F401
        import cryptography  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        return False, f"导入失败: {exc}"
    return True, "PySide6 / cryptography 导入成功"


def _check_crypto_roundtrip() -> tuple[bool, str]:
    from app.crypto_algorithms import aes_decrypt, aes_encrypt

    text = "compatibility-check"
    token = aes_encrypt(text, "Check#Pass123")
    plain = aes_decrypt(token, "Check#Pass123")
    if plain != text:
        return False, "AES 加解密结果不一致"
    return True, "AES 加解密互通"


def _check_strength() -> tuple[bool, str]:
    from app.strength import evaluate_password

    weak = evaluate_password("123456")
    strong = evaluate_password("N3xT!Wave#2026")
    if weak.score >= strong.score:
        return False, "强弱密码评分关系异常"
    return True, f"评分正常（弱={weak.score}, 强={strong.score}）"


def _check_qt_headless() -> tuple[bool, str]:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from app.ui.main_window import MainWindow

    app = QApplication([])
    win = MainWindow()
    win.show()
    app.processEvents()
    win.close()
    app.quit()
    return True, "Qt 窗口初始化成功（offscreen）"


def main() -> int:
    checks = [
        ("依赖导入", _check_imports),
        ("AES 互通", _check_crypto_roundtrip),
        ("强度评分", _check_strength),
        ("Qt 启动", _check_qt_headless),
    ]

    results = []
    for name, fn in checks:
        try:
            ok, detail = fn()
        except Exception as exc:  # noqa: BLE001
            ok, detail = False, f"异常: {exc}"
        results.append((name, ok, detail))

    report_dir = ROOT / "docs"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / "compatibility_runtime_report.md"

    with report.open("w", encoding="utf-8") as f:
        f.write("# 运行时兼容性检查报告\n\n")
        f.write(f"- 时间: {datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"- 平台: {platform.platform()}\n")
        f.write(f"- Python: {sys.version.split()[0]}\n\n")
        f.write("| 检查项 | 结果 | 说明 |\n")
        f.write("|---|---|---|\n")
        for name, ok, detail in results:
            icon = "PASS" if ok else "FAIL"
            f.write(f"| {name} | {icon} | {detail} |\n")

    all_passed = all(item[1] for item in results)
    print(report)
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
