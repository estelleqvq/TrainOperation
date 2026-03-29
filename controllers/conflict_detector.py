# controllers/conflict_detector.py
from PyQt5.QtCore import QTime


class ConflictDetector:
    def __init__(self, stations, section_times):
        self.stations = stations
        self.section_times = section_times  # 新增：接收从数据库加载的区间运行时分字典

        # 预设的高铁硬性约束参数
        self.MIN_TRACKING_INTERVAL = 3  # T_track: 最小追踪间隔 (分钟)
        self.MIN_STOP_TIME = 2  # \omega_k: 最小停站时间 (分钟)

    def validate_plan_line(self, target_line, existing_lines):
        try:
            # ================= 1. 单车硬约束校验 =================
            for i in range(len(target_line.points)):
                pt = target_line.points[i]

                # 1.1 停站时间约束
                if pt.planned_arrival and pt.planned_departure and pt.planned_arrival != pt.planned_departure:
                    stop_mins = self._diff_minutes(pt.planned_arrival, pt.planned_departure)
                    if 0 < stop_mins < self.MIN_STOP_TIME:
                        station_name = self._get_station_name(pt.station_id)
                        return False, f"【停站时间违规】\n车次 {target_line.train_number} 在 [{station_name}] 停站仅 {stop_mins} 分钟，低于最小安全停站标准 ({self.MIN_STOP_TIME} 分钟)。"

                # 1.2 核心修改：动态区间纯运行时分约束
                if i < len(target_line.points) - 1:
                    next_pt = target_line.points[i + 1]
                    if pt.planned_departure and next_pt.planned_arrival:
                        run_mins = self._diff_minutes(pt.planned_departure, next_pt.planned_arrival)

                        # 查表获取该区间的最小物理运行时间 (双向兼容查找)
                        min_run_time = self.section_times.get((pt.station_id, next_pt.station_id))
                        if min_run_time is None:
                            min_run_time = self.section_times.get((next_pt.station_id, pt.station_id))

                        # 如果数据库里配置了该区间，且运行时间小于物理极限
                        if min_run_time is not None and run_mins < min_run_time:
                            s1, s2 = self._get_station_name(pt.station_id), self._get_station_name(next_pt.station_id)
                            return False, f"【区间运行时间违规】\n车次 {target_line.train_number} 在 [{s1}] 至 [{s2}] 区间的排图运行时间为 {run_mins} 分钟，突破了该区间的物理速度极限 ({min_run_time} 分钟)。"

            # ================= 2. 多车协同约束校验 =================
            target_is_down = self._is_down_train(target_line)
            target_grade = self._get_train_grade(target_line.train_number)

            for existing in existing_lines:
                if str(existing.train_number) == str(target_line.train_number):
                    continue

                if self._is_down_train(existing) != target_is_down:
                    continue

                for i in range(len(target_line.points)):
                    t_pt1 = target_line.points[i]
                    e_pt1 = next((p for p in existing.points if p.station_id == t_pt1.station_id), None)

                    if not e_pt1: continue
                    station_name = self._get_station_name(t_pt1.station_id)

                    # 2.1 到达追踪间隔约束
                    if t_pt1.planned_arrival and e_pt1.planned_arrival:
                        arr_diff = abs(self._diff_minutes(t_pt1.planned_arrival, e_pt1.planned_arrival))
                        if arr_diff < self.MIN_TRACKING_INTERVAL:
                            return False, f"【到达追踪冲突】\n车次 {target_line.train_number} 与 {existing.train_number} 在 [{station_name}] 的到达间隔仅为 {arr_diff} 分钟，极易发生追尾！(最小限度 {self.MIN_TRACKING_INTERVAL} 分钟)。"

                    # 2.2 出发追踪间隔约束
                    if t_pt1.planned_departure and e_pt1.planned_departure:
                        dep_diff = abs(self._diff_minutes(t_pt1.planned_departure, e_pt1.planned_departure))
                        if dep_diff < self.MIN_TRACKING_INTERVAL:
                            return False, f"【出发追踪冲突】\n车次 {target_line.train_number} 与 {existing.train_number} 从 [{station_name}] 发车间隔仅为 {dep_diff} 分钟，违反安全标准！"

                    # 2.3 区间越行与车站越行约束
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
                                return False, f"【区间越行违规】\n严禁区间交会越行！\n车次 {target_line.train_number} 与 {existing.train_number} 在 [{s1}] 至 [{s2}] 区间内发生了越轨超越。"

                    # 2.4 车站越行等级约束
                    if t_pt1.planned_arrival and t_pt1.planned_departure and e_pt1.planned_arrival and e_pt1.planned_departure:
                        target_arr_first = self._time_less_than(t_pt1.planned_arrival, e_pt1.planned_arrival)
                        target_dep_first = self._time_less_than(t_pt1.planned_departure, e_pt1.planned_departure)
                        if target_arr_first != target_dep_first:
                            existing_grade = self._get_train_grade(existing.train_number)
                            if target_grade == existing_grade:
                                return False, f"【车站越行违规】\n同等级列车严禁互越！\n车次 {target_line.train_number} 与 {existing.train_number} 在 [{station_name}] 发生了同级越行。"

                            if target_arr_first and target_grade > existing_grade:
                                return False, f"【车站越行违规】\n高等级列车不避让低等级！\n车次 {target_line.train_number}(高等级) 不能在 [{station_name}] 避让 {existing.train_number}(低等级)。"

            return True, "校验通过"

        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"算法检测出现内部异常: {str(e)}，已被系统安全拦截。"

    # --- 辅助计算工具函数 ---
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

    def _get_train_grade(self, train_num):
        train_num_str = str(train_num)
        prefix = train_num_str[0].upper() if train_num_str else ''
        if prefix == 'G': return 4
        if prefix == 'D': return 3
        if prefix == 'C': return 2
        return 1