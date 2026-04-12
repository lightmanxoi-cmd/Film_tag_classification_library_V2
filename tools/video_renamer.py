import os
import datetime
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, scrolledtext
import json
from datetime import datetime
import subprocess
import re

# 定义支持的视频文件扩展名
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.mpg', '.mpeg', '.m4v']
# 配置文件路径
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".video_renamer_config.json")


def is_video_file(file_path):
    """检查文件是否为视频文件"""
    _, ext = os.path.splitext(file_path.lower())
    return ext in VIDEO_EXTENSIONS


def get_all_videos(folder_path):
    """获取文件夹中的所有视频文件"""
    videos = []
    for file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file)
        if os.path.isfile(file_path) and is_video_file(file_path):
            videos.append(file_path)
    return videos


def get_video_duration(file_path):
    """获取视频文件的时长（分钟）"""
    try:
        # 使用ffprobe获取视频信息
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        # 在Windows上隐藏命令行窗口
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, startupinfo=startupinfo)
        else:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        duration_seconds = float(result.stdout)
        # 转换为分钟并保留一位小数
        duration_minutes = round(duration_seconds / 60, 1)
        return duration_minutes
    except Exception as e:
        print(f"获取视频时长失败: {e}")
        # 如果无法获取时长，返回默认值
        return 0.0


def get_file_creation_date(file_path):
    """获取文件的创建日期"""
    try:
        # 在Windows上获取文件创建时间
        if os.name == 'nt':
            # 使用os.path.getctime获取创建时间
            timestamp = os.path.getctime(file_path)
        else:
            # 在其他系统上，尝试获取stat结果
            stat_info = os.stat(file_path)
            # Linux系统上，st_birthtime可能不存在
            try:
                timestamp = stat_info.st_birthtime
            except AttributeError:
                # 回退到修改时间
                timestamp = stat_info.st_mtime
        # 转换为日期格式 YYYYMMDD
        date = datetime.fromtimestamp(timestamp).strftime('%Y%m%d')
        return date
    except Exception as e:
        print(f"获取文件创建日期失败: {e}")
        # 如果无法获取日期，返回当前日期
        return datetime.now().strftime('%Y%m%d')


def rename_videos(folder_path, log_text, progress_var, progress_bar):
    """重命名文件夹中的视频文件"""
    # 获取所有视频文件
    videos = get_all_videos(folder_path)
    if not videos:
        messagebox.showerror("错误", f"文件夹 '{folder_path}' 中没有找到视频文件!")
        return

    # 按文件名排序视频文件
    videos.sort(key=lambda x: os.path.basename(x))

    # 按日期分组视频文件
    videos_by_date = {}
    for video in videos:
        date = get_file_creation_date(video)
        if date not in videos_by_date:
            videos_by_date[date] = []
        videos_by_date[date].append(video)

    # 准备重命名
    total_videos = len(videos)
    renamed_count = 0
    failed_count = 0
    skipped_count = 0

    log_text.delete(1.0, tk.END)
    log_text.insert(tk.END, f"找到 {total_videos} 个视频文件。\n")
    log_text.insert(tk.END, "开始处理视频文件...\n")
    log_text.update()

    # 初始化进度条
    progress_var.set(0)
    progress_bar['maximum'] = total_videos

    # 按日期处理每个视频文件
    for date, date_videos in videos_by_date.items():
        # 为同一天的文件分配序号
        for i, video_path in enumerate(date_videos, 1):
            try:
                # 检查是否已经是按照指定格式命名的文件
                file_name = os.path.basename(video_path)
                # 检查文件名是否符合 "YYYYMMDD-XXX-X.X分钟.扩展名" 的格式
                pattern = r'^\d{8}-\d{3}-\d+\.\d+分钟\..+$'
                if re.match(pattern, file_name):
                    log_text.insert(tk.END, f"跳过已按格式命名的文件: {file_name}\n")
                    skipped_count += 1
                    renamed_count += 1
                    progress_var.set(renamed_count)
                    progress_bar.update()
                    log_text.see(tk.END)
                    log_text.update()
                    continue

                # 获取视频时长
                duration = get_video_duration(video_path)
                # 获取文件扩展名
                _, ext = os.path.splitext(video_path)
                # 构建新文件名
                new_file_name = f"{date}-{i:03d}-{duration}分钟{ext}"
                new_file_path = os.path.join(folder_path, new_file_name)

                # 检查新文件名是否已存在
                counter = 1
                while os.path.exists(new_file_path):
                    # 如果文件名已存在，添加一个额外的数字
                    new_file_name = f"{date}-{i:03d}-{duration}分钟({counter}){ext}"
                    new_file_path = os.path.join(folder_path, new_file_name)
                    counter += 1

                # 重命名文件
                os.rename(video_path, new_file_path)
                renamed_count += 1
                log_text.insert(tk.END, f"重命名成功: {file_name} -> {new_file_name}\n")
            except Exception as e:
                failed_count += 1
                log_text.insert(tk.END, f"重命名失败: {os.path.basename(video_path)} - 错误: {str(e)}\n")
            finally:
                # 更新进度
                progress_var.set(renamed_count + failed_count + skipped_count)
                progress_bar.update()
                log_text.see(tk.END)
                log_text.update()

    # 显示处理结果
    log_text.insert(tk.END, "\n处理完成！\n")
    log_text.insert(tk.END, f"成功重命名: {renamed_count} 个文件\n")
    log_text.insert(tk.END, f"跳过已处理: {skipped_count} 个文件\n")
    log_text.insert(tk.END, f"重命名失败: {failed_count} 个文件\n")
    log_text.see(tk.END)
    log_text.update()

    # 提示用户处理完成
    messagebox.showinfo("完成", f"视频文件重命名处理完成！\n成功重命名: {renamed_count} 个文件\n跳过已处理: {skipped_count} 个文件\n重命名失败: {failed_count} 个文件")


def load_config():
    """加载配置文件"""
    default_config = {
        "last_folder_path": "",
        "remember_last_folder": True
    }
    
    if not os.path.exists(CONFIG_FILE):
        return default_config
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # 合并默认配置和读取的配置
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            return config
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return default_config


def save_config(config):
    """保存配置文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"保存配置文件失败: {e}")
        return False


def browse_folder(entry_field):
    """浏览文件夹"""
    folder_path = filedialog.askdirectory()
    if folder_path:
        entry_field.delete(0, tk.END)
        entry_field.insert(0, folder_path)


def create_gui():
    """创建GUI界面"""
    # 加载配置
    config = load_config()
    
    # 创建主窗口
    root = tk.Tk()
    root.title("视频文件重命名工具")
    root.geometry("700x600")
    root.resizable(True, True)
    
    # 设置样式
    style = ttk.Style()
    style.configure("TLabel", font= ("SimHei", 10))
    style.configure("TButton", font= ("SimHei", 10))
    style.configure("TEntry", font= ("SimHei", 10))
    style.configure("TCheckbutton", font= ("SimHei", 10))
    
    # 创建主框架
    main_frame = ttk.Frame(root, padding="10 10 10 10")
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # 文件夹路径选择
    folder_frame = ttk.Frame(main_frame)
    folder_frame.pack(fill=tk.X, pady=(0, 10))
    
    ttk.Label(folder_frame, text="视频文件夹:", width=12).pack(side=tk.LEFT, padx=(0, 5))
    folder_entry = ttk.Entry(folder_frame)
    folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
    if config["remember_last_folder"]:
        folder_entry.insert(0, config["last_folder_path"])
    
    browse_button = ttk.Button(folder_frame, text="浏览...", command=lambda: browse_folder(folder_entry))
    browse_button.pack(side=tk.LEFT)
    
    # 选项设置
    options_frame = ttk.Frame(main_frame)
    options_frame.pack(fill=tk.X, pady=(0, 10))
    
    remember_var = tk.BooleanVar(value=config["remember_last_folder"])
    remember_checkbox = ttk.Checkbutton(options_frame, text="记住上次选择的文件夹", variable=remember_var)
    remember_checkbox.pack(side=tk.LEFT)
    
    # 操作按钮
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=(0, 10))
    
    process_button = ttk.Button(button_frame, text="开始重命名", 
                              command=lambda: on_process_button_click(folder_entry, remember_var, log_text, progress_var, progress_bar))
    process_button.pack(side=tk.LEFT, padx=(0, 5))
    
    exit_button = ttk.Button(button_frame, text="退出", command=root.quit)
    exit_button.pack(side=tk.LEFT)
    
    # 进度条
    progress_frame = ttk.Frame(main_frame)
    progress_frame.pack(fill=tk.X, pady=(0, 10))
    
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, length=100, mode='determinate')
    progress_bar.pack(fill=tk.X, expand=True)
    
    # 日志显示
    log_frame = ttk.LabelFrame(main_frame, text="操作日志")
    log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    
    log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=("SimHei", 9))
    log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    log_text.insert(tk.END, "欢迎使用视频文件重命名工具！\n")
    log_text.insert(tk.END, "请选择包含视频文件的文件夹，然后点击'开始重命名'按钮。\n")
    log_text.insert(tk.END, "视频文件将被重命名为'创建日期-序号-时长分钟'格式，如'20240929-001-1.7分钟.mp4'。\n")
    
    # 启动主循环
    root.mainloop()


def on_process_button_click(folder_entry, remember_var, log_text, progress_var, progress_bar):
    """处理开始重命名按钮点击事件"""
    folder_path = folder_entry.get().strip()
    
    # 检查文件夹是否存在
    if not os.path.isdir(folder_path):
        messagebox.showerror("错误", f"文件夹 '{folder_path}' 不存在!")
        return
    
    # 保存当前配置
    config = {
        "last_folder_path": folder_path if remember_var.get() else "",
        "remember_last_folder": remember_var.get()
    }
    save_config(config)
    
    # 显示确认对话框
    confirm = messagebox.askyesno("确认", f"确定要重命名 '{folder_path}' 中的所有视频文件吗？\n此操作不可撤销！")
    if not confirm:
        return
    
    # 重命名视频文件
    rename_videos(folder_path, log_text, progress_var, progress_bar)


def main():
    # 检查ffprobe是否可用
    try:
        # 在Windows上隐藏命令行窗口
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)
        else:
            subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        messagebox.showerror("错误", "未找到ffprobe程序。请确保已安装FFmpeg并将其添加到系统PATH中。\n您可以从 https://ffmpeg.org/download.html 下载FFmpeg。")
        return
    
    # 创建GUI
    create_gui()


if __name__ == "__main__":
    main()