from PyQt6 import QtWidgets, QtCore
import aiohttp
import asyncio
from .search_widget import SearchWidget
import json
import os
from datetime import datetime, timedelta

class StarredTab(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.starred_repos = []
        self.filtered_repos = []
        self.init_ui()
        self.load_cached_repos()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # 添加搜索组件
        self.search_widget = SearchWidget()
        self.search_widget.search_changed.connect(self.filter_repos)
        self.search_widget.search_input.returnPressed.connect(self.perform_search)  # 添加回车键触发搜索
        layout.addWidget(self.search_widget)

        # 刷新按钮
        self.refresh_button = QtWidgets.QPushButton("刷新星标仓库")
        self.refresh_button.clicked.connect(self.refresh_starred_repos)
        layout.addWidget(self.refresh_button)

        # 创建一个滚动区域
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

        # 创建一个widget来包含所有星标仓库项目
        self.repo_container = QtWidgets.QWidget()
        self.repo_layout = QtWidgets.QVBoxLayout(self.repo_container)
        self.repo_layout.setSpacing(5)  # 减小仓库项目之间的间距
        self.repo_layout.setContentsMargins(5, 5, 5, 5)  # 减小边距
        self.scroll_area.setWidget(self.repo_container)

        layout.addWidget(self.scroll_area)

    def perform_search(self):
        search_text = self.search_widget.search_input.text()
        search_option = self.search_widget.search_options.currentText()
        self.filter_repos(search_text, search_option)

    def refresh_starred_repos(self):
        if self.main_window.token_tab.current_token:
            username = self.main_window.token_tab.current_username
            self.main_window.preloader.clear_starred_cache(username)  # 只清除星标仓库缓存
            self.main_window.preloader.starred_repos_loaded.connect(self.on_refresh_completed)
            self.main_window.preloader.start_preload(self.main_window.token_tab.current_token, username)
            self.main_window.log_message("开始刷新星标仓库列表")
        else:
            QtWidgets.QMessageBox.warning(self, "错误", "请先登录")
            self.main_window.log_message("尝试刷新星标仓库列表失败：未登录")

    def on_refresh_completed(self, repos):
        self.starred_repos = repos
        self.filtered_repos = self.starred_repos
        self.update_starred_list()
        self.main_window.log_message(f"刷新完成，获取到 {len(self.starred_repos)} 个星标仓库")
        self.main_window.preloader.starred_repos_loaded.disconnect(self.on_refresh_completed)

    def load_cached_repos(self):
        if hasattr(self.main_window, 'token_tab') and self.main_window.token_tab.current_username:
            username = self.main_window.token_tab.current_username
            cached_repos = self.main_window.preloader.get_preloaded_starred_repos(username)
            if cached_repos:
                self.starred_repos = cached_repos
                self.filtered_repos = self.starred_repos
                self.update_starred_list()
                self.main_window.log_message(f"从缓存加载了 {len(self.starred_repos)} 个星标仓库")
            else:
                self.main_window.log_message("没有找到缓存的星标仓库数据")
        else:
            print("未登录或 token_tab 不存在，无法加载缓存数据")

    @QtCore.pyqtSlot()
    def update_starred_list(self):
        # 清除现有的仓库项目
        while self.repo_layout.count():
            item = self.repo_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加新的仓库项目
        for repo in self.filtered_repos:
            repo_widget = self.create_repo_widget(repo)
            self.repo_layout.addWidget(repo_widget)

        # 添加一个弹性空间到布局的末尾
        self.repo_layout.addStretch()

        # 更新搜索结果计数
        self.search_widget.set_result_count(len(self.filtered_repos))

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
        layout.setSpacing(2)
        layout.setContentsMargins(5, 5, 5, 5)
        
        top_layout = QtWidgets.QHBoxLayout()
        
        name_label = QtWidgets.QLabel(f"<b>{repo['full_name']}</b>")
        name_label.setStyleSheet("font-weight: bold;")
        top_layout.addWidget(name_label)
        
        language_label = QtWidgets.QLabel(f"语言: {repo['language'] or '未知'}")
        language_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        top_layout.addWidget(language_label)
        
        layout.addLayout(top_layout)
        
        url_label = QtWidgets.QLabel(f"<a href='{repo['html_url']}'>{repo['html_url']}</a>")
        url_label.setOpenExternalLinks(True)
        url_label.setStyleSheet("font-size: 8pt;")
        layout.addWidget(url_label)
        
        description_label = QtWidgets.QLabel(repo['description'] or "No description")
        description_label.setWordWrap(True)
        description_label.setStyleSheet("font-size: 9pt;")
        layout.addWidget(description_label)
        
        stats_label = QtWidgets.QLabel(f"星标: {repo['stargazers_count']} | 复刻: {repo['forks_count']}")
        stats_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        stats_label.setStyleSheet("font-size: 8pt; color: #666;")
        layout.addWidget(stats_label)
        
        widget.setLayout(layout)
        return widget

    def filter_repos(self, search_text, search_option):
        self.filtered_repos = SearchWidget.filter_repos(self.starred_repos, search_text, search_option)
        self.update_starred_list()
