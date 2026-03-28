# views/plan_line_param_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QPushButton, QHBoxLayout, QGroupBox, QLabel, QComboBox)
from PyQt5.QtCore import QTime


class PlanLineParamDialog(QDialog):
    def __init__(self, parent, train_line, stations, initial_station_id=None):
        super().__init__(parent)
        self.train_line = train_line
        self.stations = stations
        self.initial_station_id = initial_station_id

        self.station_map = {s.id: s for s in self.stations}
        self.init_ui()
        self.load_initial_data()

    def init_ui(self):
        self.setWindowTitle("修改计划线参数")
        self.resize(360, 280)  # 移除了股道区，高度收紧
        layout = QVBoxLayout(self)
        layout.setSpacing(15)  # 增加模块间距
        layout.setContentsMargins(20, 20, 20, 20)  # 增加内边距使四周留白更美观

        # ================= 1. 图定信息区 =================
        group_info = QGroupBox("1. 图定信息")
        group_info.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 1ex; } "
                                 "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        form_info = QFormLayout()
        form_info.setSpacing(10)

        self.lbl_train_num = QLabel(self.train_line.train_number)
        self.lbl_train_num.setStyleSheet("font-weight: bold; color: #b71c1c; font-size: 14px;")
        form_info.addRow("车次号:", self.lbl_train_num)

        self.cb_station = QComboBox()
        self.cb_station.setStyleSheet("padding: 3px;")
        for p in self.train_line.points:
            st = self.station_map.get(p.station_id)
            if st:
                self.cb_station.addItem(st.name, p.station_id)
        self.cb_station.currentIndexChanged.connect(self.on_station_changed)
        form_info.addRow("当前调整车站:", self.cb_station)

        self.lbl_plan_arr = QLabel("--:--")
        self.lbl_plan_arr.setStyleSheet("color: #555;")
        form_info.addRow("原计划到达时间:", self.lbl_plan_arr)

        self.lbl_plan_dep = QLabel("--:--")
        self.lbl_plan_dep.setStyleSheet("color: #555;")
        form_info.addRow("原计划出发时间:", self.lbl_plan_dep)

        group_info.setLayout(form_info)
        layout.addWidget(group_info)

        # ================= 2. 输入参数区 =================
        group_input = QGroupBox("2. 输入参数 (目标调整)")
        group_input.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 1ex; } "
                                  "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        form_input = QFormLayout()
        form_input.setSpacing(10)

        self.le_target_arr = QLineEdit()
        self.le_target_arr.setPlaceholderText("HH:mm")
        self.le_target_arr.setStyleSheet("padding: 3px;")
        form_input.addRow("目标到达时间:", self.le_target_arr)

        self.le_target_dep = QLineEdit()
        self.le_target_dep.setPlaceholderText("HH:mm")
        self.le_target_dep.setStyleSheet("padding: 3px;")
        form_input.addRow("目标出发时间:", self.le_target_dep)

        group_input.setLayout(form_input)
        layout.addWidget(group_input)

        # ================= 底部按钮 =================
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("确定修改")
        self.btn_save.setMinimumHeight(30)
        self.btn_save.clicked.connect(self.accept)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setMinimumHeight(30)
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

        point = next((p for p in self.train_line.points if p.station_id == station_id), None)
        st = self.station_map.get(station_id)
        if not point or not st: return

        arr_str = point.planned_arrival.toString("HH:mm") if point.planned_arrival else ""
        dep_str = point.planned_departure.toString("HH:mm") if point.planned_departure else ""

        self.lbl_plan_arr.setText(arr_str if arr_str else "—")
        self.lbl_plan_dep.setText(dep_str if dep_str else "—")

        self.le_target_arr.setText(arr_str)
        self.le_target_dep.setText(dep_str)

    def get_data(self):
        return {
            "station_id": self.cb_station.currentData(),
            "target_arrival": self.le_target_arr.text().strip(),
            "target_departure": self.le_target_dep.text().strip()
            # 移除了 track 字段
        }