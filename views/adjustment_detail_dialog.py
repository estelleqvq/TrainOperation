# views/adjustment_detail_dialog.py
import matplotlib

matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel, \
    QPushButton
from PyQt5.QtCore import Qt


class AdjustmentDetailDialog(QDialog):
    def __init__(self, parent, delay_details, stations, algo_name, duration, section_delay, terminal_delay):
        super().__init__(parent)
        self.delay_details = delay_details
        self.station_map = {s.id: s.name for s in stations}
        self.algo_name = algo_name
        self.duration = duration
        self.section_delay = section_delay
        self.terminal_delay = terminal_delay

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"调整结果详细分析报告 - {self.algo_name}")
        self.resize(800, 600)
        layout = QVBoxLayout(self)

        # 1. 顶部指标汇总
        summary_text = (f"<b>算法:</b> {self.algo_name} &nbsp;&nbsp;|&nbsp;&nbsp; "
                        f"<b>计算耗时:</b> {self.duration:.3f} 秒 &nbsp;&nbsp;|&nbsp;&nbsp; "
                        f"<b>区段总加权晚点:</b> {self.section_delay:.2f} 分钟 &nbsp;&nbsp;|&nbsp;&nbsp; "
                        f"<b>终点站总加权晚点:</b> {self.terminal_delay:.2f} 分钟")
        lbl_summary = QLabel(summary_text)
        lbl_summary.setStyleSheet("font-size: 14px; padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        layout.addWidget(lbl_summary)

        # 数据提取排序
        sorted_station_ids = sorted(self.delay_details.keys())
        all_trains = set()
        for s_id in sorted_station_ids:
            all_trains.update(self.delay_details[s_id].keys())
        sorted_trains = sorted(list(all_trains))

        # 2. 详细数据表格
        self.table = QTableWidget()
        self.table.setRowCount(len(sorted_station_ids))
        self.table.setColumnCount(len(sorted_trains) + 1)

        headers = sorted_trains + ["各站总计"]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setVerticalHeaderLabels([self.station_map.get(sid, str(sid)) for sid in sorted_station_ids])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        station_totals = []

        for row, s_id in enumerate(sorted_station_ids):
            row_total = 0.0
            for col, train_num in enumerate(sorted_trains):
                val = self.delay_details[s_id].get(train_num, 0.0)
                row_total += val
                item = QTableWidgetItem(f"{val:.2f}")
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

            station_totals.append(row_total)
            total_item = QTableWidgetItem(f"{row_total:.2f}")
            total_item.setTextAlignment(Qt.AlignCenter)
            total_item.setBackground(Qt.yellow)
            self.table.setItem(row, len(sorted_trains), total_item)

        layout.addWidget(self.table)

        # 3. 折线图 (完美修复版)
        matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        matplotlib.rcParams['axes.unicode_minus'] = False

        self.figure = Figure(figsize=(8, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        ax = self.figure.add_subplot(111)
        station_names = [self.station_map.get(sid, str(sid)) for sid in sorted_station_ids]

        # 使用安全的数字范围作为 X 轴
        x_positions = range(len(station_names))
        line_color = 'red' if 'GSA' in self.algo_name else 'blue'

        ax.plot(x_positions, station_totals, marker='o', color=line_color, linestyle='-', linewidth=2)

        # 强制设置 X 轴刻度标签为中文车站名
        ax.set_xticks(list(x_positions))
        ax.set_xticklabels(station_names)

        ax.set_title("各站总加权到达晚点时间消解曲线")
        ax.set_ylabel("加权晚点(分)")
        ax.grid(True, linestyle='--', alpha=0.6)

        # 4. 底部按钮
        btn_layout = QHBoxLayout()
        btn_apply = QPushButton("应用此调整方案")
        btn_apply.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; height: 30px;")
        btn_apply.clicked.connect(self.accept)

        btn_cancel = QPushButton("放弃并尝试其他算法")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)