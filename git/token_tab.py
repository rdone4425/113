import sys
import site
sys.path.extend(site.getsitepackages())

import json
import asyncio
from PyQt6 import QtWidgets, QtCore
import aiohttp
import os
from cryptography.fernet import Fernet

class TokenTab(QtWidgets.QWidget):
    token_updated = QtCore.pyqtSignal(str)  # 修改信号以传递当前选中的token
    login_status_updated = QtCore.pyqtSignal(str, bool)
    username_updated = QtCore.pyqtSignal(str)  # 新增信号
    login_requested = QtCore.pyqtSignal(str)  # 新增信号

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.tokens = []
        self.current_token = None
        self.current_username = None
        
        # 创建 data/json 目录
        self.data_dir = os.path.join(os.getcwd(), 'data')
        self.json_dir = os.path.join(self.data_dir, 'json')
        os.makedirs(self.json_dir, exist_ok=True)
        
        # 确保在这里初始化 tokens_file
        self.tokens_file = os.path.join(self.json_dir, 'tokens.json')
        
        self.init_ui()
        self.load_tokens()
        self.login_requested.connect(self.login_async)
        self.load_saved_token()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()

        # 创建输入框和添加按钮
        input_layout = QtWidgets.QHBoxLayout()
        self.token_input = QtWidgets.QLineEdit()
        self.token_input.setPlaceholderText("输入新的token")
        add_button = QtWidgets.QPushButton("添加")
        add_button.clicked.connect(self.add_token)
        input_layout.addWidget(self.token_input)
        input_layout.addWidget(add_button)

        # 创建token数量标签
        self.token_count_label = QtWidgets.QLabel("当前token数量: 0")
        
        # 创建token列表
        self.token_list = QtWidgets.QListWidget()
        self.token_list.itemClicked.connect(self.select_token)
        self.token_list.itemDoubleClicked.connect(self.remove_token)

        # 创建删除按钮
        delete_button = QtWidgets.QPushButton("删除选中的Token")
        delete_button.clicked.connect(self.remove_selected_token)

        # 添加登录状态标签
        self.login_status_label = QtWidgets.QLabel("未登录")
        layout.addWidget(self.login_status_label)

        layout.addLayout(input_layout)
        layout.addWidget(self.token_count_label)
        layout.addWidget(self.token_list)
        layout.addWidget(delete_button)

        self.setLayout(layout)

    def load_tokens(self):
        if not os.path.exists(self.tokens_file):
            with open(self.tokens_file, 'w') as f:
                json.dump([], f)
            self.tokens = []
        else:
            try:
                with open(self.tokens_file, 'r') as f:
                    self.tokens = json.load(f)
                self.update_token_list()
                if self.tokens:
                    self.current_token = self.tokens[-1]
                    self.login_requested.emit(self.current_token)
            except json.JSONDecodeError:
                self.tokens = []
                self.save_tokens()  # 如果文件损坏，重新创建

    def save_tokens(self):
        try:
            with open(self.tokens_file, 'w') as f:
                json.dump(self.tokens, f)
        except IOError as e:
            QtWidgets.QMessageBox.warning(self, "错误", f"保存令牌时出错：{str(e)}")

    def load_saved_token(self):
        try:
            with open('key.bin', 'rb') as f:
                key = f.read()
            with open('encrypted_token.bin', 'rb') as f:
                encrypted_token = f.read()
            fernet = Fernet(key)
            decrypted_token = fernet.decrypt(encrypted_token).decode()
            self.current_token = decrypted_token
            self.login_requested.emit(self.current_token)
        except FileNotFoundError:
            pass  # 保存的 token

    def save_token(self, token):
        key = Fernet.generate_key()
        fernet = Fernet(key)
        encrypted_token = fernet.encrypt(token.encode())
        with open('encrypted_token.bin', 'wb') as f:
            f.write(encrypted_token)
        with open('key.bin', 'wb') as f:
            f.write(key)

    def add_token(self):
        token = self.token_input.text().strip()
        if token and token not in self.tokens:
            if len(token) >= 8:
                self.tokens.append(token)
                self.update_token_list()
                self.save_tokens()
                self.token_input.clear()
                self.save_token(token)
                QtWidgets.QMessageBox.information(self, "成功", f"成功添加新token。当前共有 {len(self.tokens)} 个token。")
                self.login_requested.emit(token)
                self.main_window.log_message(f"添加新 token：{token[:4]}...{token[-4:]}")  # 修改这行
            else:
                QtWidgets.QMessageBox.warning(self, "无效的令牌", "令牌长度应至少为8个字符。")
                self.main_window.log_message("尝试添加无效的 token")  # 修改这行
        elif token in self.tokens:
            QtWidgets.QMessageBox.warning(self, "重复的令牌", "此令牌已存在，请勿重复添加。")
            self.main_window.log_message("尝试添加重复的 token")  # 修改这行

    def remove_token(self, item):
        reply = QtWidgets.QMessageBox.question(self, '确认', '是否确定删除此token？',
                                                 QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            index = self.token_list.row(item)
            del self.tokens[index]
            self.update_token_list()
            self.save_tokens()

    def remove_selected_token(self):
        current_item = self.token_list.currentItem()
        if current_item:
            self.remove_token(current_item)

    def select_token(self, item):
        index = self.token_list.row(item)
        self.current_token = self.tokens[index]
        self.token_updated.emit(self.current_token)
        self.login_requested.emit(self.current_token)  # 发射信号而不是直接调用异步方法

    def update_token_list(self):
        self.token_list.clear()
        for i, token in enumerate(self.tokens):
            masked_token = f"{i+1}. " + token[:4] + '*' * (len(token) - 8) + token[-4:]
            self.token_list.addItem(masked_token)
        self.token_count_label.setText(f"当前token数量: {len(self.tokens)}")

    @QtCore.pyqtSlot(str)
    def login_async(self, token):
        print(f"login_async called with token: {token[:4]}...{token[-4:]}")  # 添加这行日志
        asyncio.get_event_loop().call_soon_threadsafe(
            lambda: asyncio.create_task(self.try_login_async(token))
        )

    async def try_login_async(self, token):
        headers = {'Authorization': f'token {token}'}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get('https://api.github.com/user', headers=headers, timeout=10) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        username = user_data.get('login', 'Unknown')
                        self.current_username = username  # 添加这行
                        QtCore.QMetaObject.invokeMethod(self, "update_login_status", 
                                                        QtCore.Qt.ConnectionType.QueuedConnection,
                                                        QtCore.Q_ARG(str, username), 
                                                        QtCore.Q_ARG(bool, True))
                    else:
                        QtCore.QMetaObject.invokeMethod(self, "update_login_status", 
                                                        QtCore.Qt.ConnectionType.QueuedConnection,
                                                        QtCore.Q_ARG(str, ""), 
                                                        QtCore.Q_ARG(bool, False))
            except aiohttp.ClientError as e:
                QtCore.QMetaObject.invokeMethod(self, "update_login_status", 
                                                QtCore.Qt.ConnectionType.QueuedConnection,
                                                QtCore.Q_ARG(str, ""), 
                                                QtCore.Q_ARG(bool, False))

    @QtCore.pyqtSlot(str, bool)
    def update_login_status(self, username, success):
        if success:
            self.login_status_label.setText(f"已登录: {username}")
            self.login_status_updated.emit(self.current_token, True)
            self.username_updated.emit(username)
            self.token_updated.emit(self.current_token)
            self.save_token(self.current_token)  # 保存成功登录的 token
        else:
            self.login_status_label.setText("登录失败")
            self.login_status_updated.emit(self.current_token, False)
            self.username_updated.emit("")
        
        self.current_username = username if success else None

    def try_login_with_last_token(self):
        if self.tokens:
            self.current_token = self.tokens[-1]
            print(f"Attempting to login with token: {self.current_token[:4]}...{self.current_token[-4:]}")  # 添加这行日志
            self.login_requested.emit(self.current_token)
        else:
            print("No tokens available for automatic login")  # 添加这行日志
            self.update_login_status("", False)
