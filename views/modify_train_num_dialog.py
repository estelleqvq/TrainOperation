from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QLabel


class ModifyTrainNumDialog(QDialog):
    def __init__(self, parent, train_line):
        super().__init__(parent)
        self.train_line = train_line
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("修改车次号")
        self.resize(300, 150)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.lbl_old_num = QLabel(self.train_line.train_number)
        self.lbl_old_num.setStyleSheet("font-weight: bold; color: gray;")
        form.addRow("原车次号:", self.lbl_old_num)

        self.le_new_num = QLineEdit()
        self.le_new_num.setText(self.train_line.train_number)
        form.addRow("新车次号:", self.le_new_num)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("确定")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def get_data(self):
        return self.le_new_num.text().strip()