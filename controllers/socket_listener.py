import json
import socket
from PyQt5.QtCore import QThread, pyqtSignal


class SocketListenerThread(QThread):
    # 定义信号，将接收到的 JSON 字典发送给主线程
    data_received = pyqtSignal(dict)

    def __init__(self, port):
        super().__init__()
        self.port = port
        self.running = True

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(('0.0.0.0', self.port))
                s.listen(5)
                print(f"📻 Socket 监听已启动，等待模拟器报点，端口: {self.port}")
                s.settimeout(1.0)  # 设置超时，方便安全退出线程

                while self.running:
                    try:
                        conn, addr = s.accept()
                        with conn:
                            data = conn.recv(1024)
                            if data:
                                msg = data.decode('utf-8')
                                try:
                                    json_data = json.loads(msg)
                                    self.data_received.emit(json_data)
                                except json.JSONDecodeError:
                                    print("收到非 JSON 格式的报点数据")
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print(f"Socket 接收异常: {e}")
            except Exception as e:
                print(f"Socket 绑定失败 (端口被占用?): {e}")

    def stop(self):
        self.running = False
        self.wait()