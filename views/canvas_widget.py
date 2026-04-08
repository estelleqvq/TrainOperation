# views/canvas_widget.py
import sys
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsPathItem, QMenu, \
    QGraphicsItem, QMessageBox
from PyQt5.QtCore import Qt, QTime, QRectF, QTimer
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QPainterPath, QBrush, QPainterPathStroker


class TrainGraphCanvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        self.setMinimumSize(1000, 600)

        self.top_margin = 80
        self.bottom_margin = 40
        self.left_margin = 70
        self.right_margin = 50

        # 修改为 18:00 (18*60=1080) 到次日 18:00 (1080+1440=2520)
        self.min_minutes = 1080
        self.max_minutes = 2520

        self.simulated_current_time = QTime(6, 0)
        self.base_date = "2026年4月7日"
        self.shift_info_text = None

        self.current_time_line = None
        self.current_time_text = None

        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.advance_time)
        self.time_timer.start(1000)

        self.stations = []
        self.draw_grid = True

        self.show_plan_lines = True
        self.show_actual_lines = True
        self.train_line_items = []
        self.conflict_items = []

        self.controller = None
        self.selected_line = None
        self.highlighted_line = None

        self.last_scene_x = None
        self.accumulated_delta_x = 0.0
        self.dragged_point_idx = None
        self.dragged_handle_type = None

        self.station_texts = []
        self.time_texts = []
        self.time_ticks = []
        self.time_axis_main_line = None

        self.minute_items = []

        self.update_scene_rect()

    def advance_time(self):
        self.simulated_current_time = self.simulated_current_time.addSecs(60)
        # 跨越次日 18:00 停止
        if self.simulated_current_time.hour() == 17 and self.simulated_current_time.minute() >= 59:
            pass  # 这里可以根据实际逻辑决定是否停止，原来是23:59
        self.update_current_time_indicator()

    def update_current_time_indicator(self):
        current_x = self.time_to_x(self.simulated_current_time)
        if current_x is None: return

        rect = self.scene.sceneRect()
        plot_left = self.left_margin
        plot_right = rect.width() - self.right_margin
        plot_top = self.top_margin
        plot_height = rect.height() - self.bottom_margin - plot_top

        bounded_x = max(plot_left, min(current_x, plot_right))

        if hasattr(self, 'past_bg_rect') and self.past_bg_rect:
            self.past_bg_rect.setRect(plot_left, plot_top, bounded_x - plot_left, plot_height)
        if hasattr(self, 'future_bg_rect') and self.future_bg_rect:
            self.future_bg_rect.setRect(bounded_x, plot_top, plot_right - bounded_x, plot_height)

        if hasattr(self, 'current_time_line') and self.current_time_line:
            if plot_left <= current_x <= plot_right:
                self.current_time_line.setVisible(True)
                self.current_time_text.setVisible(True)

                line = self.current_time_line.line()
                top_y = self.time_axis_main_line.line().y1() if self.time_axis_main_line else line.y1()

                self.current_time_line.setLine(current_x, top_y, current_x, line.y2())

                self.current_time_text.setText(self.simulated_current_time.toString("HH:mm"))
                rect_text = self.current_time_text.boundingRect()
                self.current_time_text.setPos(current_x - rect_text.width() / 2, top_y - 20)
            else:
                self.current_time_line.setVisible(False)
                self.current_time_text.setVisible(False)

    def wheelEvent(self, event):
        y_delta = event.angleDelta().y()
        if y_delta == 0:
            return

        zoom_in_factor = 1.15
        zoom_out_factor = 1.0 / zoom_in_factor

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        if y_delta > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)
        self.update_floating_axes()
        self.update_lod()

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self.update_floating_axes()

    def update_floating_axes(self):
        if not hasattr(self, 'station_texts') or not self.station_texts:
            return

        target_scene_x = self.mapToScene(5, 0).x()
        target_scene_x = max(5.0, target_scene_x)

        for text_item in self.station_texts:
            orig_y = text_item.data(1)
            text_item.setPos(target_scene_x, orig_y)

        target_text_scene_y = self.mapToScene(0, 10).y()
        target_text_scene_y = max(10.0, target_text_scene_y)

        for text_item in self.time_texts:
            orig_x = text_item.data(1)
            text_item.setPos(orig_x, target_text_scene_y)

        target_line_scene_y = self.mapToScene(0, 35).y()
        target_line_scene_y = max(35.0, target_line_scene_y)

        if self.time_axis_main_line:
            line = self.time_axis_main_line.line()
            self.time_axis_main_line.setLine(line.x1(), target_line_scene_y, line.x2(), target_line_scene_y)

        for tick_item, orig_x, dy1, dy2 in self.time_ticks:
            tick_item.setLine(orig_x, target_line_scene_y + dy1, orig_x, target_line_scene_y + dy2)

        if hasattr(self, 'current_time_text') and self.current_time_text:
            orig_x = self.current_time_text.x()
            self.current_time_text.setPos(orig_x, target_line_scene_y - 20)

        if hasattr(self, 'current_time_line') and self.current_time_line:
            line = self.current_time_line.line()
            self.current_time_line.setLine(line.x1(), target_line_scene_y, line.x2(), line.y2())

        # 更新班计划文字
        if hasattr(self, 'shift_info_text') and self.shift_info_text:
            curr_hour = self.simulated_current_time.hour()
            if 18 <= curr_hour or curr_hour < 6:
                shift_str = "第1班"
            else:
                shift_str = "第2班"
            self.shift_info_text.setText(f"{self.base_date}  {shift_str}")

            shift_x = self.mapToScene(10, 0).x()
            shift_y = self.mapToScene(0, 45).y()
            self.shift_info_text.setPos(shift_x, shift_y)

    def update_lod(self):
        if not hasattr(self, 'minute_items'):
            return
        scale = self.transform().m11()
        show_minutes = (scale >= 0.75)

        for item_obj, is_important in self.minute_items:
            if is_important:
                item_obj.setVisible(True)
            else:
                item_obj.setVisible(show_minutes)

    def highlight_and_locate_train(self, train_num):
        found_line = None
        if self.controller and hasattr(self.controller, 'plan_lines'):
            for line in self.controller.plan_lines:
                if line.train_number == train_num:
                    found_line = line
                    break

        if not found_line:
            self.highlighted_line = None
            self.update_lines()
            return False

        self.highlighted_line = found_line
        self.update_lines()

        for item in self.train_line_items:
            if isinstance(item, QGraphicsPathItem) and item.data(0) == found_line:
                self.centerOn(item.boundingRect().center())
                break
        return True

    def update_scene_rect(self):
        view_width = self.viewport().width()
        view_height = self.viewport().height()
        if view_width <= 0 or view_height <= 0:
            view_width = 1000
            view_height = 600

        # 将宽度放大 24/5 倍，使得视口默认显示约 5 小时的宽度，并生成滚动条
        total_width = view_width * (24.0 / 5.0)
        self.scene.setSceneRect(0, 0, total_width, view_height)

    def resizeEvent(self, event):
        self.update_scene_rect()
        self.draw_background_grid()
        self.update_lines()
        if self.controller: self.controller.detect_and_draw_conflicts()
        super().resizeEvent(event)

    def set_stations(self, stations):
        self.stations = stations
        self.draw_background_grid()

    def draw_background_grid(self):
        self.scene.clear()
        self.train_line_items.clear()
        self.conflict_items.clear()

        self.station_texts = []
        self.time_texts = []
        self.time_ticks = []
        self.minute_items = []

        if not self.stations:
            return

        rect = self.scene.sceneRect()
        width = rect.width()
        height = rect.height()
        plot_left = self.left_margin
        plot_right = width - self.right_margin
        plot_top = self.top_margin
        plot_bottom = height - self.bottom_margin
        plot_width = plot_right - plot_left
        plot_height = plot_bottom - plot_top

        time_axis_y = 35

        current_x = self.time_to_x(self.simulated_current_time)
        if current_x is not None:
            current_x_bounded = max(plot_left, min(current_x, plot_right))
            past_rect = QRectF(plot_left, plot_top, current_x_bounded - plot_left, plot_height)
            self.past_bg_rect = self.scene.addRect(past_rect, QPen(Qt.NoPen), QBrush(QColor(240, 240, 240)))
            self.past_bg_rect.setZValue(-1)

            future_rect = QRectF(current_x_bounded, plot_top, plot_right - current_x_bounded, plot_height)
            self.future_bg_rect = self.scene.addRect(future_rect, QPen(Qt.NoPen), QBrush(QColor(255, 255, 255)))
            self.future_bg_rect.setZValue(-1)

        n = len(self.stations)
        step_y = plot_height / (n - 1) if n > 1 else 0
        for i, station in enumerate(self.stations):
            y = plot_top + i * step_y
            station.y_coord = int(y)

        pen_h = QPen(QColor(180, 180, 180), 1, Qt.SolidLine)
        for station in self.stations:
            line = self.scene.addLine(plot_left, station.y_coord, plot_right, station.y_coord, pen_h)
            line.setZValue(1)

        total_minutes = self.max_minutes - self.min_minutes
        pen_10min = QPen(QColor(220, 220, 220), 1, Qt.SolidLine)
        pen_30min = QPen(QColor(180, 180, 180), 1, Qt.DashLine)
        pen_hour = QPen(QColor(120, 120, 120), 2, Qt.SolidLine)

        self.time_axis_main_line = self.scene.addLine(plot_left, time_axis_y, plot_right, time_axis_y, pen_hour)
        self.time_axis_main_line.setZValue(25)

        for minutes in range(self.min_minutes, self.max_minutes + 1, 10):
            x = plot_left + ((minutes - self.min_minutes) / total_minutes) * plot_width
            if minutes % 60 == 0:
                tick = self.scene.addLine(x, time_axis_y - 8, x, time_axis_y, pen_hour)
                tick.setZValue(25)
                self.time_ticks.append((tick, x, -8, 0))
                self.scene.addLine(x, plot_top, x, plot_bottom, pen_hour).setZValue(1)
            elif minutes % 30 == 0:
                tick = self.scene.addLine(x, time_axis_y - 5, x, time_axis_y, pen_hour)
                tick.setZValue(25)
                self.time_ticks.append((tick, x, -5, 0))
                self.scene.addLine(x, plot_top, x, plot_bottom, pen_30min).setZValue(1)
            else:
                tick = self.scene.addLine(x, time_axis_y - 3, x, time_axis_y, pen_10min)
                tick.setZValue(25)
                self.time_ticks.append((tick, x, -3, 0))
                self.scene.addLine(x, plot_top, x, plot_bottom, pen_10min).setZValue(1)

        if current_x is not None and plot_left <= current_x <= plot_right:
            pen_current_time = QPen(QColor(0, 0, 255), 2, Qt.SolidLine)
            self.current_time_line = self.scene.addLine(current_x, time_axis_y, current_x, plot_bottom,
                                                        pen_current_time)
            self.current_time_line.setZValue(25)

            self.current_time_text = QGraphicsSimpleTextItem(self.simulated_current_time.toString("HH:mm"))
            self.current_time_text.setFont(QFont("Arial", 10, QFont.Bold))
            self.current_time_text.setBrush(QBrush(QColor(0, 0, 255)))
            rect_text = self.current_time_text.boundingRect()
            self.current_time_text.setPos(current_x - rect_text.width() / 2, time_axis_y - 20)
            self.current_time_text.setZValue(30)
            self.current_time_text.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
            self.scene.addItem(self.current_time_text)

        font_station = QFont("Arial", 9)
        for station in self.stations:
            text = QGraphicsSimpleTextItem(station.name)
            text.setFont(font_station)
            orig_x = plot_left - 65
            orig_y = station.y_coord - 10
            text.setPos(orig_x, orig_y)
            text.setData(1, orig_y)
            text.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
            text.setZValue(30)
            self.scene.addItem(text)
            self.station_texts.append(text)

        font_time_large = QFont("Arial", 10, QFont.Bold)
        start_hour = int(self.min_minutes / 60)
        end_hour = int(self.max_minutes / 60)

        for hour in range(start_hour, end_hour + 1):
            x = plot_left + ((hour * 60 - self.min_minutes) / total_minutes) * plot_width
            display_hour = hour % 24
            text_top = QGraphicsSimpleTextItem(f"{display_hour:02d}:00")
            text_top.setFont(font_time_large)
            rect_top = text_top.boundingRect()
            orig_x = x - rect_top.width() / 2
            orig_y = time_axis_y - 25
            text_top.setPos(orig_x, orig_y)
            text_top.setData(1, orig_x)
            text_top.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
            text_top.setZValue(30)
            self.scene.addItem(text_top)
            self.time_texts.append(text_top)

        self.shift_info_text = QGraphicsSimpleTextItem("")
        self.shift_info_text.setFont(QFont("Arial", 11, QFont.Bold))
        self.shift_info_text.setBrush(QBrush(QColor(0, 100, 200)))
        self.shift_info_text.setZValue(50)
        self.shift_info_text.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        self.scene.addItem(self.shift_info_text)

        self.update_floating_axes()

    def update_lines(self):
        for item in self.train_line_items:
            self.scene.removeItem(item)
        self.train_line_items.clear()

        if not hasattr(self, 'minute_items'):
            self.minute_items = []
        self.minute_items.clear()

        if not self.controller: return

        if self.show_plan_lines and hasattr(self.controller, 'plan_lines'):
            self.draw_train_lines(self.controller.plan_lines, is_actual=False)

        if self.show_actual_lines and hasattr(self.controller, 'actual_lines'):
            self.draw_actual_lines(self.controller.actual_lines)

        self.update_lod()

    def draw_train_lines(self, train_lines, is_actual=False):
        for idx, line_data in enumerate(train_lines):
            line_data.handles = []

            is_selected = (line_data == getattr(self, 'selected_line', None))
            is_highlighted = (line_data == getattr(self, 'highlighted_line', None))
            is_important = is_selected or is_highlighted

            if is_highlighted:
                base_color = QColor(255, 0, 0)
                adj_color = None
                adj_station = None
                pen_width = 4
                z_line = 10
                z_text = 11
            else:
                base_color = getattr(line_data, 'color', QColor(255, 0, 0))
                # 提取智能调整的高亮蓝以及分割触发站
                adj_color = getattr(line_data, 'adjusted_color', None)
                adj_station = getattr(line_data, 'adjusted_from_station', None)

                pen_width = 3 if is_selected else 1
                z_line = 5 if is_selected else 3
                z_text = 6 if is_selected else 4

            pen_normal = QPen(base_color, pen_width, Qt.SolidLine)
            pen_adj = QPen(adj_color, pen_width, Qt.SolidLine) if adj_color else None

            path_normal = QPainterPath()
            path_adj = QPainterPath()

            current_path = path_normal
            current_color = base_color

            first_point_drawn = False
            start_coord = None
            end_coord = None
            origin_color = base_color

            valid_points = [p for p in line_data.points if p.planned_arrival or p.planned_departure]
            if len(valid_points) < 2:
                continue

            first_y = self.station_id_to_y(valid_points[0].station_id)
            last_y = self.station_id_to_y(valid_points[-1].station_id)
            if first_y is None or last_y is None:
                continue

            is_down_train = line_data.direction == "DOWN"

            prev_x = None
            prev_y = None
            prev_min_dep = None

            for i, point in enumerate(valid_points):
                y = self.station_id_to_y(point.station_id)
                if y is None:
                    continue

                t_arr = point.planned_arrival
                t_dep = point.planned_departure
                x_arr = self.time_to_x(t_arr)
                x_dep = self.time_to_x(t_dep)

                if x_arr is None and x_dep is None: continue
                if x_arr is None: x_arr = x_dep
                if x_dep is None: x_dep = x_arr

                min_arr = t_arr.hour() * 60 + t_arr.minute() if t_arr else None
                min_dep = t_dep.hour() * 60 + t_dep.minute() if t_dep else None
                if min_arr is None: min_arr = min_dep
                if min_dep is None: min_dep = min_arr

                is_start = (i == 0)
                is_end = (i == len(valid_points) - 1)

                if not first_point_drawn:
                    # 如果一开始就是调整站，直接换蓝色画笔
                    if adj_station and point.station_id == adj_station:
                        current_path = path_adj
                        current_color = adj_color
                    origin_color = current_color

                    current_path.moveTo(x_dep, y)
                    start_coord = (x_dep, y)
                    first_point_drawn = True
                else:
                    min_y = min(prev_y, y)
                    max_y = max(prev_y, y)
                    for station in self.stations:
                        sy = station.y_coord
                        if min_y < sy < max_y:
                            ratio = (sy - prev_y) / (y - prev_y)
                            sx = prev_x + ratio * (x_arr - prev_x)

                            if is_selected:
                                handle_size = 6
                                rect_pass = QRectF(sx - handle_size / 2, sy - handle_size / 2, handle_size, handle_size)
                                item_pass = self.scene.addRect(rect_pass, QPen(Qt.black, 1), QBrush(Qt.white))
                                item_pass.setZValue(z_line + 1)
                                item_pass.setData(0, line_data)
                                self.train_line_items.append(item_pass)

                                s_min_rounded = int(round(prev_min_dep + ratio * (min_arr - prev_min_dep)))
                                s_time = QTime((s_min_rounded // 60) % 24, s_min_rounded % 60)
                                line_data.handles.append({
                                    'type': 'pass', 'x': sx, 'y': sy,
                                    'station_id': station.id, 'point_ref': None, 'time': s_time
                                })

                            digit = str(int(round(prev_min_dep + ratio * (min_arr - prev_min_dep))) % 10)
                            font_digit = QFont("Arial", 7)
                            text_digit = QGraphicsSimpleTextItem(digit)
                            text_digit.setFont(font_digit)
                            # 这里动态使用 current_color，使其跟随当前区段颜色
                            text_digit.setBrush(QBrush(current_color))
                            text_digit.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
                            text_digit.setPos(sx + 2, sy - 14 if is_down_train else sy + 2)
                            text_digit.setZValue(z_text)
                            self.scene.addItem(text_digit)
                            self.train_line_items.append(text_digit)
                            self.minute_items.append((text_digit, is_important))

                    # 连线到到达点
                    current_path.lineTo(x_arr, y)

                    # 核心切割逻辑：如果该站是调整触发站，从到达点后开始换新的蓝色画笔
                    if adj_station and point.station_id == adj_station:
                        current_path = path_adj
                        current_color = adj_color
                        current_path.moveTo(x_arr, y)

                    if x_arr != x_dep:
                        current_path.lineTo(x_dep, y)

                if i == len(valid_points) - 1:
                    end_coord = (x_arr, y)

                if is_selected:
                    handle_size = 6
                    if t_arr and not is_start:
                        rect_arr = QRectF(x_arr - handle_size / 2, y - handle_size / 2, handle_size, handle_size)
                        item_arr = self.scene.addRect(rect_arr, QPen(Qt.black, 1), QBrush(Qt.white))
                        item_arr.setZValue(z_line + 1)
                        item_arr.setData(0, line_data)
                        self.train_line_items.append(item_arr)
                        line_data.handles.append(
                            {'type': 'arr', 'x': x_arr, 'y': y, 'station_id': point.station_id, 'point_ref': point,
                             'time': t_arr})

                    if t_dep and not is_end:
                        if x_arr == x_dep and not is_start:
                            if len(line_data.handles) > 0:
                                line_data.handles[-1]['type'] = 'pass'
                        else:
                            rect_dep = QRectF(x_dep - handle_size / 2, y - handle_size / 2, handle_size, handle_size)
                            item_dep = self.scene.addRect(rect_dep, QPen(Qt.black, 1), QBrush(Qt.white))
                            item_dep.setZValue(z_line + 1)
                            item_dep.setData(0, line_data)
                            self.train_line_items.append(item_dep)
                            line_data.handles.append(
                                {'type': 'dep', 'x': x_dep, 'y': y, 'station_id': point.station_id, 'point_ref': point,
                                 'time': t_dep})

                is_passing = (x_arr == x_dep)
                font_digit = QFont("Arial", 7)
                if is_passing:
                    if t_arr:
                        digit = str(t_arr.minute() % 10)
                        text_digit = QGraphicsSimpleTextItem(digit)
                        text_digit.setFont(font_digit)
                        text_digit.setBrush(QBrush(current_color))
                        text_digit.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
                        text_digit.setPos(x_arr + 2, y - 14 if is_down_train else y + 2)
                        text_digit.setZValue(z_text)
                        self.scene.addItem(text_digit)
                        self.train_line_items.append(text_digit)
                        self.minute_items.append((text_digit, is_important))
                else:
                    if t_arr:
                        arr_digit = str(t_arr.minute() % 10)
                        text_arr = QGraphicsSimpleTextItem(arr_digit)
                        text_arr.setFont(font_digit)
                        text_arr.setBrush(QBrush(current_color))
                        text_arr.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
                        text_arr.setPos(x_arr + 2, y - 14 if is_down_train else y + 2)
                        text_arr.setZValue(z_text)
                        self.scene.addItem(text_arr)
                        self.train_line_items.append(text_arr)
                        self.minute_items.append((text_arr, is_important))
                    if t_dep:
                        dep_digit = str(t_dep.minute() % 10)
                        text_dep = QGraphicsSimpleTextItem(dep_digit)
                        text_dep.setFont(font_digit)
                        text_dep.setBrush(QBrush(current_color))
                        text_dep.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
                        text_dep.setPos(x_dep - 8, y + 2 if is_down_train else y - 14)
                        text_dep.setZValue(z_text)
                        self.scene.addItem(text_dep)
                        self.train_line_items.append(text_dep)
                        self.minute_items.append((text_dep, is_important))

                prev_x = x_dep
                prev_y = y
                prev_min_dep = min_dep

            # 遍历结束，根据切割情况分别绘制前/后段
            if not path_normal.isEmpty():
                path_item1 = self.scene.addPath(path_normal, pen_normal)
                path_item1.setZValue(z_line)
                path_item1.setData(0, line_data)
                self.train_line_items.append(path_item1)

            if path_adj and not path_adj.isEmpty() and pen_adj:
                path_item2 = self.scene.addPath(path_adj, pen_adj)
                path_item2.setZValue(z_line)
                path_item2.setData(0, line_data)
                self.train_line_items.append(path_item2)

            # 绘制始发/终点信息（两端可能颜色不同，分别读取 origin_color 和 current_color）
            if start_coord and end_coord:
                if is_down_train:
                    origin_coord = start_coord
                    dest_coord = end_coord
                    dy_origin = -8
                    dy_dest = 10
                    arrow_sign = 1
                    y_offset_text = -22
                else:
                    origin_coord = end_coord
                    dest_coord = start_coord
                    dy_origin = 8
                    dy_dest = -10
                    arrow_sign = -1
                    y_offset_text = 10

                cx, cy = origin_coord
                t_width = 12 if is_important else 10
                pen_orig = QPen(origin_color, pen_width, Qt.SolidLine)
                v_line1 = self.scene.addLine(cx, cy, cx, cy + dy_origin, pen_orig)
                v_line1.setZValue(z_line)
                v_line1.setData(0, line_data)
                self.train_line_items.append(v_line1)

                t_line = self.scene.addLine(cx - t_width / 2, cy + dy_origin, cx + t_width / 2, cy + dy_origin,
                                            QPen(origin_color, pen_width + 1, Qt.SolidLine))
                t_line.setZValue(z_line + 1)
                t_line.setData(0, line_data)
                self.train_line_items.append(t_line)

                text = QGraphicsSimpleTextItem(line_data.train_number)
                font = QFont("Arial", 8, QFont.Bold)
                if is_important: font.setPointSize(9)
                text.setFont(font)
                text.setBrush(QBrush(origin_color))
                text.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)

                rect_text = text.boundingRect()
                text.setPos(cx - rect_text.width() / 2, cy + y_offset_text)
                text.setZValue(z_text)
                text.setData(0, line_data)
                self.scene.addItem(text)
                self.train_line_items.append(text)

                ex, ey = dest_coord
                arrow_size = 10 if is_important else 8
                pen_dest = QPen(current_color, pen_width, Qt.SolidLine)
                v_line2 = self.scene.addLine(ex, ey, ex, ey + dy_dest, pen_dest)
                v_line2.setZValue(z_line)
                v_line2.setData(0, line_data)
                self.train_line_items.append(v_line2)

                arrow_path = QPainterPath()
                tip_y = ey + dy_dest
                if arrow_sign == 1:
                    arrow_path.moveTo(ex, tip_y)
                    arrow_path.lineTo(ex - arrow_size / 2, tip_y - arrow_size)
                    arrow_path.lineTo(ex + arrow_size / 2, tip_y - arrow_size)
                else:
                    arrow_path.moveTo(ex, tip_y)
                    arrow_path.lineTo(ex - arrow_size / 2, tip_y + arrow_size)
                    arrow_path.lineTo(ex + arrow_size / 2, tip_y + arrow_size)
                arrow_path.closeSubpath()

                arrow_item = self.scene.addPath(arrow_path, QPen(current_color, 1),
                                                QBrush(Qt.white if not is_important else current_color))
                arrow_item.setZValue(z_line + 1)
                arrow_item.setData(0, line_data)
                self.train_line_items.append(arrow_item)

    def draw_actual_lines(self, train_lines):
        line_pen = QPen(QColor(220, 20, 20), 4, Qt.SolidLine)
        base_color = QColor(220, 20, 20)

        for idx, line_data in enumerate(train_lines):
            path = QPainterPath()
            first_point_drawn = False
            start_coord = None
            end_coord = None

            valid_actual_points = [p for p in line_data.points if p.actual_arrival or p.actual_departure]
            if not valid_actual_points:
                continue

            first_y = self.station_id_to_y(valid_actual_points[0].station_id)
            last_y = self.station_id_to_y(valid_actual_points[-1].station_id)
            if first_y is None or last_y is None:
                continue

            is_down_train = line_data.direction == "DOWN"

            for point in valid_actual_points:
                y = self.station_id_to_y(point.station_id)
                if y is None: continue

                act_arr_obj = getattr(point, 'actual_arrival', None)
                act_dep_obj = getattr(point, 'actual_departure', None)

                x_arr = self.time_to_x(act_arr_obj)
                x_dep = self.time_to_x(act_dep_obj)

                if x_arr is None and x_dep is None:
                    continue

                if x_arr is None: x_arr = x_dep
                if x_dep is None: x_dep = x_arr

                if not first_point_drawn:
                    path.moveTo(x_dep, y)
                    start_coord = (x_dep, y)
                    first_point_drawn = True
                else:
                    path.lineTo(x_arr, y)
                    if x_arr != x_dep:
                        path.lineTo(x_dep, y)

                if act_arr_obj and not act_dep_obj:
                    end_coord = (x_arr, y)
                else:
                    end_coord = None

            if not path.isEmpty():
                path_item = self.scene.addPath(path, line_pen)
                path_item.setZValue(5)
                self.train_line_items.append(path_item)

                if start_coord and end_coord:
                    if is_down_train:
                        origin_coord = start_coord
                        dest_coord = end_coord
                        dy_origin = -8
                        dy_dest = 10
                        arrow_sign = 1
                        y_offset_text = -22
                    else:
                        origin_coord = end_coord
                        dest_coord = start_coord
                        dy_origin = 8
                        dy_dest = -10
                        arrow_sign = -1
                        y_offset_text = 10

                    cx, cy = origin_coord
                    t_width = 10
                    v_line1 = self.scene.addLine(cx, cy, cx, cy + dy_origin, line_pen)
                    v_line1.setZValue(5)
                    self.train_line_items.append(v_line1)

                    t_line = self.scene.addLine(cx - t_width / 2, cy + dy_origin, cx + t_width / 2, cy + dy_origin,
                                                QPen(base_color, 2, Qt.SolidLine))
                    t_line.setZValue(5)
                    self.train_line_items.append(t_line)

                    text = QGraphicsSimpleTextItem(line_data.train_number)
                    font = QFont("Arial", 8, QFont.Bold)
                    text.setFont(font)
                    text.setBrush(QBrush(base_color))
                    text.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)

                    rect_text = text.boundingRect()
                    text.setPos(cx - rect_text.width() / 2, cy + y_offset_text)
                    text.setZValue(6)
                    self.train_line_items.append(text)

                    ex, ey = dest_coord
                    arrow_size = 8
                    v_line2 = self.scene.addLine(ex, ey, ex, ey + dy_dest, line_pen)
                    v_line2.setZValue(5)
                    self.train_line_items.append(v_line2)

                    arrow_path = QPainterPath()
                    tip_y = ey + dy_dest
                    if arrow_sign == 1:
                        arrow_path.moveTo(ex, tip_y)
                        arrow_path.lineTo(ex - arrow_size / 2, tip_y - arrow_size)
                        arrow_path.lineTo(ex + arrow_size / 2, tip_y - arrow_size)
                    else:
                        arrow_path.moveTo(ex, tip_y)
                        arrow_path.lineTo(ex - arrow_size / 2, tip_y + arrow_size)
                        arrow_path.lineTo(ex + arrow_size / 2, tip_y + arrow_size)
                    arrow_path.closeSubpath()

                    arrow_item = self.scene.addPath(arrow_path, QPen(base_color, 1), QBrush(base_color))
                    arrow_item.setZValue(6)
                    self.train_line_items.append(arrow_item)

    def draw_conflicts(self, conflicts):
        for item in self.conflict_items:
            self.scene.removeItem(item)
        self.conflict_items.clear()

        for c in conflicts:
            x = self.time_to_x(c['time'])
            y = self.station_id_to_y(c['station_id'])
            if x is None or y is None: continue

            radius = 12
            rect = QRectF(x - radius, y - radius, radius * 2, radius * 2)
            circle = self.scene.addEllipse(rect, QPen(QColor(255, 0, 0), 3, Qt.SolidLine), QBrush(Qt.transparent))
            circle.setZValue(10)
            self.conflict_items.append(circle)

            text = QGraphicsSimpleTextItem("冲突: " + c['msg'])
            text.setFont(QFont("Arial", 9, QFont.Bold))
            text.setBrush(QBrush(QColor(255, 0, 0)))
            text.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
            text.setPos(x + 14, y - 25)
            text.setZValue(10)
            self.conflict_items.append(text)

    def contextMenuEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        items = self.scene.items(scene_pos)

        clicked_line = None
        for item in items:
            if item.data(0) is not None:
                clicked_line = item.data(0)
                break

        menu = QMenu(self)

        if clicked_line:
            self.selected_line = clicked_line
            self.update_lines()

            click_y = scene_pos.y()
            min_dist = float('inf')
            closest_station_id = None

            target_plan_line = clicked_line
            if self.controller and hasattr(self.controller, 'plan_lines'):
                target_plan_line = next(
                    (l for l in self.controller.plan_lines if l.train_number == clicked_line.train_number),
                    clicked_line)

            for p in target_plan_line.points:
                sy = self.station_id_to_y(p.station_id)
                if sy is not None and abs(sy - click_y) < min_dist:
                    min_dist = abs(sy - click_y)
                    closest_station_id = p.station_id

            action_param = None
            action_track = None
            action_report = None

            if min_dist < 30 and closest_station_id:
                action_report = menu.addAction("人工报点...")
                menu.addSeparator()

                action_param = menu.addAction("修改计划线参数...")
                action_track = menu.addAction("修改接发车股道...")
            else:
                action_param = menu.addAction("修改计划线参数...")
                action_track = menu.addAction("修改接发车股道...")

            action_train_num = menu.addAction("修改车次号...")
            action_prop = menu.addAction("修改全线时刻表...")

            menu.addSeparator()
            action_delete = menu.addAction("删除该列车线")

            action = menu.exec_(event.globalPos())
            if action_report and action == action_report:
                if self.controller and hasattr(self.controller, 'open_manual_report_dialog'):
                    self.controller.open_manual_report_dialog(target_plan_line, closest_station_id)
            elif action == action_param:
                if self.controller and hasattr(self.controller, 'open_plan_line_param_dialog'):
                    self.controller.open_plan_line_param_dialog(target_plan_line, closest_station_id)
            elif action == action_track:
                if self.controller and hasattr(self.controller, 'open_modify_track_dialog'):
                    self.controller.open_modify_track_dialog(target_plan_line, closest_station_id)
            elif action == action_train_num:
                if self.controller and hasattr(self.controller, 'open_modify_train_num_dialog'):
                    self.controller.open_modify_train_num_dialog(target_plan_line)
            elif action == action_prop:
                if self.controller and hasattr(self.controller, 'open_train_property_dialog'):
                    self.controller.open_train_property_dialog(target_plan_line)
            elif action == action_delete:
                if self.controller and hasattr(self.controller, 'on_delete_specific'):
                    self.controller.on_delete_specific(target_plan_line)
        else:
            action_add = menu.addAction("加开列车...")
            action = menu.exec_(event.globalPos())
            if action == action_add:
                if self.controller and hasattr(self.controller, 'on_add_train'):
                    self.controller.on_add_train()

    def mousePressEvent(self, event):
        if self.highlighted_line:
            self.highlighted_line = None

        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            items = self.scene.items(scene_pos)

            clicked_line = None
            for item in items:
                if item.data(0) is not None:
                    clicked_line = item.data(0)
                    break

            if clicked_line:
                self.selected_line = clicked_line
                click_x = scene_pos.x()
                click_y = scene_pos.y()

                min_dist = float('inf')
                best_handle = None

                if hasattr(clicked_line, 'handles'):
                    for handle in clicked_line.handles:
                        dist = ((handle['x'] - click_x) ** 2 + (handle['y'] - click_y) ** 2) ** 0.5
                        if dist < min_dist:
                            min_dist = dist
                            best_handle = handle

                if min_dist < 15 and best_handle:
                    # ============ 时间锁拦截逻辑 ============
                    handle_time = best_handle['time']
                    curr_time = self.simulated_current_time

                    h_mins = handle_time.hour() * 60 + handle_time.minute()
                    c_mins = curr_time.hour() * 60 + curr_time.minute()
                    if h_mins < 1080: h_mins += 1440
                    if c_mins < 1080: c_mins += 1440

                    if h_mins <= c_mins:
                        QMessageBox.warning(self, "操作违规",
                                            "当前时刻之前的运行线已锁定，不可修改！")
                        self.dragged_point_idx = None
                        self.setCursor(Qt.ArrowCursor)
                        return
                    # ========================================

                    if best_handle['point_ref'] is None:
                        from models.train_line import TrainLinePoint
                        new_p = TrainLinePoint(best_handle['station_id'], best_handle['time'], best_handle['time'])
                        clicked_line.points.append(new_p)

                        order_map = {s.id: i for i, s in enumerate(self.stations)}
                        clicked_line.points.sort(key=lambda p: order_map.get(p.station_id, 0))

                        best_handle['point_ref'] = new_p

                    self.dragged_point_idx = clicked_line.points.index(best_handle['point_ref'])
                    self.dragged_handle_type = best_handle['type']
                    self.last_scene_x = click_x
                    self.accumulated_delta_x = 0.0
                    self.setCursor(Qt.SizeHorCursor)
                else:
                    self.dragged_point_idx = None
            else:
                self.selected_line = None
                self.dragged_point_idx = None
                self.setCursor(Qt.ArrowCursor)

            self.update_lines()
            if self.controller: self.controller.detect_and_draw_conflicts()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.selected_line and self.dragged_point_idx is not None and self.last_scene_x is not None:
            scene_pos = self.mapToScene(event.pos())
            current_x = scene_pos.x()

            delta_x = current_x - self.last_scene_x
            self.accumulated_delta_x += delta_x

            rect = self.scene.sceneRect()
            plot_width = rect.width() - self.left_margin - self.right_margin
            total_minutes = self.max_minutes - self.min_minutes

            if plot_width > 0:
                minutes_to_shift = int((self.accumulated_delta_x / plot_width) * total_minutes)

                if minutes_to_shift != 0:
                    self.selected_line.shift_downstream(self.dragged_point_idx, minutes_to_shift,
                                                        self.dragged_handle_type)
                    shifted_pixels = (minutes_to_shift / total_minutes) * plot_width
                    self.accumulated_delta_x -= shifted_pixels
                    self.update_lines()
                    if self.controller: self.controller.detect_and_draw_conflicts()

            self.last_scene_x = current_x

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.selected_line:
                self.last_scene_x = None
                self.dragged_point_idx = None
                self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            items = self.scene.items(scene_pos)

            clicked_line = None
            for item in items:
                if item.data(0) is not None:
                    clicked_line = item.data(0)
                    break

            if clicked_line:
                if self.controller and hasattr(self.controller, 'open_train_property_dialog'):
                    self.controller.open_train_property_dialog(clicked_line)

        super().mouseDoubleClickEvent(event)

    def time_to_x(self, time):
        if time is None: return None
        minutes = time.hour() * 60 + time.minute()

        # 处理跨越零点
        if minutes < 1080:
            minutes += 1440

        rect = self.scene.sceneRect()
        plot_left = self.left_margin
        plot_right = rect.width() - self.right_margin
        plot_width = plot_right - plot_left
        x = plot_left + ((minutes - self.min_minutes) / (self.max_minutes - self.min_minutes)) * plot_width
        return int(x)

    def station_id_to_y(self, station_id):
        for station in self.stations:
            if station.id == station_id: return station.y_coord
        return None