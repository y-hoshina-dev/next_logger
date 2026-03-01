from __future__ import annotations

from collections import deque
from datetime import datetime
from html import escape
import os
from pathlib import Path

from PySide6.QtCore import QDate, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from next_logger.application import LoggerController
from next_logger.application.log_markers import DEFAULT_CUSTOM_ERROR_KEYWORDS
from next_logger.domain import AppState, ConnectionConfig, SessionConfig
from next_logger.infrastructure import AppSettingsStore
from .setup_wizard import SetupWizardDialog

BAUDRATE_OPTIONS = [
    "1200",
    "2400",
    "4800",
    "9600",
    "19200",
    "38400",
    "57600",
    "115200",
    "230400",
    "460800",
    "921600",
]

LOG_MARKER_COLORS = {
    "error": "#D32F2F",
    "warning": "#B28704",
    "info": "#1F2937",
}

PROMPT_TEMPLATE_CHOICES = [
    ("auto", "自動選択（推奨）"),
    ("analyze_error", "異常解析"),
    ("summary", "時系列要約"),
    ("extract_error", "エラー抽出"),
    ("improvement", "改善提案"),
]

PROMPT_TEMPLATE_TEXTS = {
    "analyze_error": (
        "以下はシリアルログです。原因候補を優先度順に3つ挙げてください。\n"
        "各候補について「根拠となるログ行」「確認すべき追加ログ」「次の切り分け手順」を記載してください。\n"
        "最後に、最短で再現確認できる手順を提示してください。"
    ),
    "summary": (
        "以下のログを時系列で要約してください。\n"
        "「正常動作」「警告」「エラー」に分類し、重要イベントだけ5行以内でまとめてください。"
    ),
    "extract_error": (
        "以下のログから異常行だけ抽出し、表形式で出してください。\n"
        "列: 時刻 / レベル推定 / メッセージ / 影響度(高・中・低)"
    ),
    "improvement": (
        "以下のログを分析し、再発防止のための改善案を\n"
        "「ソフト側」「接続設定側」「運用側」に分けて提案してください。\n"
        "すぐ実施できる順に並べてください。"
    ),
}

PROMPT_TEMPLATE_LABELS = {
    "analyze_error": "異常解析",
    "summary": "時系列要約",
    "extract_error": "エラー抽出",
    "improvement": "改善提案",
}

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Next Logger")
        self.resize(1400, 850)

        self.controller = LoggerController()
        self.settings_store = AppSettingsStore()
        self._records: deque[dict[str, object]] = deque(maxlen=20000)

        self._build_ui()
        self._connect_signals()
        self._refresh_ports()
        self._run_setup_wizard_if_needed()
        self._refresh_profiles()
        self._update_preview_path()
        self._update_button_states()
        self._sync_reconnect_inputs()

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start()

        self._show_recovery_notice_if_needed()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)

        outer_layout = QVBoxLayout(root)
        toolbar = self._build_toolbar()
        outer_layout.addLayout(toolbar)

        splitter = QSplitter()
        splitter.addWidget(self._build_connection_panel())
        splitter.addWidget(self._build_log_panel())
        splitter.addWidget(self._build_session_panel())
        splitter.setSizes([310, 700, 390])
        outer_layout.addWidget(splitter)

        status = QStatusBar(self)
        self.setStatusBar(status)
        self.state_label = QLabel("状態: IDLE")
        self.recv_label = QLabel("受信: 0")
        self.drop_label = QLabel("欠損: 0")
        self.fail_label = QLabel("保存失敗: 0")
        self.err_label = QLabel("エラー行: 0")
        self.rate_label = QLabel("受信レート: 0.0 lines/s")

        status.addPermanentWidget(self.state_label)
        status.addPermanentWidget(self.recv_label)
        status.addPermanentWidget(self.drop_label)
        status.addPermanentWidget(self.fail_label)
        status.addPermanentWidget(self.err_label)
        status.addPermanentWidget(self.rate_label)

    def _build_toolbar(self) -> QHBoxLayout:
        layout = QHBoxLayout()

        self.start_btn = QPushButton("開始")
        self.pause_btn = QPushButton("一時停止")
        self.resume_btn = QPushButton("再開")
        self.stop_btn = QPushButton("停止")
        self.refresh_ports_btn = QPushButton("ポート再取得")

        layout.addWidget(self.start_btn)
        layout.addWidget(self.pause_btn)
        layout.addWidget(self.resume_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.refresh_ports_btn)
        layout.addStretch(1)
        return layout

    def _build_connection_panel(self) -> QWidget:
        box = QGroupBox("接続設定")
        layout = QFormLayout(box)

        self.port_combo = QComboBox()
        self.port_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.baud_combo = QComboBox()
        self.baud_combo.setEditable(True)
        self.baud_combo.addItems(BAUDRATE_OPTIONS)
        self.baud_combo.setCurrentText("9600")
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["N", "E", "O"])
        self.bytesize_combo = QComboBox()
        self.bytesize_combo.addItems(["8", "7", "6", "5"])
        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(["1", "1.5", "2"])
        self.timeout_edit = QLineEdit("1.0")
        self.auto_reconnect_check = QCheckBox("有効")
        self.auto_reconnect_check.setChecked(True)
        self.reconnect_retry_spin = QSpinBox()
        self.reconnect_retry_spin.setRange(0, 50)
        self.reconnect_retry_spin.setValue(5)
        self.reconnect_backoff_combo = QComboBox()
        self.reconnect_backoff_combo.addItem("fixed", userData="fixed")
        self.reconnect_backoff_combo.addItem("exponential", userData="exponential")
        self.reconnect_interval_spin = QDoubleSpinBox()
        self.reconnect_interval_spin.setRange(0.1, 60.0)
        self.reconnect_interval_spin.setSingleStep(0.5)
        self.reconnect_interval_spin.setValue(2.0)
        self.reconnect_max_interval_spin = QDoubleSpinBox()
        self.reconnect_max_interval_spin.setRange(0.1, 120.0)
        self.reconnect_max_interval_spin.setSingleStep(0.5)
        self.reconnect_max_interval_spin.setValue(10.0)

        layout.addRow("COMポート", self.port_combo)
        layout.addRow("ボーレート", self.baud_combo)
        layout.addRow("Parity", self.parity_combo)
        layout.addRow("Data bits", self.bytesize_combo)
        layout.addRow("Stop bits", self.stopbits_combo)
        layout.addRow("Timeout(sec)", self.timeout_edit)
        layout.addRow("自動再接続", self.auto_reconnect_check)
        layout.addRow("再接続上限(回)", self.reconnect_retry_spin)
        layout.addRow("再接続モード", self.reconnect_backoff_combo)
        layout.addRow("再接続待機(sec)", self.reconnect_interval_spin)
        layout.addRow("再接続最大待機(sec)", self.reconnect_max_interval_spin)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.addWidget(box)
        wrapper_layout.addStretch(1)
        return wrapper

    def _build_log_panel(self) -> QWidget:
        box = QGroupBox("ライブログ")
        outer = QVBoxLayout(box)

        filter_bar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("検索キーワード")
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["すべて", "エラーのみ", "通常のみ"])
        filter_bar.addWidget(self.search_edit)
        filter_bar.addWidget(self.filter_combo)
        outer.addLayout(filter_bar)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.document().setMaximumBlockCount(5000)
        outer.addWidget(self.log_view)

        ai_box = QGroupBox("AIプロンプト")
        ai_layout = QVBoxLayout(ai_box)

        self.ai_detection_label = QLabel("General marker detection: error=0 / warning=0")
        ai_layout.addWidget(self.ai_detection_label)

        ai_selector_row = QHBoxLayout()
        self.ai_template_combo = QComboBox()
        for key, label in PROMPT_TEMPLATE_CHOICES:
            self.ai_template_combo.addItem(label, userData=key)
        self.ai_generate_btn = QPushButton("生成")
        self.ai_copy_btn = QPushButton("コピー")
        ai_selector_row.addWidget(self.ai_template_combo)
        ai_selector_row.addWidget(self.ai_generate_btn)
        ai_selector_row.addWidget(self.ai_copy_btn)
        ai_layout.addLayout(ai_selector_row)

        self.ai_prompt_view = QPlainTextEdit()
        self.ai_prompt_view.setPlaceholderText("AIへ渡すプロンプトがここに生成されます。")
        self.ai_prompt_view.setMaximumBlockCount(2000)
        ai_layout.addWidget(self.ai_prompt_view)

        outer.addWidget(ai_box)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.addWidget(box)
        return wrapper

    def _build_session_panel(self) -> QWidget:
        top_box = QGroupBox("セッション設定")
        top_layout = QFormLayout(top_box)

        self.product_edit = QLineEdit()
        self.serial_edit = QLineEdit()
        self.comment_edit = QLineEdit()

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyyMMdd")
        self.date_edit.setDate(QDate.currentDate())

        self.save_dir_edit = QLineEdit(str(Path.cwd()))
        self.save_dir_btn = QPushButton("選択")
        save_dir_row = QWidget()
        save_dir_layout = QHBoxLayout(save_dir_row)
        save_dir_layout.setContentsMargins(0, 0, 0, 0)
        save_dir_layout.addWidget(self.save_dir_edit)
        save_dir_layout.addWidget(self.save_dir_btn)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["txt", "csv", "jsonl"])

        self.error_keywords_edit = QLineEdit(",".join(DEFAULT_CUSTOM_ERROR_KEYWORDS))

        self.resume_policy_combo = QComboBox()
        self.resume_policy_combo.addItem("同じファイルに追記", userData="append")
        self.resume_policy_combo.addItem("新しいセグメントを作成", userData="new_segment")
        self.retention_max_sessions_spin = QSpinBox()
        self.retention_max_sessions_spin.setRange(0, 100000)
        self.retention_max_sessions_spin.setValue(0)
        self.retention_max_sessions_spin.setSpecialValueText("無制限")
        self.retention_max_age_days_spin = QSpinBox()
        self.retention_max_age_days_spin.setRange(0, 3650)
        self.retention_max_age_days_spin.setValue(0)
        self.retention_max_age_days_spin.setSpecialValueText("無制限")

        top_layout.addRow("製品名", self.product_edit)
        top_layout.addRow("シリアル番号", self.serial_edit)
        top_layout.addRow("コメント", self.comment_edit)
        top_layout.addRow("日付", self.date_edit)
        top_layout.addRow("保存先", save_dir_row)
        top_layout.addRow("保存形式", self.format_combo)
        top_layout.addRow("エラーキーワード", self.error_keywords_edit)
        top_layout.addRow("再開時の保存", self.resume_policy_combo)
        top_layout.addRow("保持セッション数", self.retention_max_sessions_spin)
        top_layout.addRow("保持日数", self.retention_max_age_days_spin)

        preview_box = QGroupBox("保存先プレビュー")
        preview_layout = QVBoxLayout(preview_box)
        self.preview_label = QLabel("")
        self.preview_label.setWordWrap(True)
        self.preview_label.setTextInteractionFlags(self.preview_label.textInteractionFlags())
        preview_layout.addWidget(self.preview_label)

        profile_box = QGroupBox("プロファイル")
        profile_layout = QFormLayout(profile_box)
        self.profile_name_edit = QLineEdit()
        self.profile_combo = QComboBox()
        self.profile_load_btn = QPushButton("読込")
        self.profile_save_btn = QPushButton("保存")
        self.profile_delete_btn = QPushButton("削除")

        profile_btn_row = QWidget()
        profile_btn_layout = QHBoxLayout(profile_btn_row)
        profile_btn_layout.setContentsMargins(0, 0, 0, 0)
        profile_btn_layout.addWidget(self.profile_load_btn)
        profile_btn_layout.addWidget(self.profile_save_btn)
        profile_btn_layout.addWidget(self.profile_delete_btn)

        profile_layout.addRow("名前", self.profile_name_edit)
        profile_layout.addRow("一覧", self.profile_combo)
        profile_layout.addRow(profile_btn_row)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.addWidget(top_box)
        wrapper_layout.addWidget(preview_box)
        wrapper_layout.addWidget(profile_box)
        wrapper_layout.addStretch(1)

        self._config_widgets = [
            self.port_combo,
            self.baud_combo,
            self.parity_combo,
            self.bytesize_combo,
            self.stopbits_combo,
            self.timeout_edit,
            self.auto_reconnect_check,
            self.reconnect_retry_spin,
            self.reconnect_backoff_combo,
            self.reconnect_interval_spin,
            self.reconnect_max_interval_spin,
            self.product_edit,
            self.serial_edit,
            self.comment_edit,
            self.date_edit,
            self.save_dir_edit,
            self.save_dir_btn,
            self.format_combo,
            self.error_keywords_edit,
            self.resume_policy_combo,
            self.retention_max_sessions_spin,
            self.retention_max_age_days_spin,
        ]

        return wrapper

    def _connect_signals(self) -> None:
        self.start_btn.clicked.connect(self._on_start)
        self.pause_btn.clicked.connect(self._on_pause)
        self.resume_btn.clicked.connect(self._on_resume)
        self.stop_btn.clicked.connect(self._on_stop)
        self.refresh_ports_btn.clicked.connect(self._refresh_ports)
        self.save_dir_btn.clicked.connect(self._browse_save_dir)

        self.search_edit.textChanged.connect(self._reload_log_view)
        self.filter_combo.currentIndexChanged.connect(self._reload_log_view)

        self.profile_save_btn.clicked.connect(self._save_profile)
        self.profile_load_btn.clicked.connect(self._load_profile)
        self.profile_delete_btn.clicked.connect(self._delete_profile)
        self.auto_reconnect_check.toggled.connect(self._sync_reconnect_inputs)
        self.ai_generate_btn.clicked.connect(self._generate_ai_prompt)
        self.ai_copy_btn.clicked.connect(self._copy_ai_prompt)
        self.ai_template_combo.currentIndexChanged.connect(self._update_ai_recommendation)

        for widget in [
            self.product_edit,
            self.serial_edit,
            self.comment_edit,
            self.save_dir_edit,
            self.error_keywords_edit,
        ]:
            widget.textChanged.connect(self._update_preview_path)

        self.date_edit.dateChanged.connect(self._update_preview_path)
        self.format_combo.currentIndexChanged.connect(self._update_preview_path)

    def _run_setup_wizard_if_needed(self) -> None:
        if self.settings_store.get_bool("onboarding_completed", False):
            return

        if self.controller.list_profiles():
            self.settings_store.set_bool("onboarding_completed", True)
            return

        dialog = SetupWizardDialog(
            ports=self.controller.list_ports(),
            default_save_dir=self.save_dir_edit.text(),
            parent=self,
        )
        if not dialog.exec():
            self.statusBar().showMessage("初回セットアップをスキップしました。", 5000)
            return

        payload = dialog.result_payload()
        self._apply_setup_payload(payload)

        if bool(payload.get("save_profile", False)):
            profile_name = str(payload.get("profile_name", "default"))
            try:
                connection = self._collect_connection_config()
                session = self._collect_session_config()
                self.controller.save_profile(profile_name, connection, session)
                self._refresh_profiles(selected=profile_name)
            except ValueError as exc:
                QMessageBox.warning(self, "入力エラー", f"初期プロファイル保存に失敗: {exc}")

        self.settings_store.set_bool("onboarding_completed", True)

    def _apply_setup_payload(self, payload: dict[str, object]) -> None:
        self.port_combo.setCurrentText(str(payload.get("port", "")))
        self.baud_combo.setCurrentText(str(payload.get("baudrate", "9600")))
        self.product_edit.setText(str(payload.get("product", "")))
        self.serial_edit.setText(str(payload.get("serial_number", "")))
        self.save_dir_edit.setText(str(payload.get("save_dir", self.save_dir_edit.text())))
        self.auto_reconnect_check.setChecked(bool(payload.get("auto_reconnect", True)))
        self.reconnect_retry_spin.setValue(int(payload.get("reconnect_max_retries", 5)))
        self.reconnect_backoff_combo.setCurrentIndex(0)
        self.reconnect_interval_spin.setValue(2.0)
        self.reconnect_max_interval_spin.setValue(10.0)
        self._sync_reconnect_inputs()
        self._update_preview_path()

    def _on_tick(self) -> None:
        for event in self.controller.poll_events():
            event_type = event.get("type")
            if event_type == "line":
                self._handle_line_event(event)
            elif event_type == "status":
                self.statusBar().showMessage(str(event.get("message", "")), 5000)
            elif event_type == "error":
                self.statusBar().showMessage(str(event.get("message", "")), 10000)
                self._show_retry_dialog(str(event.get("message", "")))
            elif event_type == "session_started":
                self._handle_session_started(event)
            elif event_type == "session_stopped":
                self._handle_session_stopped(event)
            elif event_type == "preflight_failed":
                self.statusBar().showMessage("プリフライト失敗", 5000)

        self._update_stats_view()
        self._update_button_states()
        self._update_ai_recommendation()

    def _handle_line_event(self, event: dict[str, object]) -> None:
        severity = str(event.get("severity", "error" if bool(event.get("is_error", False)) else "info"))
        if severity not in LOG_MARKER_COLORS:
            severity = "info"
        marker_terms = tuple(str(item) for item in event.get("marker_terms", []))
        record = {
            "timestamp": str(event.get("timestamp", "")),
            "line": str(event.get("line", "")),
            "is_error": bool(event.get("is_error", False)),
            "severity": severity,
            "marker_terms": marker_terms,
            "write_ok": bool(event.get("write_ok", True)),
        }
        self._records.append(record)

        if self._record_matches(record):
            self.log_view.append(self._format_record_html(record))

    def _record_label(self, record: dict[str, object]) -> str:
        severity = str(record.get("severity", "info"))
        if bool(record.get("is_error", False)) or severity == "error":
            return "ERROR"
        if severity == "warning":
            return "WARN"
        return "INFO"

    def _format_record(self, record: dict[str, object]) -> str:
        label = f"[{self._record_label(record)}]"
        suffix = " [WRITE-FAILED]" if not bool(record["write_ok"]) else ""
        return f"{record['timestamp']} {label} {record['line']}{suffix}"

    def _format_record_html(self, record: dict[str, object]) -> str:
        text = escape(self._format_record(record))
        severity = str(record.get("severity", "info"))
        color = LOG_MARKER_COLORS.get(severity, LOG_MARKER_COLORS["info"])
        marker_terms = tuple(str(item) for item in record.get("marker_terms", ()))
        marker_hint = ""
        if marker_terms:
            marker_hint = f" <span style='color:#6B7280;'>({escape(','.join(marker_terms[:3]))})</span>"
        return f"<span style='color:{color};'>{text}</span>{marker_hint}"

    def _record_matches(self, record: dict[str, object]) -> bool:
        mode = self.filter_combo.currentIndex()
        severity = str(record.get("severity", "error" if bool(record.get("is_error", False)) else "info"))

        if mode == 1 and severity != "error":
            return False
        if mode == 2 and severity == "error":
            return False

        query = self.search_edit.text().strip().lower()
        if query and query not in str(record["line"]).lower():
            return False
        return True

    def _reload_log_view(self) -> None:
        self.log_view.clear()
        for record in self._records:
            if self._record_matches(record):
                self.log_view.append(self._format_record_html(record))
        self._update_ai_recommendation()

    def _count_marker_levels(self) -> tuple[int, int]:
        error_count = 0
        warning_count = 0
        for record in self._records:
            severity = str(record.get("severity", "error" if bool(record.get("is_error", False)) else "info"))
            if severity == "error":
                error_count += 1
            elif severity == "warning":
                warning_count += 1
        return error_count, warning_count

    def _recommended_prompt_key(self) -> str:
        error_count, warning_count = self._count_marker_levels()
        stats = self.controller.get_stats_snapshot()
        if stats.write_failures > 0 or error_count >= 5:
            return "analyze_error"
        if error_count > 0:
            return "extract_error"
        if warning_count > 0:
            return "improvement"
        return "summary"

    def _update_ai_recommendation(self) -> None:
        error_count, warning_count = self._count_marker_levels()
        recommended_key = self._recommended_prompt_key()
        recommended_label = PROMPT_TEMPLATE_LABELS.get(recommended_key, "summary")
        self.ai_detection_label.setText(
            f"General marker detection: error={error_count} / warning={warning_count} / recommended: {recommended_label}"
        )

    def _resolve_prompt_key(self) -> str:
        selected_key = str(self.ai_template_combo.currentData())
        if selected_key == "auto":
            return self._recommended_prompt_key()
        return selected_key

    def _collect_prompt_logs(self, max_lines: int = 300) -> str:
        records = list(self._records)[-max_lines:]
        if not records:
            return "(ログがありません)"
        return "\n".join(self._format_record(record) for record in records)

    def _generate_ai_prompt(self) -> None:
        resolved_key = self._resolve_prompt_key()
        template = PROMPT_TEMPLATE_TEXTS.get(resolved_key)
        if template is None:
            QMessageBox.warning(self, "設定エラー", "プロンプトテンプレートが見つかりません。")
            return

        prompt = f"{template}\n\n[ログ本文]\n{self._collect_prompt_logs()}"
        self.ai_prompt_view.setPlainText(prompt)
        self.statusBar().showMessage("AIプロンプトを生成しました。", 4000)

    def _copy_ai_prompt(self) -> None:
        text = self.ai_prompt_view.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "情報", "先にプロンプトを生成してください。")
            return

        QApplication.clipboard().setText(text)
        self.statusBar().showMessage("AIプロンプトをクリップボードへコピーしました。", 4000)

    def _on_start(self) -> None:
        try:
            connection = self._collect_connection_config()
        except ValueError as exc:
            QMessageBox.warning(self, "入力エラー", str(exc))
            return

        session = self._collect_session_config()
        errors = self.controller.start(connection, session)
        if errors:
            QMessageBox.warning(self, "開始できません", "\n".join(errors))

    def _on_pause(self) -> None:
        self.controller.pause()

    def _on_resume(self) -> None:
        session = self._collect_session_config()
        self.controller.resume(session)

    def _on_stop(self) -> None:
        self.controller.stop()

    def _collect_connection_config(self) -> ConnectionConfig:
        port = self.port_combo.currentText().strip()
        try:
            baudrate = int(self.baud_combo.currentText().strip())
            bytesize = int(self.bytesize_combo.currentText())
            stopbits = float(self.stopbits_combo.currentText())
            timeout = float(self.timeout_edit.text().strip())
        except ValueError as exc:
            raise ValueError("接続設定に数値以外の値が含まれています。") from exc

        return ConnectionConfig(
            port=port,
            baudrate=baudrate,
            parity=self.parity_combo.currentText(),
            bytesize=bytesize,
            stopbits=stopbits,
            timeout=timeout,
            auto_reconnect=self.auto_reconnect_check.isChecked(),
            reconnect_max_retries=self.reconnect_retry_spin.value(),
            reconnect_backoff_mode=self.reconnect_backoff_combo.currentData(),
            reconnect_interval_sec=float(self.reconnect_interval_spin.value()),
            reconnect_max_interval_sec=float(self.reconnect_max_interval_spin.value()),
        )

    def _collect_session_config(self) -> SessionConfig:
        keywords = tuple(part.strip() for part in self.error_keywords_edit.text().split(","))
        resume_policy = self.resume_policy_combo.currentData()
        return SessionConfig(
            product=self.product_edit.text().strip(),
            serial_number=self.serial_edit.text().strip(),
            comment=self.comment_edit.text().strip(),
            date=self.date_edit.date().toString("yyyyMMdd"),
            save_dir=Path(self.save_dir_edit.text().strip() or "."),
            log_format=self.format_combo.currentText(),
            error_keywords=keywords,
            resume_policy=resume_policy,
            retention_max_sessions=self.retention_max_sessions_spin.value(),
            retention_max_age_days=self.retention_max_age_days_spin.value(),
        )

    def _refresh_ports(self) -> None:
        ports = self.controller.list_ports()
        current = self.port_combo.currentText()

        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        self.port_combo.addItems(ports)

        if current and current in ports:
            self.port_combo.setCurrentText(current)
        elif ports:
            self.port_combo.setCurrentIndex(0)
        self.port_combo.blockSignals(False)

    def _browse_save_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "保存先フォルダを選択", self.save_dir_edit.text())
        if selected:
            self.save_dir_edit.setText(selected)
            self._update_preview_path()

    def _update_preview_path(self) -> None:
        session = self._collect_session_config()
        preview = self.controller.build_preview_path(session)
        self.preview_label.setText(str(preview))

    def _update_button_states(self) -> None:
        state = self.controller.state

        self.start_btn.setEnabled(state in {AppState.IDLE, AppState.READY, AppState.ERROR})
        self.pause_btn.setEnabled(state == AppState.RUNNING)
        self.resume_btn.setEnabled(state == AppState.PAUSED)
        self.stop_btn.setEnabled(state in {AppState.RUNNING, AppState.PAUSED, AppState.ERROR, AppState.STOPPING})

        editable = state in {AppState.IDLE, AppState.READY, AppState.ERROR, AppState.PAUSED}
        for widget in self._config_widgets:
            widget.setEnabled(editable)
        self._sync_reconnect_inputs()

    def _sync_reconnect_inputs(self) -> None:
        enabled = self.auto_reconnect_check.isChecked() and self.auto_reconnect_check.isEnabled()
        self.reconnect_retry_spin.setEnabled(enabled)
        self.reconnect_backoff_combo.setEnabled(enabled)
        self.reconnect_interval_spin.setEnabled(enabled)
        self.reconnect_max_interval_spin.setEnabled(enabled)

    def _update_stats_view(self) -> None:
        stats = self.controller.get_stats_snapshot()
        elapsed = 0.0
        if stats.start_time is not None:
            end = stats.end_time or datetime.now()
            elapsed = max((end - stats.start_time).total_seconds(), 1e-6)

        rate = stats.received_lines / elapsed if elapsed > 0 else 0.0

        self.state_label.setText(f"状態: {self.controller.state.value}")
        self.recv_label.setText(f"受信: {stats.received_lines}")
        self.drop_label.setText(f"欠損: {stats.dropped_lines}")
        self.fail_label.setText(f"保存失敗: {stats.write_failures}")
        self.err_label.setText(f"エラー行: {stats.error_lines}")
        self.rate_label.setText(f"受信レート: {rate:.1f} lines/s")

    def _handle_session_started(self, event: dict[str, object]) -> None:
        warnings = event.get("warnings", [])
        if warnings:
            QMessageBox.information(self, "注意", "\n".join(str(w) for w in warnings))
        self.statusBar().showMessage(f"記録開始: {event.get('session_dir', '')}", 7000)

    def _handle_session_stopped(self, event: dict[str, object]) -> None:
        manifest = str(event.get("manifest", ""))
        retention = event.get("retention", {})
        removed_age = int(retention.get("removed_age", 0)) if isinstance(retention, dict) else 0
        removed_count = int(retention.get("removed_count", 0)) if isinstance(retention, dict) else 0
        retention_suffix = ""
        if removed_age or removed_count:
            retention_suffix = f" / 保持整理: age={removed_age}, count={removed_count}"
        if manifest:
            self.statusBar().showMessage(f"停止しました。manifest: {manifest}{retention_suffix}", 10000)
        else:
            self.statusBar().showMessage(f"停止しました。{retention_suffix}", 8000)

    def _show_retry_dialog(self, message: str) -> None:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("シリアルエラー")
        dialog.setText(message)
        retry_btn = dialog.addButton("再試行", QMessageBox.ButtonRole.AcceptRole)
        stop_btn = dialog.addButton("停止", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()

        clicked = dialog.clickedButton()
        if clicked is retry_btn:
            self.controller.stop(reason="recover_retry")
            self._on_start()
        elif clicked is stop_btn:
            self.controller.stop(reason="recover_stop")

    def _save_profile(self) -> None:
        name = self.profile_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "入力エラー", "プロファイル名を入力してください。")
            return
        try:
            connection = self._collect_connection_config()
        except ValueError as exc:
            QMessageBox.warning(self, "入力エラー", str(exc))
            return

        session = self._collect_session_config()
        self.controller.save_profile(name, connection, session)
        self._refresh_profiles(selected=name)
        self.statusBar().showMessage(f"プロファイルを保存しました: {name}", 4000)

    def _load_profile(self) -> None:
        name = self.profile_combo.currentText().strip()
        if not name:
            return

        loaded = self.controller.load_profile(name)
        if loaded is None:
            QMessageBox.warning(self, "読込エラー", f"プロファイルが見つかりません: {name}")
            return

        connection, session = loaded
        self._apply_profile(connection, session)
        self.profile_name_edit.setText(name)
        self.statusBar().showMessage(f"プロファイルを読込みました: {name}", 4000)

    def _delete_profile(self) -> None:
        name = self.profile_combo.currentText().strip()
        if not name:
            return

        reply = QMessageBox.question(self, "確認", f"プロファイル '{name}' を削除しますか？")
        if reply == QMessageBox.StandardButton.Yes:
            self.controller.delete_profile(name)
            self._refresh_profiles()

    def _refresh_profiles(self, selected: str = "") -> None:
        names = self.controller.list_profiles()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(names)
        if selected and selected in names:
            self.profile_combo.setCurrentText(selected)
        self.profile_combo.blockSignals(False)

    def _apply_profile(self, connection: ConnectionConfig, session: SessionConfig) -> None:
        self.port_combo.setCurrentText(connection.port)
        self.baud_combo.setCurrentText(str(connection.baudrate))
        self.parity_combo.setCurrentText(connection.parity)
        self.bytesize_combo.setCurrentText(str(connection.bytesize))
        stopbits_text = str(int(connection.stopbits)) if float(connection.stopbits).is_integer() else str(connection.stopbits)
        self.stopbits_combo.setCurrentText(stopbits_text)
        self.timeout_edit.setText(str(connection.timeout))
        self.auto_reconnect_check.setChecked(connection.auto_reconnect)
        self.reconnect_retry_spin.setValue(connection.reconnect_max_retries)
        mode_idx = self.reconnect_backoff_combo.findData(connection.reconnect_backoff_mode)
        if mode_idx >= 0:
            self.reconnect_backoff_combo.setCurrentIndex(mode_idx)
        self.reconnect_interval_spin.setValue(connection.reconnect_interval_sec)
        self.reconnect_max_interval_spin.setValue(connection.reconnect_max_interval_sec)

        self.product_edit.setText(session.product)
        self.serial_edit.setText(session.serial_number)
        self.comment_edit.setText(session.comment)

        date = QDate.fromString(session.date, "yyyyMMdd")
        if date.isValid():
            self.date_edit.setDate(date)

        self.save_dir_edit.setText(str(session.save_dir))
        self.format_combo.setCurrentText(session.log_format)
        self.error_keywords_edit.setText(",".join(session.error_keywords))
        self.retention_max_sessions_spin.setValue(session.retention_max_sessions)
        self.retention_max_age_days_spin.setValue(session.retention_max_age_days)

        index = self.resume_policy_combo.findData(session.resume_policy)
        if index >= 0:
            self.resume_policy_combo.setCurrentIndex(index)

        self._update_preview_path()

    def _show_recovery_notice_if_needed(self) -> None:
        marker = self.controller.load_recovery_marker()
        if not marker:
            return

        session_dir = marker.get("session_dir", "")
        started_at = marker.get("started_at", "")

        msg = QMessageBox(self)
        msg.setWindowTitle("復旧案内")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText("前回セッションが正常終了していない可能性があります。")
        msg.setInformativeText(f"開始時刻: {started_at}\n保存先: {session_dir}")
        open_btn = msg.addButton("保存先を開く", QMessageBox.ButtonRole.ActionRole)
        clear_btn = msg.addButton("マーカーをクリア", QMessageBox.ButtonRole.AcceptRole)
        keep_btn = msg.addButton("そのまま", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked is open_btn and session_dir:
            try:
                if hasattr(os, "startfile"):
                    os.startfile(session_dir)
            except OSError:
                pass

        if clicked is clear_btn:
            self.controller.clear_recovery_marker()

        if clicked is keep_btn:
            self.statusBar().showMessage("復旧マーカーを保持しました。", 5000)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self.controller.state in {AppState.RUNNING, AppState.PAUSED}:
            reply = QMessageBox.question(
                self,
                "確認",
                "ログ取得中です。停止して終了しますか？",
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

            self.controller.stop(reason="window_close")

        self.controller.shutdown()
        self.timer.stop()
        event.accept()
