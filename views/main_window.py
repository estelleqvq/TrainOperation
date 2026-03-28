# views/main_window.py
from PyQt5.QtWidgets import QMainWindow, QAction, QCheckBox, QVBoxLayout, QWidget, QHBoxLayout, QMessageBox, \
    QInputDialog
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
        self.setWindowTitle("列车运行图仿真程序 —— 智能控制中心")
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.canvas = TrainGraphCanvas()
        layout.addWidget(self.canvas)

        checkbox_layout = QHBoxLayout()
        self.cb_plan = QCheckBox("显示计划线 (红色/数据库)")
        self.cb_plan.setChecked(True)
        self.cb_actual = QCheckBox("显示实际线 (蓝色/实迹库)")
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

        # ================= 新增：车次查询定位菜单项 =================
        search_action = QAction("🔍 查询定位车次...", self)
        search_action.triggered.connect(self.open_search_dialog)
        edit_menu.addAction(search_action)

        edit_menu.addSeparator()
        # ==========================================================

        add_action = QAction("➕ 新增计划线", self)
        add_action.triggered.connect(self.on_add_train)
        edit_menu.addAction(add_action)

        delete_action = QAction("❌ 删除选定线", self)
        delete_action.triggered.connect(self.on_delete)
        edit_menu.addAction(delete_action)

        edit_menu.addSeparator()

        report_action = QAction("📝 人工报点", self)
        report_action.triggered.connect(self.on_manual_report)
        edit_menu.addAction(report_action)

        edit_menu.addSeparator()
        save_action = QAction("💾 保存计划运行图", self)
        save_action.triggered.connect(self.on_save)
        edit_menu.addAction(save_action)

        # 运行图调整
        adj_menu = menubar.addMenu("运行图调整")
        param_action = QAction("⚙️ 修改计划线参数", self)
        param_action.triggered.connect(self.on_modify_plan_line_param)
        adj_menu.addAction(param_action)

        track_action = QAction("🛤️ 修改股道", self)
        track_action.triggered.connect(self.on_modify_track)
        adj_menu.addAction(track_action)

        train_num_action = QAction("🏷️ 修改车次号", self)
        train_num_action.triggered.connect(self.on_modify_train_num)
        adj_menu.addAction(train_num_action)

        adj_menu.addSeparator()
        full_schedule_action = QAction("🕒 修改全线时刻表", self)
        full_schedule_action.triggered.connect(self.on_modify_full_schedule)
        adj_menu.addAction(full_schedule_action)

    # ================= 新增：执行查询的弹窗逻辑 =================
    def open_search_dialog(self):
        # 弹出一个简单的输入对话框获取车次号
        train_num, ok = QInputDialog.getText(self, "车次查询定位", "请输入要查询定位的车次号:")

        if ok and train_num.strip():
            train_num = train_num.strip()
            # 调用画布里的查询与平移定位函数
            success = self.canvas.highlight_and_locate_train(train_num)

            if not success:
                QMessageBox.information(self, "查询结果", f"未在当前计划库中查询到车次：{train_num}")

    # ============================================================

    def on_manual_report(self):
        if self.controller and hasattr(self.controller, 'on_manual_report'):
            self.controller.on_manual_report()

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