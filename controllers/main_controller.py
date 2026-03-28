# controllers/main_controller.py

from models.database import get_all_stations, get_section_times, save_plan, delete_plan_from_db, load_plans_from_db, \
    save_manual_report
from models.station import Station
from models.train_line import TrainLine, TrainLinePoint
from PyQt5.QtCore import QTime
from PyQt5.QtWidgets import QMessageBox, QDialog

from views.train_property_dialog import TrainPropertyDialog
from views.plan_line_param_dialog import PlanLineParamDialog
from views.modify_train_num_dialog import ModifyTrainNumDialog
from views.modify_track_dialog import ModifyTrackDialog
from views.manual_report_dialog import ManualReportDialog  # 引入报点弹窗

from controllers.socket_listener import SocketListenerThread
from config import SOCKET_PORT


class MainController:
    def __init__(self, view):
        self.view = view
        self.stations = []
        self.station_name_to_id = {}
        self.section_times = {}

        # 内存中同时维护两条线的数据
        self.plan_lines = []
        self.actual_lines = []

        self.socket_thread = None

        self.load_stations()
        self.load_section_times()
        self._reload_lines()
        self.start_socket_listener()

    def load_stations(self):
        try:
            self.stations = get_all_stations('plan')
            self.station_name_to_id = {s.name: s.id for s in self.stations}
            self.view.canvas.set_stations(self.stations)
        except Exception as e:
            print(f"加载车站失败: {e}")

    def load_section_times(self):
        try:
            self.section_times = get_section_times('plan')
        except Exception as e:
            print(f"加载区间时分失败: {e}")

    def _reload_lines(self):
        try:
            # 同时从两个物理库读取
            self.plan_lines = load_plans_from_db('plan')
            self.actual_lines = load_plans_from_db('actual')

            self.view.canvas.controller = self
            self.view.canvas.update_lines()
            self.detect_and_draw_conflicts()
        except Exception as e:
            QMessageBox.critical(self.view, "错误", f"加载数据库失败: {e}")

    def on_save(self):
        try:
            for line in self.plan_lines:
                save_plan(line, 'plan')
            QMessageBox.information(self.view, "成功", "计划运行图已成功保存！")
        except Exception as e:
            QMessageBox.critical(self.view, "错误", f"保存失败: {e}")

    def on_delete(self):
        selected_line = getattr(self.view.canvas, 'selected_line', None)
        if not selected_line:
            QMessageBox.warning(self.view, "提示", "请先在画布上选中一条列车线！")
            return
        self.on_delete_specific(selected_line)

    def on_delete_specific(self, train_line):
        if not train_line: return
        reply = QMessageBox.question(self.view, "确认", f"确定删除车次 {train_line.train_number} 吗？")
        if reply == QMessageBox.Yes:
            try:
                if train_line.id is not None:
                    delete_plan_from_db(train_line.id, 'plan')
                if train_line in self.plan_lines:
                    self.plan_lines.remove(train_line)
                self.view.canvas.selected_line = None
                self._reload_lines()  # 重新拉取以防实际库有遗留
            except Exception as e:
                QMessageBox.critical(self.view, "错误", f"删除失败: {e}")

    def open_train_property_dialog(self, train_line=None):
        dialog = TrainPropertyDialog(self.view, self.stations, self.section_times, train_line)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            points = []
            for stop in data['stops']:
                p_arr = QTime.fromString(stop['planned_arrival'], "HH:mm") if stop['planned_arrival'] else None
                p_dep = QTime.fromString(stop['planned_departure'], "HH:mm") if stop['planned_departure'] else None
                point = TrainLinePoint(stop['station_id'], p_arr, p_dep, stop['track'])
                points.append(point)

            if train_line:
                train_line.train_number = data['train_number']
                train_line.direction = data['direction']
                train_line.date = data['date']
                train_line.points = points
            else:
                new_line = TrainLine(None, data['train_number'], data['direction'], data['date'], points)
                self.plan_lines.append(new_line)

            self.view.canvas.update_lines()
            self.detect_and_draw_conflicts()

    def on_add_train(self):
        self.open_train_property_dialog(None)

    def on_modify_full_schedule(self):
        selected_line = getattr(self.view.canvas, 'selected_line', None)
        if not selected_line:
            QMessageBox.warning(self.view, "提示", "请先在画布上点击选中一条列车线！")
            return
        self.open_train_property_dialog(selected_line)

    def open_plan_line_param_dialog(self, train_line=None, station_id=None):
        if not train_line:
            train_line = getattr(self.view.canvas, 'selected_line', None)
            if not train_line: return

        dialog = PlanLineParamDialog(self.view, train_line, self.stations, station_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            target_station_id = data['station_id']
            target_point = next((p for p in train_line.points if p.station_id == target_station_id), None)

            if target_point:
                if data['target_arrival']:
                    target_point.planned_arrival = QTime.fromString(data['target_arrival'], "HH:mm")
                else:
                    target_point.planned_arrival = None

                if data['target_departure']:
                    target_point.planned_departure = QTime.fromString(data['target_departure'], "HH:mm")
                else:
                    target_point.planned_departure = None

            self.view.canvas.update_lines()
            self.detect_and_draw_conflicts()

    def open_modify_track_dialog(self, train_line=None, station_id=None):
        if not train_line:
            train_line = getattr(self.view.canvas, 'selected_line', None)
            if not train_line: return
        dialog = ModifyTrackDialog(self.view, train_line, self.stations, station_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            target_point = next((p for p in train_line.points if p.station_id == data['station_id']), None)
            if target_point:
                target_point.track = data['track']
            self.view.canvas.update_lines()
            self.detect_and_draw_conflicts()

    def open_modify_train_num_dialog(self, train_line=None):
        if not train_line:
            train_line = getattr(self.view.canvas, 'selected_line', None)
            if not train_line: return
        dialog = ModifyTrainNumDialog(self.view, train_line)
        if dialog.exec_() == QDialog.Accepted:
            new_num = dialog.get_data()
            if new_num:
                train_line.train_number = new_num
            self.view.canvas.update_lines()
            self.detect_and_draw_conflicts()

    # ============ 处理人工打点并落盘实迹库 ============
    def open_manual_report_dialog(self, train_line=None, station_id=None):
        if not train_line:
            train_line = getattr(self.view.canvas, 'selected_line', None)
            if not train_line:
                QMessageBox.warning(self.view, "提示", "请先在画布上点击选中一条列车线！")
                return

        # 尝试从 actual_lines 中寻找该车的实迹数据，传给弹窗以供回显
        actual_train = next((t for t in self.actual_lines if t.train_number == train_line.train_number), None)

        dialog = ManualReportDialog(self.view, train_line, self.stations, actual_train, station_id)
        if dialog.exec_() == QDialog.Accepted:
            st_id, track, act_arr, act_dep = dialog.get_data()
            try:
                save_manual_report(train_line.train_number, train_line.direction, train_line.date, st_id, track,
                                       act_arr, act_dep)
                self._reload_lines()
            except Exception as e:
                QMessageBox.critical(self.view, "数据库错误", f"报点失败: {e}")

    def on_manual_report(self):
        """顶部菜单的人工报点入口"""
        self.open_manual_report_dialog()


    def detect_and_draw_conflicts(self):
        conflicts = []
        lines = self.plan_lines  # 冲突检测基于计划库

        def qtime_to_mins(qt):
            return qt.hour() * 60 + qt.minute() if qt else None

        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                l1 = lines[i]
                l2 = lines[j]

                points1 = {p.station_id: p for p in l1.points}
                points2 = {p.station_id: p for p in l2.points}

                for s in self.stations:
                    p1 = points1.get(s.id)
                    p2 = points2.get(s.id)
                    if not p1 or not p2: continue

                    arr1 = qtime_to_mins(p1.planned_arrival or p1.planned_departure)
                    dep1 = qtime_to_mins(p1.planned_departure or p1.planned_arrival)
                    arr2 = qtime_to_mins(p2.planned_arrival or p2.planned_departure)
                    dep2 = qtime_to_mins(p2.planned_departure or p2.planned_arrival)

                    if arr1 is None or dep1 is None or arr2 is None or dep2 is None: continue

                    if p1.track == p2.track and p1.track != "正线":
                        if arr1 == dep1: dep1 += 1
                        if arr2 == dep2: dep2 += 1

                        if max(arr1, arr2) < min(dep1, dep2):
                            conflict_mins = max(arr1, arr2)
                            conflicts.append({
                                'time': QTime(conflict_mins // 60, conflict_mins % 60),
                                'station_id': s.id,
                                'msg': f"股道冲突 ({p1.track}): {l1.train_number} 与 {l2.train_number}"
                            })

                    if l1.direction == l2.direction:
                        if abs(dep1 - dep2) < 3:
                            conflict_mins = min(dep1, dep2)
                            conflicts.append({
                                'time': QTime(conflict_mins // 60, conflict_mins % 60),
                                'station_id': s.id,
                                'msg': f"追踪间隔过小: {l1.train_number} 与 {l2.train_number}"
                            })

        self.view.canvas.draw_conflicts(conflicts)

    def start_socket_listener(self):
        port = SOCKET_PORT if SOCKET_PORT != 3306 else 9999
        self.socket_thread = SocketListenerThread(port)
        self.socket_thread.data_received.connect(self.handle_socket_data)
        self.socket_thread.start()

    def handle_socket_data(self, data):
        pass  # 后续若需真实接入物理沙盘再开放此接口