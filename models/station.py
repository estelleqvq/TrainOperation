class Station:
    def __init__(self, id, name, display_order, tracks_str="正线,1股,2股,3股,4股,5股"):
        self.id = id
        self.name = name
        self.display_order = display_order

        # 将逗号分隔的字符串转换为列表，方便后续给下拉框使用
        self.tracks = tracks_str.split(',') if tracks_str else ["正线"]

        # 记录车站在画布上的 Y 坐标，由 canvas_widget 在绘制时动态计算并赋值
        self.y_coord = 0

    def __repr__(self):
        return f"Station({self.name}, order={self.display_order})"