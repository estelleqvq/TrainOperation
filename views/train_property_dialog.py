# views/train_property_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
                             QPushButton, QHeaderView, QGridLayout, QGroupBox, QMessageBox, QCheckBox, QWidget,
                             QSpinBox)
from PyQt5.QtCore import Qt, QTime


class TrainPropertyDialog(QDialog):
    def __init__(self, parent, stations, section_times, train_line=None):
        super().__init__(parent)
        self.stations = stations
        self.section_times = section_times
        self.train_line = train_line
        self.init_ui()
        self.populate_data()

    def _format_track_name(self, tk, direction="DOWN"):
        if not tk: return "Ⅰ" if direction == "DOWN" else "Ⅱ"
        tk = tk.strip()
        if tk == "正线": return "Ⅰ" if direction == "DOWN" else "Ⅱ"
        if tk in ["1", "1股", "正线1"]: return "Ⅰ"
        if tk in ["2", "2股", "正线2"]: return "Ⅱ"
        if tk.endswith("股"): return tk[:-1]
        return tk

    def init_ui(self):
        self.setWindowTitle("列车属性与时刻表")
        self.resize(850, 650)
        layout = QVBoxLayout(self)

        group_basic = QGroupBox("列车基本属性")
        group_basic.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 1ex; } "
                                  "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        basic_layout = QGridLayout()

        basic_layout.addWidget(QLabel("车次号:"), 0, 0)
        self.le_train_number = QLineEdit()
        basic_layout.addWidget(self.le_train_number, 0, 1)

        basic_layout.addWidget(QLabel("方向:"), 0, 2)
        self.cb_direction = QComboBox()
        self.cb_direction.addItems(["DOWN", "UP"])
        self.cb_direction.currentIndexChanged.connect(self.on_direction_changed)
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
        basic_layout.addWidget(self.le_start_time, 1, 3)

        basic_layout.addWidget(QLabel("终到站:"), 2, 0)
        self.cb_end_station = QComboBox()
        self.cb_end_station.addItems([s.name for s in self.stations])
        basic_layout.addWidget(self.cb_end_station, 2, 1)

        basic_layout.addWidget(QLabel("终到时间:"), 2, 2)
        self.le_end_time = QLineEdit()
        basic_layout.addWidget(self.le_end_time, 2, 3)

        self.btn_sync_time = QPushButton("智能排线")
        self.btn_sync_time.setStyleSheet("background-color: #e3f2fd; font-weight: bold; color: #0d47a1;")
        self.btn_sync_time.clicked.connect(self.sync_top_to_table)
        basic_layout.addWidget(self.btn_sync_time, 1, 4, 2, 2)

        group_basic.setLayout(basic_layout)
        layout.addWidget(group_basic)

        group_schedule = QGroupBox("列车时刻表")
        group_schedule.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 1ex; } "
                                     "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        schedule_layout = QVBoxLayout()

        self.table = QTableWidget(len(self.stations), 6)
        self.table.setHorizontalHeaderLabels(
            ["车站名称", "办理客运", "停站时长", "接发股道", "计划到达", "计划出发"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
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

    def on_direction_changed(self):
        """当改变方向时，表格里的默认发车股道自动跟着刷新"""
        direction = self.cb_direction.currentText()
        for i in range(self.table.rowCount()):
            cb_track = self.table.cellWidget(i, 3)
            if cb_track:
                # 如果当前是旧的默认正线，自动随方向切换
                curr = cb_track.currentText()
                if curr in ["Ⅰ", "Ⅱ"]:
                    cb_track.setCurrentText("Ⅰ" if direction == "DOWN" else "Ⅱ")

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

        current_direction = self.cb_direction.currentText()

        for i, station in enumerate(self.stations):
            item_name = QTableWidgetItem(station.name)
            item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, item_name)
            self.table.item(i, 0).setData(Qt.UserRole, station.id)

            p = points_dict.get(station.id)

            raw_track = getattr(p, 'track', None)
            track = self._format_track_name(raw_track, current_direction)

            plan_arr = p.planned_arrival.toString("HH:mm") if p and p.planned_arrival else ""
            plan_dep = p.planned_departure.toString("HH:mm") if p and p.planned_departure else ""

            is_stop = False
            duration = 2
            if plan_arr and plan_dep and plan_arr != plan_dep:
                is_stop = True
                duration = p.planned_arrival.secsTo(p.planned_departure) // 60
                if duration <= 0: duration = 2

            if i == 0 or i == len(self.stations) - 1:
                is_stop = True

            cb_stop = QCheckBox()
            cb_stop.setChecked(is_stop)
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.addWidget(cb_stop)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(i, 1, chk_widget)

            sb_duration = QSpinBox()
            sb_duration.setRange(1, 60)
            sb_duration.setValue(duration)
            self.table.setCellWidget(i, 2, sb_duration)

            cb_track = QComboBox()
            # 从车站配置中获取规范的股道列表（已剔除"正线"）
            tracks_list = list(station.tracks) if station.tracks else ["Ⅰ", "Ⅱ", "3", "4", "5"]
            cb_track.addItems(tracks_list)

            if track not in tracks_list:
                cb_track.addItem(track)
            cb_track.setCurrentText(track)
            self.table.setCellWidget(i, 3, cb_track)

            self.table.setItem(i, 4, QTableWidgetItem(plan_arr))
            self.table.setItem(i, 5, QTableWidgetItem(plan_dep))

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
        start_name = self.cb_start_station.currentText()
        end_name = self.cb_end_station.currentText()
        start_time_str = self.le_start_time.text().strip()

        if not start_time_str:
            QMessageBox.warning(self, "逻辑错误", "请输入始发时间")
            return

        current_time = QTime.fromString(start_time_str, "HH:mm")
        if not current_time.isValid():
            QMessageBox.warning(self, "格式错误", "时间格式有误")
            return

        start_idx = -1
        end_idx = -1
        for i, s in enumerate(self.stations):
            if s.name == start_name: start_idx = i
            if s.name == end_name: end_idx = i

        if start_idx == -1 or end_idx == -1 or start_idx == end_idx:
            QMessageBox.warning(self, "逻辑错误", "始发站和终到站配置有误")
            return

        for i in range(self.table.rowCount()):
            self.table.setItem(i, 4, QTableWidgetItem(""))
            self.table.setItem(i, 5, QTableWidgetItem(""))

        step = 1 if start_idx < end_idx else -1
        self.cb_direction.setCurrentText("DOWN" if step == 1 else "UP")
        self.on_direction_changed()  # 更新默认股道

        self.table.setItem(start_idx, 5, QTableWidgetItem(current_time.toString("HH:mm")))

        for i in range(start_idx, end_idx, step):
            from_station = self.stations[i]
            to_station = self.stations[i + step]

            mins = self.section_times.get((from_station.id, to_station.id))
            if mins is None:
                mins = self.section_times.get((to_station.id, from_station.id))
            if mins is None:
                mins = 10

            current_time = current_time.addSecs(mins * 60)
            next_idx = i + step
            arr_str = current_time.toString("HH:mm")

            if next_idx == end_idx:
                self.table.setItem(next_idx, 4, QTableWidgetItem(arr_str))
                self.le_end_time.setText(arr_str)
            else:
                self.table.setItem(next_idx, 4, QTableWidgetItem(arr_str))

                chk_widget = self.table.cellWidget(next_idx, 1)
                cb_stop = chk_widget.layout().itemAt(0).widget()
                if cb_stop.isChecked():
                    sb_duration = self.table.cellWidget(next_idx, 2)
                    stop_mins = sb_duration.value()
                    current_time = current_time.addSecs(stop_mins * 60)
                    dep_str = current_time.toString("HH:mm")
                    self.table.setItem(next_idx, 5, QTableWidgetItem(dep_str))
                else:
                    self.table.setItem(next_idx, 5, QTableWidgetItem(arr_str))

    def _bold_font(self):
        font = self.font()
        font.setBold(True)
        return font

    def get_data(self):
        stops_data = []
        direction = self.cb_direction.currentText()

        for i in range(self.table.rowCount()):
            station_id = self.table.item(i, 0).data(Qt.UserRole)

            cb_track = self.table.cellWidget(i, 3)
            track_str = cb_track.currentText() if cb_track else ("Ⅰ" if direction == "DOWN" else "Ⅱ")

            plan_arr = self.table.item(i, 4).text().strip()
            plan_dep = self.table.item(i, 5).text().strip()

            if not plan_arr and not plan_dep:
                continue

            stops_data.append({
                "station_id": station_id,
                "track": track_str,
                "planned_arrival": plan_arr,
                "planned_departure": plan_dep
            })

        return {
            "train_number": self.le_train_number.text(),
            "direction": direction,
            "date": self.le_date.text(),
            "stops": stops_data
        }