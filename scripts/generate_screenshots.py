"""Generate feature screenshots for the test report."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ui.main_window import MainWindow


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    output_dir = Path("docs/screenshots")
    output_dir.mkdir(parents=True, exist_ok=True)

    app = QApplication([])
    window = MainWindow()
    window.show()
    app.processEvents()

    def capture(name: str) -> None:
        app.processEvents()
        image_path = output_dir / name
        ok = window.grab().save(str(image_path))
        if not ok:
            raise RuntimeError(f"failed to save screenshot: {image_path}")

    capture("01_crypto_overview.png")

    window.algorithm_combo.setCurrentText("AES")
    window.mode_combo.setCurrentText("encrypt")
    window.key_input.setText("DemoPass#2026")
    window.input_edit.setPlainText("示例：离线加密文本")
    window._process_crypto()  # noqa: SLF001
    capture("02_crypto_aes_encrypt.png")

    window.tabs.setCurrentIndex(1)
    window.password_input.setText("123456")
    window._analyze_password()  # noqa: SLF001
    capture("03_strength_weak.png")

    window.password_input.setText("N3xT!Wave#2026")
    window._analyze_password()  # noqa: SLF001
    capture("04_strength_strong.png")

    window.close()
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
