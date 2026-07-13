import os
import json
import hashlib
import logging
import threading
from pathlib import Path
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import ctypes

# ======================== 日志配置 ========================
logger = logging.getLogger("ContractInvoiceDownloader")
logger.setLevel(logging.INFO)
log_handler = logging.FileHandler("download_tool.log", encoding="utf-8")
log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(log_handler)

# ======================== 密码缓存工具函数 ========================
CACHE_PATH = Path.home() / ".eo_tool_cache.json"

def encrypt(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def save_cache(user: str, pwd: str):
    try:
        data = {"user": user, "enc_pwd": encrypt(pwd)}
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("用户信息已缓存")
    except Exception as e:
        logger.exception("保存缓存失败")

def load_cache() -> tuple[str, str]:
    if not CACHE_PATH.exists():
        return "", ""
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            d = json.load(f)
        return d.get("user", ""), d.get("enc_pwd", "")
    except Exception as e:
        logger.exception("加载缓存失败")
        return "", ""

def load_cached_password():
    user, enc_pwd = load_cache()
    return user, "", "", enc_pwd

# ======================== 主窗口类 ========================
class DownloadDialog(Tk):
    def __init__(self):
        super().__init__()
        # ---------------- 全局字体+高分屏适配 ----------------
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        from tkinter import font
        # 全局默认字体统一改为9号
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(size=9)
        text_font = font.nametofont("TkTextFont")
        text_font.configure(size=9)
        bold_font = font.Font(size=9, weight="bold")

        # 窗口基础设置
        self.title("合同发票下载工具")
        self.resizable(False, False)
        self.attributes("-toolwindow", True)

        # 界面绑定变量
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

        # 登录状态标记
        self.is_login = False

        # 加载本地缓存账号密码
        cache_user, _, _, cache_enc = load_cached_password()
        self.cache_user = cache_user
        self.cache_enc_pwd = cache_enc
        self.has_cache = bool(cache_enc)

        # 下载线程控制
        self.download_thread = None
        self.stop_flag = False

        # 创建所有界面控件
        self.create_widgets(bold_font)
        # 初始化：未登录，所有功能区控件禁用
        self.set_func_widgets_state(DISABLED)

    def create_widgets(self, bold_font):
        main = ttk.Frame(self, padding=10)
        main.grid(row=0, column=0, sticky=NSEW)

        # ========= 优先创建状态栏，解决未初始化调用崩溃BUG =========
        self.status_bar = ttk.Label(self, textvariable=self.var_status, relief=SUNKEN, anchor=W, padding=(5, 2))
        self.status_bar.grid(row=1, column=0, sticky=EW)

        # 1. EO账号行
        ttk.Label(main, text="EO账号：").grid(row=0, column=0, sticky=W, pady=4)
        self.entry_user = ttk.Entry(main, textvariable=self.var_user, width=30)
        self.entry_user.grid(row=0, column=1, columnspan=2, sticky=EW, pady=4)

        # 2. 密码行 + 登录按钮 + 清除登录按钮（依次靠右排列）
        ttk.Label(main, text="密码：").grid(row=1, column=0, sticky=W, pady=4)
        self.entry_pwd = ttk.Entry(main, textvariable=self.var_pwd, show="*", width=20)
        self.entry_pwd.grid(row=1, column=1, sticky=EW, pady=4)

        self.btn_login = ttk.Button(main, text="登录", command=self.login, width=7)
        self.btn_login.grid(row=1, column=2, padx=3, pady=4)

        # 新增：清除登录按钮
        self.btn_clear_login = ttk.Button(main, text="清除登录", command=self.clear_login, width=8)
        self.btn_clear_login.grid(row=1, column=3, padx=3, pady=4)

        # 加载缓存填充账号，设置输入框状态
        if self.has_cache:
            self.var_user.set(self.cache_user)
            self.entry_user.config(state=DISABLED)
            self.entry_pwd.config(state=DISABLED)
            self.update_status("检测到本地缓存账号，请点击登录", "info")
        else:
            self.update_status("无缓存账号，请输入账号密码登录", "info")

        # 分割线
        ttk.Separator(main, orient=HORIZONTAL).grid(row=2, column=0, columnspan=4, sticky=EW, pady=6)

        # 保存目录
        ttk.Label(main, text="保存目录：").grid(row=3, column=0, sticky=W, pady=3)
        self.entry_base = ttk.Entry(main, textvariable=self.var_base)
        self.entry_base.grid(row=3, column=1, columnspan=3, sticky=EW, pady=3)

        # Excel分组标题
        ttk.Label(main, text="从 Excel 读取项目ID", font=bold_font).grid(row=4, column=0, columnspan=4, sticky=W, pady=4)
        ttk.Label(main, text="Excel 文件：").grid(row=5, column=0, sticky=W, pady=3)
        self.entry_xlsx = ttk.Entry(main, textvariable=self.var_xlsx)
        self.entry_xlsx.grid(row=5, column=1, columnspan=2, sticky=EW, pady=3)
        self.btn_select_xlsx = ttk.Button(main, text="浏览", command=self.select_xlsx)
        self.btn_select_xlsx.grid(row=5, column=3, padx=3, pady=3)

        ttk.Label(main, text="Sheet 名：").grid(row=6, column=0, sticky=W, pady=3)
        self.entry_sheet = ttk.Entry(main, textvariable=self.var_sheet, width=16)
        self.entry_sheet.grid(row=6, column=1, sticky=W, pady=3)

        ttk.Label(main, text="项目编号列：").grid(row=7, column=0, sticky=W, pady=3)
        self.entry_col = ttk.Entry(main, textvariable=self.var_col, width=16)
        self.entry_col.grid(row=7, column=1, sticky=W, pady=3)

        # 分割线
        ttk.Separator(main, orient=HORIZONTAL).grid(row=8, column=0, columnspan=4, sticky=EW, pady=6)

        # 手动输入ID分组标题
        ttk.Label(main, text="手动输入项目ID（一行一个）", font=bold_font).grid(row=9, column=0, columnspan=4, sticky=W, pady=4)
        self.txt_project = ScrolledText(main, width=38, height=6)
        self.txt_project.grid(row=10, column=0, columnspan=4, sticky=EW, pady=3)

        # 分割线
        ttk.Separator(main, orient=HORIZONTAL).grid(row=11, column=0, columnspan=4, sticky=EW, pady=6)

        # 下载类型区域
        ttk.Label(main, text="下载类型：").grid(row=12, column=0, sticky=W, pady=3)
        self.chk_contract = ttk.Checkbutton(main, text="合同", variable=self.var_contract)
        self.chk_contract.grid(row=12, column=1, sticky=W)
        self.chk_invoice = ttk.Checkbutton(main, text="发票", variable=self.var_invoice)
        self.chk_invoice.grid(row=12, column=2, sticky=W)

        self.chk_extract = ttk.Checkbutton(main, text="自动解压压缩包", variable=self.var_extract)
        self.chk_extract.grid(row=13, column=0, columnspan=4, sticky=W, pady=3)

        # 开始下载按钮
        self.btn_start = ttk.Button(main, text="开始下载", command=self.start_download)
        self.btn_start.grid(row=14, column=0, columnspan=4, pady=8)

        # 进度条
        self.progress = ttk.Progressbar(main, mode="determinate")
        self.progress.grid(row=15, column=0, columnspan=4, sticky=EW, pady=3)

    def set_func_widgets_state(self, state):
        """统一控制所有下载功能控件启用/禁用"""
        self.entry_base.config(state=state)
        self.entry_xlsx.config(state=state)
        self.btn_select_xlsx.config(state=state)
        self.entry_sheet.config(state=state)
        self.entry_col.config(state=state)
        self.txt_project.config(state=state)
        self.chk_contract.config(state=state)
        self.chk_invoice.config(state=state)
        self.chk_extract.config(state=state)
        self.btn_start.config(state=state)

    def clear_login(self):
        """清除登录状态，删除缓存文件"""
        # 1. 删除缓存文件
        if CACHE_PATH.exists():
            try:
                os.remove(CACHE_PATH)
                logger.info("已删除本地登录缓存文件")
            except Exception as e:
                logger.exception("删除缓存文件失败")
                messagebox.showerror("错误", "缓存文件删除失败")
                return

        # 2. 重置登录状态
        self.is_login = False
        self.has_cache = False
        self.cache_user = ""
        self.cache_enc_pwd = ""

        # 3. 清空账号密码输入框
        self.var_user.set("")
        self.var_pwd.set("")

        # 4. 账号、密码输入框恢复可编辑，登录按钮启用
        self.entry_user.config(state=NORMAL)
        self.entry_pwd.config(state=NORMAL)
        self.btn_login.config(state=NORMAL)

        # 5. 所有下载功能控件禁用
        self.set_func_widgets_state(DISABLED)

        self.update_status("已清除登录缓存，请重新输入账号密码登录", "info")

    def login(self):
        """登录核心逻辑"""
        user = self.var_user.get().strip()
        pwd = self.var_pwd.get().strip()

        # 基础输入校验
        if not user:
            self.update_status("请输入EO账号", "error")
            return
        if not self.has_cache and not pwd:
            self.update_status("请输入登录密码", "error")
            return

        # ==================== 此处替换真实登录接口逻辑 ====================
        login_success = True
        # =================================================================

        if login_success:
            self.is_login = True
            self.update_status("登录成功！可进行下载操作", "info")
            messagebox.showinfo("提示", "登录验证通过")

            # 登录成功：账号、密码、登录按钮全部禁用
            self.entry_user.config(state=DISABLED)
            self.entry_pwd.config(state=DISABLED)
            self.btn_login.config(state=DISABLED)

            # 解锁全部下载功能控件
            self.set_func_widgets_state(NORMAL)

            # 无缓存时保存账号密码到本地
            if not self.has_cache:
                save_cache(user, pwd)
        else:
            self.update_status("登录失败，请检查账号密码", "error")
            messagebox.showerror("登录失败", "账号或密码错误，请重新输入")

    def select_xlsx(self):
        """选择Excel文件"""
        path = filedialog.askopenfilename(filetypes=[("Excel文件", "*.xlsx;*.xls")])
        if path:
            self.var_xlsx.set(path)
            self.txt_project.delete("1.0", END)

    def update_status(self, msg, level="info"):
        """更新底部状态栏文字"""
        self.var_status.set(msg)
        if level == "error":
            self.status_bar.config(foreground="red")
            logger.error(msg)
        else:
            self.status_bar.config(foreground="black")
            logger.info(msg)

    def get_project_ids(self):
        """读取项目ID（Excel/手动输入二选一）"""
        xlsx_path = self.var_xlsx.get().strip()
        if xlsx_path:
            logger.info(f"准备读取Excel：{xlsx_path}，Sheet：{self.var_sheet.get()}，列：{self.var_col.get()}")
            return []
        text_content = self.txt_project.get("1.0", END).strip()
        id_list = [line.strip() for line in text_content.splitlines() if line.strip()]
        return id_list

    def validate(self):
        """下载前参数校验"""
        if not self.is_login:
            self.update_status("请先完成登录", "error")
            return False
        ids = self.get_project_ids()
        xlsx = self.var_xlsx.get().strip()
        if not ids and not xlsx:
            self.update_status("请输入项目ID 或 选择Excel文件", "error")
            return False
        if ids and xlsx:
            self.update_status("Excel文件和手动输入ID不能同时使用", "error")
            return False
        if not self.var_contract.get() and not self.var_invoice.get():
            self.update_status("至少勾选一种下载类型（合同/发票）", "error")
            return False
        return True

    def download_task(self, project_ids, cfg):
        """后台下载线程任务（替换为真实业务代码）"""
        try:
            self.progress["value"] = 100
            self.update_status("所有任务下载完成！")
            messagebox.showinfo("完成", "下载任务已全部执行完毕")
        except Exception as e:
            logger.exception("下载任务发生异常")
            self.update_status(f"任务异常：{str(e)}", "error")
        finally:
            self.btn_start.config(state=NORMAL)

    def start_download(self):
        """触发下载按钮事件"""
        if not self.validate():
            return
        cfg = {
            "user": self.var_user.get(),
            "base_path": self.var_base.get(),
            "contract": self.var_contract.get(),
            "invoice": self.var_invoice.get(),
            "extract": self.var_extract.get(),
        }
        project_ids = self.get_project_ids()
        self.btn_start.config(state=DISABLED)
        self.stop_flag = False
        self.progress["value"] = 0
        self.download_thread = threading.Thread(target=self.download_task, args=(project_ids, cfg))
        self.download_thread.start()

# 程序入口
if __name__ == "__main__":
    try:
        app = DownloadDialog()
        app.mainloop()
    except Exception as e:
        logger.exception("程序全局异常退出")
