import tkinter as tk
from tkinter import ttk, filedialog
import json
import os
import threading
import time
import logging
import argparse
from enties.task_convert_contract_snapshots import convert_contract_snapshots
from uitls.log import init_with_conf, get_log, LogConfig



# 配置文件路径
CONFIG_FILE = "config-contract-snaps.json"

class ContractSnapToolUI:
    def __init__(self, root):
        self.logger = get_log()
        self.root = root
        self.root.title("合同发票截图转换工具")
        self.root.geometry("750x450")
        self.root.resizable(False, False)

        # 停止标志
        self.stop_flag = False
        self.worker_thread = None

        # 加载配置
        self.config = self.load_config()

        # 变量绑定
        self.var_input_xlsx = tk.StringVar(value=self.config.get("input-xlsx", ""))
        self.var_contract_base_root = tk.StringVar(value=self.config.get("contract-base-root", ""))
        self.var_invoice_base_root = tk.StringVar(value=self.config.get("invoice-base-root", ""))
        self.var_output_image_root = tk.StringVar(value=self.config.get("output-image-root", "./local.images"))

        self.var_sheet_name_contract = tk.StringVar(value=self.config.get("sheet-name-contract", "Contract"))
        self.var_col_project_id = tk.StringVar(value=self.config.get("col-project-id", "项目编号"))
        self.var_col_contract_name = tk.StringVar(value=self.config.get("col-contract-name", "合同名称"))
        self.var_output_file = tk.StringVar(value=self.config.get("output-file", "./local-contracts.json"))

        # 主容器
        main_frame = ttk.Frame(root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ========== 第1行：输入XLSX ==========
        ttk.Label(main_frame, text="输入XLSX文件:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_input_xlsx, width=70).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="选择", command=self.select_xlsx).grid(row=0, column=2)

        # ========== 第2行：合同根目录 ==========
        ttk.Label(main_frame, text="合同文件根目录:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_contract_base_root, width=70).grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="选择", command=self.select_contract_dir).grid(row=1, column=2)

        # ========== 第3行：发票根目录 ==========
        ttk.Label(main_frame, text="发票文件根目录:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_invoice_base_root, width=70).grid(row=2, column=1, padx=5)
        ttk.Button(main_frame, text="选择", command=self.select_invoice_dir).grid(row=2, column=2)

        # ========== 第4行：输出图片根目录 ==========
        ttk.Label(main_frame, text="输出截图根目录:").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_output_image_root, width=70).grid(row=3, column=1, padx=5)
        ttk.Button(main_frame, text="选择", command=self.select_output_img_dir).grid(row=3, column=2)

        # ========== 第5行：工作表名 ==========
        ttk.Label(main_frame, text="合同工作表名:").grid(row=4, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_sheet_name_contract, width=30).grid(row=4, column=1, sticky="w", padx=5)

        # ========== 第6行：项目编号列名 ==========
        ttk.Label(main_frame, text="项目编号列名:").grid(row=5, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_col_project_id, width=30).grid(row=5, column=1, sticky="w", padx=5)

        # ========== 第7行：合同名称列名 ==========
        ttk.Label(main_frame, text="合同名称列名:").grid(row=6, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_col_contract_name, width=30).grid(row=6, column=1, sticky="w", padx=5)

        # ========== 第8行：输出JSON文件 ==========
        ttk.Label(main_frame, text="输出JSON文件:").grid(row=7, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_output_file, width=70).grid(row=7, column=1, padx=5)
        ttk.Button(main_frame, text="选择", command=self.select_output_json).grid(row=7, column=2)

        # ========== 按钮区域 ==========
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=8, column=0, columnspan=3, pady=20)

        self.btn_start = ttk.Button(btn_frame, text="开始执行", command=self.start_run, width=15)
        self.btn_start.pack(side=tk.LEFT, padx=10)

        self.btn_stop = ttk.Button(btn_frame, text="停止执行", command=self.stop_run, state=tk.DISABLED, width=15)
        self.btn_stop.pack(side=tk.LEFT, padx=10)

        # ========== 状态栏 ==========
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=5)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # 加载配置
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载配置失败: {e}")
        return {}

    # 保存配置
    def save_config(self):
        cfg = {
            "input-xlsx": self.var_input_xlsx.get().strip(),
            "contract-base-root": self.var_contract_base_root.get().strip(),
            "invoice-base-root": self.var_invoice_base_root.get().strip(),
            "output-image-root": self.var_output_image_root.get().strip(),
            "sheet-name-contract": self.var_sheet_name_contract.get().strip(),
            "col-project-id": self.var_col_project_id.get().strip(),
            "col-contract-name": self.var_col_contract_name.get().strip(),
            "output-file": self.var_output_file.get().strip()
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            self.logger.info("配置已保存到 " + CONFIG_FILE)
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")

    # 文件选择方法
    def select_xlsx(self):
        path = filedialog.askopenfilename(filetypes=[("Excel文件", "*.xlsx;*.xls")])
        if path:
            self.var_input_xlsx.set(path)

    def select_contract_dir(self):
        path = filedialog.askdirectory(title="选择合同根目录")
        if path:
            self.var_contract_base_root.set(path)

    def select_invoice_dir(self):
        path = filedialog.askdirectory(title="选择发票根目录")
        if path:
            self.var_invoice_base_root.set(path)

    def select_output_img_dir(self):
        path = filedialog.askdirectory(title="选择截图输出目录")
        if path:
            self.var_output_image_root.set(path)

    def select_output_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON文件", "*.json")])
        if path:
            self.var_output_file.set(path)

    # 开始执行
    def start_run(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return

        # 保存配置
        self.save_config()

        self.stop_flag = False
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.update_status("任务开始运行...")
        self.logger.info("开始执行转换任务")

        self.worker_thread = threading.Thread(target=self.do_work)
        self.worker_thread.daemon = True
        self.worker_thread.start()

    # 停止执行
    def stop_run(self):
        self.stop_flag = True
        self.update_status("正在停止任务...")
        self.logger.info("用户请求停止任务")

    # 任务结束后恢复按钮
    def on_task_finished(self):
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

    # 更新状态栏
    def update_status(self, msg):
        self.status_var.set(msg)

    # 实际业务逻辑
    def do_work(self):
        try:
            # 读取参数

            args = argparse.Namespace()

            args.input_xlsx = self.var_input_xlsx.get().strip()
            args.contract_base_root = self.var_contract_base_root.get().strip()
            args.invoice_base_root = self.var_invoice_base_root.get().strip()
            args.output_image_root = self.var_output_image_root.get().strip()

            args.sheet_name_contract = self.var_sheet_name_contract.get().strip()
            args.col_project_id = self.var_col_project_id.get().strip()
            args.col_contract_name = self.var_col_contract_name.get().strip()
            args.output_file = self.var_output_file.get().strip()
            self.logger.debug(f"运行参数: {args}")


            def cb_info(project_id, project_name):
                msg = f"project_id: {project_id}, project_name: {project_name}"
                logger.info(msg)
                self.update_status(msg)
                return self.stop_flag
            result = convert_contract_snapshots(args, cb_info)
            if result:
                self.update_status("任务执行完成！")
                self.logger.info("任务执行完成")
            else:
                self.update_status("用户取消！")

        except Exception as e:
            self.logger.error(f"任务异常: {e}", exc_info=True)
            self.update_status(f"异常: {str(e)}")
        finally:
            self.root.after(0, self.on_task_finished)

if __name__ == "__main__":
    init_with_conf(LogConfig())
    logger = get_log()
    logger.info("Convert contract to snapshots ")

    root = tk.Tk()
    app = ContractSnapToolUI(root)
    root.mainloop()