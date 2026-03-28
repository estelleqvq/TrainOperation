# models/database.py
import pymysql
from PyQt5.QtCore import QTime

from config import PLAN_DB_CONFIG, ACTUAL_DB_CONFIG
from models.station import Station
from models.train_line import TrainLine, TrainLinePoint


def get_all_stations(db_mode='actual'):
    config = PLAN_DB_CONFIG if db_mode == 'plan' else ACTUAL_DB_CONFIG
    connection = pymysql.connect(**config)
    try:
        with connection.cursor() as cursor:
            sql = "SELECT id, name, display_order, tracks FROM stations ORDER BY display_order"
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [Station(row[0], row[1], row[2], row[3]) for row in rows]
    finally:
        connection.close()


def get_section_times(db_mode='actual'):
    """获取区间运行时分 (算法调整底座)"""
    config = PLAN_DB_CONFIG if db_mode == 'plan' else ACTUAL_DB_CONFIG
    connection = pymysql.connect(**config)
    try:
        with connection.cursor() as cursor:
            sql = "SELECT from_station_id, to_station_id, up_minutes, down_minutes FROM section_times"
            cursor.execute(sql)
            rows = cursor.fetchall()
            times = {}
            for row in rows:
                times[(row[0], row[1])] = row[2]  # 目前上下行时分相同，暂存 up_minutes
            return times
    finally:
        connection.close()


def load_plans_from_db(db_mode='actual'):
    """联表查询获取所有列车和时刻数据"""
    config = PLAN_DB_CONFIG if db_mode == 'plan' else ACTUAL_DB_CONFIG
    connection = pymysql.connect(**config)
    lines = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, train_number, direction, run_date FROM trains")
            trains_data = cursor.fetchall()

            for t_id, t_num, t_dir, t_date in trains_data:
                cursor.execute("""
                    SELECT station_id, track, planned_arrival, planned_departure, actual_arrival, actual_departure 
                    FROM train_stops WHERE train_id = %s ORDER BY id
                """, (t_id,))
                stops_data = cursor.fetchall()

                points = []
                for s_id, track, p_arr, p_dep, a_arr, a_dep in stops_data:
                    # MySQL 返回的 TIME 类型是 timedelta，需安全转换为 QTime
                    p_arr_qt = QTime(p_arr.seconds // 3600, (p_arr.seconds // 60) % 60) if p_arr else None
                    p_dep_qt = QTime(p_dep.seconds // 3600, (p_dep.seconds // 60) % 60) if p_dep else None
                    point = TrainLinePoint(s_id, p_arr_qt, p_dep_qt, track)

                    if a_arr:
                        point.actual_arrival = QTime(a_arr.seconds // 3600, (a_arr.seconds // 60) % 60)
                    if a_dep:
                        point.actual_departure = QTime(a_dep.seconds // 3600, (a_dep.seconds // 60) % 60)

                    points.append(point)

                date_str = t_date.strftime("%Y-%m-%d") if hasattr(t_date, 'strftime') else str(t_date)
                lines.append(TrainLine(t_id, t_num, t_dir, date_str, points))
    finally:
        connection.close()
    return lines


def save_plan(line, db_mode='actual'):
    """级联保存：先存/更新 trains，再重写 train_stops"""
    config = PLAN_DB_CONFIG if db_mode == 'plan' else ACTUAL_DB_CONFIG
    connection = pymysql.connect(**config)
    try:
        with connection.cursor() as cursor:
            # 1. 保存主表
            if line.id is not None:
                cursor.execute("SELECT id FROM trains WHERE id=%s", (line.id,))
                if cursor.fetchone():
                    cursor.execute("UPDATE trains SET train_number=%s, direction=%s, run_date=%s WHERE id=%s",
                                   (line.train_number, line.direction, line.date, line.id))
                else:
                    line.id = None

            if line.id is None:
                cursor.execute("INSERT INTO trains (train_number, direction, run_date) VALUES (%s, %s, %s)",
                               (line.train_number, line.direction, line.date))
                line.id = cursor.lastrowid

            # 2. 保存子表 (最安全的策略：先删后插)
            cursor.execute("DELETE FROM train_stops WHERE train_id=%s", (line.id,))
            for p in line.points:
                p_arr = p.planned_arrival.toString("HH:mm") if p.planned_arrival else None
                p_dep = p.planned_departure.toString("HH:mm") if p.planned_departure else None
                a_arr_obj = getattr(p, 'actual_arrival', None)
                a_dep_obj = getattr(p, 'actual_departure', None)
                a_arr = a_arr_obj.toString("HH:mm") if a_arr_obj else None
                a_dep = a_dep_obj.toString("HH:mm") if a_dep_obj else None

                cursor.execute("""
                    INSERT INTO train_stops (train_id, station_id, track, planned_arrival, planned_departure, actual_arrival, actual_departure)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (line.id, p.station_id, p.track, p_arr, p_dep, a_arr, a_dep))
        connection.commit()
    finally:
        connection.close()


def delete_plan_from_db(plan_id, db_mode='actual'):
    if plan_id is None: return
    config = PLAN_DB_CONFIG if db_mode == 'plan' else ACTUAL_DB_CONFIG
    connection = pymysql.connect(**config)
    try:
        with connection.cursor() as cursor:
            # 外键级联删除
            cursor.execute("DELETE FROM trains WHERE id=%s", (plan_id,))
        connection.commit()
    finally:
        connection.close()


def save_manual_report(train_number, direction, date, station_id, track, act_arr, act_dep):
    """人工报点专用：仅向实际运行图数据库(ctc_actual_db)写入实点"""
    connection = pymysql.connect(**ACTUAL_DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 1. 如果实迹库里还没这趟车，先建档案
            cursor.execute("SELECT id FROM trains WHERE train_number=%s AND run_date=%s", (train_number, date))
            row = cursor.fetchone()
            if row:
                train_id = row[0]
            else:
                cursor.execute("INSERT INTO trains (train_number, direction, run_date) VALUES (%s, %s, %s)",
                               (train_number, direction, date))
                train_id = cursor.lastrowid

            # 2. 插入或更新该站的实迹时间
            cursor.execute("SELECT id FROM train_stops WHERE train_id=%s AND station_id=%s", (train_id, station_id))
            stop_row = cursor.fetchone()

            arr_str = act_arr.toString("HH:mm") if act_arr else None
            dep_str = act_dep.toString("HH:mm") if act_dep else None

            if stop_row:
                cursor.execute("UPDATE train_stops SET actual_arrival=%s, actual_departure=%s WHERE id=%s",
                               (arr_str, dep_str, stop_row[0]))
            else:
                cursor.execute("""
                    INSERT INTO train_stops (train_id, station_id, track, actual_arrival, actual_departure)
                    VALUES (%s, %s, %s, %s, %s)
                """, (train_id, station_id, track, arr_str, dep_str))
        connection.commit()
    finally:
        connection.close()