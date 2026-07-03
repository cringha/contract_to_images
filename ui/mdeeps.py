import json
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk
import threading

# -------------------------- 数据模型 --------------------------
class Snapshot:
    """截图组（例如一份合同或一个订单）"""
    def __init__(self, name, snapshots):
        self.name = name
        self.snapshots = snapshots   # 文件名列表
        # 用于标记删除的集合，存储要删除的图片在 snapshots 列表中的索引
        self.deleted_indices = set()

    def to_dict(self):
        """导出为 JSON 兼容格式（仅保留未被标记删除的图片）"""
        kept = [img for i, img in enumerate(self.snapshots) if i not in self.deleted_indices]
        return {"name": self.name, "snapshots": kept}

class Project:
    def __init__(self, contract_id, meta, contracts=None, orders=None, invoices=None):
        self.contract_id = contract_id
        self.meta = meta
        self.contracts = contracts or []      # Snapshot 列表
        self.orders = orders or []            # 列表的列表，每个内部列表是 Snapshot 列表
        self.invoices = invoices or []        # 同理

    def to_dict(self):
        return {
            "contractId": self.contract_id,
            "meta": self.meta,
            "contracts": [c.to_dict() for c in self.contracts],
            "orders": [[o.to_dict() for o in order_list] for order_list in self.orders],
            "invoices": [[inv.to_dict() for inv in inv_list] for inv_list in self.invoices]
        }

# -------------------------- 主程序类 --------------------------
class ImageViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片浏览与标注工具")
        self.root.geometry("1200x700")

        # ---------- 全局状态 ----------
        self.root_dir = None                # 截图根目录
        self.json_path = None               # 当前加载的 JSON 文件路径
        self.projects = []                 # Project 列表
        self.current_project_idx = -1      # 当前项目索引
        # 当前选中的快照组类型：'contract', 'order', 'invoice'
        self.current_group_type = None
        self.current_group_index = 0       # 对于 order/invoice 的索引，contract 固定为 0
        self.current_snapshot = None       # 当前 Snapshot 对象
        self.current_image_pos = 0         # 在当前 Snapshot.snapshots 中的位置

        # ---------- UI 组件 ----------
        self._create_widgets()
        self._bind_keys()

        # ---------- 初始状态 ----------
        self.update_status("未加载数据", "未选择根目录")

    def _create_widgets(self):
        # 顶部工具栏
        toolbar = tk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        btn_load_json = tk.Button(toolbar, text="加载 JSON", command=self.load_json)
        btn_load_json.pack(side=tk.LEFT, padx=2)

        btn_select_root = tk.Button(toolbar, text="选择截图根目录", command=self.select_root_dir)
        btn_select_root.pack(side=tk.LEFT, padx=2)

        btn_save = tk.Button(toolbar, text="保存", command=self.save_json)
        btn_save.pack(side=tk.LEFT, padx=2)

        tk.Label(toolbar, text="项目:").pack(side=tk.LEFT, padx=(10,2))
        self.project_var = tk.StringVar()
        self.project_combo = ttk.Combobox(toolbar, textvariable=self.project_var, state="readonly", width=30)
        self.project_combo.pack(side=tk.LEFT, padx=2)
        self.project_combo.bind("<<ComboboxSelected>>", self.on_project_changed)

        tk.Label(toolbar, text="组:").pack(side=tk.LEFT, padx=(10,2))
        self.group_var = tk.StringVar()
        self.group_combo = ttk.Combobox(toolbar, textvariable=self.group_var, state="readonly", width=40)
        self.group_combo.pack(side=tk.LEFT, padx=2)
        self.group_combo.bind("<<ComboboxSelected>>", self.on_group_changed)

        # 图片显示区域
        self.image_frame = tk.Frame(self.root)
        self.image_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 三张图片的容器，使用 grid 分布
        self.img_labels = []  # 保存三个 Label 对象
        for i in range(3):
            frame = tk.Frame(self.image_frame, bd=2, relief=tk.RIDGE)
            frame.grid(row=0, column=i, sticky="nsew", padx=5, pady=5)
            label = tk.Label(frame, bg="#f0f0f0")
            label.pack(fill=tk.BOTH, expand=True)
            # 绑定点击事件
            label.bind("<Button-1>", lambda e, idx=i: self.on_image_click(idx))
            self.img_labels.append(label)

        # 让三列等宽
        self.image_frame.grid_columnconfigure(0, weight=1)
        self.image_frame.grid_columnconfigure(1, weight=1)
        self.image_frame.grid_columnconfigure(2, weight=1)
        self.image_frame.grid_rowconfigure(0, weight=1)

        # 页码和按钮行
        nav_frame = tk.Frame(self.root)
        nav_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

        self.page_label = tk.Label(nav_frame, text="0 / 0")
        self.page_label.pack(side=tk.LEFT, padx=10)

        btn_first = tk.Button(nav_frame, text="首页", command=self.go_first)
        btn_first.pack(side=tk.LEFT, padx=2)

        btn_prev = tk.Button(nav_frame, text="上一张", command=self.prev_image)
        btn_prev.pack(side=tk.LEFT, padx=2)

        btn_next = tk.Button(nav_frame, text="下一张", command=self.next_image)
        btn_next.pack(side=tk.LEFT, padx=2)

        btn_last = tk.Button(nav_frame, text="尾页", command=self.go_last)
        btn_last.pack(side=tk.LEFT, padx=2)

        btn_mark = tk.Button(nav_frame, text="标记/取消标记", command=self.toggle_mark)
        btn_mark.pack(side=tk.LEFT, padx=2)

        # 状态栏
        self.status_var = tk.StringVar()
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _bind_keys(self):
        self.root.bind("<Left>", lambda e: self.prev_image())
        self.root.bind("<Right>", lambda e: self.next_image())
        self.root.bind("<Delete>", lambda e: self.toggle_mark())
        # 让焦点在 root 上才能捕获键盘事件
        self.root.focus_set()

    # ---------------------- 状态更新与显示 ----------------------
    def update_status(self, json_name, root_dir):
        """更新状态栏"""
        self.status_var.set(f"JSON: {json_name}  |  截图根目录: {root_dir}")

    def update_page_label(self):
        """更新页码"""
        if self.current_snapshot:
            total = len(self.current_snapshot.snapshots)
            pos = self.current_image_pos + 1
            self.page_label.config(text=f"{pos} / {total}")
        else:
            self.page_label.config(text="0 / 0")

    def update_project_combo(self):
        """更新项目下拉列表"""
        names = [p.meta.get("项目名称", p.contract_id) for p in self.projects]
        self.project_combo['values'] = names
        if self.current_project_idx >= 0:
            self.project_var.set(names[self.current_project_idx])
        else:
            self.project_var.set("")

    def update_group_combo(self):
        """更新组下拉列表（合同/订单/发票）"""
        if self.current_project_idx < 0:
            self.group_combo['values'] = []
            self.group_var.set("")
            return

        proj = self.projects[self.current_project_idx]
        groups = []
        # 合同
        for c in proj.contracts:
            groups.append(("合同", c.name))
        # 订单
        for idx, order_list in enumerate(proj.orders):
            for o in order_list:
                groups.append((f"订单{idx+1}", o.name))
        # 发票
        for idx, inv_list in enumerate(proj.invoices):
            for inv in inv_list:
                groups.append((f"发票{idx+1}", inv.name))

        # 显示为 "类型: 名称"
        display = [f"{typ}: {name}" for typ, name in groups]
        self.group_combo['values'] = display
        # 根据当前状态选中对应项
        if self.current_group_type and self.current_snapshot:
            # 找出当前组在列表中的位置
            target = None
            if self.current_group_type == 'contract':
                target = f"合同: {self.current_snapshot.name}"
            elif self.current_group_type == 'order':
                target = f"订单{self.current_group_index+1}: {self.current_snapshot.name}"
            elif self.current_group_type == 'invoice':
                target = f"发票{self.current_group_index+1}: {self.current_snapshot.name}"
            if target in display:
                self.group_var.set(target)
            else:
                self.group_var.set("")
        else:
            self.group_var.set("")

    def load_current_snapshot(self, group_type, group_idx, snapshot):
        """设置当前快照组并刷新显示"""
        self.current_group_type = group_type
        self.current_group_index = group_idx
        self.current_snapshot = snapshot
        self.current_image_pos = 0
        self.update_group_combo()
        self.refresh_images()
        self.update_page_label()

    def refresh_images(self):
        """根据当前状态刷新三张图片"""
        if not self.current_snapshot or not self.root_dir:
            # 显示空白
            for label in self.img_labels:
                label.config(image='', text='无图片')
            return

        snapshots = self.current_snapshot.snapshots
        total = len(snapshots)
        positions = [self.current_image_pos - 1, self.current_image_pos, self.current_image_pos + 1]
        images = []

        for pos in positions:
            if 0 <= pos < total:
                fname = snapshots[pos]
                full_path = os.path.join(self.root_dir, fname)
                try:
                    img = Image.open(full_path)
                    images.append(img)
                except Exception as e:
                    print(f"加载图片失败: {full_path}, {e}")
                    images.append(None)
            else:
                images.append(None)

        # 调整大小并显示
        for i, img in enumerate(images):
            label = self.img_labels[i]
            if img is None:
                label.config(image='', text='无图片')
            else:
                # 获取 label 实际尺寸
                label.update_idletasks()
                w = label.winfo_width()
                h = label.winfo_height()
                if w <= 1 or h <= 1:
                    w, h = 300, 200  # 默认大小
                # 缩放图片，保持宽高比
                img_copy = img.copy()
                img_copy.thumbnail((w, h), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img_copy)
                label.config(image=photo, text='')
                label.image = photo  # 保持引用

        # 更新标记样式（在中间图片上叠加红色遮罩）
        self.update_mark_overlay()

    def update_mark_overlay(self):
        """在中间图片上显示/隐藏标记（透明红色）"""
        # 由于 Tkinter 无法直接在 Label 上叠加透明层，我们采用简单方法：
        # 如果当前图片已被标记，则在中间 Label 上添加一个红色边框，或改变背景色。
        # 更优雅的做法：使用 Canvas，但为了简化，我们仅改变 Label 的边框颜色。
        middle_label = self.img_labels[1]
        if self.current_snapshot and self.current_image_pos in self.current_snapshot.deleted_indices:
            middle_label.config(highlightbackground="red", highlightcolor="red", highlightthickness=3)
        else:
            middle_label.config(highlightthickness=0)

    # ---------------------- 动作方法 ----------------------
    def prev_image(self):
        if not self.current_snapshot:
            return
        if self.current_image_pos > 0:
            self.current_image_pos -= 1
            self.refresh_images()
            self.update_page_label()
        else:
            # 切换到上一个快照组
            if not self._switch_to_prev_group():
                self.root.bell()

    def next_image(self):
        if not self.current_snapshot:
            return
        total = len(self.current_snapshot.snapshots)
        if self.current_image_pos < total - 1:
            self.current_image_pos += 1
            self.refresh_images()
            self.update_page_label()
        else:
            # 切换到下一个快照组
            if not self._switch_to_next_group():
                self.root.bell()

    def toggle_mark(self):
        """标记/取消标记当前图片"""
        if not self.current_snapshot:
            return
        pos = self.current_image_pos
        if pos in self.current_snapshot.deleted_indices:
            self.current_snapshot.deleted_indices.remove(pos)
        else:
            self.current_snapshot.deleted_indices.add(pos)
        self.update_mark_overlay()

    def go_first(self):
        if self.current_snapshot:
            self.current_image_pos = 0
            self.refresh_images()
            self.update_page_label()

    def go_last(self):
        if self.current_snapshot:
            self.current_image_pos = len(self.current_snapshot.snapshots) - 1
            self.refresh_images()
            self.update_page_label()

    # ---------------------- 组切换辅助 ----------------------
    def _switch_to_next_group(self):
        """切换到下一个可用的快照组，返回是否成功"""
        if self.current_project_idx < 0:
            return False
        proj = self.projects[self.current_project_idx]
        # 构建所有组的列表：(type, index, snapshot)
        groups = []
        # 合同
        for c in proj.contracts:
            groups.append(('contract', 0, c))
        # 订单
        for idx, order_list in enumerate(proj.orders):
            for o in order_list:
                groups.append(('order', idx, o))
        # 发票
        for idx, inv_list in enumerate(proj.invoices):
            for inv in inv_list:
                groups.append(('invoice', idx, inv))

        if not groups:
            return False

        # 找当前组在列表中的位置
        cur = None
        for i, (typ, idx, snap) in enumerate(groups):
            if typ == self.current_group_type and idx == self.current_group_index and snap == self.current_snapshot:
                cur = i
                break
        if cur is None:
            # 如果当前组不在列表中（可能因为未初始化），取第一个
            typ, idx, snap = groups[0]
            self.load_current_snapshot(typ, idx, snap)
            return True

        next_idx = (cur + 1) % len(groups)
        typ, idx, snap = groups[next_idx]
        self.load_current_snapshot(typ, idx, snap)
        return True

    def _switch_to_prev_group(self):
        if self.current_project_idx < 0:
            return False
        proj = self.projects[self.current_project_idx]
        groups = []
        for c in proj.contracts:
            groups.append(('contract', 0, c))
        for idx, order_list in enumerate(proj.orders):
            for o in order_list:
                groups.append(('order', idx, o))
        for idx, inv_list in enumerate(proj.invoices):
            for inv in inv_list:
                groups.append(('invoice', idx, inv))
        if not groups:
            return False

        cur = None
        for i, (typ, idx, snap) in enumerate(groups):
            if typ == self.current_group_type and idx == self.current_group_index and snap == self.current_snapshot:
                cur = i
                break
        if cur is None:
            typ, idx, snap = groups[-1]  # 取最后一个
            self.load_current_snapshot(typ, idx, snap)
            return True

        prev_idx = (cur - 1) % len(groups)
        typ, idx, snap = groups[prev_idx]
        self.load_current_snapshot(typ, idx, snap)
        return True

    def _switch_to_next_project(self):
        if self.current_project_idx < 0:
            if self.projects:
                self.current_project_idx = 0
                self._load_project(self.current_project_idx)
                return True
            return False
        if self.current_project_idx < len(self.projects) - 1:
            self.current_project_idx += 1
            self._load_project(self.current_project_idx)
            return True
        return False

    def _switch_to_prev_project(self):
        if self.current_project_idx < 0:
            if self.projects:
                self.current_project_idx = len(self.projects) - 1
                self._load_project(self.current_project_idx)
                return True
            return False
        if self.current_project_idx > 0:
            self.current_project_idx -= 1
            self._load_project(self.current_project_idx)
            return True
        return False

    def _load_project(self, idx):
        """加载指定索引的项目，并设置默认组（第一组）"""
        proj = self.projects[idx]
        # 选择第一个非空组：合同 > 订单 > 发票
        groups = []
        if proj.contracts:
            groups.append(('contract', 0, proj.contracts[0]))
        if proj.orders:
            groups.append(('order', 0, proj.orders[0][0] if proj.orders[0] else None))
        if proj.invoices:
            groups.append(('invoice', 0, proj.invoices[0][0] if proj.invoices[0] else None))
        # 过滤掉 None
        groups = [g for g in groups if g[2] is not None]
        if groups:
            typ, idx, snap = groups[0]
            self.load_current_snapshot(typ, idx, snap)
        else:
            # 没有可用组
            self.current_snapshot = None
            self.current_group_type = None
            self.current_group_index = 0
            self.current_image_pos = 0
            self.update_group_combo()
            self.refresh_images()
            self.update_page_label()
        self.update_project_combo()
        # 更新状态栏中的 JSON 名称
        if self.json_path:
            self.update_status(os.path.basename(self.json_path), self.root_dir or "未选择")

    # ---------------------- 加载与保存 ----------------------
    def load_json(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.projects = []
            for p_data in data.get("projects", []):
                # 构建 contracts
                contracts = []
                for c in p_data.get("contracts", []):
                    contracts.append(Snapshot(c.get("name", ""), c.get("snapshots", [])))
                # 构建 orders
                orders = []
                for order_list in p_data.get("orders", []):
                    order_snapshots = []
                    for o in order_list:
                        order_snapshots.append(Snapshot(o.get("name", ""), o.get("snapshots", [])))
                    orders.append(order_snapshots)
                # 构建 invoices
                invoices = []
                for inv_list in p_data.get("invoices", []):
                    inv_snapshots = []
                    for inv in inv_list:
                        inv_snapshots.append(Snapshot(inv.get("name", ""), inv.get("snapshots", [])))
                    invoices.append(inv_snapshots)

                proj = Project(
                    contract_id=p_data.get("contractId", ""),
                    meta=p_data.get("meta", {}),
                    contracts=contracts,
                    orders=orders,
                    invoices=invoices
                )
                self.projects.append(proj)

            self.json_path = file_path
            # 重置状态
            self.current_project_idx = 0 if self.projects else -1
            if self.current_project_idx >= 0:
                self._load_project(self.current_project_idx)
            else:
                self.update_project_combo()
                self.update_group_combo()
                self.refresh_images()
                self.update_page_label()
            self.update_status(os.path.basename(file_path), self.root_dir or "未选择")
        except Exception as e:
            messagebox.showerror("加载错误", f"无法加载 JSON 文件:\n{e}")

    def save_json(self):
        if not self.json_path:
            messagebox.showwarning("保存失败", "请先加载 JSON 文件")
            return
        # 构建输出数据
        output = {"projects": []}
        for proj in self.projects:
            output["projects"].append(proj.to_dict())
        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("保存成功", f"已保存至 {self.json_path}")
        except Exception as e:
            messagebox.showerror("保存错误", f"保存失败:\n{e}")

    def select_root_dir(self):
        dir_path = filedialog.askdirectory(title="选择截图根目录")
        if dir_path:
            self.root_dir = dir_path
            self.update_status(os.path.basename(self.json_path) if self.json_path else "未加载",
                               self.root_dir)
            self.refresh_images()  # 刷新图片显示

    # ---------------------- 下拉事件 ----------------------
    def on_project_changed(self, event):
        selection = self.project_var.get()
        for idx, p in enumerate(self.projects):
            name = p.meta.get("项目名称", p.contract_id)
            if name == selection:
                self.current_project_idx = idx
                self._load_project(idx)
                break

    def on_group_changed(self, event):
        selection = self.group_var.get()
        if not selection:
            return
        # 解析 "类型: 名称"
        if ": " in selection:
            typ_part, name_part = selection.split(": ", 1)
            typ = None
            if typ_part.startswith("合同"):
                typ = 'contract'
            elif typ_part.startswith("订单"):
                typ = 'order'
                idx_str = typ_part.replace("订单", "")
                if idx_str:
                    group_idx = int(idx_str) - 1
                else:
                    group_idx = 0
            elif typ_part.startswith("发票"):
                typ = 'invoice'
                idx_str = typ_part.replace("发票", "")
                if idx_str:
                    group_idx = int(idx_str) - 1
                else:
                    group_idx = 0
            else:
                return

            # 在当前项目中查找匹配的组
            proj = self.projects[self.current_project_idx]
            if typ == 'contract':
                for c in proj.contracts:
                    if c.name == name_part:
                        self.load_current_snapshot('contract', 0, c)
                        break
            elif typ == 'order':
                for idx, order_list in enumerate(proj.orders):
                    for o in order_list:
                        if o.name == name_part:
                            self.load_current_snapshot('order', idx, o)
                            break
                    else:
                        continue
                    break
            elif typ == 'invoice':
                for idx, inv_list in enumerate(proj.invoices):
                    for inv in inv_list:
                        if inv.name == name_part:
                            self.load_current_snapshot('invoice', idx, inv)
                            break
                    else:
                        continue
                    break

    # ---------------------- 图片点击处理 ----------------------
    def on_image_click(self, idx):
        """点击图片：左图-上一张，中图-标记，右图-下一张"""
        if idx == 0:
            self.prev_image()
        elif idx == 1:
            self.toggle_mark()
        elif idx == 2:
            self.next_image()

    # ---------------------- 窗口大小变化自适应 ----------------------
    def on_resize(self, event):
        self.refresh_images()

# -------------------------- 启动 --------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = ImageViewerApp(root)
    root.bind("<Configure>", app.on_resize)  # 绑定窗口改变事件
    root.mainloop()