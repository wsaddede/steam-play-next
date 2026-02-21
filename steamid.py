import requests
import random
import tkinter as tk
from tkinter import messagebox
import threading
import json
import os
import io
import re  # 用于清理 HTML 标签
import html # 用于处理 HTML 转义字符
from PIL import Image, ImageTk

# --- 配置文件名 ---
CONFIG_FILE = "steam_picker_config.json"

# --- 核心逻辑部分 ---
def get_user_games(api_key, steam_id):
    """获取用户拥有的游戏列表"""
    url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
    params = {
        'key': api_key, 'steamid': steam_id, 'format': 'json',
        'include_appinfo': True, 'include_played_free_games': True
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'response' in data and 'games' in data['response']:
            return data['response']['games']
        return []
    except Exception:
        return None

def get_game_details(appid):
    """获取游戏封面图和中文简介"""
    result = {"image": None, "desc": "暂无简介"}
    
    # 1. 获取图片
    image_url = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg"
    try:
        img_resp = requests.get(image_url, timeout=5)
        if img_resp.status_code == 200:
            image_bytes = io.BytesIO(img_resp.content)
            pil_image = Image.open(image_bytes)
            # 调整图片大小 (固定宽度 240)
            base_width = 240
            w_percent = (base_width / float(pil_image.size[0]))
            h_size = int((float(pil_image.size[1]) * float(w_percent)))
            pil_image = pil_image.resize((base_width, h_size), Image.Resampling.LANCZOS)
            result["image"] = pil_image
    except Exception as e:
        print(f"图片下载失败: {e}")

    # 2. 获取简介 (调用商店 API)
    # l=schinese 参数请求中文数据
    store_url = f"https://store.steampowered.com/api/appdetails?appids={appid}&l=schinese"
    try:
        store_resp = requests.get(store_url, timeout=5)
        store_data = store_resp.json()
        
        if str(appid) in store_data and store_data[str(appid)]['success']:
            raw_desc = store_data[str(appid)]['data'].get('short_description', '暂无简介')
            # 清理 HTML 标签 (比如 <br>, <b>)
            clean_desc = re.sub('<[^<]+?>', '', raw_desc)
            # 处理转义字符 (比如 &quot;)
            clean_desc = html.unescape(clean_desc)
            result["desc"] = clean_desc
    except Exception as e:
        print(f"简介获取失败: {e}")

    return result

# --- 界面逻辑部分 ---
class SteamVisualApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Steam 游戏时光机 Pro 🎮")
        self.root.geometry("600x700") # 稍微加宽一点

        self.photo_refs = [] # 防止图片被回收
        self.main_frame = tk.Frame(root)
        self.result_frame = tk.Frame(root)

        self.setup_main_frame()
        self.setup_result_frame_structure()
        self.show_main_frame()
        self.load_config()

    def setup_main_frame(self):
        tk.Label(self.main_frame, text="🎲 Steam 游戏随机抽取器", font=("微软雅黑", 18, "bold")).pack(pady=30)

        input_frame = tk.Frame(self.main_frame)
        input_frame.pack(pady=10)

        tk.Label(input_frame, text="API Key:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.entry_api = tk.Entry(input_frame, width=40)
        self.entry_api.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(input_frame, text="Steam ID:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.entry_id = tk.Entry(input_frame, width=40)
        self.entry_id.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(input_frame, text="抽取数量:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.entry_n = tk.Entry(input_frame, width=10)
        self.entry_n.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        self.btn_run = tk.Button(self.main_frame, text="🚀 开始抽取", command=self.run_thread, 
                                 bg="#171a21", fg="#66c0f4", font=("微软雅黑", 12, "bold"), height=2, width=15)
        self.btn_run.pack(pady=30)
        
        self.status_label = tk.Label(self.main_frame, text="", fg="gray")
        self.status_label.pack()

    def setup_result_frame_structure(self):
        # 顶部栏
        top_bar = tk.Frame(self.result_frame, bg="#171a21", height=50)
        top_bar.pack(side="top", fill="x")
        
        tk.Button(top_bar, text="⬅ 返回重选", command=self.show_main_frame, 
                  bg="#2a475e", fg="white", relief="flat").pack(side="left", padx=15, pady=10)
        tk.Label(top_bar, text="✨ 今日推荐", bg="#171a21", fg="#66c0f4", font=("微软雅黑", 14, "bold")).pack(side="left", padx=20)

        # 滚动区域
        self.canvas = tk.Canvas(self.result_frame, bg="#e0e0e0")
        scrollbar = tk.Scrollbar(self.result_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#e0e0e0")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=580) # 设定宽度便于自动换行
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def show_main_frame(self):
        self.result_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)

    def show_result_frame(self):
        self.main_frame.pack_forget()
        self.result_frame.pack(fill="both", expand=True)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    self.entry_api.insert(0, config.get("api_key", ""))
                    self.entry_id.insert(0, config.get("steam_id", ""))
                    self.entry_n.insert(0, config.get("n", "3"))
            except: pass

    def save_config(self, api, sid, n):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"api_key": api, "steam_id": sid, "n": n}, f)
        except: pass

    def run_thread(self):
        threading.Thread(target=self.process_data).start()

    def process_data(self):
        api = self.entry_api.get().strip()
        sid = self.entry_id.get().strip()
        n_str = self.entry_n.get().strip()

        if not api or not sid or not n_str.isdigit():
            self.root.after(0, lambda: messagebox.showwarning("提示", "请填写完整信息"))
            return

        self.save_config(api, sid, n_str)
        
        self.root.after(0, lambda: self.btn_run.config(state="disabled", text="读取中..."))
        self.root.after(0, lambda: self.status_label.config(text="正在连接 Steam API..."))

        games = get_user_games(api, sid)

        if not games:
            self.root.after(0, lambda: self.status_label.config(text="获取失败，请检查网络或 ID"))
            self.root.after(0, lambda: self.btn_run.config(state="normal", text="🚀 开始抽取"))
            return

        # 随机抽取
        count = min(int(n_str), len(games))
        selected_games = random.sample(games, count)
        
        results = []
        for i, game in enumerate(selected_games):
            self.root.after(0, lambda i=i: self.status_label.config(text=f"正在下载详情 ({i+1}/{count})..."))
            
            # 这里同时获取图片和简介
            details = get_game_details(game['appid'])
            results.append({
                'name': game['name'],
                'appid': game['appid'],
                'image': details['image'],
                'desc': details['desc']
            })

        self.root.after(0, lambda: self.render_results(results))
        self.root.after(0, lambda: self.btn_run.config(state="normal", text="🚀 开始抽取"))
        self.root.after(0, lambda: self.status_label.config(text=""))

    def render_results(self, results):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.photo_refs.clear()

        for game in results:
            # 外部卡片容器
            card = tk.Frame(self.scrollable_frame, bg="white", bd=1, relief="solid")
            card.pack(fill="x", padx=10, pady=10)

            # --- 左侧：图片区域 ---
            left_frame = tk.Frame(card, bg="white")
            left_frame.pack(side="left", padx=10, pady=10, anchor="n")

            if game['image']:
                tk_photo = ImageTk.PhotoImage(game['image'])
                self.photo_refs.append(tk_photo)
                tk.Label(left_frame, image=tk_photo, bg="black").pack()
            else:
                tk.Label(left_frame, text="[无图]", bg="#ddd", width=30, height=8).pack()
            
            # 添加按钮到左侧图片下方
            tk.Button(left_frame, text="🎮 立即启动", 
                      command=lambda gid=game['appid']: self.open_steam(gid),
                      bg="#a4d007", fg="white", font=("微软雅黑", 9, "bold")).pack(pady=5, fill="x")

            # --- 右侧：信息区域 ---
            right_frame = tk.Frame(card, bg="white")
            right_frame.pack(side="left", fill="both", expand=True, padx=5, pady=10)

            # 游戏标题
            tk.Label(right_frame, text=game['name'], font=("微软雅黑", 14, "bold"), 
                     bg="white", anchor="w", justify="left").pack(fill="x")
            
            # 游戏 AppID
            tk.Label(right_frame, text=f"AppID: {game['appid']}", font=("Arial", 8), fg="gray",
                     bg="white", anchor="w").pack(fill="x")

            # 分割线
            tk.Frame(right_frame, height=1, bg="#eee").pack(fill="x", pady=5)

            # 游戏简介 (支持自动换行)
            desc_label = tk.Label(right_frame, text=game['desc'], font=("微软雅黑", 10), fg="#333",
                                  bg="white", anchor="nw", justify="left", wraplength=280)
            desc_label.pack(fill="both", expand=True)

        self.show_result_frame()

    def open_steam(self, appid):
        import webbrowser
        webbrowser.open(f"steam://run/{appid}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SteamVisualApp(root)
    root.mainloop()
