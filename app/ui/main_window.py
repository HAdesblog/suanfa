"""Main window and user interactions."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QSizePolicy,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.crypto_algorithms import (
    ALGORITHM_DESCRIPTIONS,
    CryptoError,
    InvalidCipherTextError,
    InvalidKeyError,
    NonReversibleAlgorithmError,
    process_text,
)
from app.strength import PasswordCheckResult, evaluate_password


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Mima Guard - 密码工具")
        self.resize(1100, 760)
        self.setMinimumSize(960, 680)

        app_font = QFont("Microsoft YaHei UI", 10)
        self.setFont(app_font)

        self._build_ui()
        self._apply_styles()
        self._refresh_algorithm_hints()
        self._analyze_password()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        title = QLabel("Mima Guard")
        title.setObjectName("Title")
        subtitle = QLabel("离线密码制作 + 强度检测工具")
        subtitle.setObjectName("Subtitle")

        header_row = QHBoxLayout()
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(subtitle)

        tabs = QTabWidget()
        tabs.addTab(self._build_crypto_tab(), "密码制作")
        tabs.addTab(self._build_strength_tab(), "强度检测")
        tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabs = tabs

        root_layout.addLayout(header_row)
        root_layout.addWidget(tabs)

        self.setCentralWidget(root)
        self._build_menu()

    def _build_menu(self) -> None:
        help_menu = self.menuBar().addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "关于 Mima Guard",
            "Mima Guard\n"
            "离线密码工具，支持古典/现代加密、摘要和密码强度检测。\n"
            "提示：凯撒与栅栏仅用于教学。",
        )

    def _build_crypto_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        options_box = QGroupBox("算法设置")
        options_layout = QFormLayout(options_box)

        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(["Caesar", "Rail Fence", "MD5", "SHA-256", "AES"])
        self.algorithm_combo.currentTextChanged.connect(self._refresh_algorithm_hints)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["encrypt", "decrypt"])
        self.mode_combo.currentTextChanged.connect(self._refresh_algorithm_hints)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("根据算法填写密钥")

        options_layout.addRow("算法", self.algorithm_combo)
        options_layout.addRow("模式", self.mode_combo)
        options_layout.addRow("密钥 / 口令", self.key_input)

        io_row = QHBoxLayout()
        io_row.setSpacing(12)

        input_box = QGroupBox("输入")
        input_layout = QVBoxLayout(input_box)
        self.input_edit = QPlainTextEdit()
        self.input_edit.setPlaceholderText("输入待加密 / 解密文本")
        input_layout.addWidget(self.input_edit)

        output_box = QGroupBox("输出")
        output_layout = QVBoxLayout(output_box)
        self.output_edit = QPlainTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("处理结果将显示在这里")
        output_layout.addWidget(self.output_edit)

        io_row.addWidget(input_box, 1)
        io_row.addWidget(output_box, 1)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.process_btn = QPushButton("执行")
        self.process_btn.clicked.connect(self._process_crypto)
        self.copy_btn = QPushButton("复制结果")
        self.copy_btn.clicked.connect(self._copy_result)
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self._clear_crypto)

        action_row.addWidget(self.process_btn)
        action_row.addWidget(self.copy_btn)
        action_row.addWidget(self.clear_btn)
        action_row.addStretch(1)

        self.crypto_status = QLabel("准备就绪")
        self.crypto_status.setObjectName("StatusNeutral")

        desc_box = QGroupBox("算法说明")
        desc_layout = QVBoxLayout(desc_box)
        self.algorithm_desc = QTextBrowser()
        self.algorithm_desc.setOpenExternalLinks(False)
        self.algorithm_desc.setMaximumHeight(150)
        desc_layout.addWidget(self.algorithm_desc)

        layout.addWidget(options_box)
        layout.addLayout(io_row, 1)
        layout.addLayout(action_row)
        layout.addWidget(self.crypto_status)
        layout.addWidget(desc_box)

        return page

    def _build_strength_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        top_box = QGroupBox("输入密码")
        top_layout = QHBoxLayout(top_box)
        top_layout.setSpacing(10)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("输入要检测的密码")
        self.password_input.textChanged.connect(self._analyze_password)

        self.show_password = QCheckBox("显示")
        self.show_password.toggled.connect(self._toggle_password_echo)

        self.analyze_btn = QPushButton("重新检测")
        self.analyze_btn.clicked.connect(self._analyze_password)

        top_layout.addWidget(self.password_input, 1)
        top_layout.addWidget(self.show_password)
        top_layout.addWidget(self.analyze_btn)

        score_box = QGroupBox("综合评分")
        score_layout = QHBoxLayout(score_box)
        score_layout.setSpacing(16)

        score_left = QVBoxLayout()
        self.score_label = QLabel("0 / 100")
        self.score_label.setObjectName("ScoreValue")
        self.level_label = QLabel("等级：弱")
        self.level_label.setObjectName("LevelLabel")
        score_left.addWidget(self.score_label)
        score_left.addWidget(self.level_label)
        score_left.addStretch(1)

        self.score_bar = QProgressBar()
        self.score_bar.setRange(0, 100)
        self.score_bar.setValue(0)
        self.score_bar.setTextVisible(True)
        self.score_bar.setFormat("%v")
        self.score_bar.setMinimumHeight(34)

        score_layout.addLayout(score_left)
        score_layout.addWidget(self.score_bar, 1)

        detail_row = QHBoxLayout()
        detail_row.setSpacing(12)

        stats_box = QGroupBox("字符统计")
        stats_layout = QGridLayout(stats_box)

        self.length_val = QLabel("0")
        self.upper_val = QLabel("0")
        self.lower_val = QLabel("0")
        self.digits_val = QLabel("0")
        self.symbols_val = QLabel("0")

        stats_layout.addWidget(QLabel("长度"), 0, 0)
        stats_layout.addWidget(self.length_val, 0, 1)
        stats_layout.addWidget(QLabel("大写"), 1, 0)
        stats_layout.addWidget(self.upper_val, 1, 1)
        stats_layout.addWidget(QLabel("小写"), 2, 0)
        stats_layout.addWidget(self.lower_val, 2, 1)
        stats_layout.addWidget(QLabel("数字"), 3, 0)
        stats_layout.addWidget(self.digits_val, 3, 1)
        stats_layout.addWidget(QLabel("符号"), 4, 0)
        stats_layout.addWidget(self.symbols_val, 4, 1)

        risk_box = QGroupBox("弱密码规则检测")
        risk_layout = QVBoxLayout(risk_box)
        self.risk_text = QTextBrowser()
        self.risk_text.setMaximumHeight(160)
        risk_layout.addWidget(self.risk_text)

        advice_box = QGroupBox("改进建议")
        advice_layout = QVBoxLayout(advice_box)
        self.advice_text = QTextBrowser()
        self.advice_text.setMaximumHeight(160)
        advice_layout.addWidget(self.advice_text)

        detail_row.addWidget(stats_box)
        detail_row.addWidget(risk_box, 1)
        detail_row.addWidget(advice_box, 1)

        layout.addWidget(top_box)
        layout.addWidget(score_box)
        layout.addLayout(detail_row)

        return page

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #f4fbf8,
                    stop: 1 #eaf1ff
                );
            }
            QWidget {
                color: #24303f;
            }
            QLabel#Title {
                font-size: 28px;
                font-weight: 700;
                color: #0a3d62;
            }
            QLabel#Subtitle {
                font-size: 14px;
                color: #335b77;
                margin-right: 4px;
            }
            QTabWidget::pane {
                border: 1px solid #c7d6e5;
                border-radius: 10px;
                background-color: rgba(255, 255, 255, 0.88);
            }
            QTabBar::tab {
                background: #dce9f6;
                color: #2b3f57;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                min-width: 130px;
                padding: 10px 14px;
                margin-right: 3px;
            }
            QTabBar::tab:selected {
                background: #f9fcff;
                color: #0f3b66;
                font-weight: 700;
            }
            QGroupBox {
                background: rgba(255, 255, 255, 0.92);
                border: 1px solid #d8e3ef;
                border-radius: 10px;
                margin-top: 8px;
                font-weight: 600;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 2px 6px;
                color: #284860;
            }
            QLineEdit, QComboBox, QPlainTextEdit, QTextBrowser {
                border: 1px solid #c9d7e6;
                border-radius: 8px;
                background: #ffffff;
                padding: 7px 9px;
            }
            QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QTextBrowser:focus {
                border: 1px solid #4a90c2;
            }
            QPlainTextEdit {
                selection-background-color: #93c5f6;
            }
            QPushButton {
                border: none;
                border-radius: 8px;
                background: #1f6fae;
                color: #ffffff;
                padding: 9px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #195e94;
            }
            QPushButton:pressed {
                background: #154e7a;
            }
            QLabel#StatusNeutral {
                color: #35516c;
                font-weight: 600;
            }
            QLabel#StatusOk {
                color: #157a52;
                font-weight: 700;
            }
            QLabel#StatusWarn {
                color: #975a16;
                font-weight: 700;
            }
            QLabel#StatusErr {
                color: #9b2226;
                font-weight: 700;
            }
            QLabel#ScoreValue {
                font-size: 24px;
                font-weight: 800;
                color: #123a56;
            }
            QLabel#LevelLabel {
                font-size: 14px;
                font-weight: 600;
                color: #2f5069;
            }
            QProgressBar {
                border: 1px solid #c5d5e7;
                border-radius: 12px;
                text-align: center;
                background: #edf3f9;
                color: #123a56;
                font-weight: 700;
            }
            QProgressBar::chunk {
                border-radius: 12px;
                background: #dd6b20;
            }
            QMenuBar {
                background: rgba(255, 255, 255, 0.88);
                border-bottom: 1px solid #d1dfec;
            }
            """
        )

    def _refresh_algorithm_hints(self) -> None:
        algorithm = self.algorithm_combo.currentText()
        mode = self.mode_combo.currentText()

        placeholder = "根据算法填写密钥"
        key_enabled = True

        if algorithm == "Caesar":
            placeholder = "整数偏移量，例如 3"
        elif algorithm == "Rail Fence":
            placeholder = "轨道数，例如 3"
        elif algorithm == "AES":
            placeholder = "AES 口令（至少 8 位）"
        else:
            placeholder = "摘要算法无需密钥"
            key_enabled = False

        self.key_input.setEnabled(key_enabled)
        self.key_input.setPlaceholderText(placeholder)

        desc = ALGORITHM_DESCRIPTIONS[algorithm]
        self.algorithm_desc.setHtml(
            f"<h3>{desc.name}</h3>"
            f"<p><b>用途：</b>{desc.purpose}</p>"
            f"<p><b>安全性：</b>{desc.security}</p>"
        )

        if algorithm in {"MD5", "SHA-256"} and mode == "decrypt":
            self._set_crypto_status("当前算法不可逆，无法解密", "warn")
        else:
            self._set_crypto_status("准备就绪", "neutral")

    def _set_crypto_status(self, message: str, status: str) -> None:
        mapping = {
            "neutral": "StatusNeutral",
            "ok": "StatusOk",
            "warn": "StatusWarn",
            "err": "StatusErr",
        }
        self.crypto_status.setObjectName(mapping.get(status, "StatusNeutral"))
        self.crypto_status.setText(message)
        self.crypto_status.style().unpolish(self.crypto_status)
        self.crypto_status.style().polish(self.crypto_status)

    def _process_crypto(self) -> None:
        algorithm = self.algorithm_combo.currentText()
        mode = self.mode_combo.currentText()
        text = self.input_edit.toPlainText()
        key = self.key_input.text().strip()

        if not text.strip():
            self._set_crypto_status("请输入待处理文本", "warn")
            return

        try:
            result = process_text(algorithm=algorithm, mode=mode, text=text, key=key)
            self.output_edit.setPlainText(result)
            self._set_crypto_status("处理成功", "ok")
        except NonReversibleAlgorithmError as exc:
            self.output_edit.clear()
            self._set_crypto_status(str(exc), "warn")
        except (InvalidKeyError, InvalidCipherTextError) as exc:
            self.output_edit.clear()
            self._set_crypto_status(str(exc), "err")
        except CryptoError as exc:
            self.output_edit.clear()
            self._set_crypto_status(f"处理失败：{exc}", "err")

    def _copy_result(self) -> None:
        output = self.output_edit.toPlainText()
        if not output:
            self._set_crypto_status("没有可复制内容", "warn")
            return

        QGuiApplication.clipboard().setText(output)
        self._set_crypto_status("结果已复制到剪贴板", "ok")

    def _clear_crypto(self) -> None:
        self.input_edit.clear()
        self.output_edit.clear()
        self.key_input.clear()
        self._set_crypto_status("已清空", "neutral")

    def _toggle_password_echo(self, checked: bool) -> None:
        self.password_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)

    def _analyze_password(self) -> None:
        password = self.password_input.text()
        result = evaluate_password(password)
        self._render_strength_result(result)

    def _render_strength_result(self, result: PasswordCheckResult) -> None:
        self.score_label.setText(f"{result.score} / 100")
        self.level_label.setText(f"等级：{result.level}")
        self.score_bar.setValue(result.score)
        self._update_score_bar_color(result.score)

        self.length_val.setText(str(result.stats.length))
        self.upper_val.setText(str(result.stats.uppercase))
        self.lower_val.setText(str(result.stats.lowercase))
        self.digits_val.setText(str(result.stats.digits))
        self.symbols_val.setText(str(result.stats.symbols))

        risk_lines = []
        risk_lines.append(
            "[命中] 常见密码词典" if result.flags["is_common"] else "[通过] 未命中常见密码词典"
        )
        risk_lines.append(
            "[命中] 连续字符/键盘序列" if result.flags["has_sequence"] else "[通过] 未检测到连续序列"
        )
        risk_lines.append(
            "[命中] 重复字符模式" if result.flags["has_repeat_char"] else "[通过] 未检测到重复字符"
        )
        risk_lines.append(
            "[命中] 重复片段模式" if result.flags["has_repeat_pattern"] else "[通过] 未检测到重复片段"
        )

        self.risk_text.setPlainText("\n".join(risk_lines))
        self.advice_text.setPlainText("\n".join(result.suggestions))

    def _update_score_bar_color(self, score: int) -> None:
        if score < 40:
            color = "#d94841"
        elif score < 70:
            color = "#d97706"
        elif score < 90:
            color = "#2f9e44"
        else:
            color = "#0b7285"

        self.score_bar.setStyleSheet(
            f"""
            QProgressBar {{
                border: 1px solid #c5d5e7;
                border-radius: 12px;
                text-align: center;
                background: #edf3f9;
                color: #123a56;
                font-weight: 700;
            }}
            QProgressBar::chunk {{
                border-radius: 12px;
                background: {color};
            }}
            """
        )
