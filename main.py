import sys
import os
from types import ModuleType

# --- CRITICAL SAFEGUARD FOR FROZEN BUILDS ---
# Disable ChromaDB telemetry globally to avoid missing module errors (like posthog) in frozen builds.
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_DISABLE"] = "True"

# --------------------------------------------

from PySide6.QtWidgets import QApplication
from ui.main_window import SukiMainWindow

def main():
    app_data_dir = os.path.join(os.environ.get("APPDATA", ""), "Suki8898", "Suki Desktop Assistant")
    os.makedirs(app_data_dir, exist_ok=True)
    log_file_path = os.path.join(app_data_dir, "suki.log")
    log_file = open(log_file_path, "w", encoding="utf-8")
    sys.stdout = log_file
    sys.stderr = log_file
    
    import logging
    logging.basicConfig(level=logging.INFO, stream=log_file, format='%(asctime)s - %(levelname)s - %(message)s', force=True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
                                                                       
    app.setQuitOnLastWindowClosed(False)
    
    window = SukiMainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
