# views/train_property_dialog.py

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
                             QPushButton, QHeaderView, QGridLayout, QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt, QTime


class TrainPropertyDialog(QDialog):
    # 【核心修改】接收 section_times 字典
    def __init__(self, parent, stations, section_times, train_line=None):
        super().__init__(parent)
        self.stations = stations
        self.section_times = section_times
        self.train_line = train_line
        self.init_ui()
        self.populate_data()

    def init_ui(self):
        self.setWindowTitle("列车属性与时刻表 (CTC 自动排线版)")
        self.resize(850, 650)
        layout = QVBoxLayout(self)

        group_basic = QGroupBox("列车基本属性")
        group_basic.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 1ex; } "
                                  "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        basic_layout = QGridLayout()

        basic_layout.addWidget(QLabel("车次号:"), 0, 0)
        self.le_train_number = QLineEdit()
        self.le_train_number.setPlaceholderText("如: G143")
        basic_layout.addWidget(self.le_train_number, 0, 1)

        basic_layout.addWidget(QLabel("方向:"), 0, 2)
        self.cb_direction = QComboBox()
        self.cb_direction.addItems(["DOWN", "UP"])
        basic_layout.addWidget(self.cb_direction, 0, 3)

        basic_layout.addWidget(QLabel("开行日期:"), 0, 4)
        self.le_date = QLineEdit("2026-03-01")
        basic_layout.addWidget(self.le_date, 0, 5)

        basic_layout.addWidget(QLabel("始发站:"), 1, 0)
        self.cb_start_station = QComboBox()
        self.cb_start_station.addItems([s.name for s in self.stations])
        basic_layout.addWidget(self.cb_start_station, 1, 1)

        basic_layout.addWidget(QLabel("始发时间:"), 1, 2)
        self.le_start_time = QLineEdit()
        self.le_start_time.setPlaceholderText("HH:mm (出发)")
        basic_layout.addWidget(self.le_start_time, 1, 3)

        basic_layout.addWidget(QLabel("终到站:"), 2, 0)
        self.cb_end_station = QComboBox()
        self.cb_end_station.addItems([s.name for s in self.stations])
        basic_layout.addWidget(self.cb_end_station, 2, 1)

        basic_layout.addWidget(QLabel("终到时间:"), 2, 2)
        self.le_end_time = QLineEdit()
        self.le_end_time.setPlaceholderText("自动计算或手填")
        basic_layout.addWidget(self.le_end_time, 2, 3)

        # 智能排线按钮
        self.btn_sync_time = QPushButton("智能排线")
        self.btn_sync_time.setStyleSheet("background-color: #e3f2fd; font-weight: bold; color: #0d47a1;")
        self.btn_sync_time.setToolTip("根据始发时间和区间标准运行时分，自动推算沿途所有车站的通过时间")
        self.btn_sync_time.clicked.connect(self.sync_top_to_table)
        basic_layout.addWidget(self.btn_sync_time, 1, 4, 2, 2)

        group_basic.setLayout(basic_layout)
        layout.addWidget(group_basic)

        group_schedule = QGroupBox("列车时刻表详细信息")
        group_schedule.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 1ex; } "
                                     "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        schedule_layout = QVBoxLayout()

        self.table = QTableWidget(len(self.stations), 6)
        self.table.setHorizontalHeaderLabels(
            ["车站名称", "接发股道", "计划到达", "计划出发", "实际到达", "实际出发"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        schedule_layout.addWidget(self.table)

        group_schedule.setLayout(schedule_layout)
        layout.addWidget(group_schedule)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_save = QPushButton("确定并保存")
        self.btn_save.setMinimumWidth(120)
        self.btn_save.clicked.connect(self.accept)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def populate_data(self):
        points_dict = {}
        first_valid_point = None
        last_valid_point = None

        if self.train_line:
            self.le_train_number.setText(self.train_line.train_number)
            self.cb_direction.setCurrentText(self.train_line.direction)
            self.le_date.setText(self.train_line.date)

            for p in self.train_line.points:
                points_dict[p.station_id] = p
                if p.planned_arrival or p.planned_departure:
                    if not first_valid_point:
                        first_valid_point = p
                    last_valid_point = p

        for i, station in enumerate(self.stations):
            item_name = QTableWidgetItem(station.name)
            item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, item_name)
            self.table.item(i, 0).setData(Qt.UserRole, station.id)

            p = points_dict.get(station.id)
            track = getattr(p, 'track', '正线') if p else '正线'
            plan_arr = p.planned_arrival.toString("HH:mm") if p and p.planned_arrival else ""
            plan_dep = p.planned_departure.toString("HH:mm") if p and p.planned_departure else ""

            act_arr_obj = getattr(p, 'actual_arrival', None) if p else None
            act_dep_obj = getattr(p, 'actual_departure', None) if p else None
            act_arr = act_arr_obj.toString("HH:mm") if act_arr_obj else ""
            act_dep = act_dep_obj.toString("HH:mm") if act_dep_obj else ""

            cb_track = QComboBox()
            cb_track.addItems(station.tracks)
            cb_track.setCurrentText(track)
            self.table.setCellWidget(i, 1, cb_track)

            self.table.setItem(i, 2, QTableWidgetItem(plan_arr))
            self.table.setItem(i, 3, QTableWidgetItem(plan_dep))

            item_act_arr = QTableWidgetItem(act_arr)
            item_act_arr.setForeground(Qt.blue)
            item_act_arr.setFont(self._bold_font())
            self.table.setItem(i, 4, item_act_arr)

            item_act_dep = QTableWidgetItem(act_dep)
            item_act_dep.setForeground(Qt.blue)
            item_act_dep.setFont(self._bold_font())
            self.table.setItem(i, 5, item_act_dep)

        if first_valid_point:
            start_st = next((s for s in self.stations if s.id == first_valid_point.station_id), None)
            if start_st: self.cb_start_station.setCurrentText(start_st.name)
            if first_valid_point.planned_departure:
                self.le_start_time.setText(first_valid_point.planned_departure.toString("HH:mm"))

        if last_valid_point:
            end_st = next((s for s in self.stations if s.id == last_valid_point.station_id), None)
            if end_st: self.cb_end_station.setCurrentText(end_st.name)
            if last_valid_point.planned_arrival:
                self.le_end_time.setText(last_valid_point.planned_arrival.toString("HH:mm"))

    def sync_top_to_table(self):
        """【核心功能】：基于区间运行时分，自动排线推演全线时刻"""
        start_name = self.cb_start_station.currentText()
        end_name = self.cb_end_station.currentText()
        start_time_str = self.le_start_time.text().strip()

        if not start_time_str:
            QMessageBox.warning(self, "操作错误", "请先输入始发时间！")
            return

        current_time = QTime.fromString(start_time_str, "HH:mm")
        if not current_time.isValid():
            QMessageBox.warning(self, "格式错误", "时间格式有误，请输入标准的 HH:mm 格式，例如 08:30")
            return

        # 1. 寻找始发站和终到站在表格中的行号
        start_idx = -1
        end_idx = -1
        for i, s in enumerate(self.stations):
            if s.name == start_name: start_idx = i
            if s.name == end_name: end_idx = i

        if start_idx == -1 or end_idx == -1 or start_idx == end_idx:
            QMessageBox.warning(self, "逻辑错误", "始发站和终到站不能相同！")
            return

        # 2. 清空旧的计划时间
        for i in range(self.table.rowCount()):
            self.table.setItem(i, 2, QTableWidgetItem(""))
            self.table.setItem(i, 3, QTableWidgetItem(""))

        # 3. 确定方向：从上往下是下行(DOWN)，从下往上是上行(UP)
        step = 1 if start_idx < end_idx else -1
        self.cb_direction.setCurrentText("DOWN" if step == 1 else "UP")

        # 4. 填入始发站出发时间
        self.table.setItem(start_idx, 3, QTableWidgetItem(current_time.toString("HH:mm")))

        # 5. 遍历区间，累加标准运行时分并填入中间站
        for i in range(start_idx, end_idx, step):
            from_station = self.stations[i]
            to_station = self.stations[i + step]

            # 在区间表中查找运行时分（兼容上下行存储顺序）
            mins = self.section_times.get((from_station.id, to_station.id))
            if mins is None:
                mins = self.section_times.get((to_station.id, from_station.id))

            if mins is None:
                mins = 10  # 万一数据库里漏了某个区间，兜底按10分钟算

            # 加上运行时分
            current_time = current_time.addSecs(mins * 60)
            next_idx = i + step
            time_str = current_time.toString("HH:mm")

            if next_idx == end_idx:
                # 如果是终到站，只填写“计划到达”，并反填到顶部面板
                self.table.setItem(next_idx, 2, QTableWidgetItem(time_str))
                self.le_end_time.setText(time_str)
            else:
                # 如果是中间站，默认为“通过”，到达和出发时间相同
                self.table.setItem(next_idx, 2, QTableWidgetItem(time_str))
                self.table.setItem(next_idx, 3, QTableWidgetItem(time_str))

    def _bold_font(self):
        font = self.font()
        font.setBold(True)
        return font

    def get_data(self):
        stops_data = []
        for i in range(self.table.rowCount()):
            station_id = self.table.item(i, 0).data(Qt.UserRole)
            cb_track = self.table.cellWidget(i, 1)
            track_str = cb_track.currentText() if cb_track else "正线"

            plan_arr = self.table.item(i, 2).text().strip()
            plan_dep = self.table.item(i, 3).text().strip()
            act_arr = self.table.item(i, 4).text().strip()
            act_dep = self.table.item(i, 5).text().strip()

            if not plan_arr and not plan_dep and not act_arr and not act_dep:
                continue

            stops_data.append({
                "station_id": station_id,
                "track": track_str,
                "planned_arrival": plan_arr,
                "planned_departure": plan_dep,
                "actual_arrival": act_arr,
                "actual_departure": act_dep
            })

        return {
            "train_number": self.le_train_number.text(),
            "direction": self.cb_direction.currentText(),
            "date": self.le_date.text(),
            "stops": stops_data
        }