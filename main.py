import sys

import cv2
from PySide6.QtWidgets import QApplication

from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    w = MainWindow()
    app.aboutToQuit.connect(w.release_resources) 
    w.show()
    try:
        return app.exec()
    finally:
        w.release_resources()
        cv2.destroyAllWindows()
        app.processEvents()


if __name__ == "__main__":
    sys.exit(main())
