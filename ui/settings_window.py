import os
import webbrowser
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel, 
    QPushButton, QHBoxLayout, QFormLayout, QLineEdit, 
    QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QCheckBox,
    QTimeEdit, QListWidget, QListWidgetItem, QFileDialog
)
from PySide6.QtGui import QFontDatabase, QFont, QPixmap, QPainter, QPainterPath
from PySide6.QtCore import Qt, QRectF
from core.settings_manager import SettingsManager

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

class SettingsWindow(QWidget):
    def __init__(self, settings_manager=None, alarm_manager=None, llm_manager=None, on_save_callback=None):
        super().__init__()
        self.settings_manager = settings_manager or SettingsManager()
        self.alarm_manager = alarm_manager
        self.llm_manager = llm_manager
        self.on_save_callback = on_save_callback
        char_name = self.settings_manager.get("character", "current_character", default="Suki")
        self.setWindowTitle(f"Cài đặt - {char_name}")
        self.resize(650, 500)
        
        icon_path = resource_path(os.path.join("icons", "Suki.ico"))
        if os.path.exists(icon_path):
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))
            
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
              
        self.tab_general = QWidget()
        self.tab_interaction = QWidget()
        self.tab_knowledge = QWidget()
        self.tab_history = QWidget()
        self.tab_ai = QWidget()
        self.tab_ui = QWidget()
        self.tab_character = QWidget()
        self.tab_emotion = QWidget()
        self.tab_alarm = QWidget()
        self.tab_about = QWidget()
        
        self.tabs.addTab(self.tab_general, "Chung")
        self.tabs.addTab(self.tab_interaction, "Tương tác")
        self.tabs.addTab(self.tab_knowledge, "Kiến thức")
        self.tabs.addTab(self.tab_history, "Lịch sử")
        self.tabs.addTab(self.tab_ai, "AI")
        self.tabs.addTab(self.tab_ui, "Giao diện")
        self.tabs.addTab(self.tab_character, "Nhân vật")
        self.tabs.addTab(self.tab_emotion, "Biểu cảm")
        self.tabs.addTab(self.tab_alarm, "Hẹn giờ")
        self.tabs.addTab(self.tab_about, "Suki :3")
        
        self.setup_general_tab()
        self.setup_interaction_tab()
        self.setup_knowledge_tab()
        self.setup_history_tab()
        self.setup_ai_tab()
        self.setup_ui_tab()
        self.setup_character_tab()
        self.setup_emotion_tab()
        self.setup_alarm_tab()
        self.setup_about_tab()
        
                        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_save = QPushButton("Lưu")
        self.btn_save.clicked.connect(self.save_data)
        btn_layout.addWidget(self.btn_save)
        
        self.btn_cancel = QPushButton("Hủy")
        self.btn_cancel.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)
        
    def setup_general_tab(self):
        layout = QFormLayout(self.tab_general)
        self.chk_start_os = QCheckBox("Khởi động cùng Windows")
        layout.addRow("Hệ thống:", self.chk_start_os)
        
    def setup_interaction_tab(self):
        layout = QFormLayout(self.tab_interaction)
        
        self.chk_default_browser = QCheckBox("Sử dụng trình duyệt mặc định")
        self.chk_default_browser.stateChanged.connect(self.on_default_browser_changed)
        layout.addRow("Web:", self.chk_default_browser)
        
        browser_layout = QHBoxLayout()
        self.txt_browser_path = QLineEdit()
        self.btn_browse_browser = QPushButton("Chọn .exe")
        self.btn_browse_browser.clicked.connect(self.browse_browser)
        browser_layout.addWidget(self.txt_browser_path)
        browser_layout.addWidget(self.btn_browse_browser)
        layout.addRow("Trình duyệt khác:", browser_layout)
        
        self.cmb_stt_language = QComboBox()
        self.cmb_stt_language.addItems([
            "vi-VN", "en-US", "ja-JP", "ko-KR", "zh-CN", "zh-TW", 
            "fr-FR", "de-DE", "es-ES", "ru-RU", "th-TH"
        ])
        layout.addRow("Nhận diện giọng nói:", self.cmb_stt_language)

        self.txt_touch_chest = QLineEdit()
        self.txt_touch_chest.setPlaceholderText("Các câu cách nhau bởi dấu phẩy")
        layout.addRow("Câu thoại khi chạm ngực:", self.txt_touch_chest)

        self.txt_touch_head = QLineEdit()
        self.txt_touch_head.setPlaceholderText("Các câu cách nhau bởi dấu phẩy")
        layout.addRow("Câu thoại khi xoa đầu:", self.txt_touch_head)

    def on_default_browser_changed(self, state):
        is_default = (state == Qt.Checked)
        self.txt_browser_path.setEnabled(not is_default)
        self.btn_browse_browser.setEnabled(not is_default)
        if is_default:
            self.txt_browser_path.setStyleSheet("background-color: #555;")
        else:
            self.txt_browser_path.setStyleSheet("")
            
    def browse_browser(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file thực thi trình duyệt", "", "Executable (*.exe);;All Files (*)")
        if path:
            self.txt_browser_path.setText(path)
        
    def setup_knowledge_tab(self):
        layout = QVBoxLayout(self.tab_knowledge)
        
        self.txt_static_knowledge = QTextEdit()
        self.txt_static_knowledge.setPlaceholderText("Nhập các kiến thức bạn muốn trợ lý luôn luôn ghi nhớ (ví dụ: công việc của bạn, sở thích, dự án hiện tại,...)")
        layout.addWidget(self.txt_static_knowledge)
        
    def setup_history_tab(self):
        layout = QVBoxLayout(self.tab_history)
        
        cnt_layout = QHBoxLayout()
        cnt_layout.addWidget(QLabel("Số lượng lịch sử tối đa:"))
        self.spn_max_history = QSpinBox()
        self.spn_max_history.setRange(5, 100)
        cnt_layout.addWidget(self.spn_max_history)
        
        self.btn_clear_history = QPushButton("Xóa lịch sử")
        self.btn_clear_history.clicked.connect(self.clear_history)
        cnt_layout.addWidget(self.btn_clear_history)
        
        cnt_layout.addStretch()
        layout.addLayout(cnt_layout)
        
        lbl_history = QLabel("Lịch sử trò chuyện:")
        layout.addWidget(lbl_history)
        
        self.txt_history = QTextEdit()
        self.txt_history.setReadOnly(True)
        self.load_chat_history()
        layout.addWidget(self.txt_history)

    def clear_history(self):
        if self.llm_manager:
            self.llm_manager.history = []
            self.llm_manager.save_history()
            self.load_chat_history()
        
    def load_chat_history(self):
        if hasattr(self, 'txt_history') and self.llm_manager:
            hist_str = ""
            for msg in self.llm_manager.history:
                role = "Bạn" if msg["role"] == "user" else "Suki"
                hist_str += f"{role}: {msg['content']}\n\n"
            self.txt_history.setPlainText(hist_str)
                              
            scroll_bar = self.txt_history.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())
        
    def setup_ai_tab(self):
        layout = QFormLayout(self.tab_ai)
        
        self.cmb_provider = QComboBox()
        self.cmb_provider.addItems(["Google", "OpenAI", "OpenRouter", "XAI", "LM Studio"])
        self.cmb_provider.currentTextChanged.connect(self.on_provider_changed)
        
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(self.cmb_provider)
        
        self.lbl_port = QLabel("Port:")
        self.spn_port = QSpinBox()
        self.spn_port.setRange(1, 65535)
        self.spn_port.setValue(1234)
        self.spn_port.setFixedWidth(80)
        
        provider_layout.addWidget(self.lbl_port)
        provider_layout.addWidget(self.spn_port)
        
        # Hide port by default
        self.lbl_port.setVisible(False)
        self.spn_port.setVisible(False)
        
        layout.addRow("Provider:", provider_layout)
        
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.Password)
        layout.addRow("API Key:", self.txt_api_key)
        
        model_layout = QHBoxLayout()
        self.txt_model = QLineEdit()
        self.btn_model_doc = QPushButton("Xem model hiện có")
        self.btn_model_doc.setFixedWidth(160)
        self.btn_model_doc.clicked.connect(self.open_model_docs)
        self.btn_model_doc.setCursor(Qt.PointingHandCursor)
        model_layout.addWidget(self.txt_model)
        model_layout.addWidget(self.btn_model_doc)
        layout.addRow("Model:", model_layout)
        
        self.spn_temp = QDoubleSpinBox()
        self.spn_temp.setRange(0.0, 2.0)
        self.spn_temp.setSingleStep(0.1)
        layout.addRow("Temperature:", self.spn_temp)
        
        self.txt_prompt = QTextEdit()
        layout.addRow("System prompt:", self.txt_prompt)
        
    def on_provider_changed(self, new_provider):
        if hasattr(self, 'providers_data') and hasattr(self, 'current_provider'):
            old_provider = self.current_provider
            
                      
            if old_provider in self.providers_data:
                self.providers_data[old_provider]["api_key"] = self.txt_api_key.text()
                self.providers_data[old_provider]["model"] = self.txt_model.text()
                self.providers_data[old_provider]["temperature"] = self.spn_temp.value()
                if old_provider == "LM Studio":
                    self.providers_data[old_provider]["port"] = self.spn_port.value()
                
                      
            if new_provider in self.providers_data:
                provider_cfg = self.providers_data[new_provider]
                self.txt_api_key.setText(provider_cfg.get("api_key", ""))
                self.txt_model.setText(provider_cfg.get("model", ""))
                self.spn_temp.setValue(provider_cfg.get("temperature", 0.7))
                if new_provider == "LM Studio":
                    self.spn_port.setValue(provider_cfg.get("port", 1234))
                
            self.current_provider = new_provider
            
            # Show/hide port spinbox
            is_lm_studio = (new_provider == "LM Studio")
            self.lbl_port.setVisible(is_lm_studio)
            self.spn_port.setVisible(is_lm_studio)
        
    def open_model_docs(self):
        links = {
            "Google": "https://ai.google.dev/gemini-api/docs/models",
            "OpenAI": "https://developers.openai.com/api/docs/pricing",
            "OpenRouter": "https://openrouter.ai/models",
            "XAI": "https://console.x.ai/",
            "LM Studio": "https://lmstudio.ai/docs"
        }
        url = links.get(self.cmb_provider.currentText(), "")
        if url:
            webbrowser.open(url)

    def setup_ui_tab(self):
        layout = QFormLayout(self.tab_ui)
        self.cmb_font = QComboBox()
        self.cmb_font.addItems(QFontDatabase.families())
        layout.addRow("Phông chữ:", self.cmb_font)
        
        self.spn_font_size = QSpinBox()
        self.spn_font_size.setRange(8, 72)
        layout.addRow("Cỡ chữ:", self.spn_font_size)
        
                                  
        self.cmb_bg = QComboBox()
        self.cmb_bg.addItem("")                               
        
                                            
        bg_dir = external_resource_path(os.path.join("assets", "backgrounds"))
        if os.path.exists(bg_dir):
            for file in os.listdir(bg_dir):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    self.cmb_bg.addItem(file)
        
        layout.addRow("Hình nền nhân vật:", self.cmb_bg)
        
    def setup_character_tab(self):
        layout = QFormLayout(self.tab_character)
        
        self.cmb_character = QComboBox()
        char_base_dir = external_resource_path(os.path.join("assets", "character"))
        if os.path.exists(char_base_dir):
            for d in os.listdir(char_base_dir):
                if os.path.isdir(os.path.join(char_base_dir, d)):
                    self.cmb_character.addItem(d)
        layout.addRow("Chọn nhân vật:", self.cmb_character)
        
    def setup_emotion_tab(self):
        layout = QVBoxLayout(self.tab_emotion)
        layout.addWidget(QLabel("Danh sách các thẻ biểu cảm:"))
        
        self.lst_emotions = QListWidget()
        layout.addWidget(self.lst_emotions)
        
        form = QHBoxLayout()
        self.txt_emotion_add = QLineEdit()
        self.txt_emotion_add.setPlaceholderText("Tên biểu cảm mới")
        btn_add_emotion = QPushButton("Thêm")
        btn_add_emotion.clicked.connect(self.add_emotion)
        btn_remove_emotion = QPushButton("Xóa chọn")
        btn_remove_emotion.clicked.connect(self.remove_emotion)
        
        form.addWidget(self.txt_emotion_add)
        form.addWidget(btn_add_emotion)
        form.addWidget(btn_remove_emotion)
        layout.addLayout(form)
        
    def add_emotion(self):
        text = self.txt_emotion_add.text().strip().lower()
        if text:
            items = [self.lst_emotions.item(i).text() for i in range(self.lst_emotions.count())]
            if text not in items:
                self.lst_emotions.addItem(text)
            self.txt_emotion_add.clear()
            
    def remove_emotion(self):
        for item in self.lst_emotions.selectedItems():
            self.lst_emotions.takeItem(self.lst_emotions.row(item))
        
    def setup_alarm_tab(self):
        layout = QVBoxLayout(self.tab_alarm)
        
        self.lst_alarms = QListWidget()
        layout.addWidget(self.lst_alarms)
        
        form_layout = QHBoxLayout()
        self.time_picker = QTimeEdit()
        self.time_picker.setDisplayFormat("HH:mm")
        form_layout.addWidget(QLabel("Giờ:"))
        form_layout.addWidget(self.time_picker)
        
        self.txt_alarm_msg = QLineEdit()
        self.txt_alarm_msg.setPlaceholderText("Nội dung")
        form_layout.addWidget(self.txt_alarm_msg)
        
        btn_add = QPushButton("Thêm")
        btn_add.clicked.connect(self.add_alarm)
        form_layout.addWidget(btn_add)
        
        btn_remove = QPushButton("Xóa chọn")
        btn_remove.clicked.connect(self.remove_alarm)
        form_layout.addWidget(btn_remove)
        
        layout.addLayout(form_layout)
        
                                   
        sound_layout = QHBoxLayout()
        sound_layout.addWidget(QLabel("Âm báo:"))
        self.cmb_alarm_sound = QComboBox()
        self.cmb_alarm_sound.addItem("Mặc định")
        sound_dir = external_resource_path(os.path.join("assets", "sounds"))
        if os.path.exists(sound_dir):
            for file in os.listdir(sound_dir):
                if file.lower().endswith(('.wav', '.mp3', '.ogg')):
                    self.cmb_alarm_sound.addItem(file)
        sound_layout.addWidget(self.cmb_alarm_sound)
        layout.addLayout(sound_layout)
        
        self.load_alarms()
        
    def load_alarms(self):
        if not self.alarm_manager: return
        self.lst_alarms.clear()
        for i, alarm in enumerate(self.alarm_manager.alarms):
            time_str = alarm.get("time", "00:00")
            msg = alarm.get("message", "")
            item = QListWidgetItem(f"{time_str} - {msg}")
            self.lst_alarms.addItem(item)
            
    def add_alarm(self):
        if not self.alarm_manager: return
        time_str = self.time_picker.time().toString("HH:mm")
        msg = self.txt_alarm_msg.text() or "Báo thức!"
        self.alarm_manager.add_alarm(time_str, msg)
        self.load_alarms()
        self.txt_alarm_msg.clear()
        
    def remove_alarm(self):
        if not self.alarm_manager: return
        row = self.lst_alarms.currentRow()
        if row >= 0:
            self.alarm_manager.remove_alarm(row)
            self.load_alarms()

    def setup_about_tab(self):
        layout = QVBoxLayout(self.tab_about)
        
        lbl_title = QLabel("Suki Desktop Assistant")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)
        
        lbl_desc = QLabel("Trợ lý ảo thông minh.")
        lbl_desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_desc)
        
        lbl_version = QLabel("Phiên bản: 1.1.0")
        lbl_version.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_version)
        
        def create_link_row(label_text, link_text, url):
            row = QHBoxLayout()
            row.addStretch()
            if label_text:
                lbl = QLabel(label_text)
                row.addWidget(lbl)
            
            link = QLabel(f'<a href="{url}" style="color: #db9aaa; text-decoration: none;">{link_text}</a>')
            link.setOpenExternalLinks(True)
            row.addWidget(link)
            row.addStretch()
            layout.addLayout(row)
            
        create_link_row("Tác giả: ", "Suki", "https://github.com/Suki8898")
        create_link_row("Hỗ trợ: ", "Buymeacoffee", "https://buymeacoffee.com/suki8898")
        create_link_row("Giấy phép: ", "MIT", "https://github.com/Suki8898/Suki-Desktop-Assistant/blob/main/LICENSE")

                      
        icon_layout = QHBoxLayout()
        icon_layout.setAlignment(Qt.AlignCenter)
        
        links = [
            ("github.png", "https://github.com/Suki8898"),
            ("discord.png", "https://discord.com/users/494332657098817557"),
            ("facebook.png", "https://www.facebook.com/suki8898/"),
            ("tiktok.png", "https://www.tiktok.com/@suki8898"),
            ("youtube.png", "https://www.youtube.com/suki8898")
        ]
        
        for icon_file, url in links:
            icon_path = resource_path(os.path.join("icons", icon_file)).replace("\\", "/")
            if os.path.exists(icon_path):
                lbl_icon = QLabel()
                                                       
                lbl_icon.setText(f'<a href="{url}"><img src="{icon_path}" width="24" height="24"></a>')
                lbl_icon.setOpenExternalLinks(True)
                icon_layout.addWidget(lbl_icon)
                
        layout.addLayout(icon_layout)
        
                                  
        image_path = resource_path(os.path.join("Suki UwU", "Suki.png"))
        if os.path.exists(image_path):
            lbl_img = QLabel()
            original_pixmap = QPixmap(image_path)
            if not original_pixmap.isNull():
                scaled_pixmap = original_pixmap.scaled(250, 250, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                rounded = QPixmap(scaled_pixmap.size())
                rounded.fill(Qt.transparent)
                
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.Antialiasing)
                path = QPainterPath()
                path.addRoundedRect(QRectF(0, 0, scaled_pixmap.width(), scaled_pixmap.height()), 20, 20)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.end()
                
                lbl_img.setPixmap(rounded)
                lbl_img.setAlignment(Qt.AlignCenter)
                layout.addWidget(lbl_img)
                
        layout.addStretch()
        
    def load_data(self):
        if not self.settings_manager: return
        
        self.chk_start_os.setChecked(self.settings_manager.get("general", "start_with_os"))
        
        use_def_browser = self.settings_manager.get("interaction", "use_default_browser", default=True)
        self.chk_default_browser.setChecked(use_def_browser)
        self.txt_browser_path.setText(self.settings_manager.get("interaction", "browser_path", default=""))
        self.on_default_browser_changed(Qt.Checked if use_def_browser else Qt.Unchecked)
        
        stt_lang = self.settings_manager.get("interaction", "stt_language", default="vi-VN")
        idx_lang = self.cmb_stt_language.findText(stt_lang)
        if idx_lang >= 0:
            self.cmb_stt_language.setCurrentIndex(idx_lang)
            
        chest_msgs = self.settings_manager.get("interaction", "touch_chest_msgs", default=["Đừng chạm vào em !!!", "Hentai!"])
        self.txt_touch_chest.setText(", ".join(chest_msgs))
        
        head_msgs = self.settings_manager.get("interaction", "touch_head_msgs", default=["Đừng xoa đầu em nữa mà~", "Aww, chủ nhân xoa đầu Suki~", "Chủ nhân cứ thích trêu em thôi!"])
        self.txt_touch_head.setText(", ".join(head_msgs))
            
        self.spn_max_history.setValue(self.settings_manager.get("history", "max_messages", default=20))
        
        curr_char = self.settings_manager.get("character", "current_character", default="Suki")
        idx_char = self.cmb_character.findText(curr_char)
        if idx_char >= 0:
            self.cmb_character.setCurrentIndex(idx_char)
            
        emotions_list = self.settings_manager.get("emotions", "list", default=[])
        self.lst_emotions.clear()
        self.lst_emotions.addItems(emotions_list)
        
                        
        self.txt_static_knowledge.setPlainText(self.settings_manager.get("general", "static_knowledge", default=""))
        
        self.cmb_provider.setCurrentText(self.settings_manager.get("ai", "provider"))
        self.current_provider = self.cmb_provider.currentText()
        
        providers_dict = self.settings_manager.get("ai", "providers")
        if providers_dict:
            import json
                                                               
            self.providers_data = json.loads(json.dumps(providers_dict))
            if self.current_provider in self.providers_data:
                provider_cfg = self.providers_data[self.current_provider]
                self.txt_api_key.setText(provider_cfg.get("api_key", ""))
                self.txt_model.setText(provider_cfg.get("model", ""))
                self.spn_temp.setValue(provider_cfg.get("temperature", 0.7))
                if self.current_provider == "LM Studio":
                    self.spn_port.setValue(provider_cfg.get("port", 1234))
                    self.lbl_port.setVisible(True)
                    self.spn_port.setVisible(True)
            else:
                self.txt_api_key.setText(self.settings_manager.get("ai", "api_key", default=""))
                self.txt_model.setText(self.settings_manager.get("ai", "model", default=""))
                self.spn_temp.setValue(self.settings_manager.get("ai", "temperature", default=0.7))
        else:
            self.txt_api_key.setText(self.settings_manager.get("ai", "api_key", default=""))
            self.txt_model.setText(self.settings_manager.get("ai", "model", default=""))
            self.spn_temp.setValue(self.settings_manager.get("ai", "temperature", default=0.7))

        self.txt_prompt.setPlainText(self.settings_manager.get("ai", "system_prompt"))
        
        font_family = self.settings_manager.get("ui", "font_family")
        index_font = self.cmb_font.findText(font_family)
        if index_font >= 0:
            self.cmb_font.setCurrentIndex(index_font)
            
        self.spn_font_size.setValue(self.settings_manager.get("ui", "font_size"))
        
                                               
        bg_image = self.settings_manager.get("ui", "bg_image")
        index = self.cmb_bg.findText(bg_image)
        if index >= 0:
            self.cmb_bg.setCurrentIndex(index)
            
        alarm_sound = self.settings_manager.get("alarm", "sound", default="Mặc định (Tiếng bíp)")
        index_sound = self.cmb_alarm_sound.findText(alarm_sound)
        if index_sound >= 0:
            self.cmb_alarm_sound.setCurrentIndex(index_sound)
        
    def save_data(self):
        if not self.settings_manager: return
        
        self.settings_manager.set("general", "start_with_os", self.chk_start_os.isChecked())
        self.settings_manager.set("general", "static_knowledge", self.txt_static_knowledge.toPlainText())
        
        self.settings_manager.set("interaction", "use_default_browser", self.chk_default_browser.isChecked())
        self.settings_manager.set("interaction", "browser_path", self.txt_browser_path.text())
        self.settings_manager.set("interaction", "stt_language", self.cmb_stt_language.currentText())
        
        chest_msgs = [m.strip() for m in self.txt_touch_chest.text().split(",") if m.strip()]
        self.settings_manager.set("interaction", "touch_chest_msgs", chest_msgs)
        
        head_msgs = [m.strip() for m in self.txt_touch_head.text().split(",") if m.strip()]
        self.settings_manager.set("interaction", "touch_head_msgs", head_msgs)
        
        self.settings_manager.set("history", "max_messages", self.spn_max_history.value())
        if self.llm_manager:
            self.llm_manager.max_history = self.spn_max_history.value()
            
        self.settings_manager.set("character", "current_character", self.cmb_character.currentText())
        
        emotions_list = [self.lst_emotions.item(i).text() for i in range(self.lst_emotions.count())]
        self.settings_manager.set("emotions", "list", emotions_list)
        
        self.settings_manager.set("ai", "provider", self.cmb_provider.currentText())
        
        current_provider = self.cmb_provider.currentText()
        if hasattr(self, 'providers_data'):
            if current_provider in self.providers_data:
                self.providers_data[current_provider]["api_key"] = self.txt_api_key.text()
                self.providers_data[current_provider]["model"] = self.txt_model.text()
                self.providers_data[current_provider]["temperature"] = self.spn_temp.value()
                if current_provider == "LM Studio":
                    self.providers_data[current_provider]["port"] = self.spn_port.value()
            self.settings_manager.set("ai", "providers", self.providers_data)
        
                                                     
        self.settings_manager.set("ai", "api_key", self.txt_api_key.text())
        self.settings_manager.set("ai", "model", self.txt_model.text())
        self.settings_manager.set("ai", "temperature", self.spn_temp.value())

        self.settings_manager.set("ai", "system_prompt", self.txt_prompt.toPlainText())
        
        self.settings_manager.set("ui", "font_family", self.cmb_font.currentText())
        self.settings_manager.set("ui", "font_size", self.spn_font_size.value())
        self.settings_manager.set("ui", "bg_image", self.cmb_bg.currentText())
        self.settings_manager.set("alarm", "sound", self.cmb_alarm_sound.currentText())
        
        if self.on_save_callback:
            self.on_save_callback()
            
        self.set_autostart(self.chk_start_os.isChecked())
        self.close()

    def set_autostart(self, enable):
        import sys
        import os
        import winreg
        
        app_name = "SukiDesktopAssistant"
        app_path = os.path.abspath(sys.argv[0])
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        try:
            with winreg.OpenKey(key, subkey, 0, winreg.KEY_WRITE) as regkey:
                if enable:
                    winreg.SetValueEx(regkey, app_name, 0, winreg.REG_SZ, app_path)
                else:
                    try:
                        winreg.DeleteValue(regkey, app_name)
                    except OSError:
                        pass
            return True
        except Exception as e:
            print(f"Error modifying startup: {e}")
            return False
