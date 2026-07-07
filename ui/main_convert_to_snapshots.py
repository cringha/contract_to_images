import argparse
import json
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog

from enties.task_convert_contract_snapshots import convert_contract_snapshots
from enties.task_download_contracts import CONFIG_DOWNLOAD_CONTRACT_FILE
from uitls.log import init_with_conf, get_log, LogConfig

# 日志配置


# 配置文件
CONFIG_FILE = "config-covert-contract-snapshots.json"


class ContractSnapToolUI:
    def __init__(self, root):

        self.logger = get_log()
        self.root = root
        self.root.title("合同发票截图转换工具")
        self.root.geometry("800x500")
        self.root.resizable(False, False)

        # 线程控制
        self.stop_flag = threading.Event()
        self.worker_thread = None

        self.download_contract_config = self.load_config0()

        # 加载配置并构建 Namespace
        self.config_dict = self.load_config()
        self.args = self.build_args_namespace(self.config_dict, self.download_contract_config)

        # 界面变量绑定
        self.var_input_xlsx = tk.StringVar(value=self.args.input_xlsx)
        self.var_contract_base_root = tk.StringVar(value=self.args.contract_base_root)
        self.var_invoice_base_root = tk.StringVar(value=self.args.invoice_base_root)
        self.var_output_image_root = tk.StringVar(value=self.args.output_image_root)

        self.var_sheet_name_contract = tk.StringVar(value=self.args.sheet_name_contract)
        self.var_col_project_id = tk.StringVar(value=self.args.col_project_id)
        self.var_col_contract_name = tk.StringVar(value=self.args.col_contract_name)
        self.var_output_file = tk.StringVar(value=self.args.output_file)

        # 新增：每个PDF最大截取页数，默认30
        self.var_max_pages_per_pdf = tk.StringVar(value=str(self.args.max_pages_per_pdf))

        # 主布局
        main_frame = ttk.Frame(root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 输入 XLSX
        ttk.Label(main_frame, text="输入XLSX文件:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_input_xlsx, width=70).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="选择", command=self.select_xlsx).grid(row=0, column=2)

        # 合同根目录
        ttk.Label(main_frame, text="合同文件根目录:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_contract_base_root, width=70).grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="选择", command=self.select_contract_dir).grid(row=1, column=2)

        # 发票根目录
        ttk.Label(main_frame, text="发票文件根目录:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_invoice_base_root, width=70).grid(row=2, column=1, padx=5)
        ttk.Button(main_frame, text="选择", command=self.select_invoice_dir).grid(row=2, column=2)

        # 输出图片目录
        ttk.Label(main_frame, text="输出截图根目录:").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_output_image_root, width=70).grid(row=3, column=1, padx=5)
        ttk.Button(main_frame, text="选择", command=self.select_output_img_dir).grid(row=3, column=2)

        # 新增：每个PDF最多截取页数
        ttk.Label(main_frame, text="单个PDF最大截取页数:").grid(row=4, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_max_pages_per_pdf, width=15).grid(row=4, column=1, sticky="w",
                                                                                      padx=5)

        # 工作表名
        ttk.Label(main_frame, text="合同工作表名:").grid(row=5, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_sheet_name_contract, width=30).grid(row=5, column=1, sticky="w",
                                                                                        padx=5)

        # 项目编号列
        ttk.Label(main_frame, text="项目编号列名:").grid(row=6, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_col_project_id, width=30).grid(row=6, column=1, sticky="w", padx=5)

        # 合同名称列
        ttk.Label(main_frame, text="合同名称列名:").grid(row=7, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_col_contract_name, width=30).grid(row=7, column=1, sticky="w",
                                                                                      padx=5)

        # 输出 JSON
        ttk.Label(main_frame, text="输出JSON文件:").grid(row=8, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.var_output_file, width=70).grid(row=8, column=1, padx=5)
        ttk.Button(main_frame, text="选择", command=self.select_output_json).grid(row=8, column=2)

        # 按钮区
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=9, column=0, columnspan=3, pady=20)

        self.btn_start = ttk.Button(btn_frame, text="开始执行", command=self.start_run, width=15)
        self.btn_start.pack(side=tk.LEFT, padx=10)

        self.btn_stop = ttk.Button(btn_frame, text="停止执行", command=self.stop_run, state=tk.DISABLED, width=15)
        self.btn_stop.pack(side=tk.LEFT, padx=10)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=5)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def build_args_namespace(self, config_dict, default_config_dict):
        """从配置字典构建 argparse.Namespace，带默认值"""
        ns = argparse.Namespace()

        NAME_INPUT_XLSX = "input-xlsx"
        NAME_CONTRACT_BASE_ROOT = "contract-base-root"
        NAME_INVOICE_BASE_ROOT = "invoice-base-root"
        NAME_SHEET_NAME_CONTRACT = "sheet-name-contract"
        NAME_COL_PROJECT_ID = "col-project-id"

        ns.input_xlsx = config_dict.get(NAME_INPUT_XLSX, default_config_dict.get(NAME_INPUT_XLSX, ""))
        ns.contract_base_root = config_dict.get(NAME_CONTRACT_BASE_ROOT,
                                                default_config_dict.get(NAME_CONTRACT_BASE_ROOT, ""))
        ns.invoice_base_root = config_dict.get(NAME_INVOICE_BASE_ROOT,
                                               default_config_dict.get(NAME_INVOICE_BASE_ROOT, ""))
        ns.output_image_root = config_dict.get("output-image-root", "./local.images")

        ns.sheet_name_contract = config_dict.get(NAME_SHEET_NAME_CONTRACT,
                                                 default_config_dict.get(NAME_SHEET_NAME_CONTRACT,
                                                                         "Contract"))  # config_dict.get("sheet-name-contract", "Contract")
        ns.col_project_id = config_dict.get(NAME_COL_PROJECT_ID, default_config_dict.get(NAME_COL_PROJECT_ID,
                                                                                         "项目编号"))  # config_dict.get("col-project-id", "项目编号")
        ns.col_contract_name = config_dict.get("col-contract-name", "合同名称")
        ns.output_file = config_dict.get("output-file", "./local-contracts.json")

        # 新增参数
        ns.max_pages_per_pdf = int(config_dict.get("max-pages-per-pdf", 30))

        return ns

    def load_config0(self):
        if os.path.exists(CONFIG_DOWNLOAD_CONTRACT_FILE):
            try:
                with open(CONFIG_DOWNLOAD_CONTRACT_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"加载配置失败: {e}")
        return {}

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"加载配置失败: {e}")
        return {}

    def save_config(self):
        """从界面读取并保存到配置文件"""
        cfg = {
            "input-xlsx": self.var_input_xlsx.get().strip(),
            "contract-base-root": self.var_contract_base_root.get().strip(),
            "invoice-base-root": self.var_invoice_base_root.get().strip(),
            "output-image-root": self.var_output_image_root.get().strip(),
            "max-pages-per-pdf": self.var_max_pages_per_pdf.get().strip(),
            "sheet-name-contract": self.var_sheet_name_contract.get().strip(),
            "col-project-id": self.var_col_project_id.get().strip(),
            "col-contract-name": self.var_col_contract_name.get().strip(),

            "output-file": self.var_output_file.get().strip()
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            self.logger.info("配置已保存")
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")

    def refresh_args_from_ui(self):
        """每次运行前从界面刷新 Namespace 参数"""
        self.args.input_xlsx = self.var_input_xlsx.get().strip()
        self.args.contract_base_root = self.var_contract_base_root.get().strip()
        self.args.invoice_base_root = self.var_invoice_base_root.get().strip()
        self.args.output_image_root = self.var_output_image_root.get().strip()

        # 页数做数字转换，防止输入非数字
        try:
            self.args.max_pages_per_pdf = int(self.var_max_pages_per_pdf.get().strip())
        except ValueError:
            self.args.max_pages_per_pdf = 30
            self.logger.warning("页数输入不合法，已使用默认值30")

        self.args.sheet_name_contract = self.var_sheet_name_contract.get().strip()
        self.args.col_project_id = self.var_col_project_id.get().strip()
        self.args.col_contract_name = self.var_col_contract_name.get().strip()
        self.args.output_file = self.var_output_file.get().strip()

    # ---------------------- 文件选择 ----------------------
    def select_xlsx(self):
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx;*.xls")])
        if path:
            self.var_input_xlsx.set(path)

    def select_contract_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.var_contract_base_root.set(path)

    def select_invoice_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.var_invoice_base_root.set(path)

    def select_output_img_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.var_output_image_root.set(path)

    def select_output_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            self.var_output_file.set(path)

    # ---------------------- 任务控制 ----------------------
    def start_run(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return

        self.save_config()
        self.refresh_args_from_ui()  # 刷新 Namespace

        self.stop_flag.clear()
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.update_status("任务开始")
        self.logger.info("开始执行")

        self.worker_thread = threading.Thread(target=self.do_work)
        self.worker_thread.daemon = True
        self.worker_thread.start()

    def stop_run(self):
        self.stop_flag.set()
        self.update_status("正在停止...")
        self.logger.info("请求停止任务")

    def on_task_finished(self):
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

    def update_status(self, msg):
        self.status_var.set(msg)

    # ---------------------- 业务逻辑 ----------------------
    def do_work(self):
        try:
            # 直接使用 self.args (argparse.Namespace)
            self.logger.debug(f"任务参数: {self.args}")
            self.logger.info(f"单个PDF最大截取页数: {self.args.max_pages_per_pdf}")

            def cb_info(project_id, project_name):
                msg = f"project_id: {project_id}, project_name: {project_name}"
                self.logger.info(msg)
                self.update_status(msg)
                return self.stop_flag.is_set()

            result = convert_contract_snapshots(self.args, cb_info)
            if result:
                self.update_status("任务执行完成！")
                self.logger.info("任务执行完成")
            else:
                self.update_status("用户取消！")

        except Exception as e:
            self.logger.error(f"异常: {e}", exc_info=True)
            self.update_status(f"异常: {e}")
        finally:
            self.root.after(0, self.on_task_finished)


if __name__ == "__main__":
    init_with_conf(LogConfig())
    logger = get_log()
    logger.info("Convert contract to snapshots ")

    root = tk.Tk()
    app = ContractSnapToolUI(root)
    root.mainloop()
