import requests
import random
import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading

# --- 核心逻辑部分 ---
def get_user_games(api_key, steam_id):
    url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
    params = {
        'key': api_key,
        'steamid': steam_id,
        'format': 'json',
        'include_appinfo': True,
        'include_played_free_games': True
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'response' in data and 'games' in data['response']:
            return data['response']['games']
        return []
    except Exception as e:
        return None  # 返回 None 表示出错

# --- 界面逻辑部分 ---
class SteamRandomPickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Steam 随机游戏抽取器")
        self.root.geometry("500x500")

        # 1. API Key 输入框 (为了方便打包给别人用，这里做成可输入的)
        tk.Label(root, text="Steam API Key:").pack(pady=5)
        self.entry_api = tk.Entry(root, width=50)
        self.entry_api.pack(pady=5)
        # 默认值（你可以把自己常用的填在这里，省得每次输入）
        self.entry_api.insert(0, "") 

        # 2. Steam ID 输入框
        tk.Label(root, text="Steam ID (64位数字):").pack(pady=5)
        self.entry_id = tk.Entry(root, width=50)
        self.entry_id.pack(pady=5)
        self.entry_id.insert(0, "") 

        # 3. 抽取数量
        tk.Label(root, text="抽取数量 N:").pack(pady=5)
        self.entry_n = tk.Entry(root, width=10)
        self.entry_n.pack(pady=5)
        self.entry_n.insert(0, "3")

        # 4. 按钮
        self.btn_run = tk.Button(root, text="开始随机抽取", command=self.run_thread, bg="#4CAF50", fg="white")
        self.btn_run.pack(pady=15)

        # 5. 结果显示区域
        self.text_area = scrolledtext.ScrolledText(root, width=55, height=15)
        self.text_area.pack(pady=10)

    def run_thread(self):
        # 使用线程防止界面卡死
        threading.Thread(target=self.start_process).start()

    def start_process(self):
        api_key = self.entry_api.get().strip()
        steam_id = self.entry_id.get().strip()
        n_str = self.entry_n.get().strip()

        if not api_key or not steam_id:
            messagebox.showwarning("提示", "请填写 API Key 和 Steam ID！")
            return

        if not n_str.isdigit():
            messagebox.showerror("错误", "数量 N 必须是整数！")
            return
        
        n = int(n_str)
        
        self.btn_run.config(state="disabled", text="正在读取...")
        self.text_area.delete(1.0, tk.END) # 清空旧内容

        games = get_user_games(api_key, steam_id)

        if games is None:
            self.text_area.insert(tk.END, "网络请求失败，请检查网络或 API Key。\n")
        elif not games:
            self.text_area.insert(tk.END, "未找到游戏，可能是 ID 错误或游戏库未公开。\n")
        else:
            total = len(games)
            self.text_area.insert(tk.END, f"找到 {total} 款游戏。\n")
            self.text_area.insert(tk.END, "-"*40 + "\n")
            
            # 随机逻辑
            count = min(n, total)
            selected = random.sample(games, count)
            
            for game in selected:
                self.text_area.insert(tk.END, f"ID: {game['appid']} | {game['name']}\n")
            
            self.text_area.insert(tk.END, "-"*40 + "\n完成！")

        self.btn_run.config(state="normal", text="开始随机抽取")

if __name__ == "__main__":
    root = tk.Tk()
    app = SteamRandomPickerApp(root)
    root.mainloop()
