# controllers/main_controller.py
from models.database import get_all_stations, get_section_times, save_plan, delete_plan_from_db, load_plans_from_db, \
    save_manual_report, clear_all_actual_data
from models.station import Station
from models.train_line import TrainLine, TrainLinePoint
from PyQt5.QtCore import QTime
from PyQt5.QtWidgets import QMessageBox, QDialog
from PyQt5.QtGui import QColor

from controllers.conflict_detector import ConflictDetector


class MainController:
    def __init__(self, view):
        self.view = view
        self.stations = []
        self.station_name_to_id = {}
        self.section_times = {}

        self.plan_lines = []
        self.actual_lines = []

        self.selected_train_numbers = set()
        self.all_db_plan_lines = []

        self.conflict_detector = None

        self.load_stations()
        self.load_section_times()
        self.conflict_detector = ConflictDetector(self.stations, self.section_times)

        clear_all_actual_data()
        self._reload_lines()

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
            self.all_db_plan_lines = load_plans_from_db('plan')
            self.actual_lines = load_plans_from_db('actual')

            self.plan_lines = [t for t in self.all_db_plan_lines if t.train_number in self.selected_train_numbers]

            self.view.canvas.controller = self
            self.view.canvas.update_lines()
            self.detect_and_draw_conflicts()
        except Exception as e:
            msg_box = QMessageBox(self.view)
            msg_box.setWindowTitle("错误")
            msg_box.setText(f"加载数据库失败: {e}")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).setText("确定")
            msg_box.exec_()

    def on_import_plans(self):
        from views.select_plan_dialog import SelectPlanDialog
        try:
            self.all_db_plan_lines = load_plans_from_db('plan')
            dialog = SelectPlanDialog(self.view, self.all_db_plan_lines, self.selected_train_numbers, self.stations)
            if dialog.exec_() == QDialog.Accepted:
                self.selected_train_numbers = dialog.get_selected_train_numbers()
                self._reload_lines()
        except Exception as e:
            msg_box = QMessageBox(self.view)
            msg_box.setWindowTitle("错误")
            msg_box.setText(f"读取计划失败: {e}")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).setText("确定")
            msg_box.exec_()

    def validate_new_or_modified_line(self, target_line):
        if not self.conflict_detector:
            return True, ""
        return self.conflict_detector.validate_plan_line(target_line, self.plan_lines)

    def on_save(self):
        try:
            if self.conflict_detector:
                for line in self.plan_lines:
                    is_valid, error_msg = self.conflict_detector.validate_plan_line(line, self.plan_lines)
                    if not is_valid:
                        msg_box = QMessageBox(self.view)
                        msg_box.setWindowTitle("冲突报警")
                        msg_box.setIcon(QMessageBox.Warning)
                        msg_box.setText(error_msg)
                        msg_box.setStandardButtons(QMessageBox.Ok)
                        msg_box.button(QMessageBox.Ok).setText("确定")
                        msg_box.exec_()
                        return

            for line in self.plan_lines:
                save_plan(line, 'plan')

            msg_box = QMessageBox(self.view)
            msg_box.setWindowTitle("成功")
            msg_box.setText("计划运行图已成功保存！")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).setText("确定")
            msg_box.exec_()

        except Exception as e:
            import traceback
            traceback.print_exc()
            msg_box = QMessageBox(self.view)
            msg_box.setWindowTitle("程序异常")
            msg_box.setText(f"保存过程中发生错误:\n{str(e)}")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).setText("确定")
            msg_box.exec_()

    def on_delete(self):
        selected_line = getattr(self.view.canvas, 'selected_line', None)
        if not selected_line:
            msg_box = QMessageBox(self.view)
            msg_box.setWindowTitle("提示")
            msg_box.setText("请先在画布上选中一条列车线！")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).setText("确定")
            msg_box.exec_()
            return
        self.on_delete_specific(selected_line)

    def on_delete_specific(self, train_line):
        if not train_line: return

        msg_box = QMessageBox(self.view)
        msg_box.setWindowTitle("确认")
        msg_box.setText(f"确定删除车次 {train_line.train_number} 吗？")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.button(QMessageBox.Yes).setText("确定")
        msg_box.button(QMessageBox.No).setText("取消")
        reply = msg_box.exec_()

        if reply == QMessageBox.Yes:
            try:
                if train_line.id is not None:
                    delete_plan_from_db(train_line.id, 'plan')
                if train_line.train_number in self.selected_train_numbers:
                    self.selected_train_numbers.remove(train_line.train_number)

                self.view.canvas.selected_line = None
                self._reload_lines()
            except Exception as e:
                msg_box = QMessageBox(self.view)
                msg_box.setWindowTitle("错误")
                msg_box.setText(f"删除失败: {e}")
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).setText("确定")
                msg_box.exec_()

    def open_train_property_dialog(self, train_line=None):
        from views.train_property_dialog import TrainPropertyDialog
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
                old_num = train_line.train_number
                train_line.train_number = data['train_number']
                train_line.direction = data['direction']
                train_line.date = data['date']
                train_line.points = points

                if old_num in self.selected_train_numbers:
                    self.selected_train_numbers.remove(old_num)
                self.selected_train_numbers.add(data['train_number'])
            else:
                new_line = TrainLine(None, data['train_number'], data['direction'], data['date'], points)
                self.selected_train_numbers.add(new_line.train_number)
                self.plan_lines.append(new_line)

            self.view.canvas.update_lines()
            self.detect_and_draw_conflicts()

    def on_add_train(self):
        self.open_train_property_dialog(None)

    def on_modify_full_schedule(self):
        selected_line = getattr(self.view.canvas, 'selected_line', None)
        if not selected_line:
            msg_box = QMessageBox(self.view)
            msg_box.setWindowTitle("提示")
            msg_box.setText("请先在画布上点击选中一条列车线！")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.button(QMessageBox.Ok).setText("确定")
            msg_box.exec_()
            return
        self.open_train_property_dialog(selected_line)

    def open_plan_line_param_dialog(self, train_line=None, station_id=None):
        from views.plan_line_param_dialog import PlanLineParamDialog
        if not train_line:
            train_line = getattr(self.view.canvas, 'selected_line', None)
            if not train_line: return

        dialog = PlanLineParamDialog(self, train_line, self.stations, station_id)
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
        from views.modify_track_dialog import ModifyTrackDialog
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
        from views.modify_train_num_dialog import ModifyTrainNumDialog
        if not train_line:
            train_line = getattr(self.view.canvas, 'selected_line', None)
            if not train_line: return
        dialog = ModifyTrainNumDialog(self.view, train_line)
        if dialog.exec_() == QDialog.Accepted:
            new_num = dialog.get_data()
            if new_num:
                old_num = train_line.train_number
                if old_num in self.selected_train_numbers:
                    self.selected_train_numbers.remove(old_num)
                train_line.train_number = new_num
                self.selected_train_numbers.add(new_num)

            self.view.canvas.update_lines()
            self.detect_and_draw_conflicts()

    def open_manual_report_dialog(self, train_line=None, station_id=None):
        from views.manual_report_dialog import ManualReportDialog
        if not train_line:
            train_line = getattr(self.view.canvas, 'selected_line', None)
            if not train_line:
                msg_box = QMessageBox(self.view)
                msg_box.setWindowTitle("提示")
                msg_box.setText("请先在画布上点击选中一条列车线！")
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).setText("确定")
                msg_box.exec_()
                return

        actual_train = next((t for t in self.actual_lines if t.train_number == train_line.train_number), None)
        dialog = ManualReportDialog(self.view, train_line, self.stations, actual_train, station_id)
        if dialog.exec_() == QDialog.Accepted:
            st_id, track, act_arr, act_dep = dialog.get_data()
            try:
                save_manual_report(train_line.train_number, train_line.direction, train_line.date, st_id, track,
                                   act_arr, act_dep)
                self._reload_lines()
            except Exception as e:
                msg_box = QMessageBox(self.view)
                msg_box.setWindowTitle("数据库错误")
                msg_box.setText(f"报点失败: {e}")
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).setText("确定")
                msg_box.exec_()

    def on_manual_report(self):
        self.open_manual_report_dialog()

    def open_report_record_dialog(self):
        from views.report_record_dialog import ReportRecordDialog
        dialog = ReportRecordDialog(self.view, self.plan_lines, self.actual_lines, self.stations)
        dialog.exec_()

    def detect_and_draw_conflicts(self):
        conflicts = []
        lines = self.plan_lines

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

                    # ====== 核心修改：实时渲染拦截也纳入全股道监控 ======
                    if p1.track == p2.track:
                        dep_calc1 = dep1 + 1 if arr1 == dep1 else dep1
                        dep_calc2 = dep2 + 1 if arr2 == dep2 else dep2

                        if max(arr1, arr2) < min(dep_calc1, dep_calc2):
                            conflict_mins = max(arr1, arr2)
                            conflicts.append({
                                'time': QTime(conflict_mins // 60, conflict_mins % 60),
                                'station_id': s.id,
                                'msg': f"股道冲突: {p1.track}, {l1.train_number} 与 {l2.train_number}"
                            })
                    # =================================================

                    if l1.direction == l2.direction:
                        if abs(dep1 - dep2) < 3:
                            conflict_mins = min(dep1, dep2)
                            conflicts.append({
                                'time': QTime(conflict_mins // 60, conflict_mins % 60),
                                'station_id': s.id,
                                'msg': f"追踪间隔过小: {l1.train_number} 与 {l2.train_number}"
                            })

        self.view.canvas.draw_conflicts(conflicts)

    def _clone_lines(self, lines):
        new_lines = []
        for l in lines:
            new_pts = []
            for p in l.points:
                arr = QTime(p.planned_arrival.hour(), p.planned_arrival.minute()) if p.planned_arrival else None
                dep = QTime(p.planned_departure.hour(), p.planned_departure.minute()) if p.planned_departure else None
                new_pt = TrainLinePoint(p.station_id, arr, dep, p.track)
                new_pts.append(new_pt)
            new_l = TrainLine(l.id, l.train_number, l.direction, l.date, new_pts)
            new_lines.append(new_l)
        return new_lines

    def _add_mins_to_qtime(self, qt, mins):
        if not qt: return None
        total = qt.hour() * 60 + qt.minute() + mins
        return QTime((total // 60) % 24, total % 60)

    def on_simulate_delay(self):
        from views.delay_simulation_dialog import DelaySimulationDialog
        from controllers.ga_optimizer import GAOptimizer

        dialog = DelaySimulationDialog(self.view, self.plan_lines, self.stations)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            target_train_num = data['train_num']
            station_id = data['station_id']
            delay_mins = data['delay_mins']

            temp_lines = self._clone_lines(self.plan_lines)
            target_train = next((t for t in temp_lines if t.train_number == target_train_num), None)
            if not target_train: return

            target_pt_idx = next((i for i, p in enumerate(target_train.points) if p.station_id == station_id), -1)
            if target_pt_idx == -1 or target_pt_idx == len(target_train.points) - 1:
                msg_box = QMessageBox(self.view)
                msg_box.setWindowTitle("提示")
                msg_box.setText("所选车站为终点站或无效，无需向后调整。")
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).setText("确定")
                msg_box.exec_()
                return

            target_pt = target_train.points[target_pt_idx]
            next_station_id = target_train.points[target_pt_idx + 1].station_id

            target_pt.planned_arrival = self._add_mins_to_qtime(target_pt.planned_arrival, delay_mins)
            if target_pt.planned_departure:
                target_pt.planned_departure = self._add_mins_to_qtime(target_pt.planned_departure, delay_mins)
            else:
                target_pt.planned_departure = self._add_mins_to_qtime(target_pt.planned_arrival, 2)

            target_is_down = target_train.points[0].station_id < target_train.points[-1].station_id
            affected_trains = []
            for t in temp_lines:
                is_down = t.points[0].station_id < t.points[-1].station_id
                if is_down == target_is_down:
                    pt = next((p for p in t.points if p.station_id == station_id), None)
                    if pt and pt.planned_departure:
                        affected_trains.append(t)

            def get_dep_mins(tr):
                p = next((x for x in tr.points if x.station_id == station_id), None)
                return p.planned_departure.hour() * 60 + p.planned_departure.minute()

            affected_trains.sort(key=get_dep_mins)

            optimizer = GAOptimizer(self.stations, self.section_times)
            optimized_trains = optimizer.optimize_dispatch_order(station_id, next_station_id, affected_trains)

            last_departure_mins = -999
            for t in optimized_trains:
                curr_p = next(p for p in t.points if p.station_id == station_id)
                next_p = next(p for p in t.points if p.station_id == next_station_id)

                ready_to_dep = curr_p.planned_departure.hour() * 60 + curr_p.planned_departure.minute()
                actual_dep_mins = max(ready_to_dep, last_departure_mins + 3)
                extra_delay = actual_dep_mins - ready_to_dep

                curr_p.planned_departure = QTime(actual_dep_mins // 60, actual_dep_mins % 60)
                last_departure_mins = actual_dep_mins

                idx = t.points.index(next_p)
                for j in range(idx, len(t.points)):
                    p = t.points[j]
                    p.planned_arrival = self._add_mins_to_qtime(p.planned_arrival, extra_delay)
                    p.planned_departure = self._add_mins_to_qtime(p.planned_departure, extra_delay)

            original_lines = self.plan_lines
            self.plan_lines = temp_lines
            for t in self.plan_lines:
                if t in affected_trains:
                    t.color = QColor(255, 0, 255)
            self.view.canvas.update_lines()

            msg_box = QMessageBox(self.view)
            msg_box.setWindowTitle("智能调整完成")
            msg_box.setText("遗传算法已完成局部重排。\n紫色线条为临时调整方案，是否应用写入？")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.button(QMessageBox.Yes).setText("确定")
            msg_box.button(QMessageBox.No).setText("取消")
            reply = msg_box.exec_()

            if reply == QMessageBox.Yes:
                for t in self.plan_lines:
                    if hasattr(t, 'color'): del t.color
                self.view.canvas.update_lines()
                self.on_save()
            else:
                self.plan_lines = original_lines
                self.view.canvas.update_lines()