# views/delay_simulation_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QSpinBox, QPushButton, QHBoxLayout


class DelaySimulationDialog(QDialog):
    def __init__(self, parent, plan_lines, stations, current_sim_time=None):
        super().__init__(parent)
        self.plan_lines = plan_lines
        self.stations = stations
        self.station_map = {s.id: s for s in stations}
        self.current_sim_time = current_sim_time
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("模拟突发晚点与智能调整")
        self.resize(360, 240)
        layout = QVBoxLayout(self)

        form = QFormLayout()

        # 1. 选择列车
        self.cb_train = QComboBox()
        for line in self.plan_lines:
            self.cb_train.addItem(line.train_number, line.train_number)
        self.cb_train.currentIndexChanged.connect(self.on_train_changed)
        form.addRow("选择晚点列车:", self.cb_train)

        # 2. 选择车站
        self.cb_station = QComboBox()
        form.addRow("发生晚点的车站:", self.cb_station)

        # 3. 输入晚点时长
        self.sb_delay = QSpinBox()
        self.sb_delay.setRange(1, 300)
        self.sb_delay.setValue(30)
        self.sb_delay.setSuffix(" 分钟")
        form.addRow("输入晚点时长:", self.sb_delay)

        # 4. 新增：选择调度算法
        self.cb_algo = QComboBox()
        self.cb_algo.addItem("单一遗传算法 (GA)", "GA")
        self.cb_algo.addItem("遗传模拟退火算法 (GSA)", "GSA")
        # 默认选中 GSA，因为它是你的毕设核心
        self.cb_algo.setCurrentIndex(1)
        form.addRow("选择调整算法:", self.cb_algo)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("开始智能调整")
        self.btn_ok.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold;")
        self.btn_ok.clicked.connect(self.accept)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.on_train_changed()

    def on_train_changed(self):
        self.cb_station.clear()
        train_num = self.cb_train.currentData()
        train = next((t for t in self.plan_lines if t.train_number == train_num), None)
        if train:
            for i in range(len(train.points) - 1):
                p = train.points[i]
                # 过滤掉已经过去的车站 (如果有当前模拟时间的话)
                if self.current_sim_time:
                    dep_time = p.planned_departure or p.planned_arrival
                    if dep_time and dep_time < self.current_sim_time:
                        continue

                st = self.station_map.get(p.station_id)
                if st:
                    self.cb_station.addItem(st.name, p.station_id)

    def get_data(self):
        """返回对话框收集的所有数据"""
        return {
            'train_num': self.cb_train.currentData(),
            'station_id': self.cb_station.currentData(),
            'delay_mins': self.sb_delay.value(),
            'algo_type': self.cb_algo.currentData()  # 新增：算法类型
        }