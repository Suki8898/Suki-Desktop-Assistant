import json
import os
from datetime import datetime, timedelta
from PySide6.QtCore import QObject, QTimer, Signal

class AlarmManager(QObject):
                                                       
    alarm_triggered = Signal(str)
    # Signal phát trước báo thức 10 phút: (time_str, message)
    pre_alarm_triggered = Signal(str, str)

    def __init__(self, config_folder="config", config_file="alarms.json"):
        super().__init__()
        app_data_dir = os.path.join(os.environ.get("APPDATA", ""), "Suki8898", "Suki Desktop Assistant")
        self.config_path = os.path.join(app_data_dir, config_file)
        self.alarms = []                                                                           
        self.load_alarms()
        
        # Lưu các báo thức đã skip (chỉ hiệu lực 1 lần trong ngày)
        # Key: "HH:MM|YYYY-MM-DD"
        self.skipped_alarms = set()
        # Lưu các báo thức đã hiển thị pre-alarm (tránh hiện lại)
        # Key: "HH:MM|YYYY-MM-DD"  
        self.pre_alarm_shown = set()
        
                                       
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_alarms)
        self.check_timer.start(30000)
        self.last_triggered_time = ""

    def load_alarms(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.alarms = json.load(f)
            except:
                self.alarms = []
        else:
            self.alarms = []
        self._sort_alarms()

    def _sort_alarms(self):
        """Sắp xếp danh sách báo thức theo thời gian."""
        self.alarms.sort(key=lambda x: x.get("time", "00:00"))

    def save_alarms(self):
        self._sort_alarms()
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.alarms, f, ensure_ascii=False, indent=4)

    def add_alarm(self, time_str, message, days=None):
        if days is None:
            days = [0, 1, 2, 3, 4, 5, 6]  # Mặc định tất cả các ngày (T2-CN)
        self.alarms.append({
            "time": time_str,
            "message": message,
            "enabled": True,
            "days": days
        })
        self.save_alarms()

    def remove_alarm(self, index):
        if 0 <= index < len(self.alarms):
            self.alarms.pop(index)
            self.save_alarms()
            
    def remove_alarm_by_match(self, time_str, message):
        for i, alarm in enumerate(self.alarms):
            if alarm.get("time") == time_str and alarm.get("message") == message:
                self.alarms.pop(i)
                self.save_alarms()
                return True
        return False

    def toggle_alarm(self, index, enabled):
        if 0 <= index < len(self.alarms):
            self.alarms[index]["enabled"] = enabled
            self.save_alarms()

    def skip_alarm_once(self, time_str):
        """Bỏ qua báo thức 1 lần (chỉ ngày hôm nay)"""
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"{time_str}|{today}"
        self.skipped_alarms.add(key)

    def check_alarms(self):
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        today_str = now.strftime("%Y-%m-%d")
        current_weekday = now.weekday()  # 0=Monday, 6=Sunday
        
        # Dọn dẹp skip/pre-alarm cũ của ngày trước
        self.skipped_alarms = {k for k in self.skipped_alarms if k.endswith(today_str)}
        self.pre_alarm_shown = {k for k in self.pre_alarm_shown if k.endswith(today_str)}
        
        # Kiểm tra pre-alarm (10 phút trước)
        time_in_10min = (now + timedelta(minutes=10)).strftime("%H:%M")
        for alarm in self.alarms:
            alarm_days = alarm.get("days", [0, 1, 2, 3, 4, 5, 6])
            if alarm.get("enabled", True) and alarm.get("time") == time_in_10min and current_weekday in alarm_days:
                pre_key = f"{alarm['time']}|{today_str}"
                if pre_key not in self.pre_alarm_shown:
                    self.pre_alarm_shown.add(pre_key)
                    self.pre_alarm_triggered.emit(
                        alarm.get("time"),
                        alarm.get("message", "Đã đến giờ!")
                    )
        
        # Kiểm tra báo thức chính                                                 
        if current_time_str == self.last_triggered_time:
            return

        for alarm in self.alarms:
            alarm_days = alarm.get("days", [0, 1, 2, 3, 4, 5, 6])
            if alarm.get("enabled", True) and alarm.get("time") == current_time_str and current_weekday in alarm_days:
                skip_key = f"{current_time_str}|{today_str}"
                if skip_key in self.skipped_alarms:
                    # Đã được skip, bỏ qua lần này
                    self.skipped_alarms.discard(skip_key)
                    self.last_triggered_time = current_time_str
                    break
                self.last_triggered_time = current_time_str
                self.alarm_triggered.emit(alarm.get("message", "Đã đến giờ!"))
                break                                    
