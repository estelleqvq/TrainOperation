import sys
from PyQt5.QtWidgets import QApplication
from views.main_window import MainWindow
from controllers.main_controller import MainController

def main():
    app = QApplication(sys.argv)
    try:
        view = MainWindow()
        controller = MainController(view)
        view.set_controller(controller)
        view.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"发生异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()