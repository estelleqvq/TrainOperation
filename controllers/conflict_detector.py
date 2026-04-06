# controllers/conflict_detector.py
from PyQt5.QtCore import QTime


class ConflictDetector:
    def __init__(self, stations, section_times):
        self.stations = stations
        self.section_times = section_times

        self.MIN_TRACKING_INTERVAL = 3
        self.MIN_STOP_TIME = 2

    def validate_plan_line(self, target_line, existing_lines):
        try:
            # ================= 1. 单车硬约束校验 =================
            for i in range(len(target_line.points)):
                pt = target_line.points[i]

                if pt.planned_arrival and pt.planned_departure and pt.planned_arrival != pt.planned_departure:
                    stop_mins = self._diff_minutes(pt.planned_arrival, pt.planned_departure)
                    if 0 < stop_mins < self.MIN_STOP_TIME:
                        station_name = self._get_station_name(pt.station_id)
                        return False, f"{target_line.train_number}在{station_name}停站时间不足，请重新调整"

                if i < len(target_line.points) - 1:
                    next_pt = target_line.points[i + 1]
                    if pt.planned_departure and next_pt.planned_arrival:
                        run_mins = self._diff_minutes(pt.planned_departure, next_pt.planned_arrival)

                        min_run_time = self.section_times.get((pt.station_id, next_pt.station_id))
                        if min_run_time is None:
                            min_run_time = self.section_times.get((next_pt.station_id, pt.station_id))

                        if min_run_time is not None and run_mins < min_run_time:
                            s1, s2 = self._get_station_name(pt.station_id), self._get_station_name(next_pt.station_id)
                            return False, f"{target_line.train_number}在{s1}至{s2}区间运行时分不足，请重新调整"

            # ================= 2. 多车协同约束校验 =================
            target_is_down = self._is_down_train(target_line)
            target_grade = self._get_train_grade(target_line.train_number)

            for existing in existing_lines:
                if str(existing.train_number) == str(target_line.train_number):
                    continue

                for i in range(len(target_line.points)):
                    t_pt1 = target_line.points[i]
                    e_pt1 = next((p for p in existing.points if p.station_id == t_pt1.station_id), None)

                    if not e_pt1: continue
                    station_name = self._get_station_name(t_pt1.station_id)

                    # ====== 核心新增：股道绝对防撞占用校验 ======
                    if t_pt1.track == e_pt1.track:
                        t_arr_m = self._time_to_mins(t_pt1.planned_arrival) if t_pt1.planned_arrival else None
                        t_dep_m = self._time_to_mins(t_pt1.planned_departure) if t_pt1.planned_departure else None
                        e_arr_m = self._time_to_mins(e_pt1.planned_arrival) if e_pt1.planned_arrival else None
                        e_dep_m = self._time_to_mins(e_pt1.planned_departure) if e_pt1.planned_departure else None

                        if t_arr_m is None: t_arr_m = t_dep_m
                        if t_dep_m is None: t_dep_m = t_arr_m
                        if e_arr_m is None: e_arr_m = e_dep_m
                        if e_dep_m is None: e_dep_m = e_arr_m

                        if t_arr_m is not None and e_arr_m is not None:
                            # 如果是办理通过（到达时间=出发时间），强制分配1分钟的占用时间窗
                            t_dep_calc = t_dep_m + 1 if t_arr_m == t_dep_m else t_dep_m
                            e_dep_calc = e_dep_m + 1 if e_arr_m == e_dep_m else e_dep_m

                            # 数学时间窗交集判定
                            if max(t_arr_m, e_arr_m) < min(t_dep_calc, e_dep_calc):
                                return False, f"{target_line.train_number}和{existing.train_number}在{station_name}的 {t_pt1.track} 股道发生冲突，请重新调整"
                    # ==========================================

                # 追踪与越行约束仅针对同向列车
                if self._is_down_train(existing) != target_is_down:
                    continue

                for i in range(len(target_line.points)):
                    t_pt1 = target_line.points[i]
                    e_pt1 = next((p for p in existing.points if p.station_id == t_pt1.station_id), None)

                    if not e_pt1: continue
                    station_name = self._get_station_name(t_pt1.station_id)

                    if t_pt1.planned_arrival and e_pt1.planned_arrival:
                        arr_diff = abs(self._diff_minutes(t_pt1.planned_arrival, e_pt1.planned_arrival))
                        if arr_diff < self.MIN_TRACKING_INTERVAL:
                            return False, f"{target_line.train_number}和{existing.train_number}在{station_name}发生追踪冲突，请重新调整"

                    if t_pt1.planned_departure and e_pt1.planned_departure:
                        dep_diff = abs(self._diff_minutes(t_pt1.planned_departure, e_pt1.planned_departure))
                        if dep_diff < self.MIN_TRACKING_INTERVAL:
                            return False, f"{target_line.train_number}和{existing.train_number}在{station_name}发生追踪冲突，请重新调整"

                    if i < len(target_line.points) - 1:
                        t_pt2 = target_line.points[i + 1]
                        e_pt2 = next((p for p in existing.points if p.station_id == t_pt2.station_id), None)

                        if e_pt2 is not None and t_pt1.planned_departure and t_pt2.planned_arrival and e_pt1.planned_departure and e_pt2.planned_arrival:
                            t_dep = t_pt1.planned_departure
                            t_arr = t_pt2.planned_arrival
                            e_dep = e_pt1.planned_departure
                            e_arr = e_pt2.planned_arrival

                            target_departs_first = self._time_less_than(t_dep, e_dep)
                            target_arrives_first = self._time_less_than(t_arr, e_arr)

                            if target_departs_first != target_arrives_first:
                                s1, s2 = self._get_station_name(t_pt1.station_id), self._get_station_name(
                                    t_pt2.station_id)
                                return False, f"{target_line.train_number}和{existing.train_number}在{s1}至{s2}区间发生越行冲突，请重新调整"

                    if t_pt1.planned_arrival and t_pt1.planned_departure and e_pt1.planned_arrival and e_pt1.planned_departure:
                        target_arr_first = self._time_less_than(t_pt1.planned_arrival, e_pt1.planned_arrival)
                        target_dep_first = self._time_less_than(t_pt1.planned_departure, e_pt1.planned_departure)
                        if target_arr_first != target_dep_first:
                            existing_grade = self._get_train_grade(existing.train_number)
                            if target_grade == existing_grade:
                                return False, f"{target_line.train_number}和{existing.train_number}在{station_name}发生越行冲突，请重新调整"

                            if target_arr_first and target_grade > existing_grade:
                                return False, f"{target_line.train_number}和{existing.train_number}在{station_name}发生越行冲突，请重新调整"

            return True, "校验通过"

        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"算法检测出现内部异常: {str(e)}，已被系统安全拦截。"

    def _diff_minutes(self, t1: QTime, t2: QTime):
        return t1.secsTo(t2) // 60

    def _time_less_than(self, t1: QTime, t2: QTime):
        return t1.secsTo(t2) > 0

    def _get_station_name(self, station_id):
        for s in self.stations:
            if s.id == station_id: return s.name
        return str(station_id)

    def _is_down_train(self, train_line):
        if len(train_line.points) < 2: return True
        return train_line.points[0].station_id < train_line.points[-1].station_id

    def _time_to_mins(self, qt):
        return qt.hour() * 60 + qt.minute()

    def _get_train_grade(self, train_num):
        train_num_str = str(train_num)
        prefix = train_num_str[0].upper() if train_num_str else ''
        if prefix == 'G': return 4
        if prefix == 'D': return 3
        if prefix == 'C': return 2
        return 1