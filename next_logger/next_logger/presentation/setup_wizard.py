from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


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
class SetupWizardDialog(QDialog):
    def __init__(self, ports: list[str], default_save_dir: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("初回セットアップ")
        self.resize(520, 360)

        root = QVBoxLayout(self)
        root.addWidget(QLabel("最初に基本設定を入力してください。後で画面から変更できます。"))

        form = QFormLayout()

        self.port_combo = QComboBox()
        self.port_combo.addItems(ports)

        self.baud_combo = QComboBox()
        self.baud_combo.setEditable(True)
        self.baud_combo.addItems(BAUDRATE_OPTIONS)
        self.baud_combo.setCurrentText("9600")
        self.product_edit = QLineEdit()
        self.serial_edit = QLineEdit()

        self.save_dir_edit = QLineEdit(default_save_dir)
        self.save_dir_btn = QPushButton("選択")
        save_row = QWidget()
        save_layout = QHBoxLayout(save_row)
        save_layout.setContentsMargins(0, 0, 0, 0)
        save_layout.addWidget(self.save_dir_edit)
        save_layout.addWidget(self.save_dir_btn)

        self.auto_reconnect_check = QCheckBox("自動再接続を有効にする")
        self.auto_reconnect_check.setChecked(True)
        self.reconnect_retry_spin = QSpinBox()
        self.reconnect_retry_spin.setRange(0, 50)
        self.reconnect_retry_spin.setValue(5)

        self.save_profile_check = QCheckBox("この設定をデフォルトプロファイルとして保存")
        self.save_profile_check.setChecked(True)
        self.profile_name_edit = QLineEdit("default")

        form.addRow("COMポート", self.port_combo)
        form.addRow("ボーレート", self.baud_combo)
        form.addRow("製品名", self.product_edit)
        form.addRow("シリアル番号", self.serial_edit)
        form.addRow("保存先", save_row)
        form.addRow(self.auto_reconnect_check)
        form.addRow("再接続上限(回)", self.reconnect_retry_spin)
        form.addRow(self.save_profile_check)
        form.addRow("プロファイル名", self.profile_name_edit)

        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        root.addWidget(buttons)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.save_dir_btn.clicked.connect(self._choose_save_dir)

    def _choose_save_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "保存先フォルダを選択", self.save_dir_edit.text())
        if selected:
            self.save_dir_edit.setText(selected)

    def result_payload(self) -> dict[str, object]:
        return {
            "port": self.port_combo.currentText().strip(),
            "baudrate": self.baud_combo.currentText().strip(),
            "product": self.product_edit.text().strip(),
            "serial_number": self.serial_edit.text().strip(),
            "save_dir": str(Path(self.save_dir_edit.text().strip() or ".")),
            "auto_reconnect": self.auto_reconnect_check.isChecked(),
            "reconnect_max_retries": self.reconnect_retry_spin.value(),
            "save_profile": self.save_profile_check.isChecked(),
            "profile_name": self.profile_name_edit.text().strip() or "default",
        }
