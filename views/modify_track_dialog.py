from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QPushButton, QHBoxLayout, QLabel


class ModifyTrackDialog(QDialog):
    def __init__(self, parent, train_line, stations, initial_station_id=None):
        super().__init__(parent)
        self.train_line = train_line
        self.stations = stations
        self.initial_station_id = initial_station_id
        self.station_map = {s.id: s for s in self.stations}
        self.init_ui()
        self.load_initial_data()

    def init_ui(self):
        self.setWindowTitle("修改接发车股道")
        self.resize(320, 200)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        lbl_train = QLabel(self.train_line.train_number)
        lbl_train.setStyleSheet("font-weight: bold; color: #b71c1c;")
        form.addRow("车次号:", lbl_train)

        # 支持下拉选择要修改的车站
        self.cb_station = QComboBox()
        for p in self.train_line.points:
            st = self.station_map.get(p.station_id)
            if st:
                self.cb_station.addItem(st.name, p.station_id)
        self.cb_station.currentIndexChanged.connect(self.on_station_changed)
        form.addRow("目标车站:", self.cb_station)

        self.cb_track = QComboBox()
        form.addRow("接发股道:", self.cb_track)

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

        self.cb_track.blockSignals(True)
        self.cb_track.clear()
        self.cb_track.addItems(st.tracks)
        self.cb_track.setCurrentText(point.track if point.track else "正线")
        self.cb_track.blockSignals(False)

    def get_data(self):
        return {
            "station_id": self.cb_station.currentData(),
            "track": self.cb_track.currentText()
        }