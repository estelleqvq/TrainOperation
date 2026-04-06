"""
CTC 列车运行图仿真程序 - 数据库双库重构及初始化脚本
"""
import pymysql
from config import PLAN_DB_CONFIG, ACTUAL_DB_CONFIG

STATIONS = [
    "北京南", "廊坊", "天津南", "沧州西", "德州东", "济南西", "泰安", "曲阜东",
    "滕州东", "枣庄", "徐州东", "宿州东", "蚌埠南", "定远", "滁州", "南京南",
    "镇江南", "丹阳北", "常州北", "无锡东", "苏州北", "昆山南", "上海虹桥"
]

SECTION_TIMES_RAW = [
    ("北京南", "廊坊", 16.33), ("廊坊", "天津南", 12.75), ("天津南", "沧州西", 17.85),
    ("沧州西", "德州东", 21.10), ("德州东", "济南西", 19.13), ("济南西", "泰安", 12.50),
    ("泰安", "曲阜东", 14.33), ("曲阜东", "滕州东", 11.38), ("滕州东", "枣庄", 7.33),
    ("枣庄", "徐州东", 13.13), ("徐州东", "宿州东", 13.77), ("宿州东", "蚌埠南", 17.83),
    ("蚌埠南", "定远", 11.03), ("定远", "滁州", 12.62), ("滁州", "南京南", 13.33),
    ("南京南", "镇江南", 14.50), ("镇江南", "丹阳北", 5.83), ("丹阳北", "常州北", 6.58),
    ("常州北", "无锡东", 11.67), ("无锡东", "苏州北", 5.47), ("苏州北", "昆山南", 6.40),
    ("昆山南", "上海虹桥", 12.12)
]
SECTION_TIMES = [(s, e, round(m)) for s, e, m in SECTION_TIMES_RAW]

def get_train_schedules():
    return {
        "G143": [("北京南", None, "08:00"), ("天津南", "08:24", "08:31"), ("济南西", "09:37", "09:39"), ("南京南", "11:55", "11:57"), ("常州北", "12:29", "12:31"), ("上海虹桥", "13:12", None)],
        "G107": [("北京南", None, "08:05"), ("德州东", "09:20", "09:22"), ("济南西", "09:46", "09:48"), ("枣庄", "10:38", "10:40"), ("徐州东", "10:58", "11:00"), ("南京南", "12:15", "12:18"), ("镇江南", "12:37", "12:43"), ("苏州北", "13:19", "13:21"), ("上海虹桥", "13:46", None)],
        "G111": [("北京南", None, "08:35"), ("德州东", "09:48", "09:50"), ("济南西", "10:14", "10:17"), ("泰安", "10:35", "10:40"), ("枣庄", "11:18", "11:20"), ("定远", "12:21", "12:23"), ("南京南", "12:54", "12:57"), ("丹阳北", "13:22", "13:24"), ("无锡东", "13:47", "13:49"), ("上海虹桥", "14:22", None)],
        "G113": [("北京南", None, "08:50"), ("廊坊", "09:11", "09:19"), ("沧州西", "09:55", "09:57"), ("济南西", "10:43", "10:47"), ("徐州东", "11:51", "11:53"), ("南京南", "13:07", "13:11"), ("苏州北", "14:03", "14:09"), ("上海虹桥", "14:33", None)],
        "G41": [("北京南", None, "09:15"), ("沧州西", "10:07", "10:09"), ("济南西", "10:55", "10:58"), ("泰安", "11:15", "11:17"), ("蚌埠南", "12:42", "12:47"), ("南京南", "13:29", "13:31"), ("常州北", "14:03", "14:08"), ("上海虹桥", "14:49", None)],
        "G115": [("北京南", None, "09:20"), ("天津南", "09:55", "09:57"), ("德州东", "10:41", "10:43"), ("济南西", "11:07", "11:09"), ("宿州东", "12:26", "12:38"),("南京南", "13:38", "13:41"), ("镇江南", "14:00", "14:02"), ("上海虹桥", "14:59", None)],
        "G117": [("北京南", None, "09:25"), ("天津南", "09:59", "10:10"), ("德州东", "10:54", "11:09"), ("济南西", "11:33", "11:38"), ("枣庄", "12:28", "12:30"), ("滁州", "13:44", "13:46"), ("南京南", "14:04", "14:08"), ("丹阳北", "14:34", "14:36"), ("苏州北", "15:05", "15:07"), ("昆山南", "15:18", "15:20"), ("上海虹桥", "15:37", None)],
        "G121": [("北京南", None, "10:20"), ("廊坊", "10:41", "10:45"), ("沧州西", "11:21", "11:24"), ("德州东", "11:51", "11:53"), ("济南西", "12:17", "12:29"), ("徐州东", "13:39", "13:42"), ("南京南", "14:56", "15:00"), ("无锡东", "15:46", "15:48"), ("苏州北", "15:58", "16:00"), ("上海虹桥", "16:25", None)],

    }

def create_database_if_not_exists(db_name):
    conn = pymysql.connect(host=PLAN_DB_CONFIG['host'], user=PLAN_DB_CONFIG['user'], password=PLAN_DB_CONFIG['password'], charset='utf8mb4')
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
    finally:
        conn.close()

def init_tables(config):
    conn = pymysql.connect(**config)
    try:
        with conn.cursor() as cursor:
            # 1. 车站表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(50) UNIQUE NOT NULL,
                    display_order INT NOT NULL,
                    tracks VARCHAR(100) DEFAULT '正线,1股,2股,3股,4股,5股'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            # 2. 区间运行时分表 (算法底座)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS section_times (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    from_station_id INT NOT NULL,
                    to_station_id INT NOT NULL,
                    up_minutes INT NOT NULL,
                    down_minutes INT NOT NULL,
                    FOREIGN KEY (from_station_id) REFERENCES stations(id),
                    FOREIGN KEY (to_station_id) REFERENCES stations(id),
                    UNIQUE KEY unique_section (from_station_id, to_station_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            # 3. 列车主表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trains (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    train_number VARCHAR(20) NOT NULL,
                    direction ENUM('UP','DOWN') NOT NULL,
                    run_date DATE NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            # 4. 列车停站子表 (严格关系型)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS train_stops (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    train_id INT NOT NULL,
                    station_id INT NOT NULL,
                    track VARCHAR(20) DEFAULT '正线',
                    planned_arrival TIME NULL,
                    planned_departure TIME NULL,
                    actual_arrival TIME NULL,
                    actual_departure TIME NULL,
                    FOREIGN KEY (train_id) REFERENCES trains(id) ON DELETE CASCADE,
                    FOREIGN KEY (station_id) REFERENCES stations(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # 插入车站数据
            for idx, name in enumerate(STATIONS):
                cursor.execute(
                    "INSERT INTO stations (name, display_order) VALUES (%s, %s) ON DUPLICATE KEY UPDATE display_order=VALUES(display_order)",
                    (name, idx)
                )

            # 插入区间时分数据
            cursor.execute("SELECT id, name FROM stations")
            station_id_map = {name: sid for sid, name in cursor.fetchall()}
            for from_station, to_station, minutes in SECTION_TIMES:
                from_id = station_id_map.get(from_station)
                to_id = station_id_map.get(to_station)
                if from_id and to_id:
                    cursor.execute("""
                        INSERT IGNORE INTO section_times (from_station_id, to_station_id, up_minutes, down_minutes)
                        VALUES (%s, %s, %s, %s)
                    """, (from_id, to_id, minutes, minutes))

        conn.commit()
    finally:
        conn.close()

def import_default_plans(config):
    conn = pymysql.connect(**config)
    try:
        with conn.cursor() as cursor:
            # 清空旧计划数据
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            cursor.execute("TRUNCATE TABLE train_stops")
            cursor.execute("TRUNCATE TABLE trains")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

            cursor.execute("SELECT id, name FROM stations")
            station_map = {name: sid for sid, name in cursor.fetchall()}

            schedules = get_train_schedules()
            for train_num, stops in schedules.items():
                cursor.execute(
                    "INSERT INTO trains (train_number, direction, run_date) VALUES (%s, %s, %s)",
                    (train_num, "DOWN", "2026-03-01")
                )
                train_id = cursor.lastrowid

                for station, arr, dep in stops:
                    s_id = station_map.get(station)
                    if s_id:
                        cursor.execute("""
                            INSERT INTO train_stops (train_id, station_id, track, planned_arrival, planned_departure) 
                            VALUES (%s, %s, %s, %s, %s)
                        """, (train_id, s_id, "正线", arr, dep))
        conn.commit()
        print(f"[{config['database']}] 底稿及字典数据导入成功！")
    finally:
        conn.close()

def main():
    print("开始重构双数据库架构 (包含区间运行时分表)...")
    create_database_if_not_exists(PLAN_DB_CONFIG['database'])
    create_database_if_not_exists(ACTUAL_DB_CONFIG['database'])

    init_tables(PLAN_DB_CONFIG)
    init_tables(ACTUAL_DB_CONFIG)

    import_default_plans(PLAN_DB_CONFIG)
    import_default_plans(ACTUAL_DB_CONFIG)
    print("物理隔离数据库初始化完成！请运行主程序。")

if __name__ == "__main__":
    main()