import os
import json
import hashlib
import logging
import threading
from pathlib import Path
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

from enties.task_download_contracts import load_cached_password

# ======================== 日志配置 ========================
logger = logging.getLogger("ContractInvoiceDownloader")
logger.setLevel(logging.INFO)
log_handler = logging.FileHandler("download_tool.log", encoding="utf-8")
log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(log_handler)

# ======================== 密码缓存 ========================
# CACHE_PATH = Path.home() / ".eo_tool_cache.json"
#
# def encrypt(s: str) -> str:
#     return hashlib.sha256(s.encode("utf-8")).hexdigest()
#
# def save_cache(user: str, pwd: str):
#     try:
#         data = {"user": user, "enc_pwd": encrypt(pwd)}
#         with open(CACHE_PATH, "w", encoding="utf-8") as f:
#             json.dump(data, f, ensure_ascii=False, indent=2)
#         logger.info("用户信息已缓存")
#     except Exception as e:
#         logger.exception("保存缓存失败")
#
# def load_cache() -> tuple[str, str]:
#     if not CACHE_PATH.exists():
#         return "", ""
#     try:
#         with open(CACHE_PATH, encoding="utf-8") as f:
#             d = json.load(f)
#         return d.get("user", ""), d.get("enc_pwd", "")
#     except Exception as e:
#         logger.exception("加载缓存失败")
#         return "", ""

# ======================== 主窗口 ========================
class DownloadDialog(Tk):
    def __init__(self):
        super().__init__()
        self.title("合同发票下载工具")
        self.resizable(False, False)
        self.attributes("-toolwindow", True)  # 仅关闭按钮

        # 变量
        self.var_user = StringVar()
        self.var_pwd = StringVar()
        self.var_base = StringVar(value="./local.data")
        self.var_xlsx = StringVar()
        self.var_sheet = StringVar(value="Contract")
        self.var_col = StringVar(value="项目编号")
        self.var_contract = BooleanVar()
        self.var_invoice = BooleanVar()
        self.var_extract = BooleanVar()
        self.var_status = StringVar()
        # 加载缓存
        cache_user, _, _, cache_enc = load_cached_password()
        self.var_user.set(cache_user)
        self.var_pwd.set("******************")
        self.has_cache = bool(cache_enc)

        # 线程控制
        self.download_thread = None
        self.stop_flag = False


        self.create_widgets()

    def create_widgets(self):
        main = ttk.Frame(self, padding=10)
        main.grid(row=0, column=0, sticky=NSEW)

        # 账号
        ttk.Label(main, text="EO账号：").grid(row=0, column=0, sticky=W, pady=3)
        ttk.Entry(main, textvariable=self.var_user, width=32).grid(row=0, column=1, columnspan=2, sticky=EW, pady=3)

        # 密码
        ttk.Label(main, text="密码：").grid(row=1, column=0, sticky=W, pady=3)
        self.entry_pwd = ttk.Entry(main, textvariable=self.var_pwd, show="*", width=32)
        self.entry_pwd.grid(row=1, column=1, columnspan=2, sticky=EW, pady=3)

        # 根目录
        ttk.Label(main, text="保存目录：").grid(row=2, column=0, sticky=W, pady=3)
        ttk.Entry(main, textvariable=self.var_base, width=32).grid(row=2, column=1, sticky=EW, pady=3)

        # 分割线
        ttk.Separator(main, orient=HORIZONTAL).grid(row=3, column=0, columnspan=3, sticky=EW, pady=6)

        # Excel 区域
        ttk.Label(main, text="从 Excel 读取项目ID", font="bold").grid(row=4, column=0, columnspan=3, sticky=W)
        ttk.Label(main, text="Excel 文件：").grid(row=5, column=0, sticky=W, pady=3)
        ttk.Entry(main, textvariable=self.var_xlsx, state=DISABLED, width=24).grid(row=5, column=1, sticky=EW, pady=3)
        ttk.Button(main, text="浏览", command=self.select_xlsx).grid(row=5, column=2, padx=2, pady=3)

        ttk.Label(main, text="Sheet 名：").grid(row=6, column=0, sticky=W, pady=3)
        ttk.Entry(main, textvariable=self.var_sheet, width=15).grid(row=6, column=1, sticky=W, pady=3)

        ttk.Label(main, text="项目编号列：").grid(row=7, column=0, sticky=W, pady=3)
        ttk.Entry(main, textvariable=self.var_col, width=15).grid(row=7, column=1, sticky=W, pady=3)

        # 分割线
        ttk.Separator(main, orient=HORIZONTAL).grid(row=8, column=0, columnspan=3, sticky=EW, pady=6)

        # 手动输入项目ID（一行一个）
        ttk.Label(main, text="手动输入项目ID（一行一个）", font="bold").grid(row=9, column=0, columnspan=3, sticky=W)
        self.txt_project = ScrolledText(main, width=35, height=6)
        self.txt_project.grid(row=10, column=0, columnspan=3, sticky=EW, pady=3)

        # 分割线
        ttk.Separator(main, orient=HORIZONTAL).grid(row=11, column=0, columnspan=3, sticky=EW, pady=6)

        # 下载类型
        ttk.Label(main, text="下载类型：").grid(row=12, column=0, sticky=W, pady=3)
        ttk.Checkbutton(main, text="合同", variable=self.var_contract).grid(row=12, column=1, sticky=W)
        ttk.Checkbutton(main, text="发票", variable=self.var_invoice).grid(row=12, column=2, sticky=W)

        # 解压
        ttk.Checkbutton(main, text="自动解压压缩包", variable=self.var_extract).grid(row=13, column=0, columnspan=3, sticky=W, pady=3)

        # 按钮
        self.btn_start = ttk.Button(main, text="开始下载", command=self.start_download)
        self.btn_start.grid(row=14, column=0, columnspan=3, pady=8)

        # 进度条
        self.progress = ttk.Progressbar(main, mode="determinate")
        self.progress.grid(row=15, column=0, columnspan=3, sticky=EW, pady=3)

        # 状态栏

        self.status_bar = ttk.Label(self, textvariable=self.var_status, relief=SUNKEN, anchor=W, padding=(5, 2))
        self.status_bar.grid(row=1, column=0, sticky=EW)

        if self.has_cache:
            self.entry_pwd.config(state=DISABLED)
            self.update_status("已加载缓存密码", "info")


    def select_xlsx(self):
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx;*.xls")])
        if path:
            self.var_xlsx.set(path)
            self.txt_project.delete("1.0", END)

    def update_status(self, msg, level="info"):
        self.var_status.set(msg)
        if level == "error":
            self.status_bar.config(foreground="red")
            logger.error(msg)
        else:
            self.status_bar.config(foreground="black")
            logger.info(msg)

    def get_project_ids(self):
        xlsx = self.var_xlsx.get().strip()
        if xlsx:
            # 实际这里用 pandas 读 Excel
            logger.info(f"读取Excel: {xlsx}, sheet={self.var_sheet.get()}, col={self.var_col.get()}")
            return []

        text = self.txt_project.get("1.0", END).strip()
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        return lines

    def validate(self):
        if not self.var_user.get().strip():
            self.update_status("请输入EO账号", "error")
            return False

        if not self.has_cache and not self.var_pwd.get().strip():
            self.update_status("请输入密码", "error")
            return False

        ids = self.get_project_ids()
        xlsx = self.var_xlsx.get().strip()
        if not ids and not xlsx:
            self.update_status("请输入项目ID 或 选择Excel", "error")
            return False

        if ids and xlsx:
            self.update_status("Excel 和 手动输入不能同时使用", "error")
            return False

        if not self.var_contract.get() and not self.var_invoice.get():
            self.update_status("至少选择一种下载类型", "error")
            return False

        return True

    # ==================== 下载逻辑（线程执行） ====================
    def download_task(self, project_ids, cfg):
        try:

                # ========== 这里替换成你的真实下载逻辑 ==========
                # download_contract(pid, ...)
                # download_invoice(pid, ...)
                # if cfg["extract"]: unzip(...)

            self.progress["value"] = 100
            self.update_status("所有任务下载完成！")
            messagebox.showinfo("完成", "下载任务已全部完成")

        except Exception as e:
            logger.exception("下载任务异常")
            self.update_status(f"异常: {str(e)}", "error")
        finally:
            self.btn_start.config(state=NORMAL)

    def start_download(self):
        if not self.validate():
            return

        # 保存密码
        # if not self.has_cache:
        #     save_cache(self.var_user.get(), self.var_pwd.get())

        # 构造参数
        cfg = {
            "user": self.var_user.get(),
            "base_path": self.var_base.get(),
            "contract": self.var_contract.get(),
            "invoice": self.var_invoice.get(),
            "extract": self.var_extract.get(),
        }
        project_ids = self.get_project_ids()

        # 线程启动
        self.btn_start.config(state=DISABLED)
        self.stop_flag = False
        self.progress["value"] = 0
        self.download_thread = threading.Thread(
            target=self.download_task,
            args=(project_ids, cfg)
        )
        self.download_thread.start()

if __name__ == "__main__":
    try:
        app = DownloadDialog()
        app.mainloop()
    except Exception as e:
        logger.exception("程序异常退出")
