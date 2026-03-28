# views/manual_report_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QPushButton, QHBoxLayout, QGroupBox, QLabel, QComboBox)
from PyQt5.QtCore import QTime


class ManualReportDialog(QDialog):
    def __init__(self, parent, train_line, stations, actual_train=None, initial_station_id=None):
        super().__init__(parent)
        self.train_line = train_line
        self.stations = stations
        self.actual_train = actual_train
        self.initial_station_id = initial_station_id
        self.station_map = {s.id: s for s in self.stations}
        self.init_ui()
        self.load_initial_data()

    def init_ui(self):
        self.setWindowTitle("人工报点 (记入实际运行图)")
        self.resize(320, 220)
        layout = QVBoxLayout(self)

        group = QGroupBox(f"当前操作车次: {self.train_line.train_number}")
        group.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 1ex; color: #0000FF;} "
                            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        form = QFormLayout()
        form.setSpacing(15)

        # 增加：报点车站下拉框
        self.cb_station = QComboBox()
        for p in self.train_line.points:
            st = self.station_map.get(p.station_id)
            if st:
                self.cb_station.addItem(st.name, p.station_id)
        self.cb_station.currentIndexChanged.connect(self.on_station_changed)
        form.addRow("报点车站:", self.cb_station)

        self.le_act_arr = QLineEdit()
        self.le_act_arr.setPlaceholderText("HH:mm")
        form.addRow("实际到达时间:", self.le_act_arr)

        self.le_act_dep = QLineEdit()
        self.le_act_dep.setPlaceholderText("HH:mm")
        form.addRow("实际出发时间:", self.le_act_dep)

        group.setLayout(form)
        layout.addWidget(group)

        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("确认报点")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def load_initial_data(self):
        if self.initial_station_id:
            idx = self.cb_station.findData(self.initial_station_id)
            if idx >= 0:
                self.cb_station.setCurrentIndex(idx)
        self.on_station_changed()

    def on_station_changed(self):
        station_id = self.cb_station.currentData()
        if not station_id: return

        # 尝试读取该站已有的实迹数据进行回显
        act_arr_str = ""
        act_dep_str = ""
        if self.actual_train:
            act_point = next((p for p in self.actual_train.points if p.station_id == station_id), None)
            if act_point:
                act_arr_str = act_point.actual_arrival.toString("HH:mm") if act_point.actual_arrival else ""
                act_dep_str = act_point.actual_departure.toString("HH:mm") if act_point.actual_departure else ""

        self.le_act_arr.setText(act_arr_str)
        self.le_act_dep.setText(act_dep_str)

    def get_data(self):
        arr_str = self.le_act_arr.text().strip()
        dep_str = self.le_act_dep.text().strip()
        arr_time = QTime.fromString(arr_str, "HH:mm") if arr_str else None
        dep_time = QTime.fromString(dep_str, "HH:mm") if dep_str else None

        station_id = self.cb_station.currentData()
        # 顺便查出该站的接发车股道以供保存
        point = next((p for p in self.train_line.points if p.station_id == station_id), None)
        track = point.track if point else "正线"

        return station_id, track, arr_time, dep_time