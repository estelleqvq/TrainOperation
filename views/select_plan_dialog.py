# views/select_plan_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, QHeaderView
from PyQt5.QtCore import Qt

class SelectPlanDialog(QDialog):
    # 增加 stations 参数，以便通过 ID 匹配出中文车站名
    def __init__(self, parent, all_trains, selected_numbers, stations):
        super().__init__(parent)
        self.all_trains = all_trains
        self.selected_numbers = selected_numbers
        self.station_map = {s.id: s.name for s in stations}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("读取图定计划")
        self.resize(650, 500)
        layout = QVBoxLayout(self)

        # 改为专业的表格形式
        self.table = QTableWidget(len(self.all_trains), 5)
        self.table.setHorizontalHeaderLabels(["选择", "车次号", "方向", "始发站", "终到站"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)

        for i, train in enumerate(self.all_trains):
            # 第一列：勾选框
            item_check = QTableWidgetItem()
            item_check.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            if train.train_number in self.selected_numbers:
                item_check.setCheckState(Qt.Checked)
            else:
                item_check.setCheckState(Qt.Unchecked)
            self.table.setItem(i, 0, item_check)

            # 第二列：车次号
            item_num = QTableWidgetItem(train.train_number)
            item_num.setFlags(item_num.flags() & ~Qt.ItemIsEditable)
            item_num.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 1, item_num)

            # 第三列：方向
            direction_text = "下行" if train.direction == "DOWN" else "上行"
            item_dir = QTableWidgetItem(direction_text)
            item_dir.setFlags(item_dir.flags() & ~Qt.ItemIsEditable)
            item_dir.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 2, item_dir)

            # 第四列：始发站
            start_st = self.station_map.get(train.points[0].station_id, "") if train.points else ""
            item_start = QTableWidgetItem(start_st)
            item_start.setFlags(item_start.flags() & ~Qt.ItemIsEditable)
            item_start.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 3, item_start)

            # 第五列：终到站
            end_st = self.station_map.get(train.points[-1].station_id, "") if train.points else ""
            item_end = QTableWidgetItem(end_st)
            item_end.setFlags(item_end.flags() & ~Qt.ItemIsEditable)
            item_end.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 4, item_end)

        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("全选")
        self.btn_select_all.clicked.connect(self.select_all)
        self.btn_clear_all = QPushButton("清空")
        self.btn_clear_all.clicked.connect(self.clear_all)

        # 彻底抛弃默认英文按钮，采用纯中文定义
        self.btn_ok = QPushButton("确定")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_select_all)
        btn_layout.addWidget(self.btn_clear_all)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def select_all(self):
        for i in range(self.table.rowCount()):
            self.table.item(i, 0).setCheckState(Qt.Checked)

    def clear_all(self):
        for i in range(self.table.rowCount()):
            self.table.item(i, 0).setCheckState(Qt.Unchecked)

    def get_selected_train_numbers(self):
        selected = set()
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).checkState() == Qt.Checked:
                selected.add(self.table.item(i, 1).text())
        return selected