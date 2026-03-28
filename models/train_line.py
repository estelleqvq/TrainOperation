# models/train_line.py

class TrainLinePoint:
    def __init__(self, station_id, planned_arrival=None, planned_departure=None, track="正线"):
        self.station_id = station_id
        self.planned_arrival = planned_arrival
        self.planned_departure = planned_departure
        self.actual_arrival = None
        self.actual_departure = None
        self.track = track


class TrainLine:
    def __init__(self, id, train_number, direction, date, points):
        self.id = id
        self.train_number = train_number
        self.direction = direction
        self.date = date
        self.points = points

    def shift(self, delta_minutes):
        for point in self.points:
            if point.planned_arrival:
                point.planned_arrival = point.planned_arrival.addSecs(delta_minutes * 60)
            if point.planned_departure:
                point.planned_departure = point.planned_departure.addSecs(delta_minutes * 60)

    def shift_downstream(self, start_index, delta_minutes, handle_type='dep'):
        """
        工业级打折线推演算法：
        - handle_type == 'arr': 拖拽到达点，整体晚点（保持该站停站时间不变）
        - handle_type == 'dep': 拖拽出发点，到达时间不变，仅增加该站停站时间并影响后续行程
        - handle_type == 'pass': 拖拽通过点，整体晚点
        """
        if start_index < 0 or start_index >= len(self.points):
            return

        point = self.points[start_index]

        # 1. 优先处理被拖拽的当前车站
        if handle_type == 'arr' or handle_type == 'pass':
            # 拖拽到达或通过点，到达和出发都跟着晚点
            if point.planned_arrival:
                point.planned_arrival = point.planned_arrival.addSecs(delta_minutes * 60)
            if point.planned_departure:
                point.planned_departure = point.planned_departure.addSecs(delta_minutes * 60)
        elif handle_type == 'dep':
            # 拖拽出发点，只改变出发时间（相当于拉长了停站待避时间）
            if point.planned_departure:
                point.planned_departure = point.planned_departure.addSecs(delta_minutes * 60)

        # 2. 处理该站之后的所有后续车站（同步向后推演）
        for i in range(start_index + 1, len(self.points)):
            p = self.points[i]
            if p.planned_arrival:
                p.planned_arrival = p.planned_arrival.addSecs(delta_minutes * 60)
            if p.planned_departure:
                p.planned_departure = p.planned_departure.addSecs(delta_minutes * 60)