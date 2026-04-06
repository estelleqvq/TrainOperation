# views/report_record_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt


class ReportRecordDialog(QDialog):
    def __init__(self, parent, plan_lines, actual_lines, stations):
        super().__init__(parent)
        self.plan_lines = plan_lines
        self.actual_lines = actual_lines
        self.station_map = {s.id: s.name for s in stations}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("列车报点记录查询")
        self.resize(750, 500)
        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["车次号", "车站名称", "计划到达", "计划出发", "实际到达", "实际出发"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # 将表格设为只读
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        self.populate_data()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton("关闭")
        btn_ok.setMinimumWidth(100)
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    def populate_data(self):
        row = 0
        # 遍历所有存在实际点的列车线
        for act_line in self.actual_lines:
            # 找到对应的图定计划线以对照时间
            plan_line = next((p for p in self.plan_lines if p.train_number == act_line.train_number), None)

            for act_pt in act_line.points:
                if act_pt.actual_arrival or act_pt.actual_departure:
                    self.table.insertRow(row)

                    item_num = QTableWidgetItem(act_line.train_number)
                    item_num.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 0, item_num)

                    st_name = self.station_map.get(act_pt.station_id, str(act_pt.station_id))
                    item_st = QTableWidgetItem(st_name)
                    item_st.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 1, item_st)

                    plan_arr_str = "--:--"
                    plan_dep_str = "--:--"
                    if plan_line:
                        plan_pt = next((p for p in plan_line.points if p.station_id == act_pt.station_id), None)
                        if plan_pt:
                            plan_arr_str = plan_pt.planned_arrival.toString(
                                "HH:mm") if plan_pt.planned_arrival else "--:--"
                            plan_dep_str = plan_pt.planned_departure.toString(
                                "HH:mm") if plan_pt.planned_departure else "--:--"

                    item_parr = QTableWidgetItem(plan_arr_str)
                    item_parr.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 2, item_parr)

                    item_pdep = QTableWidgetItem(plan_dep_str)
                    item_pdep.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 3, item_pdep)

                    act_arr_str = act_pt.actual_arrival.toString("HH:mm") if act_pt.actual_arrival else "--:--"
                    act_dep_str = act_pt.actual_departure.toString("HH:mm") if act_pt.actual_departure else "--:--"

                    item_arr = QTableWidgetItem(act_arr_str)
                    item_arr.setForeground(Qt.red)
                    item_arr.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 4, item_arr)

                    item_dep = QTableWidgetItem(act_dep_str)
                    item_dep.setForeground(Qt.red)
                    item_dep.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 5, item_dep)

                    row += 1