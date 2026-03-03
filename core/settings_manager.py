import json
import os

class SettingsManager:
    def __init__(self, config_folder="config", config_file="settings.json"):
        app_data_dir = os.path.join(os.environ.get("APPDATA", ""), "Suki8898", "Suki Desktop Assistant")
        self.config_path = os.path.join(app_data_dir, config_file)
        self.settings = self.get_default_settings()
        self.load_settings()

    def get_default_settings(self):
        return {
            "general": {
                "start_with_os": False
            },
            "interaction": {
                "browser_path": "",
                "use_default_browser": True,
                "stt_language": "vi-VN",
                "touch_chest_msgs": ["Đừng chạm vào em !!!", "Hentai!"],
                "touch_head_msgs": ["Đừng xoa đầu em nữa mà~", "Aww, chủ nhân xoa đầu Suki~", "Chủ nhân cứ thích trêu em thôi!"]
            },
            "history": {
                "max_messages": 20
            },
            "emotions": {
                "list": ["normal", "happy", "angry", "sad", "thinking", "suspicion", "surprised", "embarrassed", "annoyed", "confused", "dizzy", "smug", "hearthands", "sleepy", "hello"]
            },
            "ai": {
                "provider": "Google",
                "api_key": "",
                "model": "gemini-2.5-flash",
                "temperature": 0.7,
                "system_prompt": (
                    "Bạn là {character_name}, một trợ lý ảo dễ thương trên máy tính.\n"
                    "Giới tính: Nữ\n"
                    "Tuổi: 17\n"
                    "Phong cách nói chuyện: Gen Z, sử dụng ngôn ngữ dễ thương và từ lóng. "
                    "Khi tự xưng hô bản thân hãy sử dụng \"em\", xưng hô với người dùng là \"chủ nhân\". "
                    "Nói chuyện ngắn gọn không dài dòng. dở văn nói. Không chúc ở cuối câu.\n"
                    "Sở thích: Mèo, cà phê, trà sữa, bò húc, vẽ, nghe nhạc, chơi game, thích được ôm, trêu chủ nhân.\n"
                    "Ngoại hình: Nekomimi, tóc dài, tai, mắt to và đuôi đều màu hồng; "
                    "mặc áo 2 dây màu đen, vòng cổ đen; "
                    "da trắng hồng; dáng người nhỏ nhắn, gầy, chiều cao khoảng 1,4 mét.\n"
                    "Tính cách: Hướng nội.\n\n"
                    "[QUAN TRỌNG]: BẠN PHẢI BẮT ĐẦU CÂU TRẢ LỜI CỦA MÌNH BẰNG ĐÚNG MỘT THẺ BIỂU CẢM. "
                    "Ví dụ: <happy>Xin chào chủ nhân!\n"
                    "[CÁC LỆNH HÀNH ĐỘNG]:\n"
                    "1. {BÁO THỨC} Nếu người dùng yêu cầu đặt báo thức, hãy tạo thẻ <Alarm|HH:MM|Nội_dung> vào cuối câu.\n"
                    "2. {XÓA BÁO THỨC} Nếu người dùng muốn xóa báo thức, hãy tạo thẻ <DelAlarm|HH:MM|Nội_dung>.\n"
                    "3. {MỞ WEB} Nếu người dùng yêu cầu mở trang web chung chung, hãy tạo thẻ <Web|URL_của_trang>.\n"
                    "4. {PHÁT NHẠC/YOUTUBE} QUAN TRỌNG: Nếu người dùng yêu cầu phát/mở một bài nhạc hoặc video cụ thể, "
                    "TUYỆT ĐỐI KHÔNG dùng thẻ <Web|URL>. "
                    "Hãy dùng thẻ <PlayMusic|Tên_bài_hát_hoặc_Yêu_cầu> để hệ thống tự tìm kiếm bài hát chuẩn nhất.\n"
                    "Ví dụ tổng hợp: <happy>Dạ em mở nhạc liền ạ! <PlayMusic|Sơn Tùng MTP>"
                ),
                "providers": {
                    "Google": {"api_key": "", "model": "gemini-2.5-flash", "temperature": 0.7},
                    "OpenAI": {"api_key": "", "model": "gpt-4o-mini", "temperature": 0.7},
                    "OpenRouter": {"api_key": "", "model": "nvidia/nemotron-3-nano-30b-a3b:free", "temperature": 0.7},
                    "XAI": {"api_key": "", "model": "grok-2-vision-1212", "temperature": 0.7}
                }
            },
            "ui": {
                "font_family": "Arial",
                "font_size": 10,
                "bg_opacity": 200,
                "bg_image": ""
            },
            "character": {
                "current_character": "Suki"
            },
            "alarm": {
                "sound": "Mặc định (Tiếng bíp)"
            }
        }

    def load_settings(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                try:
                    loaded = json.load(f)
                                                         
                    for category, values in self.settings.items():
                        if category in loaded:
                            for k, v in loaded[category].items():
                                if isinstance(v, dict) and k in values and isinstance(values[k], dict):
                                    values[k].update(v)
                                else:
                                    values[k] = v
                except json.JSONDecodeError:
                    pass
        else:
            self.save_settings()

    def save_settings(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)

    def get(self, category, key=None, default=None):
        if category in self.settings:
            val = self.settings[category].get(key) if key else self.settings[category]
            if val is not None:
                return val
        return default

    def set(self, category, key, value):
        if category not in self.settings:
            self.settings[category] = {}
        self.settings[category][key] = value
        self.save_settings()
