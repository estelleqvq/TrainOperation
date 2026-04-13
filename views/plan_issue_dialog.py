# views/plan_issue_dialog.py
import random
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QCheckBox, QTimeEdit, QSpinBox, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
                             QWidget, QMessageBox)
from PyQt5.QtCore import QTime, QTimer, Qt


class PlanIssueDialog(QDialog):
    def __init__(self, parent, stations, plan_lines, current_sim_time=None):
        super().__init__(parent)
        self.stations = stations
        # 建立车站ID到名称的映射
        self.station_map = {s.id: s.name for s in stations}
        self.plan_lines = plan_lines
        self.current_sim_time = current_sim_time or QTime.currentTime()

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("CTC 阶段计划下发控制台 (按车次)")
        self.resize(900, 600)
        main_layout = QVBoxLayout(self)

        # ================= 1. 筛选配置区 =================
        filter_group = QGroupBox("阶段计划时间范围设定")
        filter_layout = QHBoxLayout()

        f_form = QFormLayout()
        self.te_start = QTimeEdit(self.current_sim_time)
        self.te_start.setDisplayFormat("HH:mm")
        self.te_start.timeChanged.connect(self.refresh_table_data)
        f_form.addRow("计划起始时间:", self.te_start)
        filter_layout.addLayout(f_form)

        f_form2 = QFormLayout()
        self.sb_hours = QSpinBox()
        self.sb_hours.setRange(1, 4)
        self.sb_hours.setValue(3)
        self.sb_hours.setSuffix(" 小时")
        self.sb_hours.valueChanged.connect(self.refresh_table_data)
        f_form2.addRow("阶段计划时长:", self.sb_hours)
        filter_layout.addLayout(f_form2)

        filter_layout.addStretch()

        self.btn_send = QPushButton("下达阶段计划")
        self.btn_send.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold; padding: 10px 20px;")
        self.btn_send.clicked.connect(self.on_send_selected)
        filter_layout.addWidget(self.btn_send)

        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)

        # ================= 2. 待下达车次列表区 =================
        status_group = QGroupBox("时间范围内涉及的计划线列表")
        status_layout = QVBoxLayout()

        self.table = QTableWidget()
        # 列定义：选择 | 车次 | 始发车站 | 终到车站 | 下达状态 | 下达时间
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["选择", "车次", "始发车站", "终到车站", "下达状态", "下达时间"])

        # 调整列宽行为
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setAlternatingRowColors(True)

        status_layout.addWidget(self.table)
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        # 初始化时自动填充数据
        self.refresh_table_data()

    def _qtime_to_mins(self, qt):
        return qt.hour() * 60 + qt.minute() if qt else -1

    def refresh_table_data(self):
        """筛选有交集的计划线，并展示在表格中"""
        self.table.setRowCount(0)

        start_qt = self.te_start.time()
        hours = self.sb_hours.value()

        start_mins = self._qtime_to_mins(start_qt)
        end_mins = start_mins + hours * 60

        row = 0
        for t in self.plan_lines:
            if not t.points:
                continue

            # 提取车次的起止时间范围
            t_mins = []
            for p in t.points:
                if p.planned_arrival:
                    t_mins.append(self._qtime_to_mins(p.planned_arrival))
                if p.planned_departure:
                    t_mins.append(self._qtime_to_mins(p.planned_departure))

            if not t_mins: continue

            t_start = min(t_mins)
            t_end = max(t_mins)

            # 判定计划线运行时间与窗口是否有交集
            if t_start <= end_mins and t_end >= start_mins:
                self.table.insertRow(row)

                # 0. 选择勾选框
                cb_container = QWidget()
                cb_layout = QHBoxLayout(cb_container)
                cb = QCheckBox()
                cb_layout.addWidget(cb)
                cb_layout.setAlignment(Qt.AlignCenter)
                cb_layout.setContentsMargins(0, 0, 0, 0)
                self.table.setCellWidget(row, 0, cb_container)

                # 1. 车次
                item_num = QTableWidgetItem(t.train_number)
                item_num.setTextAlignment(Qt.AlignCenter)
                if t.train_number.startswith(('G', 'D')):
                    font = item_num.font()
                    font.setBold(True)
                    item_num.setFont(font)
                self.table.setItem(row, 1, item_num)

                # 2. 始发车站
                start_st_name = self.station_map.get(t.points[0].station_id, "未知")
                item_start = QTableWidgetItem(start_st_name)
                item_start.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 2, item_start)

                # 3. 终到车站
                end_st_name = self.station_map.get(t.points[-1].station_id, "未知")
                item_end = QTableWidgetItem(end_st_name)
                item_end.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 3, item_end)

                # 4. 下达状态
                item_status = QTableWidgetItem("未下达")
                item_status.setTextAlignment(Qt.AlignCenter)
                item_status.setForeground(Qt.gray)
                self.table.setItem(row, 4, item_status)

                # 5. 下达时间
                item_issue_time = QTableWidgetItem("--:--:--")
                item_issue_time.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 5, item_issue_time)

                row += 1

    def on_send_selected(self):
        """组包下发勾选的车次计划线"""
        issued_count = 0
        now_time_str = QTime.currentTime().toString("HH:mm:ss")

        for i in range(self.table.rowCount()):
            cb_widget = self.table.cellWidget(i, 0)
            cb = cb_widget.findChild(QCheckBox)

            if cb and cb.isChecked():
                # 状态列索引为 4
                status_item = self.table.item(i, 4)
                if status_item.text() in ["未下达", "下发失败"]:
                    issued_count += 1
                    status_item.setText("组包下发中...")
                    status_item.setForeground(Qt.blue)

                    # 下达时间列索引为 5
                    self.table.item(i, 5).setText(now_time_str)

                    # 模拟计划线组包推送的网络延迟
                    delay_ms = random.randint(800, 2500)
                    QTimer.singleShot(delay_ms, lambda r=i: self.process_receive_feedback(r))

                    cb.setChecked(False)
                    cb.setEnabled(False)

        if issued_count == 0:
            QMessageBox.information(self, "提示", "请勾选至少一条需要下达的列车计划线。")

    def process_receive_feedback(self, row_index):
        """反馈接收结果"""
        if row_index < self.table.rowCount():
            status_item = self.table.item(row_index, 4)
            if random.random() > 0.1:
                status_item.setText("下发成功")
                status_item.setForeground(Qt.darkGreen)
            else:
                status_item.setText("下发失败")
                status_item.setForeground(Qt.red)
                cb_widget = self.table.cellWidget(row_index, 0)
                cb = cb_widget.findChild(QCheckBox)
                if cb: cb.setEnabled(True)