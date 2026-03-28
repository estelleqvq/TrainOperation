# views/station_time_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QPushButton, QHBoxLayout, QGroupBox, QLabel)
from PyQt5.QtCore import QTime


class StationTimeDialog(QDialog):
    def __init__(self, parent, train_line, station_name, point):
        super().__init__(parent)
        self.train_line = train_line
        self.station_name = station_name
        self.point = point
        self.init_ui()
        self.load_data()

    def init_ui(self):
        self.setWindowTitle("微调单站时刻")
        self.resize(320, 240)
        layout = QVBoxLayout(self)

        group = QGroupBox(f"车次: {self.train_line.train_number}  |  车站: {self.station_name}")
        group.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 1ex; } "
                            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        form = QFormLayout()

        self.le_plan_arr = QLineEdit()
        self.le_plan_arr.setPlaceholderText("HH:mm")
        form.addRow("计划到达时间:", self.le_plan_arr)

        self.le_plan_dep = QLineEdit()
        self.le_plan_dep.setPlaceholderText("HH:mm")
        form.addRow("计划出发时间:", self.le_plan_dep)

        self.lbl_act_arr = QLabel("—")
        self.lbl_act_arr.setStyleSheet("color: blue; font-weight: bold;")
        form.addRow("实际到达时间 (实迹):", self.lbl_act_arr)

        self.lbl_act_dep = QLabel("—")
        self.lbl_act_dep.setStyleSheet("color: blue; font-weight: bold;")
        form.addRow("实际出发时间 (实迹):", self.lbl_act_dep)

        group.setLayout(form)
        layout.addWidget(group)

        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("确定")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def load_data(self):
        p = self.point
        if p.planned_arrival:
            self.le_plan_arr.setText(p.planned_arrival.toString("HH:mm"))
        if p.planned_departure:
            self.le_plan_dep.setText(p.planned_departure.toString("HH:mm"))

        act_arr = getattr(p, 'actual_arrival', None)
        if act_arr:
            self.lbl_act_arr.setText(act_arr.toString("HH:mm"))

        act_dep = getattr(p, 'actual_departure', None)
        if act_dep:
            self.lbl_act_dep.setText(act_dep.toString("HH:mm"))

    def get_data(self):
        arr_str = self.le_plan_arr.text().strip()
        dep_str = self.le_plan_dep.text().strip()
        return {
            "planned_arrival": arr_str if arr_str else None,
            "planned_departure": dep_str if dep_str else None
        }