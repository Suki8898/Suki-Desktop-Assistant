import os
import random
import re
import math
import webbrowser
import subprocess
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, 
    QLineEdit, QSystemTrayIcon, QMenu, QApplication,
    QHBoxLayout, QPushButton, QTextEdit
)
from PySide6.QtCore import Qt, QPoint, QTimer, Slot, Signal, QThread, QUrl, QPropertyAnimation, QEasingCurve, QRect, QParallelAnimationGroup, QSize
from PySide6.QtGui import QIcon, QPixmap, QAction, QColor, QFont, QKeySequence, QCursor, QTextCursor, QPainter, QPainterPath
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

def resource_path(relative_path):
    import sys, os
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def external_resource_path(relative_path):
    import sys, os
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(".")
    return os.path.join(base_dir, relative_path)

class ChatInput(QTextEdit):
    image_pasted = Signal(QPixmap)
    files_dropped = Signal(list)
    returnPressed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMinimumWidth(250)
        self.sent_history = []
        self.history_index = -1
        
                                        
        self.base_height = 40
        self.setFixedHeight(self.base_height)
        self.textChanged.connect(self.adjust_height)

    def adjust_height(self):
        doc_height = int(self.document().size().height())
        new_height = min(max(self.base_height, doc_height + 10), 80)
        self.setFixedHeight(new_height)

    def keyPressEvent(self, event):
                                                               
        if event.key() == Qt.Key_Up:
            if self.sent_history and self.history_index < len(self.sent_history) - 1:
                self.history_index += 1
                self.setPlainText(self.sent_history[len(self.sent_history) - 1 - self.history_index])
                self.moveCursor(QTextCursor.End)
            return
            
        elif event.key() == Qt.Key_Down:
            if self.history_index > 0:
                self.history_index -= 1
                self.setPlainText(self.sent_history[len(self.sent_history) - 1 - self.history_index])
                self.moveCursor(QTextCursor.End)
            elif self.history_index == 0:
                self.history_index = -1
                self.clear()
            return
            
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
            text = self.toPlainText().strip()
            if text:
                if not self.sent_history or self.sent_history[-1] != text:
                    self.sent_history.append(text)
            self.history_index = -1
            self.returnPressed.emit()
            return
            
        if event.matches(QKeySequence.Paste):
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            if mime_data.hasImage():
                pixmap = QPixmap(mime_data.imageData())
                if not pixmap.isNull():
                    self.image_pasted.emit(pixmap)
                    return                     
        super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            file_paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            if file_paths:
                self.files_dropped.emit(file_paths)
                event.acceptProposedAction()
        else:
            super().dropEvent(event)

from ui.settings_window import SettingsWindow
from core.settings_manager import SettingsManager

class EvasiveButton(QWidget):
    shutdownRequested = Signal()
    startedMoving = Signal()
    stoppedMoving = Signal()

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self.char_name = self.parent_window.settings_manager.get("character", "current_character", default="Suki")
        layout = QVBoxLayout(self)
        self.btn = QPushButton(f"Tắt {self.char_name}")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setStyleSheet("""
            QPushButton {
                background-color: #ff5555;
                color: white;
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid white;
            }
            QPushButton:hover {
                background-color: #ff0000;
            }
        """)
        self.btn.clicked.connect(self.shutdownRequested.emit)
        layout.addWidget(self.btn)
        
        self.is_stunned = False
        
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(150)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)
        
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(1000)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.finished.connect(self.close)
        
        self.dodge_timer = QTimer(self)
        self.dodge_timer.timeout.connect(self.dodge_mouse)
        
        self.stop_timer = QTimer(self)
        self.stop_timer.setSingleShot(True)
        self.stop_timer.timeout.connect(self._emit_stopped)
        
        self.life_timer = QTimer(self)
        self.life_timer.setSingleShot(True)
        self.life_timer.timeout.connect(self.fade_anim.start)
        self.life_timer.start(19000)
        
        self.moving = False
        self.max_dist = 250                               
        self.adjustSize()

    def fly_out(self, target_pos):
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.OutBack)
        self.anim.setStartValue(self.pos())
        self.anim.setEndValue(target_pos)
        self.dodge_timer.stop()
        
        def on_fly_out_done():
            self.anim.setDuration(150)
            self.anim.setEasingCurve(QEasingCurve.OutQuad)
            self.dodge_timer.start(50)
            try:
                self.anim.finished.disconnect(on_fly_out_done)
            except:
                pass
                
        self.anim.finished.connect(on_fly_out_done)
        self.anim.start()

    def set_stun(self, stunned):
        self.is_stunned = stunned
        if stunned:
            if self.moving:
                self.moving = False
                self.stop_timer.stop()
                self.stoppedMoving.emit()
            self.anim.stop()
            self.btn.setText(f"Tắt {self.char_name}")
            self.btn.setStyleSheet(self.btn.styleSheet().replace("#ff5555", "#aaa"))
        else:
            self.btn.setText(f"Tắt {self.char_name}")
            self.btn.setStyleSheet(self.btn.styleSheet().replace("#aaa", "#ff5555"))

    def dodge_mouse(self):
        if self.is_stunned:
            return

        self.raise_()
        cursor_pos = QCursor.pos()
        btn_center = self.geometry().center()
        
        dist_vec = btn_center - cursor_pos
        distance = math.sqrt(dist_vec.x()**2 + dist_vec.y()**2)
        
                                    
        if distance < 150:
            if not self.moving:
                self.moving = True
                self.stop_timer.stop()
                self.startedMoving.emit()
            
                                          
            move_dist = 60
            if distance == 0:
                dx, dy = move_dist, move_dist
            else:
                dx = (dist_vec.x() / distance) * move_dist
                dy = (dist_vec.y() / distance) * move_dist
            
            new_pos = self.pos() + QPoint(int(dx), int(dy))
            
                                                
            char_center = self.parent_window.geometry().center()
            btn_center_target = new_pos + QPoint(self.width()//2, self.height()//2)
            dist_from_char_vec = btn_center_target - char_center
            dist_from_char = math.sqrt(dist_from_char_vec.x()**2 + dist_from_char_vec.y()**2)
            
                                                                                
            if dist_from_char >= self.max_dist:
                if dist_from_char > 0:
                    constrained_x = char_center.x() + (dist_from_char_vec.x() / dist_from_char) * self.max_dist
                    constrained_y = char_center.y() + (dist_from_char_vec.y() / dist_from_char) * self.max_dist
                    new_pos = QPoint(int(constrained_x) - self.width()//2, int(constrained_y) - self.height()//2)
            
            if self.anim.state() == QPropertyAnimation.Running:
                self.anim.stop()
            self.anim.setStartValue(self.pos())
            self.anim.setEndValue(new_pos)
            self.anim.start()
            
        else:
            if self.moving and self.anim.state() != QPropertyAnimation.Running:
                self.moving = False
                if not self.stop_timer.isActive():
                    self.stop_timer.start(3000)

    def _emit_stopped(self):
        if not self.moving and not self.is_stunned:
            self.stoppedMoving.emit()

    def closeEvent(self, event):
        self.dodge_timer.stop()
        self.stop_timer.stop()
        self.life_timer.stop()
        if self.anim.state() == QPropertyAnimation.Running:
            self.anim.stop()
        if hasattr(self, 'fade_anim') and self.fade_anim.state() == QPropertyAnimation.Running:
            self.fade_anim.stop()
        if self.moving or self.stop_timer.isActive():
            self.moving = False
            self.stoppedMoving.emit()
            
        if self.parent_window and hasattr(self.parent_window, "change_emotion"):
            self.parent_window.change_emotion("normal")
            
        super().closeEvent(event)

from core.llm_manager import LLMManager
from core.alarm_manager import AlarmManager
# from ui.alarm_popup import AlarmPopup

import speech_recognition as sr

class VoiceWorker(QThread):
    finished = Signal(str, str)              

    def __init__(self, lang="vi-VN"):
        super().__init__()
        self.lang = lang

    def run(self):
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
            text = recognizer.recognize_google(audio, language=self.lang)
            self.finished.emit(text, "")
        except sr.WaitTimeoutError:
            self.finished.emit("", "Không nghe thấy gì.")
        except sr.RequestError:
            self.finished.emit("", "Lỗi API.")
        except sr.UnknownValueError:
            self.finished.emit("", "Không nghe rõ.")
        except Exception as e:
            self.finished.emit("", f"Lỗi: {str(e)}")



class ChatBubble(QWidget):
    bubble_hidden = Signal()

    def __init__(self, parent=None):
                                                                                        
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)                                     
        self.setMinimumSize(10, 10)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setStyleSheet("""
            QLabel {
                background-color: white;
                color: black;
                border: 2px solid #db9aaa;
                border-radius: 15px;
                padding: 10px;
            }
        """)
        self.label.setMaximumWidth(300)
        layout.addWidget(self.label)
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_bubble)

    def hide_bubble(self):
                                         
        if hasattr(self, 'anim_group') and self.anim_group.state() == QPropertyAnimation.Running:
            self.anim_group.stop()

        self.anim_group = QParallelAnimationGroup(self)

                  
        fade_anim = QPropertyAnimation(self, b"windowOpacity")
        fade_anim.setDuration(300)
        fade_anim.setStartValue(self.windowOpacity())
        fade_anim.setEndValue(0.0)

                                                  
        slide_anim = QPropertyAnimation(self, b"pos")
        slide_anim.setDuration(300)
        slide_anim.setStartValue(self.pos())
        end_pos = QPoint(self.pos().x() + 30, self.pos().y() + 30)
        slide_anim.setEndValue(end_pos)
        slide_anim.setEasingCurve(QEasingCurve.InBack)

        self.anim_group.addAnimation(fade_anim)
        self.anim_group.addAnimation(slide_anim)
        self.anim_group.finished.connect(self._do_hide)
        self.anim_group.start()

    def _do_hide(self):
        self.hide()
        self.bubble_hidden.emit()

    def snap_to_character(self, character_window):
                                                                                 
        x = character_window.x() - self.width() + 100
        y = character_window.y() + 60
        self.move(x, y)

    def show_message(self, text, character_window):
        self.label.setText(text)
        self.adjustSize()
        
                                                                                
        duration = max(5000, len(text) * 100)
        self.hide_timer.start(duration)
        
                                                                                           
        self.snap_to_character(character_window)
        target_pos = self.pos()

                                                         
        start_x = target_pos.x() + 80
        start_y = target_pos.y() + 40
        start_pos = QPoint(start_x, start_y)

                                         
        if hasattr(self, 'anim_group') and self.anim_group.state() == QPropertyAnimation.Running:
            self.anim_group.stop()

        self.anim_group = QParallelAnimationGroup(self)

                 
        fade_anim = QPropertyAnimation(self, b"windowOpacity")
        fade_anim.setDuration(300)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)

                            
        slide_anim = QPropertyAnimation(self, b"pos")
        slide_anim.setDuration(600)
        slide_anim.setStartValue(start_pos)
        slide_anim.setEndValue(target_pos)
        slide_anim.setEasingCurve(QEasingCurve.OutBounce)

        self.anim_group.addAnimation(fade_anim)
        self.anim_group.addAnimation(slide_anim)
        
        self.setWindowOpacity(0.0)
        self.move(start_pos)
        self.show()
        
        self.anim_group.start()


class ThoughtBubble(QWidget):
    """Bong bóng suy nghĩ hình đám mây hiển thị trước báo thức 10 phút hoặc khi báo thức kêu."""
    choice_made = Signal(bool, str)  # (accepted, alarm_time_str) - cho pre-alarm
    alarm_dismissed = Signal()       # Khi nhấn tắt báo thức chính

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(280, 180)
        
        self._alarm_time = ""
        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        
        # Layout chính nằm bên trong vùng đám mây
        # Vùng mây chính: dịch xuống 8px để tránh cắt gờ trên
        self.content_widget = QWidget(self)
        self.content_widget.setGeometry(10, 16, 250, 115)
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(20, 18, 20, 12)
        content_layout.setSpacing(10)
        
        self.msg_label = QLabel("Tắt báo thức sắp tới?")
        self.msg_label.setWordWrap(True)
        self.msg_label.setAlignment(Qt.AlignCenter)
        self.msg_label.setStyleSheet("""
            QLabel {
                color: #4a4a4a;
                font-size: 13px;
                font-weight: bold;
                background: transparent;
            }
        """)
        content_layout.addWidget(self.msg_label)
        
        # Nút Có / Không
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.btn_yes = QPushButton("Có")
        self.btn_yes.setCursor(Qt.PointingHandCursor)
        self.btn_yes.setFixedSize(75, 28)
        self.btn_yes.setStyleSheet("""
            QPushButton {
                background-color: #7ec8a0;
                color: white;
                border-radius: 14px;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #5fb885;
            }
        """)
        self.btn_yes.clicked.connect(self._on_yes)
        
        self.btn_no = QPushButton("Không")
        self.btn_no.setCursor(Qt.PointingHandCursor)
        self.btn_no.setFixedSize(75, 28)
        self.btn_no.setStyleSheet("""
            QPushButton {
                background-color: #e88a9a;
                color: white;
                border-radius: 14px;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #d06a7a;
            }
        """)
        self.btn_no.clicked.connect(self._on_no)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_yes)
        btn_layout.addWidget(self.btn_no)
        btn_layout.addStretch()
        content_layout.addLayout(btn_layout)
        
        # Timer tự ẩn sau 10 phút
        self.auto_hide_timer = QTimer(self)
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self._on_no)

    def paintEvent(self, event):
        """Vẽ hình đám mây (thought bubble) với bong bóng nhỏ bên phải (hướng về nhân vật)."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        cloud_color = QColor(255, 255, 255, 245)
        border_color = QColor(219, 154, 170, 180)  # #db9aaa mờ nhẹ
        
        # Tạo path cho thân mây (dịch xuống 8px - offset Y)
        oy = 8  # offset Y để gờ trên không bị cắt
        cloud_path = QPainterPath()
        cloud_path.setFillRule(Qt.WindingFill)
        cloud_path.addRoundedRect(15, 12+oy, 245, 108, 30, 30)
        # Gờ mây phía trên
        cloud_path.addEllipse(25, 2+oy, 70, 45)
        cloud_path.addEllipse(75, -3+oy, 80, 42)
        cloud_path.addEllipse(140, 0+oy, 75, 40)
        cloud_path.addEllipse(195, 5+oy, 55, 35)
        # Gờ mây hai bên
        cloud_path.addEllipse(5, 30+oy, 40, 55)
        cloud_path.addEllipse(230, 25+oy, 42, 55)
        # Gờ dưới
        cloud_path.addEllipse(30, 90+oy, 60, 38)
        cloud_path.addEllipse(100, 95+oy, 70, 32)
        cloud_path.addEllipse(180, 88+oy, 55, 36)
        
        # Vẽ fill (WindingFill đảm bảo không bị lủng)
        painter.setPen(Qt.NoPen)
        painter.setBrush(cloud_color)
        painter.drawPath(cloud_path)
        
        # Vẽ viền ngoài - dùng simplified() chỉ cho outline
        from PySide6.QtGui import QPen
        pen = QPen(border_color, 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        outline = cloud_path.simplified()
        painter.drawPath(outline)
        
        # Bong bóng nhỏ (dấu chấm suy nghĩ) bên PHẢI dưới
        # Bong bóng 1 (to nhất, gần thân mây)
        painter.setPen(Qt.NoPen)
        painter.setBrush(cloud_color)
        painter.drawEllipse(222, 133, 20, 16)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(222, 133, 20, 16)
        
        # Bong bóng 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(cloud_color)
        painter.drawEllipse(240, 150, 14, 11)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(240, 150, 14, 11)
        
        # Bong bóng 3 (nhỏ nhất)
        painter.setPen(Qt.NoPen)
        painter.setBrush(cloud_color)
        painter.drawEllipse(253, 161, 9, 7)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(253, 161, 9, 7)
        
        painter.end()

    def show_for_alarm(self, alarm_time, character_window):
        """Hiển thị bong bóng suy nghĩ bên TRÁI nhân vật cho pre-alarm."""
        self._alarm_time = alarm_time
        self.msg_label.setText(f"Tắt báo thức {alarm_time}\nsắp tới?")
        self.btn_yes.setText("Có")
        self.btn_no.setVisible(True)
        self._show_bubble(character_window)
        # Tự ẩn sau 10 phút
        self.auto_hide_timer.start(10 * 60 * 1000)

    def show_for_active_alarm(self, message, character_window):
        """Hiển thị bong bóng cho báo thức đang kêu."""
        self.auto_hide_timer.stop()
        self._alarm_time = ""
        self.msg_label.setText(message)
        self.btn_yes.setText("Tắt")
        self.btn_no.setVisible(False)
        self._show_bubble(character_window)
        # Báo thức chính không tự ẩn, user phải nhấn tắt (hoặc auto stop sau 5p ở MainWindow)

    def _show_bubble(self, character_window):
        # Đặt vị trí bên TRÁI nhân vật
        x = character_window.x() - self.width() + 60
        y = character_window.y() - 20
        self.move(x, y)
        
        # Stop existing animations
        if self._opacity_anim.state() == QPropertyAnimation.Running:
            self._opacity_anim.stop()
            
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        
        # Animation hiện lên
        self._opacity_anim.setDuration(500)
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.setEasingCurve(QEasingCurve.OutQuad)
        try:
            self._opacity_anim.finished.disconnect()
        except:
            pass
        self._opacity_anim.start()

    def _on_yes(self):
        self.auto_hide_timer.stop()
        if self.btn_no.isVisible():
            self.choice_made.emit(True, self._alarm_time)
        else:
            self.alarm_dismissed.emit()
        self.hide_with_animation()

    def _on_no(self):
        self.auto_hide_timer.stop()
        self.choice_made.emit(False, self._alarm_time)
        self.hide_with_animation()

    def hide_with_animation(self):
        if self._opacity_anim.state() == QPropertyAnimation.Running:
            self._opacity_anim.stop()
            
        self._opacity_anim.setDuration(400)
        self._opacity_anim.setStartValue(self.windowOpacity())
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.setEasingCurve(QEasingCurve.InQuad)
        try:
            self._opacity_anim.finished.disconnect()
        except:
            pass
        self._opacity_anim.finished.connect(self.hide)
        self._opacity_anim.start()

    def snap_to_character(self, character_window):
        """Cập nhật vị trí khi nhân vật di chuyển."""
        if self.isVisible():
            x = character_window.x() - self.width() + 60
            y = character_window.y() - 20
            self.move(x, y)

class SukiMainWindow(QMainWindow):
                                                                       
    llm_response_signal = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()
        self.llm_manager = LLMManager(self.settings_manager)
        self.alarm_manager = AlarmManager()
        self.alarm_manager.alarm_triggered.connect(self.show_alarm)
        self.alarm_manager.pre_alarm_triggered.connect(self.show_pre_alarm)
        
        self.char_name = self.settings_manager.get("character", "current_character", default="Suki")
        self.current_emotion = "normal"
        self.init_ui()
        self.init_tray_icon()
        
                               
        self.chat_bubble = ChatBubble(self)
        self.chat_bubble.bubble_hidden.connect(self.on_bubble_hidden)
        
        # Bong bóng suy nghĩ pre-alarm / báo thức chính
        self.thought_bubble = ThoughtBubble(self)
        self.thought_bubble.choice_made.connect(self.on_pre_alarm_choice)
        self.thought_bubble.alarm_dismissed.connect(self.stop_alarm)
        
                            
        self.llm_response_signal.connect(self.on_llm_response_received)

    @Slot()
    def on_bubble_hidden(self):
        self.set_emotion("normal")

    @Slot(str, str)
    def show_pre_alarm(self, alarm_time, message):
        """Hiển thị bong bóng suy nghĩ trước báo thức 10 phút."""
        self.ensure_visible()
        self.change_emotion("thinking")
        self.thought_bubble.show_for_alarm(alarm_time, self)

    def ensure_visible(self):
        """Đảm bảo Suki hiện lên trên cùng nếu đang ẩn."""
        if not self.isVisible():
            self.toggle_visibility()
        self.showNormal()
        self.activateWindow()
        self.raise_()

    @Slot(bool, str)
    def on_pre_alarm_choice(self, accepted, alarm_time):
        """Xử lý khi người dùng chọn Có/Không trên bong bóng suy nghĩ."""
        if accepted:
            # Bỏ qua báo thức lần này
            self.alarm_manager.skip_alarm_once(alarm_time)
            self.chat_bubble.show_message(f"Đã bỏ qua báo thức {alarm_time} lần này~", self)
            self.change_emotion("happy")
        else:
            self.change_emotion("normal")

    @Slot(str)
    def show_alarm(self, message):
        """Xử lý khi báo thức chính kêu."""
        self.ensure_visible()
        
        self.change_emotion("happy")                            
        import winsound
        import os
        
        sound_file = self.settings_manager.get("alarm", "sound", default="Mặc định (Tiếng bíp)")
        self._alarm_playing_mode = "none"
        
        if sound_file and sound_file != "Mặc định (Tiếng bíp)":
            sound_path = external_resource_path(os.path.join("assets", "sounds", sound_file))
            if os.path.exists(sound_path):
                self.alarm_player = QMediaPlayer(self)
                self.alarm_audio = QAudioOutput(self)
                self.alarm_player.setAudioOutput(self.alarm_audio)
                self.alarm_player.setSource(QUrl.fromLocalFile(sound_path))
                self.alarm_player.setLoops(QMediaPlayer.Infinite)
                self.alarm_audio.setVolume(1.0)
                self.alarm_player.play()
                self._alarm_playing_mode = "media"
                
        if self._alarm_playing_mode == "none":
            flags = winsound.SND_ASYNC | winsound.SND_LOOP
            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | flags)
            self._alarm_playing_mode = "winsound"
            
        # 2. Hiển thị thông báo trong bong bóng thay vì popup
        self.thought_bubble.show_for_active_alarm(message, self)
        
        # 3. Hẹn giờ tự tắt âm sau 1 phút (60,000 ms)
        if not hasattr(self, 'alarm_auto_stop_timer'):
            self.alarm_auto_stop_timer = QTimer(self)
            self.alarm_auto_stop_timer.setSingleShot(True)
            self.alarm_auto_stop_timer.timeout.connect(self.stop_alarm)
        self.alarm_auto_stop_timer.start(60000)

    @Slot()
    def stop_alarm(self):
        """Dừng âm báo thức và reset trạng thái."""
        if hasattr(self, 'alarm_auto_stop_timer'):
            self.alarm_auto_stop_timer.stop()
            
        import winsound
        if hasattr(self, '_alarm_playing_mode'):
            if self._alarm_playing_mode == "media" and hasattr(self, 'alarm_player'):
                self.alarm_player.stop()
            elif self._alarm_playing_mode == "winsound":
                winsound.PlaySound(None, winsound.SND_PURGE)
        
        self._alarm_playing_mode = "none"
        self.set_emotion("normal")
        if self.thought_bubble.isVisible() and self.thought_bubble.btn_yes.text() == "Tắt":
            self.thought_bubble.hide_with_animation()

    def open_settings(self):
        if not hasattr(self, 'settings_window') or not self.settings_window.isVisible():
            self.settings_window = SettingsWindow(self.settings_manager, self.alarm_manager, self.llm_manager, self.reload_ui)
            self.settings_window.show()
        else:
            self.settings_window.activateWindow()

    def reload_ui(self):
        self.char_name = self.settings_manager.get("character", "current_character", default="Suki")
        self.load_background()
        self.apply_fonts()

    def apply_fonts(self):
        font_family = self.settings_manager.get("ui", "font_family", default="Arial")
        font_size = self.settings_manager.get("ui", "font_size", default=14)
        
                           
        app_font = QFont(font_family, font_size)
        QApplication.instance().setFont(app_font)
        
                                                                                           
        if hasattr(self, 'chat_input'):
            self.chat_input.setStyleSheet(f"""
                QTextEdit {{ 
                    border: 2px solid #555555;
                    border-radius: 10px;
                    padding: 8px;
                    background-color: rgba(30, 30, 30, 220);
                    color: white;
                    font-family: "{font_family}";
                    font-size: {font_size}pt;
                }} 
                QTextEdit:focus {{ 
                    border: 2px solid #db9aaa;
                }} 
            """)
            
        if hasattr(self, 'chat_bubble'):
            self.chat_bubble.label.setStyleSheet(f"""
                QLabel {{ 
                    background-color: white;
                    color: black;
                    border: 2px solid #db9aaa;
                    border-radius: 15px;
                    padding: 10px;
                    font-family: "{font_family}";
                    font-size: {font_size}pt;
                }} 
            """)

        
    def init_ui(self):
                                                    
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
                        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
                
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
                                                                                              
        self.char_bg_container = QWidget()
        self.char_bg_container.setFixedSize(350, 350)
        self.char_bg_layout = QVBoxLayout(self.char_bg_container)
        self.char_bg_layout.setContentsMargins(0, 0, 0, 0)
        
                          
        self.bg_label = QLabel(self.char_bg_container)
        self.bg_label.setAlignment(Qt.AlignCenter)
        self.bg_label.setAttribute(Qt.WA_TransparentForMouseEvents)                           
                                                                                       
        
                               
        self.character_label = QLabel(self.char_bg_container)
        self.character_label.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        self.character_label.setScaledContents(True)
        self.set_emotion("normal") 
        
        self.char_bg_layout.addWidget(self.character_label, 0, Qt.AlignBottom | Qt.AlignHCenter)
        
                                   
        self.breath_timer = QTimer(self)
        self.breath_timer.timeout.connect(self.update_breath)
        self.breath_timer.start(16)
        self.breath_phase = 0.0
        self.breath_base_size = 300
        
                              
        self.bounce_amplitude = 0.0
        self.bounce_phase = 0.0
        
        self.layout.addWidget(self.char_bg_container)
        
                                
        self.load_background()
        
                        
        self.chat_container = QWidget()
        self.chat_container.setFixedWidth(350)
        chat_layout = QHBoxLayout(self.chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chat_input = ChatInput()
        self.chat_input.setPlaceholderText(f"Chat với {self.char_name}...")
        self.chat_input.image_pasted.connect(self.on_image_pasted)
        self.chat_input.files_dropped.connect(self.on_files_dropped)
        
        self.attached_images = []
        
                                                  
        self.preview_container = QWidget()
        self.preview_layout = QHBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(5, 5, 5, 5)
        self.preview_layout.setAlignment(Qt.AlignLeft)
        
        self.preview_container.setVisible(False)
        self.layout.addWidget(self.preview_container)
        
        self.btn_mic = QPushButton("🎙️")
        self.btn_mic.setFixedSize(40, 40)
        self.btn_mic.setCursor(Qt.PointingHandCursor)
        self.btn_mic.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 30, 30, 220);
                color: white;
                border: 2px solid #555555;
                border-radius: 10px;
                font-size: 16px;
            }
            QPushButton:hover {
                border: 2px solid #db9aaa;
            }
        """)
        self.btn_mic.clicked.connect(self.start_voice_input)
        
        self.btn_attach = QPushButton("🖼️")
        self.btn_attach.setFixedSize(40, 40)
        self.btn_attach.setCursor(Qt.PointingHandCursor)
        self.btn_attach.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 30, 30, 220);
                color: white;
                border: 2px solid #555555;
                border-radius: 10px;
                font-size: 16px;
            }
            QPushButton:hover {
                border: 2px solid #db9aaa;
            }
        """)
        self.btn_attach.clicked.connect(self.attach_image)
        
        chat_layout.addWidget(self.btn_attach, 0, Qt.AlignBottom)
        chat_layout.addWidget(self.chat_input, 1, Qt.AlignBottom)
        chat_layout.addWidget(self.btn_mic, 0, Qt.AlignBottom)
        self.layout.addWidget(self.chat_container, 0, Qt.AlignHCenter | Qt.AlignBottom)
        
                                         
        self.apply_fonts()
        
        self.chat_input.returnPressed.connect(self.send_message)
        self.drag_pos = QPoint()
        self.is_dragging = False

    def start_voice_input(self):
        self.chat_input.setPlaceholderText("Đang nghe...")
        self.chat_input.setEnabled(False)
        self.btn_mic.setEnabled(False)
        self.btn_attach.setEnabled(False)
        self.set_emotion("thinking")
        
        stt_lang = self.settings_manager.get("interaction", "stt_language", default="vi-VN")
        self.voice_worker = VoiceWorker(lang=stt_lang)
        self.voice_worker.finished.connect(self.on_voice_finished)
        self.voice_worker.start()

    def update_image_previews(self):
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                                   
                inner_layout = item.layout()
                while inner_layout.count():
                    inner_item = inner_layout.takeAt(0)
                    inner_widget = inner_item.widget()
                    if inner_widget:
                        inner_widget.deleteLater()
                inner_layout.deleteLater()
                
        if not self.attached_images:
            self.preview_container.setVisible(False)
            QApplication.processEvents()
            self.adjustSize()
            return
            
        self.preview_container.setVisible(True)
        for i, img_path in enumerate(self.attached_images):
            wrapper = QWidget()
            wrapper_layout = QHBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(0, 0, 5, 0)
            
            img_label = QLabel()
            img_label.setFixedSize(60, 60)
            img_label.setScaledContents(True)
            img_label.setStyleSheet("border: 1px solid #555; border-radius: 5px;")
            
                                                                            
            ext = os.path.splitext(img_path)[1].lower()
            if ext in ['.txt', '.csv', '.md', '.json']:
                                                                                                                    
                doc_pixmap = QPixmap(60, 60)
                doc_pixmap.fill(QColor("#2d2d2d"))
                
                                          
                from PySide6.QtGui import QPainter
                painter = QPainter(doc_pixmap)
                painter.setPen(QColor("#ffffff"))
                painter.setFont(QFont("Arial", 14, QFont.Bold))
                base_name = os.path.basename(img_path)
                display_text = "DOC"
                if ext == ".txt": display_text = "TXT"
                elif ext == ".csv": display_text = "CSV"
                elif ext == ".md": display_text = "MD"
                elif ext == ".json": display_text = "JSON"
                painter.drawText(doc_pixmap.rect(), Qt.AlignCenter, display_text)
                painter.end()
                
                img_label.setPixmap(doc_pixmap)
            else:
                img_label.setPixmap(QPixmap(img_path))
            
            btn_remove = QPushButton("✖")
            btn_remove.setFixedSize(20, 20)
            btn_remove.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 50, 50, 200);
                    color: white;
                    border-radius: 10px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(255, 100, 100, 255);
                }
            """)
            btn_remove.clicked.connect(lambda checked=False, idx=i: self.remove_attached_image(idx))
            
            vbox = QVBoxLayout()
            vbox.addWidget(btn_remove, alignment=Qt.AlignRight | Qt.AlignTop)
            vbox.addStretch()
            
            wrapper_layout.addWidget(img_label)
            wrapper_layout.addLayout(vbox)
            self.preview_layout.addWidget(wrapper)

        self.preview_layout.addStretch()
        
                                                                             
        QApplication.processEvents()
        self.adjustSize()

    @Slot(list)
    def on_files_dropped(self, file_paths):
        if len(self.attached_images) >= 3:
            char_name = self.settings_manager.get("character", "current_character", default="Suki")
            self.chat_bubble.show_message(f"{char_name} chỉ nhận tối đa 3 file một lúc thôi ạ!", self)
            return
            
        slots_left = 3 - len(self.attached_images)
        # Lọc các file có định dạng hỗ trợ
        supported_exts = ['.png', '.jpg', '.jpeg', '.webp', '.txt', '.csv', '.md', '.json']
        valid_files = [f for f in file_paths if os.path.splitext(f)[1].lower() in supported_exts]
        
        if not valid_files:
            self.chat_bubble.show_message("Định dạng file không được hỗ trợ rồi ạ!", self)
            return
            
        if len(valid_files) > slots_left:
            self.chat_bubble.show_message(f"Suki chỉ lấy thêm {slots_left} file thôi nha!", self)
            valid_files = valid_files[:slots_left]
            
        self.attached_images.extend(valid_files)
        self.update_image_previews()

    def attach_image(self):
        if len(self.attached_images) >= 3:
            char_name = self.settings_manager.get("character", "current_character", default="Suki")
            self.chat_bubble.show_message(f"{char_name} chỉ nhận tối đa 3 file một lúc thôi ạ!", self)
            return
            
        from PySide6.QtWidgets import QFileDialog
        slots_left = 3 - len(self.attached_images)
        file_names, _ = QFileDialog.getOpenFileNames(
            self, "Chọn tài liệu đính kèm (Tối đa 3 file)", "", "Supported Files (*.png *.jpg *.jpeg *.webp *.txt *.csv *.md *.json)"
        )
        if file_names:
            if len(file_names) > slots_left:
                self.chat_bubble.show_message(f"Suki chỉ lấy thêm {slots_left} file thôi nha!", self)
                file_names = file_names[:slots_left]
            self.attached_images.extend(file_names)
            self.update_image_previews()

    @Slot(QPixmap)
    def on_image_pasted(self, pixmap):
        if len(self.attached_images) >= 3:
            char_name = self.settings_manager.get("character", "current_character", default="Suki")
            self.chat_bubble.show_message(f"{char_name} chỉ nhận tối đa 3 file một lúc thôi ạ!", self)
            return
            
        import tempfile
        import os
        import uuid
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"suki_paste_{uuid.uuid4().hex[:8]}.jpg")
        pixmap.save(temp_path, "JPG")
        
        self.attached_images.append(temp_path)
        self.update_image_previews()

    def remove_attached_image(self, index):
        if 0 <= index < len(self.attached_images):
            self.attached_images.pop(index)
            self.update_image_previews()

    @Slot(str, str)
    def on_voice_finished(self, text, error):
        self.chat_input.setEnabled(True)
        self.btn_mic.setEnabled(True)
        self.btn_attach.setEnabled(True)
        char_name = self.settings_manager.get("character", "current_character", default="Suki")
        if error:
            self.set_emotion("sad")
            self.chat_input.setPlaceholderText(f"Chat với {char_name}...")
            self.attached_image_path = None
            self.chat_bubble.show_message(error, self)
        else:
            self.chat_input.setPlainText(text)
            self.send_message()

    def update_breath(self):
        if self.isHidden():
            return
            
        self.breath_phase += 0.033
        
                                     
        base_scale_w = 1.0 + 0 * ((math.sin(self.breath_phase) + 1) / 2)
        base_scale_h = 1.0 + 0.02 * ((math.sin(self.breath_phase) + 1) / 2)
        
                                           
        bounce_scale_w = 1.0
        bounce_scale_h = 1.0
        
        if hasattr(self, 'bounce_amplitude') and self.bounce_amplitude > 0.001:
            bounce_scale_h = 1.0 - self.bounce_amplitude * math.cos(self.bounce_phase)
            bounce_scale_w = 1.0 + self.bounce_amplitude * math.cos(self.bounce_phase) * 0.5
            
            self.bounce_phase += 0.4               
            self.bounce_amplitude *= 0.85          
        else:
            self.bounce_amplitude = 0.0
            
        scale_w = base_scale_w * bounce_scale_w
        scale_h = base_scale_h * bounce_scale_h

        new_w = int(self.breath_base_size * scale_w)
        new_h = int(self.breath_base_size * scale_h)
        
                                                                                                 
        self.character_label.setFixedSize(new_w, new_h)


    def send_message(self):
        text = self.chat_input.toPlainText().strip()
        img_paths = self.attached_images.copy()
        if not text and not img_paths: return
        
        char_name = self.settings_manager.get("character", "current_character", default="Suki")
        self.chat_input.clear()
        self.chat_input.setPlaceholderText(f"{char_name} đang suy nghĩ...")
        self.chat_input.setEnabled(False)
        self.btn_attach.setEnabled(False)
        self.btn_mic.setEnabled(False)
        self.set_emotion("thinking")
                                                       
        self.attached_images.clear()
        self.update_image_previews()
        
                     
        def llm_callback(response, error):
            self.llm_response_signal.emit(response or "", error or "")
            
        self.llm_manager.generate_response(text, file_paths=img_paths, callback=llm_callback)
        if hasattr(self, 'settings_window') and self.settings_window.isVisible():
            self.settings_window.load_chat_history()
        
    @Slot(str, str)
    def on_llm_response_received(self, response_text, error_text):
        self.chat_input.setEnabled(True)
        self.btn_attach.setEnabled(True)
        self.btn_mic.setEnabled(True)
        char_name = self.settings_manager.get("character", "current_character", default="Suki")
        if error_text:
            self.chat_input.setPlaceholderText(f"Lỗi: {error_text[:30]}...")
            self.set_emotion("sad")                               
            self.chat_bubble.show_message(f"{char_name} gặp lỗi rồi...", self)
        else:
            self.chat_input.setPlaceholderText(f"Chat với {char_name}...")
            if hasattr(self, 'settings_window') and self.settings_window.isVisible():
                self.settings_window.load_chat_history()
            
            # Refined Tag Processing
            emotion = "normal"
            text_to_show = response_text
            
            emotions_list = self.settings_manager.get("emotions", "list", default=["normal", "happy", "angry", "sad", "thinking", "suspicion", "surprised", "embarrassed", "confused", "dizzy", "smug", "hearthands", "sleepy", "hello"])
            
            # 1. Tìm biểu cảm hợp lệ đầu tiên (nhưng chưa xóa vội để tránh lệch vị trí các thẻ chức năng)
            all_simple_tags = re.findall(r"<([a-zA-Z0-9_]+)>", text_to_show)
            for tag in all_simple_tags:
                if tag.lower() in [e.lower() for e in emotions_list]:
                    emotion = tag.lower()
                    break
                    
            # 2. Xử lý các thẻ chức năng theo cách truyền thống (Xử lý đến đâu xóa đến đó)
            
            # Alarm match: <Alarm|HH:MM|Message>
            while True:
                alarm_match = re.search(r"<Alarm\|(\d{2}:\d{2})\|(.*?)>", text_to_show, re.IGNORECASE)
                if not alarm_match: break
                self.alarm_manager.add_alarm(alarm_match.group(1), alarm_match.group(2).strip())
                if hasattr(self, 'settings_window') and self.settings_window.isVisible():
                    self.settings_window.load_alarms()
                text_to_show = text_to_show[:alarm_match.start()] + text_to_show[alarm_match.end():]
            
            # Delete Alarm match: <DelAlarm|HH:MM|Message>
            while True:
                del_alarm_match = re.search(r"<DelAlarm\|(\d{2}:\d{2})\|(.*?)>", text_to_show, re.IGNORECASE)
                if not del_alarm_match: break
                self.alarm_manager.remove_alarm_by_match(del_alarm_match.group(1), del_alarm_match.group(2).strip())
                if hasattr(self, 'settings_window') and self.settings_window.isVisible():
                    self.settings_window.load_alarms()
                text_to_show = text_to_show[:del_alarm_match.start()] + text_to_show[del_alarm_match.end():]
                    
            # Web match: <Web|URL>
            while True:
                web_match = re.search(r"<Web\|(.*?)>", text_to_show, re.IGNORECASE)
                if not web_match: break
                self.open_web(web_match.group(1).strip())
                text_to_show = text_to_show[:web_match.start()] + text_to_show[web_match.end():]
                
            # PlayMusic match: <PlayMusic|Query>
            while True:
                music_match = re.search(r"<PlayMusic\|(.*?)>", text_to_show, re.IGNORECASE)
                if not music_match: break
                query = music_match.group(1).strip()
                try:
                    import urllib.request
                    import urllib.parse
                    query_string = urllib.parse.urlencode({"search_query": query})
                    req = urllib.request.Request("https://www.youtube.com/results?" + query_string, headers={'User-Agent': 'Mozilla/5.0'})
                    html_content = urllib.request.urlopen(req, timeout=5)
                    search_results = re.findall(r'watch\?v=(.{11})', html_content.read().decode())
                    if search_results:
                        self.open_web("https://www.youtube.com/watch?v=" + search_results[0])
                    else:
                        self.open_web("https://www.youtube.com/results?" + query_string)
                except Exception as e:
                    import urllib.parse
                    print(f"Lỗi tìm kiếm YouTube: {e}")
                    self.open_web(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
                text_to_show = text_to_show[:music_match.start()] + text_to_show[music_match.end():]
            
            # 3. Cuối cùng, loại bỏ tất cả các thẻ cảm xúc (hợp lệ hoặc tự chế) còn sót lại
            # Chỉ xóa các thẻ dạng <word> không có thanh đứng | bên trong
            text_to_show = re.sub(r"<[a-zA-Z0-9_]+?>", "", text_to_show).strip()
            
            self.set_emotion(emotion)
            self.chat_bubble.show_message(text_to_show, self)
            
    def open_web(self, url):
        use_default_browser = self.settings_manager.get("interaction", "use_default_browser", default=True)
        browser_path = self.settings_manager.get("interaction", "browser_path", default="")
        
        if not use_default_browser and browser_path and os.path.exists(browser_path):
            try:
                subprocess.Popen([browser_path, url])
                return
            except Exception as e:
                print(f"Lỗi mở trình duyệt custom: {e}")
        
                                                                        
        if "www.youtube.com" in url or "youtu.be" in url:
            try:
                import pygetwindow as gw
                import pyautogui
                import pyperclip
                import time
                
                                                      
                all_windows = gw.getAllWindows()
                yt_windows = [w for w in all_windows if w.title and 'youtube' in w.title.lower()]
                
                if yt_windows:
                    win = yt_windows[0]
                                          
                    if win.isMinimized:
                        win.restore()
                    
                    try:
                        win.activate()
                    except Exception:
                                                                                                               
                        import pyautogui
                        pyautogui.press('alt')
                        win.activate()
                        
                    time.sleep(0.3)
                    
                                            
                    pyperclip.copy(url)
                    pyautogui.hotkey('ctrl', 'l')                    
                    time.sleep(0.1)
                    pyautogui.hotkey('ctrl', 'v')            
                    time.sleep(0.1)
                    pyautogui.press('enter')                
                    return
            except ImportError:
                print("Cần cài đặt thư viện: pip install pygetwindow pyautogui pyperclip")
            except Exception as e:
                print(f"Lỗi tái sử dụng tab YouTube: {e}")

        webbrowser.open(url)
        
    def change_emotion(self, emotion):
        self.set_emotion(emotion)
                                                                                                 

    def load_background(self):
        bg_image_name = self.settings_manager.get("ui", "bg_image")
        if bg_image_name:
            bg_path = external_resource_path(os.path.join("assets", "backgrounds", bg_image_name))
            if os.path.exists(bg_path):
                original_pixmap = QPixmap(bg_path)
                
                target_size = self.char_bg_container.size()
                if target_size.isEmpty():
                    target_size = QSize(350, 350)
                    
                scaled_pixmap = original_pixmap.scaled(target_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                
                rounded_pixmap = QPixmap(target_size)
                rounded_pixmap.fill(Qt.transparent)
                
                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setRenderHint(QPainter.SmoothPixmapTransform)
                
                path = QPainterPath()
                path.addRoundedRect(0, 0, target_size.width(), target_size.height(), 20, 20)
                
                painter.setClipPath(path)
                
                x_offset = (target_size.width() - scaled_pixmap.width()) // 2
                y_offset = (target_size.height() - scaled_pixmap.height()) // 2
                painter.drawPixmap(x_offset, y_offset, scaled_pixmap)
                painter.end()
                
                self.bg_label.setPixmap(rounded_pixmap)
                self.bg_label.setScaledContents(False)
                self.bg_label.show()
                return

        self.bg_label.clear()
        self.bg_label.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
                                                              
        if hasattr(self, 'bg_label') and hasattr(self, 'char_bg_container'):
            self.bg_label.resize(self.char_bg_container.size())

    def set_emotion(self, emotion):
        if hasattr(self, 'current_emotion') and self.current_emotion != emotion:
            self.bounce_amplitude = 0.15                                         
            self.bounce_phase = 0.0
            
        self.current_emotion = emotion
        char_folder = self.settings_manager.get("character", "current_character", default="Suki")
        char_dir = external_resource_path(os.path.join("assets", "character", char_folder))
        search_emotion = emotion.lower()
        
        found_images = []
        if os.path.exists(char_dir):
            for file in os.listdir(char_dir):
                if file.lower().startswith(search_emotion) and file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    found_images.append(os.path.join(char_dir, file))
                    
                                                                                                        
        if not found_images and search_emotion == "blink":
            for file in os.listdir(char_dir):
                if file.lower().startswith("sad") and file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    found_images.append(os.path.join(char_dir, file))
            if not found_images:
                for file in os.listdir(char_dir):
                    if file.lower().startswith("normal") and file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        found_images.append(os.path.join(char_dir, file))
                        
        pixmap = QPixmap(300, 300)
        if found_images:
            img_path = random.choice(found_images)
            pixmap.load(img_path)
            pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            if emotion == "normal":
                pixmap.fill(QColor(255, 180, 200, 200))                 
            elif emotion == "blink":
                pixmap.fill(QColor(200, 150, 180, 200))                        
            elif emotion == "happy":
                pixmap.fill(QColor(255, 255, 100, 200))                   
            else:
                pixmap.fill(QColor(100, 255, 100, 200))                   
                
                                                                               
                                                     
        self.character_label.setPixmap(pixmap)

    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        icon_path = resource_path(os.path.join("icons", "Suki.ico"))
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            self.tray_icon.setIcon(app_icon)
            self.setWindowIcon(app_icon)
        else:
            icon_pixmap = QPixmap(32, 32)
            icon_pixmap.fill(QColor(255, 180, 200))
            self.tray_icon.setIcon(QIcon(icon_pixmap))
        
                   
        self.tray_menu = QMenu()
        
        settings_action = QAction("Tùy chỉnh", self)
        settings_action.triggered.connect(self.open_settings)
        self.tray_menu.addAction(settings_action)
        
        self.toggle_action = QAction(f"Ẩn {self.char_name}" if self.isVisible() else f"Hiện {self.char_name}", self)
        self.toggle_action.triggered.connect(self.toggle_visibility)
        self.tray_menu.addAction(self.toggle_action)
        
        log_action = QAction("Mở Log", self)
        log_action.triggered.connect(self.open_log)
        self.tray_menu.addAction(log_action)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()
        
    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'toggle_action'):
            self.toggle_action.setText(f"Ẩn {self.char_name}")
            
    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, 'toggle_action'):
            self.toggle_action.setText(f"Hiện {self.char_name}")
        
    def quit_app(self):
        self.tray_icon.hide()
        QApplication.instance().quit()
        
    def open_log(self):
        try:
            app_data_dir = os.path.join(os.environ.get("APPDATA", ""), "Suki8898", "Suki Desktop Assistant")
            log_path = os.path.join(app_data_dir, "suki.log")
            if os.path.exists(log_path):
                os.startfile(log_path)
            else:
                self.chat_bubble.show_message("Chưa có file log!", self)
        except Exception as e:
            print(f"Lỗi mở log: {e}")
            
                                               
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.is_dragging = False
            event.accept()
        elif event.button() == Qt.RightButton:
            if getattr(self, 'evasive_btn', None):
                try:
                    self.evasive_btn.close()
                except RuntimeError:
                    pass
            
            self.evasive_btn = EvasiveButton(self)
            self.evasive_btn.shutdownRequested.connect(self.quit_app)
            self.evasive_btn.startedMoving.connect(lambda: self.change_emotion("Smug"))
            self.evasive_btn.stoppedMoving.connect(lambda: self.change_emotion("normal"))
            
            spawn_pos = event.globalPosition().toPoint()
            target_pos = QPoint(self.x() - 150, self.y() + 100)
            self.evasive_btn.move(spawn_pos)
            self.evasive_btn.show()
            self.evasive_btn.fly_out(target_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            if self.character_label.geometry().contains(pos):
                char_pos = self.character_label.mapFromParent(pos)
                y_from_bottom = self.character_label.height() - char_pos.y()
                
                                          
                if 130 <= y_from_bottom <= 270:
                    self.is_stunned = True
                    self.change_emotion("Dizzy")
                    if getattr(self, 'evasive_btn', None):
                        try:
                            self.evasive_btn.set_stun(True)
                        except RuntimeError:
                            self.evasive_btn = None
                    
                    QTimer.singleShot(3000, self.unstun)
        event.accept()

    def unstun(self):
        self.is_stunned = False
        self.change_emotion("normal")
        if getattr(self, 'evasive_btn', None):
            try:
                self.evasive_btn.set_stun(False)
            except RuntimeError:
                self.evasive_btn = None

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, 'chat_bubble') and self.chat_bubble.isVisible():
            self.chat_bubble.snap_to_character(self)
        if hasattr(self, 'thought_bubble') and self.thought_bubble.isVisible():
            self.thought_bubble.snap_to_character(self)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            self.is_dragging = True
            event.accept()
            
    def mouseReleaseEvent(self, event):
        if getattr(self, 'is_stunned', False):
            event.accept()
            return
            
        if event.button() == Qt.LeftButton and not self.is_dragging:
                                                 
            pos = event.position().toPoint()
            if self.character_label.geometry().contains(pos):
                char_pos = self.character_label.mapFromParent(pos)
                y_from_bottom = self.character_label.height() - char_pos.y()
                
                if 0 <= y_from_bottom <= 100:
                    import random
                    char_name = self.settings_manager.get("character", "current_character", default="Suki")
                    chest_msgs = self.settings_manager.get("interaction", "touch_chest_msgs", default=["Đừng chạm vào em !!!", "Hentai!"])
                    msg = random.choice(chest_msgs)
                    self.chat_bubble.show_message(msg, self)
                    self.llm_manager.history.append({"role": "user", "content": f"Chạm vào ngực {char_name}"})
                    self.llm_manager.history.append({"role": "assistant", "content": f"<angry>{msg}"})
                    self.llm_manager.save_history()
                    self.change_emotion("CoveringBreasts")
                    QTimer.singleShot(3000, lambda: self.change_emotion("normal"))
                    
                elif 130 <= y_from_bottom <= 270:
                    import random
                    char_name = self.settings_manager.get("character", "current_character", default="Suki")
                    head_msgs = self.settings_manager.get("interaction", "touch_head_msgs", default=["Đừng xoa đầu em nữa mà~", "Aww, chủ nhân xoa đầu Suki~", "Chủ nhân cứ thích trêu em thôi!"])
                    msg = random.choice(head_msgs)
                    self.chat_bubble.show_message(msg, self)
                    self.llm_manager.history.append({"role": "user", "content": f"Xoa đầu {char_name}"})
                    self.llm_manager.history.append({"role": "assistant", "content": f"<happy>{msg}"})
                    self.llm_manager.save_history()
                    self.change_emotion("Pet")
                    QTimer.singleShot(3000, lambda: self.change_emotion("normal"))
        event.accept()