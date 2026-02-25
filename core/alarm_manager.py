import json
import os
from datetime import datetime
from PySide6.QtCore import QObject, QTimer, Signal

class AlarmManager(QObject):
                                                       
    alarm_triggered = Signal(str)

    def __init__(self, config_folder="config", config_file="alarms.json"):
        super().__init__()
        app_data_dir = os.path.join(os.environ.get("APPDATA", ""), "Suki8898", "Suki Desktop Assistant")
        self.config_path = os.path.join(app_data_dir, config_file)
        self.alarms = []                                                                           
        self.load_alarms()
        
                                       
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

    def save_alarms(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.alarms, f, ensure_ascii=False, indent=4)

    def add_alarm(self, time_str, message):
        self.alarms.append({
            "time": time_str,
            "message": message,
            "enabled": True
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

    def check_alarms(self):
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        
                                                                  
        if current_time_str == self.last_triggered_time:
            return

        for alarm in self.alarms:
            if alarm.get("enabled", True) and alarm.get("time") == current_time_str:
                self.last_triggered_time = current_time_str
                self.alarm_triggered.emit(alarm.get("message", "Đã đến giờ!"))
                break                                    
