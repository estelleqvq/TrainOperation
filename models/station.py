# models/station.py
class Station:
    def __init__(self, id, name, display_order, tracks_str=None):
        self.id = id
        self.name = name
        self.display_order = display_order
        self.y_coord = 0

        self.tracks = []
        if tracks_str:
            raw_tracks = tracks_str.split(',')
            for tk in raw_tracks:
                tk = tk.strip()
                # 核心修改：遇到“正线”直接丢弃，不作为独立股道展示
                if tk == "正线":
                    continue

                if tk in ["1", "1股", "正线1"]:
                    tk = "Ⅰ"
                elif tk in ["2", "2股", "正线2"]:
                    tk = "Ⅱ"
                elif tk.endswith("股"):
                    tk = tk[:-1]

                if tk and tk not in self.tracks:
                    self.tracks.append(tk)
        else:
            # 默认配置也直接摒弃正线
            self.tracks = ['Ⅰ', 'Ⅱ', '3', '4', '5', '6']