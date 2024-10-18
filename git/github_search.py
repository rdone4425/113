import asyncio
import aiohttp
from PyQt6 import QtWidgets, QtCore, QtGui
from datetime import datetime
import re
import requests
from bs4 import BeautifulSoup
from git.search_widget import SearchWidget

class GitHubSearchWidget(QtWidgets.QWidget):
    search_completed = QtCore.pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("搜索 GitHub 仓库...")
        layout.addWidget(self.search_input)

        self.search_button = QtWidgets.QPushButton("搜索")
        self.search_button.clicked.connect(self.perform_search)
        layout.addWidget(self.search_button)

    def perform_search(self):
        search_text = self.search_input.text()
        if search_text:
            asyncio.get_event_loop().call_soon_threadsafe(
                lambda: asyncio.create_task(self.search_github(search_text))
            )

    async def search_github(self, search_text):
        async with aiohttp.ClientSession() as session:
            exact_matches = await self.search_exact(session, search_text)
            partial_matches = await self.search_partial(session, search_text)
            
            all_results = self.remove_duplicates(exact_matches + partial_matches)
            sorted_results = self.sort_results(all_results)
            
            self.search_completed.emit(sorted_results)

    async def search_exact(self, session, search_text):
        queries = [
            f'user:{search_text}',
            f'repo:{search_text}',
            f'"{search_text}" in:name',
            f'"{search_text}" in:description',
            f'"{search_text}" in:readme'
        ]
        results = []
        for query in queries:
            results.extend(await self.fetch_results(session, query))
        return results

    async def search_partial(self, session, search_text):
        query = f'{search_text} in:name,description,readme'
        return await self.fetch_results(session, query)

    async def fetch_results(self, session, query):
        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data['items']
            else:
                print(f"GitHub 搜索失败: {response.status}")
                return []

    def remove_duplicates(self, repos):
        seen = set()
        unique_repos = []
        for repo in repos:
            if repo['id'] not in seen:
                seen.add(repo['id'])
                unique_repos.append(repo)
        return unique_repos

    def sort_results(self, results):
        return sorted(results, key=lambda x: (
            -x['stargazers_count'],
            -x['watchers_count'],
            datetime.strptime(x['updated_at'], "%Y-%m-%dT%H:%M:%SZ")
        ), reverse=True)

def create_repo_widget(repo, search_text):
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(widget)

    name_label = QtWidgets.QLabel(highlight_text(repo['full_name'], search_text))
    name_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
    layout.addWidget(name_label)

    description_label = QtWidgets.QLabel(highlight_text(repo.get('description', 'No description'), search_text))
    description_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
    description_label.setWordWrap(True)
    layout.addWidget(description_label)

    stats_label = QtWidgets.QLabel(f"⭐ {repo['stargazers_count']} | 👀 {repo['watchers_count']} | 🕒 {repo['updated_at']}")
    layout.addWidget(stats_label)

    url_label = QtWidgets.QLabel(f"<a href='{repo['html_url']}'>{repo['html_url']}</a>")
    url_label.setOpenExternalLinks(True)
    layout.addWidget(url_label)

    widget.setStyleSheet("""
        QWidget {
            background-color: white;
            border-radius: 5px;
            margin-bottom: 5px;
            padding: 10px;
        }
    """)

    return widget

def highlight_text(text, search_text):
    if not text or not search_text:
        return text
    highlighted_text = re.sub(
        f'({re.escape(search_text)})',
        r'<span style="background-color: yellow;">\1</span>',
        text,
        flags=re.IGNORECASE
    )
    return highlighted_text

def search_github(search_text, callback):
    search_widget = GitHubSearchWidget()
    search_widget.search_completed.connect(callback)
    search_widget.search_input.setText(search_text)
    search_widget.perform_search()

def show_github_search_dialog(parent):
    dialog = GitHubSearchDialog(parent)
    dialog.exec()

def github_search(query, token):
    url = "https://api.github.com/search/repositories"
    headers = {"Authorization": f"token {token}"}
    params = {"q": query}
    response = requests.get(url, headers=headers, params=params)
    # ...

class GitHubSearchDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, token=None):
        super().__init__(parent)
        self.token = token
        self.setWindowTitle("GitHub 搜索")
        layout = QtWidgets.QVBoxLayout(self)
        
        self.search_widget = SearchWidget()
        layout.addWidget(self.search_widget)
        
        self.results_list = QtWidgets.QListWidget()
        layout.addWidget(self.results_list)
        
        close_button = QtWidgets.QPushButton("关闭")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        
        self.search_widget.search_completed.connect(self.display_results)
    
    def display_results(self, results):
        self.results_list.clear()
        for repo in results:
            self.results_list.addItem(repo['full_name'])

# 确保其他必要的函数和类（如 SearchWidget）也在这个文件中定义
