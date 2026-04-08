# views/delay_simulation_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QSpinBox, QPushButton, QHBoxLayout


class DelaySimulationDialog(QDialog):
    def __init__(self, parent, plan_lines, stations, current_time):
        super().__init__(parent)
        self.plan_lines = plan_lines
        self.stations = stations
        self.current_time = current_time
        self.station_map = {s.id: s for s in stations}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("模拟突发晚点")
        self.resize(320, 200)
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.cb_train = QComboBox()
        for line in self.plan_lines:
            self.cb_train.addItem(line.train_number, line.train_number)
        self.cb_train.currentIndexChanged.connect(self.on_train_changed)
        form.addRow("选择晚点列车:", self.cb_train)

        self.cb_station = QComboBox()
        form.addRow("发生晚点的车站:", self.cb_station)

        self.sb_delay = QSpinBox()
        self.sb_delay.setRange(1, 300)
        self.sb_delay.setValue(30)
        self.sb_delay.setSuffix("")
        form.addRow("输入晚点时长(分):", self.sb_delay)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("触发智能调整")
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

        c_mins = self.current_time.hour() * 60 + self.current_time.minute()
        if c_mins < 1080: c_mins += 1440

        if train:
            for i in range(len(train.points) - 1):
                p = train.points[i]
                node_time = p.planned_arrival or p.planned_departure
                if not node_time: continue

                n_mins = node_time.hour() * 60 + node_time.minute()
                if n_mins < 1080: n_mins += 1440

                # 只有计划到达时间大于当前模拟时间的车站才可以引发晚点调整
                if n_mins >= c_mins:
                    st = self.station_map.get(p.station_id)
                    if st:
                        self.cb_station.addItem(st.name, p.station_id)

    def get_data(self):
        return {
            'train_num': self.cb_train.currentData(),
            'station_id': self.cb_station.currentData(),
            'delay_mins': self.sb_delay.value()
        }