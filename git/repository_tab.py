from PyQt6 import QtWidgets, QtCore, QtGui
import aiohttp
import asyncio
import webbrowser
from .search_widget import SearchWidget  # 导入新创建的 SearchWidget
import os
import base64
import requests
import zipfile
import io
import shutil
import re

class RepositoryTab(QtWidgets.QWidget):
    repo_info_updated = QtCore.pyqtSignal(dict)
    update_repo_list_signal = QtCore.pyqtSignal(list)
    add_repo_widget_signal = QtCore.pyqtSignal(dict)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.current_username = None
        self.current_token = None
        self.selected_repo = None
        self.all_repos = []
        self.progress_dialog = None
        self.current_search_text = ""
        self.has_refreshed = False
        
        self.update_repo_list_signal.connect(self._update_repo_list)
        self.add_repo_widget_signal.connect(self._add_repo_widget)
        
        self.init_ui()
        self.load_cached_repos()  # 在初始化时加载缓存数据

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()

        # 修改搜索部分
        search_layout = QtWidgets.QHBoxLayout()
        self.search_widget = SearchWidget()
        self.search_widget.search_input.returnPressed.connect(self.perform_search)  # 连接回车键事件
        search_layout.addWidget(self.search_widget)

        # 移除搜索按钮（如果有的话）

        layout.addLayout(search_layout)

        # 创一个滚动区域
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #f0f0f0;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #f0f0f0;
            }
        """)

        # 创建一个widget来包含所有仓库项目
        self.repo_container = QtWidgets.QWidget()
        self.repo_layout = QtWidgets.QVBoxLayout(self.repo_container)
        self.repo_layout.setSpacing(5)  # 减小仓项目之间的间距
        self.repo_layout.setContentsMargins(5, 5, 5, 5)  # 减小边距
        self.scroll_area.setWidget(self.repo_container)

        layout.addWidget(self.scroll_area)

        # 修改径布局，添加上传按钮
        path_layout = QtWidgets.QHBoxLayout()
        path_label = QtWidgets.QLabel("本地路径:")
        self.path_input = QtWidgets.QLineEdit()
        self.path_input.setPlaceholderText("输入本地仓库路径")
        file_button = QtWidgets.QPushButton("选择文件")
        folder_button = QtWidgets.QPushButton("选择文件夹")
        upload_button = QtWidgets.QPushButton("上传到GitHub")
        
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(file_button)
        path_layout.addWidget(folder_button)
        path_layout.addWidget(upload_button)
        
        layout.addLayout(path_layout)

        # 添加按钮布局到底部
        button_layout = QtWidgets.QHBoxLayout()
        
        # 添加刷新按钮
        self.refresh_button = QtWidgets.QPushButton("刷新仓库列表")
        self.refresh_button.clicked.connect(self.refresh_repos)
        button_layout.addWidget(self.refresh_button)

        # 添加一个新建仓库按钮
        self.create_repo_button = QtWidgets.QPushButton("新建仓库")
        self.create_repo_button.clicked.connect(self.create_new_repo)
        button_layout.addWidget(self.create_repo_button)

        # 添加一个删除仓库按钮
        self.delete_repo_button = QtWidgets.QPushButton("删除选中的仓库")
        self.delete_repo_button.clicked.connect(self.delete_selected_repo)
        button_layout.addWidget(self.delete_repo_button)

        # 添加克隆仓库按钮
        self.clone_button = QtWidgets.QPushButton("克隆选中的仓库")
        self.clone_button.clicked.connect(self.clone_selected_repo)
        button_layout.addWidget(self.clone_button)

        # 移除 GitHub 搜索按钮
        # self.github_search_button = QtWidgets.QPushButton("搜索 GitHub")
        # self.github_search_button.clicked.connect(self.open_github_search)
        # button_layout.addWidget(self.github_search_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 连接按钮点击事件
        file_button.clicked.connect(self.select_file)
        folder_button.clicked.connect(self.select_folder)
        upload_button.clicked.connect(self.upload_to_github)

    def perform_search(self):
        search_text = self.search_widget.search_input.text()
        search_option = self.search_widget.search_options.currentText()
        filtered_repos = self.filter_repos(search_text, search_option)
        self._update_repo_list(filtered_repos)  # 修改这里，使用 _update_repo_list 而不是 update_repo_list
        self.search_widget.set_result_count(len(filtered_repos))

    def filter_repos(self, search_text, search_option):
        self.current_search_text = search_text
        filtered_repos = SearchWidget.filter_repos(self.all_repos, search_text, search_option)
        return filtered_repos if filtered_repos is not None else []

    def refresh_repos(self):
        if self.current_token and self.current_username:
            self.create_progress_dialog("刷新仓库", "正在获取仓库列表...")
            self.main_window.preloader.clear_repos_cache(self.current_username)  # 只清除仓库缓存
            self.main_window.preloader.preload_completed.connect(self.on_refresh_completed)
            self.main_window.preloader.start_preload(self.current_token, self.current_username)
            self.main_window.log_message("开始刷新仓库列表")
        else:
            QtWidgets.QMessageBox.warning(self, "错误", "请先登录")
            self.main_window.log_message("尝试刷新仓库列表失败：未登录")

    def on_refresh_completed(self, repos):
        self.all_repos = repos
        self._update_repo_list(repos)
        self.has_refreshed = True
        self.main_window.log_message(f"刷新完成，获取到 {len(repos)} 个仓库")
        self.close_progress_dialog()
        self.main_window.preloader.preload_completed.disconnect(self.on_refresh_completed)

    def _update_repo_list(self, repos):
        print(f"开始更新仓库列表，共 {len(repos)} 个仓库")
        # 清除现有的仓库项目
        while self.repo_layout.count():
            item = self.repo_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加新的仓库项目
        for repo in repos:
            repo_widget = self.create_repo_widget(repo)
            self.repo_layout.addWidget(repo_widget)

        # 添加一个弹性空间到布局的末尾
        self.repo_layout.addStretch()

        # 更新搜索结果计数
        self.search_widget.set_result_count(len(repos))
        print("仓库列表更新完成")

    def update_search_count(self, count):
        self.search_widget.set_result_count(count)

    @QtCore.pyqtSlot(dict)
    def _add_repo_widget(self, repo):
        repo_widget = self.create_repo_widget(repo)
        self.repo_layout.addWidget(repo_widget)

    def create_repo_widget(self, repo):
        widget = QtWidgets.QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(2)  # 减小垂直间距
        layout.setContentsMargins(5, 5, 5, 5)  # 减小边距
        
        # 创建一个水平布局来包含名称和言
        top_layout = QtWidgets.QHBoxLayout()
        
        name_label = QtWidgets.QLabel(SearchWidget.highlight_text(repo['name'], self.current_search_text))
        name_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        name_label.setStyleSheet("font-weight: bold;")
        top_layout.addWidget(name_label)
        
        language_label = QtWidgets.QLabel(f"语言: {SearchWidget.highlight_text(repo['language'] or '未知', self.current_search_text)}")
        language_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        language_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        top_layout.addWidget(language_label)
        
        layout.addLayout(top_layout)
        
        url_label = QtWidgets.QLabel(f"<a href='{repo['html_url']}'>{repo['html_url']}</a>")
        url_label.setOpenExternalLinks(True)
        url_label.setStyleSheet("font-size: 8pt;")
        layout.addWidget(url_label)
        
        description_label = QtWidgets.QLabel(SearchWidget.highlight_text(repo['description'] or "No description", self.current_search_text))
        description_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        description_label.setWordWrap(True)
        description_label.setStyleSheet("font-size: 9pt;")
        layout.addWidget(description_label)
        
        # 创建一个标签来包含统计信息
        stats_label = QtWidgets.QLabel(f"星标: {repo['stargazers_count']} | 复刻: {repo['forks_count']}")
        stats_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        stats_label.setStyleSheet("font-size: 8pt; color: #666;")
        layout.addWidget(stats_label)
        
        widget.setLayout(layout)
        widget.repo_name = repo['name']  # 存储仓库名称
        widget.clone_url = repo['clone_url']  # 存储克隆 URL
        widget.mousePressEvent = lambda event: self.toggle_repo_selection(widget)
        
        return widget

    def toggle_repo_selection(self, widget):
        if self.selected_repo == widget.repo_name:
            self.selected_repo = None
            widget.setStyleSheet("""
                QWidget {
                    background-color: white;
                    border-radius: 5px;
                    padding: 10px;
                }
            """)
        else:
            if self.selected_repo:
                # 取消之前选中的仓库的高
                for i in range(self.repo_layout.count()):
                    item = self.repo_layout.itemAt(i)
                    if item.widget() and item.widget().repo_name == self.selected_repo:
                        item.widget().setStyleSheet("""
                            QWidget {
                                background-color: white;
                                border-radius: 5px;
                                padding: 10px;
                            }
                        """)
                        break
            self.selected_repo = widget.repo_name
            widget.setStyleSheet("""
                QWidget {
                    background-color: #e6f3ff;
                    border-radius: 5px;
                    padding: 10px;
                }
            """)

    @QtCore.pyqtSlot(str)
    def fetch_repos(self, token):
        asyncio.create_task(self.fetch_all_repos_async(token))

    def get_event_loop(self):
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def create_new_repo(self):
        if not self.current_token:
            QtWidgets.QMessageBox.warning(self, "错", "请先登录")
            return

        dialog = NewRepoDialog(self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            repo_name = dialog.repo_name.text()
            description = dialog.description.toPlainText()
            is_private = dialog.private_checkbox.isChecked()
            with_readme = dialog.readme_checkbox.isChecked()
            asyncio.get_event_loop().call_soon_threadsafe(
                lambda: asyncio.create_task(self.create_repo_async(repo_name, description, is_private, with_readme))
            )

    async def create_repo_async(self, name, description, private, with_readme):
        # 首先检查仓库名是否已存在
        if await self.check_repo_exists(name):
            QtCore.QMetaObject.invokeMethod(self, "show_warning_message",
                                            QtCore.Qt.ConnectionType.QueuedConnection,
                                            QtCore.Q_ARG(str, "错"),
                                            QtCore.Q_ARG(str, f"仓库名 '{name}' 已存在"))
            return

        headers = {'Authorization': f'token {self.current_token}'}
        data = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": with_readme
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post('https://api.github.com/user/repos', headers=headers, json=data) as response:
                    if response.status == 201:
                        QtCore.QMetaObject.invokeMethod(self, "show_info_message",
                                                        QtCore.Qt.ConnectionType.QueuedConnection,
                                                        QtCore.Q_ARG(str, "成功"),
                                                        QtCore.Q_ARG(str, f"仓库 '{name}' 创建成功"))
                        await self.fetch_all_repos_async(self.current_token)
                    else:
                        error_msg = await response.text()
                        QtCore.QMetaObject.invokeMethod(self, "show_warning_message",
                                                        QtCore.Qt.ConnectionType.QueuedConnection,
                                                        QtCore.Q_ARG(str, "错误"),
                                                        QtCore.Q_ARG(str, f"创建仓库失败: {error_msg}"))
            except aiohttp.ClientError as e:
                QtCore.QMetaObject.invokeMethod(self, "show_warning_message",
                                                QtCore.Qt.ConnectionType.QueuedConnection,
                                                QtCore.Q_ARG(str, "错"),
                                                QtCore.Q_ARG(str, f"创建仓库时发生错误: {str(e)}"))

    async def check_repo_exists(self, name):
        headers = {'Authorization': f'token {self.current_token}'}
        async with aiohttp.ClientSession() as session:
            try:
                url = f'https://api.github.com/repos/{self.current_username}/{name}'
                async with session.get(url, headers=headers) as response:
                    return response.status == 200
            except aiohttp.ClientError:
                return False

    def delete_selected_repo(self):
        if not self.selected_repo:
            QtWidgets.QMessageBox.warning(self, "警告", "请选择要删除的仓库")
            return
        
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle('确认删除')
        msg_box.setText(f'您确定要删除仓库 "{self.selected_repo}" 吗？\n此操作不可逆')
        msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        
        yes_button = msg_box.button(QtWidgets.QMessageBox.StandardButton.Yes)
        no_button = msg_box.button(QtWidgets.QMessageBox.StandardButton.No)
        yes_button.setText('是')
        no_button.setText('否')
        
        reply = msg_box.exec()
        
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            asyncio.get_event_loop().call_soon_threadsafe(
                lambda: asyncio.create_task(self.delete_repos_async([self.selected_repo]))
            )

    async def delete_repos_async(self, repo_names):
        headers = {'Authorization': f'token {self.current_token}'}
        async with aiohttp.ClientSession() as session:
            for repo_name in repo_names:
                try:
                    url = f'https://api.github.com/repos/{self.current_username}/{repo_name}'
                    async with session.delete(url, headers=headers) as response:
                        if response.status == 204:
                            print(f"Successfully deleted repository: {repo_name}")
                        else:
                            print(f"Failed to delete repository: {repo_name}. Status: {response.status}")
                except aiohttp.ClientError as e:
                    print(f"Error deleting repository {repo_name}: {str(e)}")
        
        # 删除选中的库
        self.selected_repo = None
        # 刷新仓表
        await self.fetch_all_repos_async(self.current_token)

    @QtCore.pyqtSlot(str, str)
    def show_warning_message(self, title, message):
        QtWidgets.QMessageBox.warning(self, title, message)

    @QtCore.pyqtSlot(str, str)
    def show_info_message(self, title, message):
        QtWidgets.QMessageBox.information(self, title, message)

    def select_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "选择文件", "", "All Files (*)")
        if file_path:
            self.path_input.setText(file_path)

    def select_folder(self):
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:
            self.path_input.setText(folder_path)

    def upload_to_github(self):
        if not self.selected_repo:
            QtWidgets.QMessageBox.warning(self, "警告", "请先选择一个仓库")
            return
        
        local_path = self.path_input.text()
        if not local_path:
            QtWidgets.QMessageBox.warning(self, "警告", "请选择要上传的文件或文件夹")
            return

        self.create_progress_dialog("上传文件", "正在上传文件...")
        asyncio.get_event_loop().call_soon_threadsafe(
            lambda: asyncio.create_task(self.upload_files_async(local_path, self.selected_repo))
        )

    async def upload_files_async(self, local_path, repo_name):
        headers = {'Authorization': f'token {self.current_token}'}
        base_url = f'https://api.github.com/repos/{self.current_username}/{repo_name}/contents/'

        # 获取选择的目录名称
        dir_name = os.path.basename(local_path)

        async with aiohttp.ClientSession() as session:
            if os.path.isfile(local_path):
                await self.upload_file(session, headers, base_url, local_path, dir_name)
            elif os.path.isdir(local_path):
                await self.upload_directory(session, headers, base_url, local_path, dir_name)
        
            if os.path.isdir(local_path) and not os.listdir(local_path):
                # 如果选择的是个空目录，保创建它
                await self.create_gitkeep(session, headers, base_url, dir_name)

        QtCore.QMetaObject.invokeMethod(self, "close_progress_dialog",
                                        QtCore.Qt.ConnectionType.QueuedConnection)
        QtCore.QMetaObject.invokeMethod(self, "show_upload_status",
                                        QtCore.Qt.ConnectionType.QueuedConnection,
                                        QtCore.Q_ARG(str, "success"),
                                        QtCore.Q_ARG(str, "上传完成"))

    async def upload_directory(self, session, headers, base_url, dir_path, parent_dir):
        # 首先创建父目录
        await self.create_directory(session, headers, base_url, parent_dir)

        # 然后上传所有文件和子目录
        for root, dirs, files in os.walk(dir_path):
            relative_root = os.path.relpath(root, dir_path)
            current_dir = os.path.join(parent_dir, relative_root).replace(os.path.sep, '/')
            if current_dir.endswith('.'):
                current_dir = current_dir[:-1]

            # 创当前目录
            if current_dir != parent_dir:
                await self.create_directory(session, headers, base_url, current_dir)

            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, dir_path)
                github_path = os.path.join(parent_dir, relative_path).replace(os.path.sep, '/')
                try:
                    await self.upload_file(session, headers, base_url, file_path, github_path)
                except Exception as e:
                    print(f"Error uploading {github_path}: {str(e)}")

        if not os.listdir(dir_path):
            await self.create_gitkeep(session, headers, base_url, parent_dir)

    async def upload_file(self, session, headers, base_url, file_path, github_path):
        file_name = os.path.basename(file_path)
        if file_name == 'tokens.json' or file_name.endswith('.pyc'):
            return

        try:
            with open(file_path, 'rb') as file:
                content = file.read()
        except IOError:
            return

        encoded_content = base64.b64encode(content).decode('utf-8')
        data = {
            "message": f"Upload {github_path}",
            "content": encoded_content
        }

        url = base_url + github_path
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    existing_file = await response.json()
                    data["sha"] = existing_file["sha"]

            async with session.put(url, headers=headers, json=data) as response:
                if response.status not in [201, 200]:
                    error_content = await response.text()
                    print(f"Failed to upload {github_path}. Status: {response.status}, Error: {error_content}")
        except Exception as e:
            print(f"Error during API request for {github_path}: {str(e)}")

    async def create_directory(self, session, headers, base_url, path):
        url = base_url + path + '/.gitkeep'
        data = {
            "message": f"Create directory: {path}",
            "content": base64.b64encode(b"").decode('utf-8')
        }
        
        async with session.put(url, headers=headers, json=data) as response:
            if response.status not in [201, 200, 422]:
                error_content = await response.text()
                print(f"Failed to create directory: {path}. Status: {response.status}, Error: {error_content}")

    async def create_gitkeep(self, session, headers, base_url, relative_path):
        relative_path = relative_path.lstrip('/')
        url = base_url + relative_path + '.gitkeep'
        data = {
            "message": f"Create directory: {relative_path}",
            "content": base64.b64encode(b"").decode('utf-8')
        }
        
        async with session.put(url, headers=headers, json=data) as response:
            if response.status not in [201, 200, 422]:
                error_content = await response.text()
                print(f"Failed to create directory: {relative_path}. Status: {response.status}, Error: {error_content}")

    @QtCore.pyqtSlot(str, str)
    def show_upload_status(self, status, message):
        if status == "success":
            QtWidgets.QMessageBox.information(self, "上传成功", message)
        else:
            QtWidgets.QMessageBox.warning(self, "上传失败", message)

    def clone_selected_repo(self):
        if not self.selected_repo:
            QtWidgets.QMessageBox.warning(self, "警告", "请先选择一个仓库")
            return
        
        for i in range(self.repo_layout.count()):
            item = self.repo_layout.itemAt(i)
            if item.widget() and item.widget().repo_name == self.selected_repo:
                self.clone_repository(item.widget().clone_url)
                break

    def clone_repository(self, clone_url):
        # 选择克隆目录
        clone_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "选择克隆目")
        if clone_dir:
            # 执行克隆操作
            asyncio.get_event_loop().call_soon_threadsafe(
                lambda: asyncio.create_task(self.clone_repo_async(clone_url, clone_dir))
            )

    async def clone_repo_async(self, clone_url, clone_dir):
        try:
            # 从 clone_url 中提取用户名和仓库名
            parts = clone_url.split('/')
            username = parts[-2]
            repo_name = parts[-1].replace('.git', '')

            # 构建 API URL
            api_url = f'https://api.github.com/repos/{username}/{repo_name}/zipball'

            # 发送请求下载 zip 文件
            response = requests.get(api_url, headers={'Authorization': f'token {self.current_token}'})
            
            if response.status_code == 200:
                # 使用仓库作为目标录
                repo_dir = os.path.join(clone_dir, repo_name)
                
                # 如果目录已存在，询问用户是否覆盖
                if os.path.exists(repo_dir):
                    reply = QtWidgets.QMessageBox.question(self, '目录已存在',
                                                           f'目录 "{repo_name}" 已存在。是否覆盖？',
                                                           QtWidgets.QMessageBox.StandardButton.Yes | 
                                                           QtWidgets.QMessageBox.StandardButton.No,
                                                           QtWidgets.QMessageBox.StandardButton.No)
                    if reply == QtWidgets.QMessageBox.StandardButton.No:
                        return
                    shutil.rmtree(repo_dir)  # 删除现有目录
                
                os.makedirs(repo_dir, exist_ok=True)

                # 解压 zip 文件
                with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                    zip_ref.extractall(repo_dir)

                # 移动文件到正确的位置
                extracted_dir = os.path.join(repo_dir, os.listdir(repo_dir)[0])
                for item in os.listdir(extracted_dir):
                    shutil.move(os.path.join(extracted_dir, item), repo_dir)
                os.rmdir(extracted_dir)

                QtCore.QMetaObject.invokeMethod(self, "show_info_message",
                                                QtCore.Qt.ConnectionType.QueuedConnection,
                                                QtCore.Q_ARG(str, "下载成功"),
                                                QtCore.Q_ARG(str, f"仓库内容已成功下载到 {repo_dir}"))
            else:
                QtCore.QMetaObject.invokeMethod(self, "show_warning_message",
                                                QtCore.Qt.ConnectionType.QueuedConnection,
                                                QtCore.Q_ARG(str, "下载失败"),
                                                QtCore.Q_ARG(str, f"下载失败: {response.status_code} - {response.text}"))
        except Exception as e:
            QtCore.QMetaObject.invokeMethod(self, "show_warning_message",
                                            QtCore.Qt.ConnectionType.QueuedConnection,
                                            QtCore.Q_ARG(str, "错误"),
                                            QtCore.Q_ARG(str, f"下载过程中发生错误: {str(e)}"))

    def create_progress_dialog(self, title, message):
        self.progress_dialog = QtWidgets.QProgressDialog(message, None, 0, 0, self)
        self.progress_dialog.setWindowTitle(title)
        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.show()

    @QtCore.pyqtSlot(int, int)
    def update_progress_dialog(self, value, maximum):
        if self.progress_dialog:
            self.progress_dialog.setMaximum(maximum)
            self.progress_dialog.setValue(value)

    @QtCore.pyqtSlot()
    def close_progress_dialog(self):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

    def update_repos(self, repos):
        self.all_repos = repos
        self._update_repo_list(repos)
        self.main_window.log_message(f"更新了 {len(repos)} 个仓库")

    def load_cached_repos(self):
        if self.current_username:
            cached_repos = self.main_window.preloader.get_preloaded_repos(self.current_username)
            if cached_repos:
                self.all_repos = cached_repos
                self._update_repo_list(cached_repos)
                self.main_window.log_message(f"从缓存加载了 {len(cached_repos)} 个仓库")
            else:
                self.main_window.log_message("没有找到缓存的仓库数据")
        else:
            print("未登录，无法加载缓存数据")  # 使用 print 而不是 log_message

    def update_repo_summary(self, summary):
        # 移除这个方法的内容，因为我们不再显示最常用的仓库摘要
        pass

class NewRepoDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建仓库")
        self.setMinimumWidth(400)
        layout = QtWidgets.QVBoxLayout(self)

        form_layout = QtWidgets.QFormLayout()

        self.repo_name = QtWidgets.QLineEdit(self)
        self.repo_name.setPlaceholderText("仓库名称")
        form_layout.addRow("仓库名称:", self.repo_name)

        self.description = QtWidgets.QTextEdit(self)
        self.description.setPlaceholderText("仓库描述（可选）")
        self.description.setMaximumHeight(100)
        form_layout.addRow("述:", self.description)

        self.private_checkbox = QtWidgets.QCheckBox("私有仓库", self)
        form_layout.addRow("", self.private_checkbox)

        self.readme_checkbox = QtWidgets.QCheckBox("初始化仓库并添加 README.md", self)
        self.readme_checkbox.setChecked(True)
        form_layout.addRow("", self.readme_checkbox)

        layout.addLayout(form_layout)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
            QtCore.Qt.Orientation.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)