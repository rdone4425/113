from PyQt6 import QtWidgets, QtCore, QtGui
import datetime
import os

class LogTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
        # 创建 data/log 目录
        self.data_dir = os.path.join(os.getcwd(), 'data')
        self.log_dir = os.path.join(self.data_dir, 'log')
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.log_file = os.path.join(self.log_dir, 'app.log')

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # 创建文本编辑器用于显示日志
        self.log_display = QtWidgets.QTextEdit()
        self.log_display.setReadOnly(True)
        layout.addWidget(self.log_display)

        # 创建清除按钮
        clear_button = QtWidgets.QPushButton("清除日志")
        clear_button.clicked.connect(self.clear_log)
        layout.addWidget(clear_button)

    def add_log(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_display.append(log_entry)
        
        # 将日志写入文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')

    def clear_log(self):
        self.log_display.clear()
        # 清除日志文件内容
        open(self.log_file, 'w').close()
