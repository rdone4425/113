# Note: QtAsyncio is not used in this file
import sys
import os

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import asyncio
from PyQt6 import QtWidgets, QtGui, QtCore
from git.token_tab import TokenTab
from git.repository_tab import RepositoryTab
from git.search_widget import SearchWidget
from git.github_search import GitHubSearchDialog, search_github, create_repo_widget
import aiohttp
from datetime import datetime
from git.log_tab import LogTab
from git.preloader import Preloader
from git.starred_tab import StarredTab

# 临时创建占位类
class PlaceholderTab(QtWidgets.QWidget):
    def __init__(self, name):
        super().__init__()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QWidget())  # 添加一个空的widget作为占位符
        self.setLayout(layout)
        self.setWindowTitle(name)

class HomeTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # 创建一个容器来包含搜索框
        search_container = QtWidgets.QWidget()
        search_container.setFixedWidth(600)  # 限制搜索区域的宽度
        search_layout = QtWidgets.QHBoxLayout(search_container)
        
        # 创建并设置搜索框样式
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("搜索 GitHub 仓库...")
        self.search_input.setFixedHeight(40)  # 增加高度
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #3498db;
                border-radius: 20px;
                padding: 0 15px;
                font-size: 16px;
            }
            QLineEdit:focus {
                border: 2px solid #2980b9;
            }
        """)
        self.search_input.returnPressed.connect(self.perform_search)  # 连接回车键事件到搜索函数
        search_layout.addWidget(self.search_input)

        # 移除搜索按钮
        
        # 将搜索容器添加到主布局并居中
        layout.addWidget(search_container, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)

        # 创建一个水平布局来包含搜索结果和滚动按钮
        results_and_buttons_layout = QtWidgets.QHBoxLayout()

        # 修改搜索结果区域
        self.search_results_scroll = QtWidgets.QScrollArea()
        self.search_results_scroll.setWidgetResizable(True)
        self.search_results_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.search_results_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.search_results_scroll.setFixedHeight(500)
        self.search_results_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e1e4e8;
                border-radius: 6px;
                background-color: white;
            }
            QScrollArea > QWidget > QWidget {
                background-color: white;
            }
        """)
        self.search_results_scroll.setVisible(False)

        self.search_results_widget = QtWidgets.QWidget()
        self.search_results_layout = QtWidgets.QVBoxLayout(self.search_results_widget)
        self.search_results_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.search_results_layout.setSpacing(0)  # 移除项目之间的间距
        self.search_results_layout.setContentsMargins(1, 1, 1, 1)  # 添加小边距
        self.search_results_scroll.setWidget(self.search_results_widget)

        results_and_buttons_layout.addWidget(self.search_results_scroll)

        # 创建滚动按钮
        scroll_buttons_layout = QtWidgets.QVBoxLayout()
        
        self.scroll_top_button = QtWidgets.QPushButton("↑")
        self.scroll_top_button.setFixedSize(30, 30)
        self.scroll_top_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.1);
                border: none;
                border-radius: 15px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.2);
            }
        """)
        self.scroll_top_button.clicked.connect(self.scroll_to_top)
        self.scroll_top_button.setVisible(False)
        
        self.scroll_bottom_button = QtWidgets.QPushButton("↓")
        self.scroll_bottom_button.setFixedSize(30, 30)
        self.scroll_bottom_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.1);
                border: none;
                border-radius: 15px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.2);
            }
        """)
        self.scroll_bottom_button.clicked.connect(self.scroll_to_bottom)
        self.scroll_bottom_button.setVisible(False)

        scroll_buttons_layout.addWidget(self.scroll_top_button)
        scroll_buttons_layout.addStretch()
        scroll_buttons_layout.addWidget(self.scroll_bottom_button)

        results_and_buttons_layout.addLayout(scroll_buttons_layout)

        layout.addLayout(results_and_buttons_layout)

        # 欢迎标签和卡片部分
        self.welcome_widget = QtWidgets.QWidget()
        welcome_layout = QtWidgets.QVBoxLayout(self.welcome_widget)

        self.welcome_label = QtWidgets.QLabel("欢迎使用 Git 客户端")
        self.welcome_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.welcome_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px 0;")
        welcome_layout.addWidget(self.welcome_label)

        self.cards_layout = QtWidgets.QHBoxLayout()
        self.cards_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        
        self.repo_card = self.create_card("仓库管理", lambda: self.main_window.tab_widget.setCurrentIndex(1), "#3498db")
        self.cards_layout.addWidget(self.repo_card)

        self.token_card = self.create_card("令牌管理", lambda: self.main_window.tab_widget.setCurrentIndex(2), "#2ecc71")
        self.cards_layout.addWidget(self.token_card)

        welcome_layout.addLayout(self.cards_layout)
        layout.addWidget(self.welcome_widget)

    def create_card(self, title, on_click, color):
        card = QtWidgets.QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: {color};
                border-radius: 10px;
                padding: 20px;
                color: white;
            }}
        """)
        card_layout = QtWidgets.QVBoxLayout(card)
        
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        card_layout.addWidget(title_label)
        
        card.mousePressEvent = lambda event: on_click()
        
        return card

    def perform_search(self):
        search_text = self.search_input.text()
        if search_text:
            self.welcome_widget.setVisible(False)
            self.search_results_scroll.setVisible(True)
            self.scroll_top_button.setVisible(True)
            self.scroll_bottom_button.setVisible(True)
            self.search_github_repos(search_text)
        else:
            self.welcome_widget.setVisible(True)
            self.search_results_scroll.setVisible(False)
            self.scroll_top_button.setVisible(False)
            self.scroll_bottom_button.setVisible(False)

    def search_github_repos(self, search_text):
        self.clear_search_results()
        search_github(search_text, self.display_github_results)

    @QtCore.pyqtSlot(list)
    def display_github_results(self, repos):
        for repo in repos:
            result_widget = self.create_repo_widget(repo, False)  # 修改这里，传 False 表示不是本地仓库
            self.search_results_layout.addWidget(result_widget)
        self.search_results_scroll.setVisible(True)
        self.welcome_widget.setVisible(False)

    def add_search_result(self, repo, is_local):
        result_widget = self.create_repo_widget(repo, is_local)
        self.search_results_layout.addWidget(result_widget)

    def clear_search_results(self):
        while self.search_results_layout.count():
            item = self.search_results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.scroll_top_button.setVisible(False)
        self.scroll_bottom_button.setVisible(False)

    def create_repo_widget(self, repo, is_local):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)
        
        # 仓库名称
        name_label = QtWidgets.QLabel(f"<a href='{repo['html_url']}' style='text-decoration: none; color: #0366d6;'>{repo['full_name']}</a>")
        name_label.setOpenExternalLinks(True)
        name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(name_label)
        
        # 仓库描述
        if repo['description']:
            description_label = QtWidgets.QLabel(repo['description'])
            description_label.setWordWrap(True)
            description_label.setStyleSheet("font-size: 12px; color: #586069; margin-top: 3px;")
            layout.addWidget(description_label)
        
        # 统计信息
        stats_layout = QtWidgets.QHBoxLayout()
        stats_layout.setSpacing(15)
        
        star_label = QtWidgets.QLabel(f"★ {repo['stargazers_count']}")
        star_label.setStyleSheet("font-size: 12px; color: #586069;")
        stats_layout.addWidget(star_label)
        
        fork_label = QtWidgets.QLabel(f"🍴 {repo['forks_count']}")
        fork_label.setStyleSheet("font-size: 12px; color: #586069;")
        stats_layout.addWidget(fork_label)
        
        if repo['language']:
            language_label = QtWidgets.QLabel(f"● {repo['language']}")
            language_label.setStyleSheet("font-size: 12px; color: #586069;")
            stats_layout.addWidget(language_label)
        
        updated_label = QtWidgets.QLabel(f"Updated on {repo['updated_at'][:10]}")
        updated_label.setStyleSheet("font-size: 12px; color: #586069;")
        stats_layout.addWidget(updated_label)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # 使用交替的背景颜色
        if self.search_results_layout.count() % 2 == 0:
            bg_color = "#ffffff"  # 白色
        else:
            bg_color = "#f6f8fa"  # 浅灰色
        
        widget.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                padding: 10px 0;
            }}
        """)
        
        return widget

    def scroll_to_top(self):
        self.search_results_scroll.verticalScrollBar().setValue(0)

    def scroll_to_bottom(self):
        self.search_results_scroll.verticalScrollBar().setValue(
            self.search_results_scroll.verticalScrollBar().maximum()
        )

    def update_repo_card_summary(self, summary):
        # 由于我们之前移除了显示仓库摘要的功能，这个方法可以保留为空
        pass

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Git客户端")
        self.setGeometry(100, 100, 1000, 600)
        
        self.setFont(QtGui.QFont("微雅黑", 10))
        
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)
        
        self.tab_widget = QtWidgets.QTabWidget()
        self.main_layout.addWidget(self.tab_widget)
        
        # 创建 Preloader 实例
        self.preloader = Preloader()
        self.preloader.preload_completed.connect(self.on_preload_completed)
        self.preloader.preload_progress.connect(self.on_preload_progress)
        self.preloader.summary_completed.connect(self.on_summary_completed)
        
        # 创建并启动事件循环线程
        self.event_loop_thread = QtCore.QThread()
        self.event_loop_thread.run = self.run_event_loop
        self.event_loop_thread.start()
        
        # 初始化所有标签页
        self.home_tab = HomeTab(self)
        self.log_tab = LogTab()
        self.repository_tab = RepositoryTab(self)
        self.token_tab = TokenTab(self)  # 确保这行在 starred_tab 之前
        self.starred_tab = StarredTab(self)
        
        # 添加标签页到 tab_widget，调整顺序
        self.tab_widget.addTab(self.home_tab, "主页")
        self.tab_widget.addTab(self.repository_tab, "仓库")
        self.tab_widget.addTab(self.starred_tab, "星标")
        self.tab_widget.addTab(self.token_tab, "令牌")
        self.tab_widget.addTab(self.log_tab, "日志")
        
        # 创建状态栏
        self.statusBar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        
        # 添加登录状态标签到状态栏
        self.login_status_label = QtWidgets.QLabel("未登录")
        self.statusBar.addPermanentWidget(self.login_status_label)
        
        # 设置样式
        self.set_styles()

        # 连接信号
        self.token_tab.token_updated.connect(self.on_token_updated)
        self.token_tab.login_status_updated.connect(self.on_login_status_updated)
        self.token_tab.username_updated.connect(self.on_username_updated)
        self.token_tab.username_updated.connect(self.update_repository_username)
        self.token_tab.token_updated.connect(self.starred_tab.refresh_starred_repos)

        # 尝试使用最后一个 token 登录
        QtCore.QTimer.singleShot(0, self.token_tab.try_login_with_last_token)

        # 创建 data 目录
        self.data_dir = os.path.join(os.getcwd(), 'data')
        os.makedirs(self.data_dir, exist_ok=True)

    def search_local_repos(self, search_text):
        self.tab_widget.setCurrentIndex(1)  # 换到仓库标签页
        self.repository_tab.filter_repos(search_text, "全")

    def search_github(self, search_text):
        dialog = GitHubSearchDialog(self)
        dialog.search_widget.search_input.setText(search_text)
        dialog.search_widget.perform_search()
        dialog.exec()

    def show_search_results(self, local_results, github_results):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("搜索结果")
        layout = QtWidgets.QVBoxLayout(dialog)

        tabs = QtWidgets.QTabWidget()
        local_tab = QtWidgets.QWidget()
        github_tab = QtWidgets.QWidget()

        local_layout = QtWidgets.QVBoxLayout(local_tab)
        github_layout = QtWidgets.QVBoxLayout(github_tab)

        for repo in local_results:
            local_layout.addWidget(self.create_repo_widget(repo, is_local=True))

        for repo in github_results:
            github_layout.addWidget(self.create_repo_widget(repo, is_local=False))

        tabs.addTab(local_tab, f"本地结果 ({len(local_results)})")
        tabs.addTab(github_tab, f"GitHub结果 ({len(github_results)})")

        layout.addWidget(tabs)

        close_button = QtWidgets.QPushButton("关闭")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)

        dialog.setLayout(layout)
        dialog.resize(600, 400)
        dialog.exec()

    def create_repo_widget(self, repo, is_local):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        name_label = QtWidgets.QLabel(f"<b>{repo['name']}</b>")
        layout.addWidget(name_label)

        description_label = QtWidgets.QLabel(repo['description'] or "No description")
        layout.addWidget(description_label)

        if is_local:
            url_label = QtWidgets.QLabel(f"<a href='{repo['html_url']}'>{repo['html_url']}</a>")
        else:
            url_label = QtWidgets.QLabel(f"<a href='{repo['html_url']}'>{repo['full_name']}</a>")
        url_label.setOpenExternalLinks(True)
        layout.addWidget(url_label)

        return widget

    def set_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #ecf0f1;
                color: #2c3e50;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border: 1px solid #cccccc;
                border-bottom: 1px solid white;
            }
            QStatusBar {
                background-color: #2c3e50;
                color: white;
            }
        """)

    def on_token_updated(self, token):
        print(f"当前选中的token: {token}")
        if self.token_tab.current_username:
            self.preloader.start_preload(token, self.token_tab.current_username)

    @QtCore.pyqtSlot(str)
    def on_username_updated(self, username):
        if username:
            self.login_status_label.setText(f"已登录: {username}")
            self.repository_tab.current_username = username
            self.repository_tab.current_token = self.token_tab.current_token
            self.repository_tab.load_cached_repos()
            self.starred_tab.refresh_starred_repos()  # 添加这行
            if self.token_tab.current_token:
                QtCore.QTimer.singleShot(0, lambda: self.preloader.start_preload(self.token_tab.current_token, username))
        else:
            self.login_status_label.setText("未登录")
            self.repository_tab.current_username = None
            self.repository_tab.current_token = None
            self.repository_tab.all_repos = []
            self.repository_tab._update_repo_list([])
            self.starred_tab.starred_list.clear()  # 添加这行

    @QtCore.pyqtSlot(str, bool)
    def on_login_status_updated(self, token, success):
        if success:
            self.statusBar.showMessage(f"Token {token[:4]}...{token[-4:]} 验证成功", 5000)  # 显示5秒
        else:
            self.statusBar.showMessage(f"Token {token[:4]}...{token[-4:]} 验证失败", 5000)  # 显示5秒
            self.tab_widget.setTabText(2, "令牌")
            self.login_status_label.setText("未登录")

    def update_repository_username(self, username):
        self.repository_tab.current_username = username
        self.repository_tab.current_token = self.token_tab.current_token  # 添加这行

    def log_message(self, message):
        if hasattr(self, 'log_tab'):
            self.log_tab.add_log(message)
        else:
            print(f"Log message (log_tab not initialized): {message}")

    def on_preload_completed(self, repos):
        self.repository_tab.load_cached_repos()

    def on_preload_progress(self, current, total):
        # 更新预加载进度
        progress = (current / total) * 100
        self.statusBar.showMessage(f"正在预加载仓库... {progress:.1f}%")
        if current == total:
            self.statusBar.showMessage("预加载完成", 3000)  # 显示3秒后消失

    def run_event_loop(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        self.preloader.loop = loop
        loop.run_forever()

    def closeEvent(self, event):
        # 停止所有正在运行的异步任务
        if hasattr(self, 'preloader') and self.preloader.loop:
            self.preloader.loop.call_soon_threadsafe(self.preloader.loop.stop)

        # 等待事件循环线程结束
        if hasattr(self, 'event_loop_thread'):
            self.event_loop_thread.quit()
            self.event_loop_thread.wait(5000)  # 等待最多5秒

        # 如果线程仍在运行，强制终止
        if self.event_loop_thread.isRunning():
            self.event_loop_thread.terminate()
            self.event_loop_thread.wait()

        # 关闭所有打开的会话
        if hasattr(self, 'preloader'):
            asyncio.run(self.close_all_sessions())

        super().closeEvent(event)

    async def close_all_sessions(self):
        if hasattr(self.preloader, 'session') and isinstance(self.preloader.session, aiohttp.ClientSession):
            await self.preloader.session.close()

    def on_summary_completed(self, summary):
        # 移除打印最常用仓库总结的代码
        # 只更新首页的仓库管理卡片
        self.home_tab.update_repo_card_summary(summary)

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()

    # 创建一个新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def run_async_loop():
        asyncio.set_event_loop(loop)
        loop.run_forever()

    # 在单独的线程中运行异步事件循环
    import threading
    threading.Thread(target=run_async_loop, daemon=True).start()

    # 运行 Qt 事件循环
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
