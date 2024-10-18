import asyncio
import aiohttp
import json
import os
from PyQt6 import QtCore
from datetime import datetime, timedelta

class Preloader(QtCore.QObject):
    preload_completed = QtCore.pyqtSignal(list)
    preload_progress = QtCore.pyqtSignal(int, int)
    summary_completed = QtCore.pyqtSignal(list)
    starred_repos_loaded = QtCore.pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.repos = {}
        self.starred_repos = {}
        self.cache_dir = os.path.join(os.getcwd(), 'data', 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.loop = None
        self.session = None

    async def preload_repos(self, token, username):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

        print(f"开始为 {username} 预加载仓库列表")
        headers = {'Authorization': f'token {token}'}
        all_repos = []
        starred_repos = []
        page = 1
        per_page = 100

        async with self.session as session:
            # 获取所有仓库
            while True:
                try:
                    url = f'https://api.github.com/user/repos?page={page}&per_page={per_page}'
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            repos = await response.json()
                            if not repos:
                                break
                            all_repos.extend(repos)
                            self.preload_progress.emit(len(all_repos), len(all_repos))
                            page += 1
                        else:
                            break
                except aiohttp.ClientError:
                    break

            # 获取星标仓库
            page = 1
            while True:
                url = f'https://api.github.com/user/starred?page={page}&per_page={per_page}'
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        starred = await response.json()
                        if not starred:
                            break
                        starred_repos.extend(starred)
                        page += 1
                    else:
                        break

        print(f"预加载完成，为 {username} 获取到 {len(all_repos)} 个仓库，{len(starred_repos)} 个星标仓库")
        self.repos[username] = all_repos
        self.starred_repos[username] = starred_repos
        self.save_cache(username)
        self.save_starred_cache(username)
        self.preload_completed.emit(all_repos)
        self.starred_repos_loaded.emit(starred_repos)
        self.preload_progress.emit(len(all_repos), len(all_repos))
        
        # 生成仓库使用总结
        summary = self.generate_repo_summary(all_repos)
        self.summary_completed.emit(summary)

    def generate_repo_summary(self, repos):
        # 按照更新时间、星标数和提交频率对仓库进行排序
        sorted_repos = sorted(repos, key=lambda r: (
            datetime.strptime(r['updated_at'], "%Y-%m-%dT%H:%M:%SZ"),
            r['stargazers_count'],
            r['pushed_at']
        ), reverse=True)

        # 取前10个最常用的仓库
        top_repos = sorted_repos[:10]

        summary = []
        for repo in top_repos:
            summary.append({
                'name': repo['name'],
                'full_name': repo['full_name'],
                'updated_at': repo['updated_at'],
                'stars': repo['stargazers_count'],
                'language': repo['language'],
                'description': repo['description']
            })

        return summary

    def start_preload(self, token, username):
        if self.loop is None or self.loop.is_closed():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        
        future = asyncio.run_coroutine_threadsafe(self.preload_repos(token, username), self.loop)
        future.add_done_callback(lambda f: print("预加载完成"))

    def get_preloaded_repos(self, username):
        if username not in self.repos:
            self.load_cache(username)
        return self.repos.get(username, [])

    def save_cache(self, username):
        cache_file = os.path.join(self.cache_dir, f'{username}_repos_cache.json')
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'repos': self.repos[username]
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print(f"保存仓库缓存到 {cache_file}")

    def load_cache(self, username):
        cache_file = os.path.join(self.cache_dir, f'{username}_repos_cache.json')
        if not os.path.exists(cache_file):
            print(f"仓库缓存文件不存在: {cache_file}")
            return False
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        self.repos[username] = cache_data['repos']
        print(f"从 {cache_file} 加载了 {len(self.repos[username])} 个仓库")
        return True

    def clear_repos_cache(self, username):
        cache_file = os.path.join(self.cache_dir, f'{username}_repos_cache.json')
        if os.path.exists(cache_file):
            os.remove(cache_file)
        self.repos.pop(username, None)

    def clear_starred_cache(self, username):
        starred_cache_file = os.path.join(self.cache_dir, f'{username}_starred_repos_cache.json')
        if os.path.exists(starred_cache_file):
            os.remove(starred_cache_file)
        self.starred_repos.pop(username, None)

    def save_starred_cache(self, username):
        cache_file = os.path.join(self.cache_dir, f'{username}_starred_repos_cache.json')
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'repos': self.starred_repos[username]
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print(f"保存星标仓库缓存到 {cache_file}")

    def load_starred_cache(self, username):
        cache_file = os.path.join(self.cache_dir, f'{username}_starred_repos_cache.json')
        if not os.path.exists(cache_file):
            print(f"星标仓库缓存文件不存在: {cache_file}")
            return False
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        self.starred_repos[username] = cache_data['repos']
        print(f"从 {cache_file} 加载了 {len(self.starred_repos[username])} 个星标仓库")
        return True

    def get_preloaded_starred_repos(self, username):
        if username not in self.starred_repos:
            self.load_starred_cache(username)
        return self.starred_repos.get(username, [])

    def clear_all_cache(self, username):
        self.clear_repos_cache(username)
        self.clear_starred_cache(username)
