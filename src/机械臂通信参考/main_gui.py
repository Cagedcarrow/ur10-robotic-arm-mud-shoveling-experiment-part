import sys
import time
import csv
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, QTabWidget)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
import pyqtgraph as pg
from ur_full_monitor import URFullMonitor


class DataWorker(QThread):
    """数据采集与保存线程"""
    data_signal = pyqtSignal(list)
    status_signal = pyqtSignal(str)

    def __init__(self, ip):
        super().__init__()
        self.ip = ip
        self.running = True
        self.current_label = 0
        self.start_time_offset = None  # 时间偏移量
        self.monitor = URFullMonitor(robot_ip=self.ip)

    def set_label(self, value):
        self.current_label = value

    def run(self):
        if not self.monitor.connect():
            self.status_signal.emit("连接失败")
            return

        self.status_signal.emit("监控中...")
        filename = f"ur_exp_{time.strftime('%Y%m%d_%H%M%S')}.csv"

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(self.monitor.header)

            while self.running:
                try:
                    header = self.monitor.socket.recv(4)
                    if len(header) < 4: continue
                    p_len = np.frombuffer(header, dtype='>i4')[0]

                    body = b''
                    while len(body) < (p_len - 4):
                        chunk = self.monitor.socket.recv(p_len - 4 - len(body))
                        if not chunk: break
                        body += chunk

                    full_packet = header + body
                    if len(full_packet) >= 1060:
                        row = self.monitor.parse_packet(full_packet)
                        if row:
                            # 1. 时间归零处理
                            if self.start_time_offset is None:
                                self.start_time_offset = row[0]
                            row[0] = round(row[0] - self.start_time_offset, 3)

                            # 2. 追加标签
                            row.append(self.current_label)

                            writer.writerow(row)
                            self.data_signal.emit(row)
                except:
                    break
        self.status_signal.emit(f"已停止并保存至: {filename}")

    def stop(self):
        """修复了报错：添加停止方法"""
        self.running = False
        self.wait()  # 等待线程自然结束


class URMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UR10 实验数据监控系统 (时间归零版)")
        self.resize(1200, 800)
        self.points = 300
        self.cache = np.zeros((37, self.points))  # 36个数据列 + 1个Label列
        self.is_marking = False
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 控制区域
        ctrl_layout = QHBoxLayout()
        self.ip_input = QLineEdit("10.160.9.21")
        self.btn_start = QPushButton("开始监控")
        self.btn_mark = QPushButton("标记实验 (Space)")
        self.btn_mark.setCheckable(True)
        self.btn_mark.setEnabled(False)
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setEnabled(False)
        self.status_label = QLabel("状态: 等待连接")

        self.btn_mark.setStyleSheet("QPushButton:checked { background-color: #ff4d4d; color: white; }")

        ctrl_layout.addWidget(QLabel("IP:"))
        ctrl_layout.addWidget(self.ip_input)
        ctrl_layout.addWidget(self.btn_start)
        ctrl_layout.addWidget(self.btn_mark)
        ctrl_layout.addWidget(self.btn_stop)
        ctrl_layout.addWidget(self.status_label)
        layout.addLayout(ctrl_layout)

        # 绘图区域
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.plot_widgets = {}
        self.curves = {}
        self.groups = {
            "关节位置 (q)": {"idx": range(1, 7), "names": [f"q{i}" for i in range(6)]},
            "关节速度 (qd)": {"idx": range(7, 13), "names": [f"qd{i}" for i in range(6)]},
            "关节电流 (I)": {"idx": range(13, 19), "names": [f"I{i}" for i in range(6)]},
            "TCP位姿 (X-RZ)": {"idx": range(19, 25), "names": ["X", "Y", "Z", "RX", "RY", "RZ"]},
            "TCP速度 (dX-dRZ)": {"idx": range(25, 31), "names": ["dX", "dY", "dZ", "dRX", "dRY", "dRZ"]},
            "目标位置 (Tgt_q)": {"idx": range(31, 37), "names": [f"Tgt_q{i}" for i in range(6)]},
        }

        for title, info in self.groups.items():
            pw = pg.PlotWidget(title=title)
            pw.addLegend()
            self.tabs.addTab(pw, title)
            self.plot_widgets[title] = pw
            self.curves[title] = [pw.plot(pen=(i, 6), name=info['names'][i]) for i in range(6)]

        self.btn_start.clicked.connect(self.start_task)
        self.btn_stop.clicked.connect(self.stop_task)
        self.btn_mark.clicked.connect(self.toggle_mark)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and self.btn_mark.isEnabled():
            self.btn_mark.setChecked(not self.btn_mark.isChecked())
            self.toggle_mark()

    def toggle_mark(self):
        if self.btn_mark.isChecked():
            self.is_marking = True
            if hasattr(self, 'worker'): self.worker.set_label(1)
            self.btn_mark.setText("正在录制...")
        else:
            self.is_marking = False
            if hasattr(self, 'worker'): self.worker.set_label(0)
            self.btn_mark.setText("标记实验 (Space)")

    def start_task(self):
        self.worker = DataWorker(self.ip_input.text())
        self.worker.data_signal.connect(self.update_plots)
        self.worker.status_signal.connect(self.status_label.setText)
        self.worker.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_mark.setEnabled(True)

    def stop_task(self):
        if hasattr(self, 'worker'):
            self.worker.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_mark.setEnabled(False)

    def update_plots(self, row):
        # 此时 row[0] 已经是 0 开头的时间，row[-1] 是 Label
        new_data = row[1:37] + [row[-1]]
        new_vals = np.array(new_data).reshape(-1, 1)
        self.cache = np.hstack([self.cache[:, 1:], new_vals])

        current_title = self.tabs.tabText(self.tabs.currentIndex())
        if current_title in self.groups:
            if self.is_marking:
                self.plot_widgets[current_title].setBackground('#1a0000')
            else:
                self.plot_widgets[current_title].setBackground('k')

            indices = self.groups[current_title]["idx"]
            for i, curve in enumerate(self.curves[current_title]):
                curve.setData(self.cache[indices[i] - 1])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = URMonitorApp()
    window.show()
    sys.exit(app.exec_())