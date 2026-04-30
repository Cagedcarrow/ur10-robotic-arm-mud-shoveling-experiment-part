#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import shutil
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from deepseek_reporter import ensure_config_file, generate_single_experiment_report, test_connection
from metrics_utils import process_experiment


class AnalysisWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("UR10 FT300 分析 GUI")
        self.resize(1100, 700)

        self.root_dir = Path(__file__).resolve().parents[1]
        self.data_root = self.root_dir / "data"
        self.results_dir = self.root_dir / "results"
        self.config_path = self.root_dir / "config" / "llm_config.yaml"
        ensure_config_file(self.config_path)
        self.last_report_path: Path | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        vbox = QVBoxLayout(central)

        self.status = QLabel("状态: 就绪")
        vbox.addWidget(self.status)

        exp_bar = QHBoxLayout()
        self.exp_dir_line = QLineEdit(str(self.data_root))
        self.btn_pick_exp_dir = QPushButton("读取数据文件夹")
        self.btn_test_llm = QPushButton("测试DeepSeek连接")
        self.btn_llm_report = QPushButton("执行分析")
        self.btn_open_report = QPushButton("打开最新报告")
        self.btn_open_report.setEnabled(False)
        exp_bar.addWidget(QLabel("实验目录"))
        exp_bar.addWidget(self.exp_dir_line)
        exp_bar.addWidget(self.btn_pick_exp_dir)
        exp_bar.addWidget(self.btn_test_llm)
        exp_bar.addWidget(self.btn_llm_report)
        exp_bar.addWidget(self.btn_open_report)
        vbox.addLayout(exp_bar)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("分析结果预览...")
        vbox.addWidget(self.preview)

        self.btn_pick_exp_dir.clicked.connect(self.pick_exp_dir)
        self.btn_test_llm.clicked.connect(self.test_llm_action)
        self.btn_llm_report.clicked.connect(self.generate_llm_report_action)
        self.btn_open_report.clicked.connect(self.open_latest_report)

    def pick_exp_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择单实验目录", self.exp_dir_line.text().strip() or str(self.data_root))
        if path:
            self.exp_dir_line.setText(path)

    def test_llm_action(self) -> None:
        self.status.setText(f"状态: 测试 DeepSeek 连接中 ({self.config_path}) ...")
        QApplication.processEvents()
        try:
            msg = test_connection(self.config_path)
        except Exception as exc:
            self.status.setText(f"状态: 连接测试失败: {exc}")
            QMessageBox.critical(self, "DeepSeek连接失败", str(exc))
            return
        self.status.setText("状态: DeepSeek 连接成功")
        self.preview.setPlainText(msg)

    def generate_llm_report_action(self) -> None:
        src_dir = Path(self.exp_dir_line.text().strip()).expanduser().resolve()
        if not src_dir.exists() or not src_dir.is_dir():
            self.status.setText(f"状态: 实验目录不存在: {src_dir}")
            return

        out_dir = self.results_dir / f"{src_dir.name}_analysis_result"
        out_dir.mkdir(parents=True, exist_ok=True)

        src_csv = src_dir / "ur10_ft300_realtime_data.csv"
        src_metrics = src_dir / "processed_metrics.csv"
        target_metrics = out_dir / "processed_metrics.csv"

        if not src_metrics.exists():
            reply = QMessageBox.question(
                self,
                "缺少指标文件",
                f"源目录未检测到 {src_metrics.name}。\n是否先自动处理原始 CSV 再进行 DeepSeek 分析？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply != QMessageBox.Yes:
                self.status.setText("状态: 用户取消自动处理")
                return
            if not src_csv.exists():
                self.status.setText(f"状态: 原始 CSV 不存在: {src_csv}")
                QMessageBox.critical(self, "分析失败", f"未找到原始 CSV:\n{src_csv}")
                return
            self.status.setText(f"状态: 正在本地处理 ({src_dir.name}) ...")
            QApplication.processEvents()
            try:
                process_experiment(
                    experiment_dir=out_dir,
                    csv_path=src_csv,
                    mass_g_cli=None,
                    force_threshold=10.0,
                    smooth_window=5,
                )
            except Exception as exc:
                self.status.setText(f"状态: 本地处理失败: {exc}")
                QMessageBox.critical(self, "本地处理失败", str(exc))
                return
        else:
            shutil.copy2(src_metrics, target_metrics)

        src_meta = src_dir / "metadata.txt"
        src_manual = src_dir / "manual_record.txt"
        if src_meta.exists():
            shutil.copy2(src_meta, out_dir / "metadata.txt")
        if src_manual.exists():
            shutil.copy2(src_manual, out_dir / "manual_record.txt")
        if src_csv.exists():
            shutil.copy2(src_csv, out_dir / "ur10_ft300_realtime_data.csv")

        self.status.setText(f"状态: 生成 DeepSeek 报告中 ({src_dir.name}) ...")
        QApplication.processEvents()
        try:
            result = generate_single_experiment_report(
                experiment_dir=out_dir,
                root_dir=self.root_dir,
                config_path=self.config_path,
                force_threshold=10.0,
                smooth_window=5,
                report_dir=out_dir,
            )
        except Exception as exc:
            self.status.setText(f"状态: 报告生成失败: {exc}")
            QMessageBox.critical(self, "报告生成失败", str(exc))
            return

        self.last_report_path = result.report_path
        self.btn_open_report.setEnabled(True)
        self.status.setText(f"状态: 报告完成 -> {result.report_path}")
        self.preview.setPlainText(result.report_path.read_text(encoding="utf-8", errors="ignore"))

    def open_latest_report(self) -> None:
        if self.last_report_path is None or not self.last_report_path.exists():
            self.status.setText("状态: 尚无可打开的报告")
            return
        subprocess.run(["xdg-open", str(self.last_report_path)], check=False)
        self.status.setText(f"状态: 已打开报告 {self.last_report_path.name}")


def main() -> int:
    app = QApplication(sys.argv)
    win = AnalysisWindow()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
