"""Generate repeatable MP4 demo videos for all major features."""

from __future__ import annotations

import os
import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QPoint
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QLabel, QWidget

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.ui.main_window import MainWindow

FPS = 12
RIPPLE_FRAMES = 9
OUTPUT_DIR = ROOT / "docs" / "videos"


@dataclass(frozen=True)
class DemoStyle:
    name: str
    output_file: Path
    cursor_enabled: bool
    hold_scale: float
    move_duration: float
    click_pause: float
    plain_text_step: int
    line_text_step: int
    plain_text_delay: float
    line_text_delay: float


@dataclass
class CursorState:
    x: float
    y: float
    pulse_frames: int = 0


STYLES = {
    "standard": DemoStyle(
        name="standard",
        output_file=OUTPUT_DIR / "mima_demo.mp4",
        cursor_enabled=False,
        hold_scale=1.0,
        move_duration=0.0,
        click_pause=0.0,
        plain_text_step=4,
        line_text_step=3,
        plain_text_delay=0.08,
        line_text_delay=0.07,
    ),
    "human": DemoStyle(
        name="human",
        output_file=OUTPUT_DIR / "mima_demo_human.mp4",
        cursor_enabled=True,
        hold_scale=1.32,
        move_duration=0.34,
        click_pause=0.16,
        plain_text_step=1,
        line_text_step=1,
        plain_text_delay=0.075,
        line_text_delay=0.075,
    ),
}


def _parse_args() -> DemoStyle:
    parser = ArgumentParser(description="Generate Mima Guard demo videos.")
    parser.add_argument(
        "--style",
        choices=sorted(STYLES),
        default="standard",
        help="Video style to generate. Use 'human' for slower typing and cursor highlights.",
    )
    args = parser.parse_args()
    return STYLES[args.style]


def _qimage_to_array(image: QImage) -> np.ndarray:
    converted = image.convertToFormat(QImage.Format.Format_RGBA8888)
    ptr = converted.bits()
    width = converted.width()
    height = converted.height()
    frame = np.frombuffer(ptr, dtype=np.uint8).reshape((height, width, 4)).copy()
    return frame[:, :, :3]


def _grab_frame(window: MainWindow) -> np.ndarray:
    return np.ascontiguousarray(_qimage_to_array(window.grab().toImage()))


def _draw_cursor(frame: np.ndarray, cursor: CursorState) -> None:
    tip_x = int(round(cursor.x))
    tip_y = int(round(cursor.y))
    center = (tip_x + 8, tip_y + 9)

    if cursor.pulse_frames > 0:
        progress = 1 - (cursor.pulse_frames / RIPPLE_FRAMES)
        radius = int(16 + progress * 30)
        alpha = max(0.04, 0.34 * (1 - progress))
        pulse_layer = frame.copy()
        cv2.circle(
            pulse_layer,
            center,
            radius,
            (76, 171, 245),
            3,
            lineType=cv2.LINE_AA,
        )
        frame[:] = cv2.addWeighted(pulse_layer, alpha, frame, 1 - alpha, 0)

    points = np.array(
        [
            [tip_x, tip_y],
            [tip_x + 1, tip_y + 25],
            [tip_x + 7, tip_y + 18],
            [tip_x + 12, tip_y + 31],
            [tip_x + 18, tip_y + 29],
            [tip_x + 12, tip_y + 17],
            [tip_x + 23, tip_y + 17],
        ],
        dtype=np.int32,
    )
    shadow = points + np.array([4, 5], dtype=np.int32)

    shadow_layer = frame.copy()
    cv2.fillPoly(shadow_layer, [shadow], (8, 24, 38), lineType=cv2.LINE_AA)
    frame[:] = cv2.addWeighted(shadow_layer, 0.24, frame, 0.76, 0)
    cv2.fillPoly(frame, [points], (255, 255, 255), lineType=cv2.LINE_AA)
    cv2.polylines(frame, [points], True, (22, 82, 136), 2, lineType=cv2.LINE_AA)


def _position_overlay(window: MainWindow, overlay: QLabel) -> None:
    margin = 24
    overlay.adjustSize()
    width = min(max(520, overlay.sizeHint().width()), window.width() - margin * 2)
    overlay.resize(width, overlay.sizeHint().height() + 12)
    overlay.move(margin, window.height() - overlay.height() - margin)


def _set_caption(window: MainWindow, overlay: QLabel, text: str) -> None:
    overlay.setText(text)
    _position_overlay(window, overlay)


def _settle(app: QApplication, cycles: int = 3) -> None:
    for _ in range(cycles):
        app.processEvents()


def _write_frame(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    style: DemoStyle,
    cursor: CursorState | None,
) -> None:
    _settle(app, 1)
    frame = _grab_frame(window)
    if style.cursor_enabled and cursor is not None:
        _draw_cursor(frame, cursor)
        if cursor.pulse_frames > 0:
            cursor.pulse_frames -= 1
    writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))


def _hold_frame(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    style: DemoStyle,
    cursor: CursorState | None,
    seconds: float,
) -> None:
    repeat = max(1, round(seconds * style.hold_scale * FPS))
    for _ in range(repeat):
        _write_frame(writer, app, window, style, cursor)


def _ease(value: float) -> float:
    return value * value * (3 - 2 * value)


def _move_cursor(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    style: DemoStyle,
    cursor: CursorState | None,
    target: tuple[int, int],
    seconds: float | None = None,
) -> None:
    if not style.cursor_enabled or cursor is None:
        return

    duration = style.move_duration if seconds is None else seconds
    frames = max(1, round(duration * FPS))
    start_x = cursor.x
    start_y = cursor.y
    end_x, end_y = target
    for index in range(frames):
        progress = _ease((index + 1) / frames)
        cursor.x = start_x + (end_x - start_x) * progress
        cursor.y = start_y + (end_y - start_y) * progress
        _write_frame(writer, app, window, style, cursor)


def _click(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    style: DemoStyle,
    cursor: CursorState | None,
) -> None:
    if style.cursor_enabled and cursor is not None:
        cursor.pulse_frames = RIPPLE_FRAMES
    _hold_frame(writer, app, window, style, cursor, style.click_pause)


def _widget_point(
    window: MainWindow,
    widget: QWidget,
    x_ratio: float = 0.5,
    y_ratio: float = 0.5,
    viewport: bool = False,
) -> tuple[int, int]:
    target = widget.viewport() if viewport and hasattr(widget, "viewport") else widget
    rect = target.rect()
    point = QPoint(int(rect.width() * x_ratio), int(rect.height() * y_ratio))
    mapped = target.mapTo(window, point)
    return mapped.x(), mapped.y()


def _tab_point(window: MainWindow, index: int) -> tuple[int, int]:
    tab_bar = window.tabs.tabBar()
    mapped = tab_bar.mapTo(window, tab_bar.tabRect(index).center())
    return mapped.x(), mapped.y()


def _focus_widget(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    style: DemoStyle,
    cursor: CursorState | None,
    widget: QWidget,
    x_ratio: float = 0.18,
    y_ratio: float = 0.5,
    viewport: bool = False,
) -> None:
    _move_cursor(
        writer,
        app,
        window,
        style,
        cursor,
        _widget_point(window, widget, x_ratio, y_ratio, viewport),
    )
    widget.setFocus()
    _click(writer, app, window, style, cursor)


def _choose_combo(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    style: DemoStyle,
    cursor: CursorState | None,
    combo,
    value: str,
) -> None:
    _focus_widget(writer, app, window, style, cursor, combo, 0.5, 0.5)
    combo.setCurrentText(value)
    _hold_frame(writer, app, window, style, cursor, 0.16)


def _press_button(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    style: DemoStyle,
    cursor: CursorState | None,
    button,
) -> None:
    _move_cursor(
        writer,
        app,
        window,
        style,
        cursor,
        _widget_point(window, button, 0.5, 0.5),
    )
    _click(writer, app, window, style, cursor)
    button.click()
    _hold_frame(writer, app, window, style, cursor, 0.18)


def _switch_tab(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    style: DemoStyle,
    cursor: CursorState | None,
    index: int,
) -> None:
    _move_cursor(writer, app, window, style, cursor, _tab_point(window, index))
    _click(writer, app, window, style, cursor)
    window.tabs.setCurrentIndex(index)
    _hold_frame(writer, app, window, style, cursor, 0.2)


def _animate_text(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    style: DemoStyle,
    cursor: CursorState | None,
    edit,
    text: str,
) -> None:
    edit.clear()
    _hold_frame(writer, app, window, style, cursor, 0.18)
    step = style.plain_text_step
    for index in range(step, len(text) + step, step):
        edit.setPlainText(text[:index])
        _hold_frame(writer, app, window, style, cursor, style.plain_text_delay)
        if style.cursor_enabled and index % 6 == 0:
            _hold_frame(writer, app, window, style, cursor, 0.04)


def _animate_line_edit(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    style: DemoStyle,
    cursor: CursorState | None,
    edit,
    text: str,
) -> None:
    edit.clear()
    _hold_frame(writer, app, window, style, cursor, 0.16)
    step = style.line_text_step
    for index in range(step, len(text) + step, step):
        edit.setText(text[:index])
        _hold_frame(writer, app, window, style, cursor, style.line_text_delay)
        if style.cursor_enabled and index % 5 == 0:
            _hold_frame(writer, app, window, style, cursor, 0.04)


def _paste_plain_text(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    style: DemoStyle,
    cursor: CursorState | None,
    edit,
    text: str,
) -> None:
    _focus_widget(writer, app, window, style, cursor, edit, 0.18, 0.24, True)
    edit.setPlainText(text)
    _hold_frame(writer, app, window, style, cursor, 0.28)


def _show_intro(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    overlay: QLabel,
    style: DemoStyle,
    cursor: CursorState | None,
) -> None:
    window.tabs.setCurrentIndex(0)
    window._clear_crypto()  # noqa: SLF001
    window.algorithm_combo.setCurrentText("Caesar")
    window.mode_combo.setCurrentText("encrypt")
    caption = "Mima Guard 演示视频：依次验证密码制作、不可逆提示、复制结果和强度检测。"
    if style.name == "human":
        caption = "Mima Guard 真人操作感演示：放慢节奏，加入输入过程、鼠标移动和点击高亮。"
    _set_caption(window, overlay, caption)
    _hold_frame(writer, app, window, style, cursor, 1.8)


def _demo_caesar(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    overlay: QLabel,
    style: DemoStyle,
    cursor: CursorState | None,
) -> None:
    window._clear_crypto()  # noqa: SLF001
    _choose_combo(writer, app, window, style, cursor, window.algorithm_combo, "Caesar")
    _choose_combo(writer, app, window, style, cursor, window.mode_combo, "encrypt")
    _set_caption(window, overlay, "1. 凯撒加密：输入偏移量 3，验证古典密码加密。")
    _focus_widget(writer, app, window, style, cursor, window.key_input)
    _animate_line_edit(writer, app, window, style, cursor, window.key_input, "3")
    _focus_widget(writer, app, window, style, cursor, window.input_edit, 0.18, 0.24, True)
    _animate_text(writer, app, window, style, cursor, window.input_edit, "Attack At Dawn")
    _press_button(writer, app, window, style, cursor, window.process_btn)
    _hold_frame(writer, app, window, style, cursor, 0.75)

    encrypted = window.output_edit.toPlainText()
    _choose_combo(writer, app, window, style, cursor, window.mode_combo, "decrypt")
    _set_caption(window, overlay, "2. 凯撒解密：将结果反向还原，验证加解密互通。")
    _paste_plain_text(writer, app, window, style, cursor, window.input_edit, encrypted)
    _press_button(writer, app, window, style, cursor, window.process_btn)
    _hold_frame(writer, app, window, style, cursor, 0.85)


def _demo_rail_fence(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    overlay: QLabel,
    style: DemoStyle,
    cursor: CursorState | None,
) -> None:
    _press_button(writer, app, window, style, cursor, window.clear_btn)
    _choose_combo(writer, app, window, style, cursor, window.algorithm_combo, "Rail Fence")
    _choose_combo(writer, app, window, style, cursor, window.mode_combo, "encrypt")
    _set_caption(window, overlay, "3. 栅栏加密：使用 3 条轨道，验证字符重排效果。")
    _focus_widget(writer, app, window, style, cursor, window.key_input)
    _animate_line_edit(writer, app, window, style, cursor, window.key_input, "3")
    _focus_widget(writer, app, window, style, cursor, window.input_edit, 0.18, 0.24, True)
    _animate_text(writer, app, window, style, cursor, window.input_edit, "WEAREDISCOVEREDFLEEATONCE")
    _press_button(writer, app, window, style, cursor, window.process_btn)
    _hold_frame(writer, app, window, style, cursor, 0.65)

    encrypted = window.output_edit.toPlainText()
    _choose_combo(writer, app, window, style, cursor, window.mode_combo, "decrypt")
    _set_caption(window, overlay, "4. 栅栏解密：验证可以恢复原文。")
    _paste_plain_text(writer, app, window, style, cursor, window.input_edit, encrypted)
    _press_button(writer, app, window, style, cursor, window.process_btn)
    _hold_frame(writer, app, window, style, cursor, 0.8)


def _demo_hashes(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    overlay: QLabel,
    style: DemoStyle,
    cursor: CursorState | None,
) -> None:
    _press_button(writer, app, window, style, cursor, window.clear_btn)
    _choose_combo(writer, app, window, style, cursor, window.algorithm_combo, "MD5")
    _choose_combo(writer, app, window, style, cursor, window.mode_combo, "encrypt")
    _set_caption(window, overlay, "5. MD5 摘要：生成固定长度指纹，并测试复制结果。")
    _focus_widget(writer, app, window, style, cursor, window.input_edit, 0.18, 0.24, True)
    _animate_text(writer, app, window, style, cursor, window.input_edit, "hello-md5")
    _press_button(writer, app, window, style, cursor, window.process_btn)
    _hold_frame(writer, app, window, style, cursor, 0.55)
    _press_button(writer, app, window, style, cursor, window.copy_btn)
    _hold_frame(writer, app, window, style, cursor, 0.6)

    _press_button(writer, app, window, style, cursor, window.clear_btn)
    _choose_combo(writer, app, window, style, cursor, window.algorithm_combo, "SHA-256")
    _choose_combo(writer, app, window, style, cursor, window.mode_combo, "encrypt")
    _set_caption(window, overlay, "6. SHA-256 摘要：生成更强摘要。")
    _focus_widget(writer, app, window, style, cursor, window.input_edit, 0.18, 0.24, True)
    _animate_text(writer, app, window, style, cursor, window.input_edit, "hello-sha256")
    _press_button(writer, app, window, style, cursor, window.process_btn)
    _hold_frame(writer, app, window, style, cursor, 0.65)

    _choose_combo(writer, app, window, style, cursor, window.mode_combo, "decrypt")
    _set_caption(window, overlay, "7. 不可逆提示：切到解密时，界面明确提示摘要算法无法还原。")
    _press_button(writer, app, window, style, cursor, window.process_btn)
    _hold_frame(writer, app, window, style, cursor, 0.85)


def _demo_aes(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    overlay: QLabel,
    style: DemoStyle,
    cursor: CursorState | None,
) -> None:
    _press_button(writer, app, window, style, cursor, window.clear_btn)
    _choose_combo(writer, app, window, style, cursor, window.algorithm_combo, "AES")
    _choose_combo(writer, app, window, style, cursor, window.mode_combo, "encrypt")
    _set_caption(window, overlay, "8. AES 加密：输入口令并加密敏感文本。")
    _focus_widget(writer, app, window, style, cursor, window.key_input)
    _animate_line_edit(writer, app, window, style, cursor, window.key_input, "DemoPass#2026")
    _focus_widget(writer, app, window, style, cursor, window.input_edit, 0.18, 0.24, True)
    _animate_text(writer, app, window, style, cursor, window.input_edit, "示例：离线加密文本")
    _press_button(writer, app, window, style, cursor, window.process_btn)
    _hold_frame(writer, app, window, style, cursor, 0.75)
    _press_button(writer, app, window, style, cursor, window.copy_btn)

    token = window.output_edit.toPlainText()
    _choose_combo(writer, app, window, style, cursor, window.mode_combo, "decrypt")
    _set_caption(window, overlay, "9. AES 解密：使用相同口令还原原文，验证完整闭环。")
    _paste_plain_text(writer, app, window, style, cursor, window.input_edit, token)
    _press_button(writer, app, window, style, cursor, window.process_btn)
    _hold_frame(writer, app, window, style, cursor, 0.85)


def _demo_strength(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    overlay: QLabel,
    style: DemoStyle,
    cursor: CursorState | None,
) -> None:
    _switch_tab(writer, app, window, style, cursor, 1)
    window.password_input.clear()
    _set_caption(window, overlay, "10. 强度检测：先看弱密码，命中常见密码和连续字符规则。")
    _focus_widget(writer, app, window, style, cursor, window.password_input)
    _animate_line_edit(writer, app, window, style, cursor, window.password_input, "123456")
    _press_button(writer, app, window, style, cursor, window.analyze_btn)
    _hold_frame(writer, app, window, style, cursor, 1.0)

    _set_caption(window, overlay, "11. 显示密码：切换明文展示，便于演示输入内容。")
    _move_cursor(
        writer,
        app,
        window,
        style,
        cursor,
        _widget_point(window, window.show_password, 0.5, 0.5),
    )
    _click(writer, app, window, style, cursor)
    window.show_password.click()
    _hold_frame(writer, app, window, style, cursor, 0.65)
    _click(writer, app, window, style, cursor)
    window.show_password.click()
    _hold_frame(writer, app, window, style, cursor, 0.42)

    _set_caption(window, overlay, "12. 强密码样例：验证高分、类型统计和改进建议。")
    _focus_widget(writer, app, window, style, cursor, window.password_input)
    window.password_input.clear()
    _hold_frame(writer, app, window, style, cursor, 0.2)
    _animate_line_edit(writer, app, window, style, cursor, window.password_input, "N3xT!Wave#2026")
    _press_button(writer, app, window, style, cursor, window.analyze_btn)
    _hold_frame(writer, app, window, style, cursor, 1.2)


def _show_outro(
    writer: cv2.VideoWriter,
    app: QApplication,
    window: MainWindow,
    overlay: QLabel,
    style: DemoStyle,
    cursor: CursorState | None,
) -> None:
    _set_caption(
        window,
        overlay,
        "演示完成：所有核心功能均已走通，可继续在 Windows 上复录或打包后展示。",
    )
    _hold_frame(writer, app, window, style, cursor, 1.7)


def _create_writer(output_file: Path, frame_size: tuple[int, int]) -> cv2.VideoWriter:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_file), fourcc, FPS, frame_size)
    if not writer.isOpened():
        raise RuntimeError("无法创建 MP4 视频文件，请检查 OpenCV 编码支持")
    return writer


def main() -> int:
    style = _parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    app = QApplication([])
    window = MainWindow()
    window.resize(1280, 860)
    window.show()

    overlay = QLabel(window)
    overlay.setWordWrap(True)
    overlay.setStyleSheet(
        """
        QLabel {
            background: rgba(10, 32, 52, 0.82);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 12px;
            padding: 12px 16px;
            font-size: 16px;
            font-weight: 700;
        }
        """
    )
    overlay.show()

    _settle(app, 6)
    cursor = CursorState(72, 72) if style.cursor_enabled else None
    writer = _create_writer(style.output_file, (window.width(), window.height()))

    try:
        _show_intro(writer, app, window, overlay, style, cursor)
        _demo_caesar(writer, app, window, overlay, style, cursor)
        _demo_rail_fence(writer, app, window, overlay, style, cursor)
        _demo_hashes(writer, app, window, overlay, style, cursor)
        _demo_aes(writer, app, window, overlay, style, cursor)
        _demo_strength(writer, app, window, overlay, style, cursor)
        _show_outro(writer, app, window, overlay, style, cursor)
    finally:
        writer.release()
        window.close()
        app.quit()

    print(style.output_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
