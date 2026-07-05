import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import argparse
import logging
import threading

from enties.task_convert_to_docx import task_convert_docx
from uitls.log import init_with_conf, get_log, LogConfig



# ==================== 主界面类 ====================
class ContractSnapApp:
    CONFIG_FILE = "config-covert-contract-docx.json"

    def __init__(self, root: tk.Tk):
        self.logger = get_log()
        self.root = root
        self.root.title("合同发票截图转DOCX")
        self.root.geometry("650x320")
        self.root.resizable(False, False)

        # 停止标志
        self.stop_flag = threading.Event()
        self.is_running = False

        # 加载配置
        self.config = self.load_config()

        # 界面组件
        self._create_widgets()
        # 状态栏
        self._create_status_bar()

    def load_config(self) -> argparse.Namespace:
        default = argparse.Namespace(
            input_json="",
            input_image_root="./local.images",
            docx_template_file="./templates/default-template.docx",
            output_docx_file="./contract-order-and-invoices.docx"
        )
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in data.items():
                    if hasattr(default, k):
                        setattr(default, k, v)
                self.logger.info("配置加载成功")
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
        return default

    def save_config(self):
        try:
            data = {
                "input_json": self.var_input_json.get(),
                "input_image_root": self.var_image_root.get(),
                "docx_template_file": self.var_template.get(),
                "output_docx_file": self.var_output.get()
            }
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.info("配置已保存")
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 变量
        self.var_input_json = tk.StringVar(value=self.config.input_json)
        self.var_image_root = tk.StringVar(value=self.config.input_image_root)
        self.var_template = tk.StringVar(value=self.config.docx_template_file)
        self.var_output = tk.StringVar(value=self.config.output_docx_file)

        # -------------------- 输入JSON文件 --------------------
        ttk.Label(main_frame, text="输入Json文件:").grid(row=0, column=0, sticky="w", pady=8)
        ttk.Entry(main_frame, textvariable=self.var_input_json, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="选择", command=self.select_json).grid(row=0, column=2)

        # -------------------- 图片根目录 --------------------
        ttk.Label(main_frame, text="截图根目录:").grid(row=1, column=0, sticky="w", pady=8)
        ttk.Entry(main_frame, textvariable=self.var_image_root, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="选择", command=self.select_image_dir).grid(row=1, column=2)

        # -------------------- DOCX模板 --------------------
        ttk.Label(main_frame, text="DOCX模板文件:").grid(row=2, column=0, sticky="w", pady=8)
        ttk.Entry(main_frame, textvariable=self.var_template, width=50).grid(row=2, column=1, padx=5)
        ttk.Button(main_frame, text="选择", command=self.select_template).grid(row=2, column=2)

        # -------------------- 输出DOCX --------------------
        ttk.Label(main_frame, text="输出DOCX文件:").grid(row=3, column=0, sticky="w", pady=8)
        ttk.Entry(main_frame, textvariable=self.var_output, width=50).grid(row=3, column=1, padx=5)
        ttk.Button(main_frame, text="选择", command=self.select_output).grid(row=3, column=2)

        # -------------------- 按钮区 --------------------
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=20)

        self.btn_start = ttk.Button(btn_frame, text="开始执行", command=self.start_task, width=12)
        self.btn_start.pack(side=tk.LEFT, padx=10)

        self.btn_stop = ttk.Button(btn_frame, text="停止执行", command=self.stop_task, state=tk.DISABLED, width=12)
        self.btn_stop.pack(side=tk.LEFT, padx=10)

    def _create_status_bar(self):
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def set_status(self, msg: str):
        self.status_var.set(msg)
        self.logger.info(msg)

    # ==================== 文件选择 ====================
    def select_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if path:
            self.var_input_json.set(path)

    def select_image_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.var_image_root.set(path)

    def select_template(self):
        path = filedialog.askopenfilename(filetypes=[("DOCX Files", "*.docx"), ("All Files", "*.*")])
        if path:
            self.var_template.set(path)

    def select_output(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("DOCX Files", "*.docx"), ("All Files", "*.*")]
        )
        if path:
            self.var_output.set(path)

    # ==================== 任务控制 ====================
    def start_task(self):
        if self.is_running:
            return

        # 保存配置
        self.save_config()

        # 构造 Namespace 参数
        args = argparse.Namespace(
            input_json=self.var_input_json.get().strip(),
            input_image_root=self.var_image_root.get().strip(),
            docx_template_file=self.var_template.get().strip(),
            output_docx_file=self.var_output.get().strip()
        )

        # 简单校验
        if not args.input_json:
            messagebox.showwarning("提示", "请选择输入JSON文件")
            return

        # 状态切换
        self.is_running = True
        self.stop_flag.clear()
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.set_status("任务执行中...")

        # 后台线程执行
        threading.Thread(target=self._run_task, args=(args,), daemon=True).start()

    def stop_task(self):
        if not self.is_running:
            return
        self.stop_flag.set()
        self.set_status("正在停止任务...")

    def _run_task(self, args: argparse.Namespace):
        try:
            self.logger.info("===== 开始执行任务 =====")
            self.logger.debug(f"参数: {args}")

            new_file_name = task_convert_docx( args )

            if not self.stop_flag.is_set():
                self.set_status(f"任务执行完成:{new_file_name}")
                self.logger.info("===== 任务执行完成 =====")

        except Exception as e:
            self.logger.error(f"任务异常: {e}")
            self.set_status(f"任务异常: {str(e)}")
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.btn_start.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_stop.config(state=tk.DISABLED))

# ==================== 启动 ====================
if __name__ == "__main__":

    init_with_conf(LogConfig())
    logger = get_log()
    logger.debug("Convert contract  to docx")

    root = tk.Tk()
    app = ContractSnapApp(root)
    root.mainloop()
