from PyQt6 import QtWidgets, QtCore
import re

class SearchWidget(QtWidgets.QWidget):
    search_changed = QtCore.pyqtSignal(str, str)  # 只发送搜索文本和搜索选项

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("搜索仓库...")
        self.search_input.textChanged.connect(self.on_search_changed)
        layout.addWidget(self.search_input)

        self.search_options = QtWidgets.QComboBox()
        self.search_options.addItems(["全部", "名称", "描述", "语言"])
        self.search_options.currentTextChanged.connect(self.on_search_changed)
        layout.addWidget(self.search_options)

        self.result_count_label = QtWidgets.QLabel()
        layout.addWidget(self.result_count_label)

    def on_search_changed(self):
        search_text = self.search_input.text()
        search_option = self.search_options.currentText()
        self.search_changed.emit(search_text, search_option)

    def set_result_count(self, count):
        self.result_count_label.setText(f"找到 {count} 个结果")

    @staticmethod
    def filter_repos(repos, search_text, search_option):
        search_text = search_text.lower()
        exact_matches = set()
        partial_matches = set()
        
        for repo in repos:
            if search_option == "名称" or search_option == "全部":
                if SearchWidget.exact_match(search_text, repo['name']):
                    exact_matches.add(repo['id'])
                elif SearchWidget.partial_match(search_text, repo['name']):
                    partial_matches.add(repo['id'])
            
            if search_option == "描述" or search_option == "全部":
                if SearchWidget.exact_match(search_text, repo['description']):
                    exact_matches.add(repo['id'])
                elif SearchWidget.partial_match(search_text, repo['description']):
                    partial_matches.add(repo['id'])
            
            if search_option == "语言" or search_option == "全部":
                if SearchWidget.exact_match(search_text, repo['language']):
                    exact_matches.add(repo['id'])
                elif SearchWidget.partial_match(search_text, repo['language']):
                    partial_matches.add(repo['id'])

        # 移除在精确匹配中已经存在的部分匹配
        partial_matches -= exact_matches

        # 构建结果列表
        results = []
        for repo in repos:
            if repo['id'] in exact_matches:
                results.append(repo)
        for repo in repos:
            if repo['id'] in partial_matches:
                results.append(repo)

        return results

    @staticmethod
    def exact_match(search_text, target_text):
        if target_text is None:
            return False
        return search_text == target_text.lower()

    @staticmethod
    def partial_match(search_text, target_text):
        if target_text is None:
            return False
        return search_text in target_text.lower()

    @staticmethod
    def highlight_text(text, search_text):
        if not text or not search_text:
            return text
        
        def replace_func(match):
            return f'<span style="background-color: yellow; color: black;">{match.group()}</span>'
        
        pattern = re.compile(re.escape(search_text), re.IGNORECASE)
        highlighted_text = pattern.sub(replace_func, text)
        return f'<span style="color: black;">{highlighted_text}</span>'
