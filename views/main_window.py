# views/main_window.py
from PyQt5.QtWidgets import QMainWindow, QAction, QCheckBox, QVBoxLayout, QWidget, QHBoxLayout, QMessageBox, QDialog, \
    QLabel, QLineEdit, QPushButton
from PyQt5.QtCore import Qt
from .canvas_widget import TrainGraphCanvas


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.controller = None
        self.init_ui()

    def set_controller(self, controller):
        self.controller = controller
        self.canvas.controller = controller

    def init_ui(self):
        self.setWindowTitle("列车运行图仿真程序")
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.canvas = TrainGraphCanvas()
        layout.addWidget(self.canvas)

        checkbox_layout = QHBoxLayout()
        self.cb_plan = QCheckBox("显示计划线")
        self.cb_plan.setChecked(True)
        self.cb_actual = QCheckBox("显示实际线")
        self.cb_actual.setChecked(True)

        self.cb_plan.stateChanged.connect(self.on_plan_display_changed)
        self.cb_actual.stateChanged.connect(self.on_actual_display_changed)

        checkbox_layout.addWidget(self.cb_plan)
        checkbox_layout.addWidget(self.cb_actual)
        checkbox_layout.addStretch()
        layout.addLayout(checkbox_layout)

        self.create_menu()

    def create_menu(self):
        menubar = self.menuBar()

        # 计划图操作
        edit_menu = menubar.addMenu("计划图操作")

        import_action = QAction("读取图定计划...", self)
        import_action.triggered.connect(self.on_import_plans)
        edit_menu.addAction(import_action)
        edit_menu.addSeparator()

        search_action = QAction("车次号查询...", self)
        search_action.triggered.connect(self.open_search_dialog)
        edit_menu.addAction(search_action)
        edit_menu.addSeparator()

        add_action = QAction("加开列车", self)
        add_action.triggered.connect(self.on_add_train)
        edit_menu.addAction(add_action)

        delete_action = QAction("删除选定线", self)
        delete_action.triggered.connect(self.on_delete)
        edit_menu.addAction(delete_action)
        edit_menu.addSeparator()

        report_action = QAction("人工报点", self)
        report_action.triggered.connect(self.on_manual_report)
        edit_menu.addAction(report_action)

        # ====== 新增：报点记录查看 ======
        record_action = QAction("报点记录查询", self)
        record_action.triggered.connect(self.on_report_record)
        edit_menu.addAction(record_action)
        edit_menu.addSeparator()

        # ====== 新增：阶段计划下发入口 ======
        issue_action = QAction("下发阶段计划...", self)
        issue_action.triggered.connect(self.on_issue_stage_plan)
        edit_menu.addAction(issue_action)
        edit_menu.addSeparator()

        save_action = QAction("保存计划运行图", self)
        save_action.triggered.connect(self.on_save)
        edit_menu.addAction(save_action)

        # 运行图调整
        adj_menu = menubar.addMenu("运行图调整")
        param_action = QAction("修改计划线参数", self)
        param_action.triggered.connect(self.on_modify_plan_line_param)
        adj_menu.addAction(param_action)

        track_action = QAction("修改接发车股道", self)
        track_action.triggered.connect(self.on_modify_track)
        adj_menu.addAction(track_action)

        train_num_action = QAction("修改车次号", self)
        train_num_action.triggered.connect(self.on_modify_train_num)
        adj_menu.addAction(train_num_action)
        adj_menu.addSeparator()

        full_schedule_action = QAction("修改全线时刻表", self)
        full_schedule_action.triggered.connect(self.on_modify_full_schedule)
        adj_menu.addAction(full_schedule_action)

        # 智能辅助决策
        ai_menu = menubar.addMenu("智能辅助决策")
        delay_action = QAction("模拟突发晚点...", self)
        delay_action.triggered.connect(self.on_simulate_delay)
        ai_menu.addAction(delay_action)

    def on_import_plans(self):
        if self.controller and hasattr(self.controller, 'on_import_plans'):
            self.controller.on_import_plans()

    def open_search_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("车次号查询")
        dialog.resize(300, 120)
        layout = QVBoxLayout(dialog)

        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("请输入车次号:"))
        le_train_num = QLineEdit()
        form_layout.addWidget(le_train_num)
        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("确定")
        btn_cancel = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        btn_ok.clicked.connect(dialog.accept)
        btn_cancel.clicked.connect(dialog.reject)

        if dialog.exec_() == QDialog.Accepted:
            train_num = le_train_num.text().strip()
            if train_num:
                success = self.canvas.highlight_and_locate_train(train_num)
                if not success:
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("查询结果")
                    msg_box.setText(f"未查询到车次：{train_num}")
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).setText("确定")
                    msg_box.exec_()

    def on_simulate_delay(self):
        if self.controller and hasattr(self.controller, 'on_simulate_delay'):
            self.controller.on_simulate_delay()

    def on_manual_report(self):
        if self.controller and hasattr(self.controller, 'on_manual_report'):
            self.controller.on_manual_report()

    def on_report_record(self):
        if self.controller and hasattr(self.controller, 'open_report_record_dialog'):
            self.controller.open_report_record_dialog()

    def on_plan_display_changed(self, state):
        self.canvas.show_plan_lines = (state == Qt.Checked)
        self.canvas.update_lines()

    def on_actual_display_changed(self, state):
        self.canvas.show_actual_lines = (state == Qt.Checked)
        self.canvas.update_lines()

    def on_save(self):
        if self.controller: self.controller.on_save()

    def on_add_train(self):
        if self.controller: self.controller.on_add_train()

    def on_delete(self):
        if self.controller: self.controller.on_delete()

    def on_modify_plan_line_param(self):
        if self.controller and hasattr(self.controller, 'open_plan_line_param_dialog'):
            self.controller.open_plan_line_param_dialog()

    def on_modify_track(self):
        if self.controller and hasattr(self.controller, 'open_modify_track_dialog'):
            self.controller.open_modify_track_dialog()

    def on_modify_train_num(self):
        if self.controller and hasattr(self.controller, 'open_modify_train_num_dialog'):
            self.controller.open_modify_train_num_dialog()

    def on_modify_full_schedule(self):
        if self.controller and hasattr(self.controller, 'on_modify_full_schedule'):
            self.controller.on_modify_full_schedule()

    # 在 views/main_window.py 底部增加：
    def on_issue_stage_plan(self):
        if self.controller and hasattr(self.controller, 'open_plan_issue_dialog'):
            self.controller.open_plan_issue_dialog()