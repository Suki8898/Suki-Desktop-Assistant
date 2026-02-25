from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

class AlarmPopup(QDialog):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Suki Báo Thức!")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.resize(300, 150)
        
        layout = QVBoxLayout(self)
        
        msg_label = QLabel(message)
        msg_label.setAlignment(Qt.AlignCenter)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #db9aaa;")
        layout.addWidget(msg_label)
        
        btn_ok = QPushButton("Tắt báo thức")
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #db9aaa;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c98a9a;
            }
        """)
        btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok)
        
        self.center_on_screen()
        
    def center_on_screen(self):
        screen = QGuiApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
