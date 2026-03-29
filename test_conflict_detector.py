# test_conflict_detector.py
from PyQt5.QtCore import QTime
from controllers.conflict_detector import ConflictDetector
from models.train_line import TrainLine, TrainLinePoint


# 1. 模拟基础数据：伪造两个车站
class MockStation:
    def __init__(self, s_id, name):
        self.id = s_id
        self.name = name


stations = [MockStation(1, "北京南"), MockStation(2, "天津南")]
detector = ConflictDetector(stations)


def create_mock_train(train_num, time_points):
    """辅助函数：快速生成一列用于测试的列车"""
    points = []
    for s_id, arr_str, dep_str in time_points:
        arr = QTime.fromString(arr_str, "HH:mm") if arr_str else None
        dep = QTime.fromString(dep_str, "HH:mm") if dep_str else None
        points.append(TrainLinePoint(s_id, arr, dep, "正线"))
    return TrainLine(None, train_num, 1, "2026-03-29", points)


def run_tests():
    print("开始执行冲突检测模块自动化测试...\n")

    # ================= 测试 1：合法的列车运行 =================
    existing_train = create_mock_train("G101", [
        (1, None, "10:00"),  # 北京南 10:00 发
        (2, "10:30", None)  # 天津南 10:30 到
    ])

    # 构造一条完全合法的新车 (相隔 10 分钟追踪)
    valid_train = create_mock_train("G103", [
        (1, None, "10:10"),
        (2, "10:40", None)
    ])
    is_valid, msg = detector.validate_plan_line(valid_train, [existing_train])
    assert is_valid == True, f"测试失败：合法列车被误杀！错误信息：{msg}"
    print("✅ 测试 1 (合法运行) 通过")

    # ================= 测试 2：追踪间隔冲突 (追尾) =================
    # G105 仅比 G101 晚 2 分钟发车，小于规定的 3 分钟
    tailing_train = create_mock_train("G105", [
        (1, None, "10:02"),
        (2, "10:32", None)
    ])
    is_valid, msg = detector.validate_plan_line(tailing_train, [existing_train])
    assert is_valid == False and "追踪" in msg, "测试失败：未检测出追踪间隔冲突！"
    print("✅ 测试 2 (追踪间隔违规拦截) 通过")

    # ================= 测试 3：区间越行冲突 =================
    # G107 在北京南晚于 G101 发车 (10:05)，但在天津南却早于 G101 到达 (10:25)
    overtake_train = create_mock_train("G107", [
        (1, None, "10:05"),
        (2, "10:25", None)
    ])
    is_valid, msg = detector.validate_plan_line(overtake_train, [existing_train])
    assert is_valid == False and "区间越行" in msg, "测试失败：未检测出区间越行冲突！"
    print("✅ 测试 3 (区间越行拦截) 通过")

    # ================= 测试 4：停站时间不足 =================
    # G109 在北京南到达 10:00，出发 10:01 (停站仅 1 分钟)
    short_stop_train = create_mock_train("G109", [
        (1, "10:00", "10:01"),
        (2, "10:30", None)
    ])
    is_valid, msg = detector.validate_plan_line(short_stop_train, [])
    assert is_valid == False and "停站时间" in msg, "测试失败：未检测出停站时间不足！"
    print("✅ 测试 4 (停站时间不足拦截) 通过")

    print("\n🎉 所有核心约束条件验证通过！模块逻辑严密。")


if __name__ == "__main__":
    run_tests()