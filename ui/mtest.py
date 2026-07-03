import copy
import json
import os
import tkinter as tk
from tkinter import ttk, filedialog

import winsound
from PIL import Image, ImageTk

from ui.uisnaps.uisnapmodels import ProjectModelManager, ProjectModel, SnapshotModel

UI_TK_X = 'x'  # tk.X


class MainViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("项目合同订单发票截图清理工具")
        self.geometry("1600x980")
        self.minsize(1300, 750)

        # 全局数据
        self.json_full_path = ""
        self.image_root = ""
        self.all_projects: ProjectModelManager = ProjectModelManager()
        self.marked_file_set = set()  # 待删除截图文件名

        # 当前浏览指针
        self.cur_proj_idx = 0
        # self.cur_snap_type = "contracts"  # contracts / orders / invoices
        self.cur_group_idx = 0  # Snapshot分组下标
        self.cur_snapshot_idx = 0
        self.cur_img_pos = 0  # 当前截图下标

        # 图片缓存防止GC
        self.img_cache = [None, None, None]

        self.build_ui()
        # 键盘绑定
        self.bind("<Left>", lambda e: self.do_prev_img())
        self.bind("<Right>", lambda e: self.do_next_img())
        self.bind("<Delete>", lambda e: self.toggle_mark())
        self.update_status()

    def build_ui(self):
        # 顶部下拉栏
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=12, pady=8)

        ttk.Label(top_frame, text="项目：").grid(row=0, column=0, sticky="w")
        self.cb_proj = ttk.Combobox(top_frame, state="readonly", font=("微软雅黑", 10))
        self.cb_proj.grid(row=0, column=1, sticky="ew", padx=6)
        top_frame.columnconfigure(index=1, weight=1)
        self.cb_proj.bind("<<ComboboxSelected>>", self.on_proj_switch)

        ttk.Label(top_frame, text="分类：").grid(row=0, column=2, sticky="w")
        self.cb_item = ttk.Combobox(top_frame, state="readonly", font=("微软雅黑", 10))
        self.cb_item.grid(row=0, column=3, sticky="ew", padx=6)
        top_frame.columnconfigure(index=3, weight=1)
        self.cb_item.bind("<<ComboboxSelected>>", self.on_item_switch)

        # 功能按钮栏
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=12, pady=4)
        ttk.Button(btn_frame, text="选择截图根目录", command=self.set_img_root).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="加载local.project.json", command=self.load_json).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="上一张", command=self.do_prev_img).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="下一张", command=self.do_next_img).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="跳到头部", command=self.jump_head).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="跳到尾部", command=self.jump_tail).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="标记/取消", command=self.toggle_mark).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="标记到末尾", command=self.mark_to_end).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="保存JSON", command=self.save_clean_json).pack(side=tk.RIGHT, padx=4)

        # 三图容器
        img_box = ttk.Frame(self)
        img_box.pack(expand=True, fill=tk.BOTH, padx=12, pady=10)

        # 左图
        left_wrap = ttk.Frame(img_box)
        left_wrap.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5)
        self.label_left = ttk.Label(left_wrap, text="上一页")
        self.label_left.pack(fill=tk.X)
        self.canvas_left = tk.Canvas(left_wrap, bg="#e2e2e2", bd=2, relief=tk.SUNKEN)
        self.canvas_left.pack(expand=True, fill=tk.BOTH)
        self.canvas_left.bind("<Button-1>", lambda e: self.do_prev_img())

        # 中图
        mid_wrap = ttk.Frame(img_box)
        mid_wrap.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5)
        self.label_mid = ttk.Label(mid_wrap, text="当前页")
        self.label_mid.pack(fill=tk.X)
        self.canvas_mid = tk.Canvas(mid_wrap, bg="#ffffff", bd=2, relief=tk.SUNKEN)
        self.canvas_mid.pack(expand=True, fill=tk.BOTH)
        self.canvas_mid.bind("<Button-1>", lambda e: self.toggle_mark())

        # 右图
        right_wrap = ttk.Frame(img_box)
        right_wrap.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5)
        self.label_right = ttk.Label(right_wrap, text="下一页")
        self.label_right.pack(fill=tk.X)
        self.canvas_right = tk.Canvas(right_wrap, bg="#e2e2e2", bd=2, relief=tk.SUNKEN)
        self.canvas_right.pack(expand=True, fill=tk.BOTH)
        self.canvas_right.bind("<Button-1>", lambda e: self.do_next_img())

        # 底部状态栏
        self.status_label = ttk.Label(self, anchor="w", relief=tk.SUNKEN)
        self.status_label.pack(fill=tk.X, padx=1, pady=1)

    def update_status(self, extra_msg=""):
        root_txt = self.image_root if self.image_root else "未设置截图目录"
        # 修复：json_path → json_full_path
        json_name = os.path.basename(self.json_full_path) if self.json_full_path else "未加载JSON"
        text = f"截图目录：{root_txt} | JSON文件：{json_name}"
        if extra_msg:
            text += f" | {extra_msg}"
        self.status_label.config(text=text)

    def set_img_root(self):
        path = filedialog.askdirectory(mustexist=True)
        if path:
            self.image_root = path
            self.update_status("已更新截图根目录")
            self.refresh_all_view()

    def load_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON文件", "*.json")], initialfile="local.project.json")
        if not path:
            return
        try:

            self.all_projects.load_from_json(path)
            # with open(path, "r", encoding="utf-8") as f:
            #     raw = json.load(f)
            #     self.all_projects = load_project_models_from_json(raw)  # raw["projects"]

            self.json_full_path = path
            self.marked_file_set.clear()
            self.cur_proj_idx = 0
            # self.cur_snap_type = "contracts"
            self.cur_group_idx = 0
            self.cur_img_pos = 0
            self.refresh_proj_combo()
            self.refresh_all_view()
            self.update_status("JSON加载完成")
        except Exception as e:
            self.update_status(f"加载失败：{str(e)}")

    def refresh_proj_combo(self):
        if self.all_projects.is_empty():
            self.cb_proj["values"] = []
            return
        names = self.all_projects.get_all_project_names()  # [p["meta"]["项目名称"] for p in self.all_projects]
        self.cb_proj["values"] = names
        self.cb_proj.current(self.cur_proj_idx)
        self.refresh_item_combo()

    def get_current_project(self) -> None | ProjectModel:
        proj = self.all_projects.get_project(self.cur_proj_idx)
        if proj is None:
            # ????
            pass
        return proj

    def refresh_item_combo(self):
        if self.all_projects.is_empty():
            self.cb_item["values"] = []
            return
        proj = self.get_current_project()
        if proj is None:
            # ????
            pass
            return
        item_list = proj.get_item_names()
        # # 合同
        # for idx, c in enumerate(proj["contracts"]):
        #     item_list.append(f"合同-{idx + 1}: {c['name']}")
        # # 过滤空订单分组
        # for g_idx, group in enumerate(proj["orders"]):
        #     if len(group) > 0:
        #         for item in group:
        #             item_list.append(f"订单组{g_idx + 1}: {item['name']}")
        # # 过滤空发票分组
        # for g_idx, group in enumerate(proj["invoices"]):
        #     if len(group) > 0:
        #         for item in group:
        #             item_list.append(f"发票组{g_idx + 1}: {item['name']}")
        self.cb_item["values"] = item_list
        if item_list:
            self.cb_item.current(0)

    def on_proj_switch(self, event):
        self.cur_proj_idx = self.cb_proj.current()
        # self.cur_snap_type = "contracts"
        self.cur_group_idx = 0
        self.cur_img_pos = 0
        self.refresh_item_combo()
        self.refresh_all_view()

    def on_item_switch(self, event):
        idx = self.cb_item.current()
        # proj = self.all_projects[self.cur_proj_idx]

        proj = self.get_current_project()

        self.cur_snapshot_idx = idx
        self.cur_img_pos = 0
        self.refresh_all_view()

        # contract_len = len(proj["contracts"])
        # valid_order_count = sum(1 for g in proj["orders"] if len(g) > 0)
        # # 合同区域
        # if idx < contract_len:
        #     self.cur_snap_type = "contracts"
        #     self.cur_group_idx = idx
        # else:
        #     offset = idx - contract_len
        #     cnt = 0
        #     # 订单区域
        #     for g_idx, g in enumerate(proj["orders"]):
        #         if len(g) == 0:
        #             continue
        #         if cnt == offset:
        #             self.cur_snap_type = "orders"
        #             self.cur_group_idx = g_idx
        #             break
        #         cnt += 1
        #     else:
        #         # 发票区域
        #         offset = offset - valid_order_count
        #         cnt = 0
        #         for g_idx, g in enumerate(proj["invoices"]):
        #             if len(g) == 0:
        #                 continue
        #             if cnt == offset:
        #                 self.cur_snap_type = "invoices"
        #                 self.cur_group_idx = g_idx
        #                 break
        #             cnt += 1

    def get_current_snap_obj(self) -> SnapshotModel | None:
        proj = self.get_current_project()
        if proj is None:
            return None

        idx = self.cur_snapshot_idx

        snapshot = proj.get_snapshot_by_index(idx)
        if snapshot is None:
            # 没有找到
            assert False, f"Not found snapshot by index {idx}"
            return
        return snapshot

        # proj = self.all_projects[self.cur_proj_idx]
        # if self.cur_snap_type == "contracts":
        #     return proj["contracts"][self.cur_group_idx]
        # elif self.cur_snap_type == "orders":
        #     group = proj["orders"][self.cur_group_idx]
        #     if len(group) == 0:
        #         raise Exception("订单分组无数据")
        #     return group[0]
        # else:
        #     group = proj["invoices"][self.cur_group_idx]
        #     if len(group) == 0:
        #         raise Exception("发票分组无数据")
        #     return group[0]


    def go_next_snap(self):
        p_idx = self.cur_proj_idx
        stype = self.cur_snap_type
        g_idx = self.cur_group_idx
        proj = self.all_projects[p_idx]

        assert not  self.all_projects.is_empty()
        proj = self.get_current_project()
        assert proj is not None

        idx = self.cur_snapshot_idx



    def get_next_snap_pos(self):
        p_idx = self.cur_proj_idx
        stype = self.cur_snap_type
        g_idx = self.cur_group_idx
        proj = self.all_projects[p_idx]
        # 获取当前类型所有有效非空分组
        if stype == "contracts":
            valid_groups = list(range(len(proj["contracts"])))
        elif stype == "orders":
            valid_groups = [i for i, g in enumerate(proj["orders"]) if len(g) > 0]
        else:
            valid_groups = [i for i, g in enumerate(proj["invoices"]) if len(g) > 0]
        curr_valid = valid_groups.index(g_idx)
        # 当前类型还有下一分组
        if curr_valid < len(valid_groups) - 1:
            return (p_idx, stype, valid_groups[curr_valid + 1])
        # 切换下一类
        if stype == "contracts":
            valid_orders = [i for i, g in enumerate(proj["orders"]) if len(g) > 0]
            if valid_orders:
                return (p_idx, "orders", valid_orders[0])
            valid_inv = [i for i, g in enumerate(proj["invoices"]) if len(g) > 0]
            if valid_inv:
                return (p_idx, "invoices", valid_inv[0])
        elif stype == "orders":
            valid_inv = [i for i, g in enumerate(proj["invoices"]) if len(g) > 0]
            if valid_inv:
                return (p_idx, "invoices", valid_inv[0])
        # 切换下一个项目
        if p_idx < len(self.all_projects) - 1:
            return (p_idx, "contracts", 0)
        return None

    def get_prev_snap_pos(self):
        p_idx = self.cur_proj_idx
        stype = self.cur_snap_type
        g_idx = self.cur_group_idx
        proj = self.all_projects[p_idx]
        if stype == "contracts":
            valid_groups = list(range(len(proj["contracts"])))
        elif stype == "orders":
            valid_groups = [i for i, g in enumerate(proj["orders"]) if len(g) > 0]
        else:
            valid_groups = [i for i, g in enumerate(proj["invoices"]) if len(g) > 0]
        curr_valid = valid_groups.index(g_idx)
        if curr_valid > 0:
            return (p_idx, stype, valid_groups[curr_valid - 1])
        # 切换上一类
        if stype == "invoices":
            valid_ord = [i for i, g in enumerate(proj["orders"]) if len(g) > 0]
            if valid_ord:
                return (p_idx, "orders", valid_ord[-1])
            return (p_idx, "contracts", len(proj["contracts"]) - 1)
        elif stype == "orders":
            return (p_idx, "contracts", len(proj["contracts"]) - 1)
        # 切换上一个项目
        if p_idx == 0:
            return None
        prev_p = self.all_projects[p_idx - 1]
        valid_inv = [i for i, g in enumerate(prev_p["invoices"]) if len(g) > 0]
        if valid_inv:
            return (p_idx - 1, "invoices", valid_inv[-1])
        valid_ord = [i for i, g in enumerate(prev_p["orders"]) if len(g) > 0]
        if valid_ord:
            return (p_idx - 1, "orders", valid_ord[-1])
        return (p_idx - 1, "contracts", len(prev_p["contracts"]) - 1)

    def do_next_img(self):

        if self.all_projects.is_empty():
            winsound.Beep(600, 150)
            return

        try:
            snap = self.get_current_snap_obj()
            if snap is None:
                return

            cur_pos = self.cur_img_pos
            total = snap.get_snapshot_count()

            end_pos = total - 1
            if cur_pos < end_pos:
                cur_pos += 1
            elif cur_pos == end_pos: # 最后一个位置
                # 切换到下一个SNAP

                pass
            else:
                pass
            # 硬件到了

            self.cur_img_pos = cur_pos



        except Exception as e:
            self.update_status(f"浏览错误：{str(e)}")
            winsound.Beep(800, 200)
            return
        total = len(snap["snapshots"])
        # 优先同组内翻图片，修复发票同组多张无法下一页
        if self.cur_img_pos < total - 1:
            self.cur_img_pos += 1
            self.refresh_all_view()
            return
        # 本组到末尾，切换下一个分组
        pos = self.get_next_snap_pos()
        if pos is None:
            winsound.Beep(600, 150)
            return
        self.cur_proj_idx, self.cur_snap_type, self.cur_group_idx = pos
        self.cur_img_pos = 0
        self.sync_combo_select()
        self.refresh_all_view()

    def do_prev_img(self):
        if not self.all_projects:
            winsound.Beep(600, 150)
            return
        try:
            snap = self.get_current_snap_obj()
        except Exception as e:
            self.update_status(f"浏览错误：{str(e)}")
            winsound.Beep(800, 200)
            return
        total = len(snap["snapshots"])
        # 优先同组回翻
        if self.cur_img_pos > 0:
            self.cur_img_pos -= 1
            self.refresh_all_view()
            return
        # 本组第一张，切换上一分组末尾
        pos = self.get_prev_snap_pos()
        if pos is None:
            winsound.Beep(600, 150)
            return
        self.cur_proj_idx, self.cur_snap_type, self.cur_group_idx = pos
        try:
            new_snap = self.get_current_snap_obj()
        except Exception as e:
            self.update_status(f"切换分组失败：{str(e)}")
            winsound.Beep(800, 200)
            return
        self.cur_img_pos = len(new_snap["snapshots"]) - 1
        self.sync_combo_select()
        self.refresh_all_view()

    def sync_combo_select(self):
        self.cb_proj.current(self.cur_proj_idx)
        self.refresh_item_combo()
        proj = self.all_projects[self.cur_proj_idx]
        c_len = len(proj["contracts"])
        valid_ord = sum(1 for g in proj["orders"] if len(g) > 0)
        offset = c_len
        if self.cur_snap_type == "contracts":
            offset = self.cur_group_idx
        elif self.cur_snap_type == "orders":
            cnt = 0
            for g_idx, g in enumerate(proj["orders"]):
                if len(g) == 0:
                    continue
                if g_idx == self.cur_group_idx:
                    offset += cnt
                    break
                cnt += 1
        else:
            cnt = 0
            for g_idx, g in enumerate(proj["orders"]):
                if len(g) > 0:
                    cnt += 1
            offset += cnt
            inv_cnt = 0
            for g_idx, g in enumerate(proj["invoices"]):
                if len(g) == 0:
                    continue
                if g_idx == self.cur_group_idx:
                    offset += inv_cnt
                    break
                inv_cnt += 1
        self.cb_item.current(offset)

    def jump_head(self):
        if self.all_projects.is_empty():
            return
        try:
            snap = self.get_current_snap_obj()
            if snap is None:
                return

            self.cur_img_pos = 0
            self.refresh_all_view()
        except Exception as e:
            self.update_status(f"跳转失败：{str(e)}")

    def jump_tail(self):
        if self.all_projects.is_empty():
            return
        try:
            snap = self.get_current_snap_obj()
            if snap is None:
                return

            self.cur_img_pos = snap.get_last_pos()
            # self.cur_img_pos = len(snap["snapshots"]) - 1
            self.refresh_all_view()
        except Exception as e:
            self.update_status(f"跳转失败：{str(e)}")

    def toggle_mark(self):
        if self.all_projects.is_empty():
            return
        try:
            snap = self.get_current_snap_obj()
            if snap is None:
                return
            filename = snap.get_snapshot_url(self.cur_img_pos)
            # filename = snap["snapshots"][self.cur_img_pos]
            if filename is None:
                assert False, f"why filename is not ,{self.cur_img_pos}?"
                return
            if filename in self.marked_file_set:
                self.marked_file_set.remove(filename)
                self.update_status("已取消标记")
            else:
                self.marked_file_set.add(filename)
                self.update_status("已标记待删除")
            self.refresh_all_view()
        except Exception as e:
            self.update_status(f"标记失败：{str(e)}")

    def mark_to_end(self):
        if self.all_projects.is_empty():
            return
        return
        # try:
        #     snap = self.get_current_snap_obj()
        #     snap_list = snap["snapshots"]
        #     for idx in range(self.cur_img_pos, len(snap_list)):
        #         self.marked_file_set.add(snap_list[idx])
        #     self.update_status(f"已标记第{self.cur_img_pos + 1}张至末尾全部截图")
        #     self.refresh_all_view()
        # except Exception as e:
        #     self.update_status(f"批量标记失败：{str(e)}")

    def draw_canvas(self, tk_canvas: tk.Canvas,
                    tk_label: ttk.Label,
                    snapshot_img: str,
                    label_text: str,
                    cache_idx: int):
        tk_canvas.delete("all")
        tk_label.config(text=label_text)
        full_path = os.path.join(self.image_root, snapshot_img)
        im = Image.open(full_path)

        w_can = tk_canvas.winfo_width()
        h_can = tk_canvas.winfo_height()
        im.thumbnail((w_can - 30, h_can - 40), Image.Resampling.LANCZOS)
        img_tk = ImageTk.PhotoImage(im)
        self.img_cache[cache_idx] = img_tk
        tk_canvas.create_image(w_can // 2, h_can // 2, image=img_tk, anchor=tk.CENTER)
        if snapshot_img in self.marked_file_set:
            tk_canvas.create_rectangle(0, 0, w_can, h_can, fill="#ff4444", stipple="gray50", outline="")

    # def draw_canvas1(self, canvas, label, target_p, target_stype, target_g, cache_idx):
    #     canvas.delete("all")
    #     try:
    #         # proj = self.all_projects[target_p]
    #         # if target_stype == "contracts":
    #         #     snap_obj = proj["contracts"][target_g]
    #         # elif target_stype == "orders":
    #         #     group = proj["orders"][target_g]
    #         #     snap_obj = group[0]
    #         # else:
    #         #     group = proj["invoices"][target_g]
    #         #     snap_obj = group[0]
    #         # total_img = len(snap_obj["snapshots"])
    #         # if cache_idx == 0:
    #         #     draw_pos = self.cur_img_pos - 1
    #         # elif cache_idx == 1:
    #         #     draw_pos = self.cur_img_pos
    #         # else:
    #         #     draw_pos = self.cur_img_pos + 1
    #         if 0 <= draw_pos < total_img:
    #             img_name = snap_obj["snapshots"][draw_pos]
    #             label.config(text=f"{draw_pos + 1}/{total_img}")
    #             full_path = os.path.join(self.image_root, img_name)
    #             im = Image.open(full_path)
    #         else:
    #             raise ValueError("图片下标超出范围")
    #     except Exception:
    #         label.config(text="无图片")
    #         w = canvas.winfo_width()
    #         h = canvas.winfo_height()
    #         canvas.create_rectangle(10, 10, w - 10, h - 10, fill="#d1d1d1", outline="#666")
    #         return
    #     w_can = canvas.winfo_width()
    #     h_can = canvas.winfo_height()
    #     im.thumbnail((w_can - 30, h_can - 40), Image.Resampling.LANCZOS)
    #     img_tk = ImageTk.PhotoImage(im)
    #     self.img_cache[cache_idx] = img_tk
    #     canvas.create_image(w_can // 2, h_can // 2, image=img_tk, anchor=tk.CENTER)
    #     if img_name in self.marked_file_set:
    #         canvas.create_rectangle(0, 0, w_can, h_can, fill="#ff4444", stipple="gray50", outline="")

    def _draw_one_canvas(self, snap: SnapshotModel, cur_img: int,
                         tk_canvas: tk.Canvas,
                         tk_label: ttk.Label, cache_idx: int):
        # 左画布
        image_url = snap.get_pre_snapshot_url(cur_img)
        if image_url is None:
            tk_canvas.delete("all")
            tk_label.config(text="无")
            w = tk_canvas.winfo_width()
            h = tk_canvas.winfo_height()
            tk_canvas.create_rectangle(10, 10, w - 10, h - 10, fill="#d1d1d1", outline="#666")
        else:
            label_text = f'{cur_img}/{snap.get_snapshot_count()}'
            # self.draw_canvas(self.canvas_left,
            #                  self.label_left,
            #                  image_url,
            #                  label_text, cache_idx)
            tk_canvas.delete("all")
            tk_label.config(text=label_text)
            full_path = os.path.join(self.image_root, image_url)
            im = Image.open(full_path)

            w_can = tk_canvas.winfo_width()
            h_can = tk_canvas.winfo_height()
            im.thumbnail((w_can - 30, h_can - 40), Image.Resampling.LANCZOS)
            img_tk = ImageTk.PhotoImage(im)
            self.img_cache[cache_idx] = img_tk
            tk_canvas.create_image(w_can // 2, h_can // 2, image=img_tk, anchor=tk.CENTER)
            if image_url in self.marked_file_set:
                tk_canvas.create_rectangle(0, 0, w_can, h_can, fill="#ff4444", stipple="gray50", outline="")

    def show_error(self, msg):
        self.update_status(msg)

    def refresh_all_view(self):
        # 么有初始化
        if self.all_projects.is_empty():
            self.canvas_left.delete("all")
            self.canvas_mid.delete("all")
            self.canvas_right.delete("all")

            self.label_left.config(text="无")
            self.label_mid.config(text="无")
            self.label_right.config(text="无")
            return

        p = self.cur_proj_idx
        st = self.cur_snap_type
        g = self.cur_group_idx
        cur_img = self.cur_img_pos
        try:

            snap = self.get_current_snap_obj()
            if snap is None:
                return
            # 左画布
            self._draw_one_canvas(snap, cur_img - 1, self.canvas_left, self.label_left, 0)
            self._draw_one_canvas(snap, cur_img, self.canvas_mid, self.label_mid, 1)
            self._draw_one_canvas(snap, cur_img - 1, self.canvas_right, self.label_right, 2)

        except Exception as e:
            self.canvas_left.delete("all")
            self.canvas_mid.delete("all")
            self.canvas_right.delete("all")
            self.label_left.config(text="数据异常")
            self.label_mid.config(text="数据异常")
            self.label_right.config(text="数据异常")
            self.show_error(f'{e}')
        return


#
# def refresh_all_view1(self):
#     if not self.all_projects:
#         self.canvas_left.delete("all")
#         self.canvas_mid.delete("all")
#         self.canvas_right.delete("all")
#         self.label_left.config(text="无")
#         self.label_mid.config(text="无")
#         self.label_right.config(text="无")
#         return
#     p = self.cur_proj_idx
#     st = self.cur_snap_type
#     g = self.cur_group_idx
#     try:
#         snap = self.get_current_snap_obj()
#     except Exception:
#         self.canvas_left.delete("all")
#         self.canvas_mid.delete("all")
#         self.canvas_right.delete("all")
#         self.label_left.config(text="数据异常")
#         self.label_mid.config(text="数据异常")
#         self.label_right.config(text="数据异常")
#         return
#     total = len(snap["snapshots"])
#     # # 左画布
#     # if self.cur_img_pos - 1 < 0:
#     #     self.canvas_left.delete("all")
#     #     self.label_left.config(text="无")
#     #     w = self.canvas_left.winfo_width()
#     #     h = self.canvas_left.winfo_height()
#     #     self.canvas_left.create_rectangle(10, 10, w - 10, h - 10, fill="#d1d1d1", outline="#666")
#     # else:
#     #     self.draw_canvas(self.canvas_left, self.label_left, p, st, g, 0)
#     # 中画布
#     self.draw_canvas(self.canvas_mid, self.label_mid, p, st, g, 1)
#     # 右画布
#     if self.cur_img_pos + 1 >= total:
#         self.canvas_right.delete("all")
#         self.label_right.config(text="无")
#         w = self.canvas_right.winfo_width()
#         h = self.canvas_right.winfo_height()
#         self.canvas_right.create_rectangle(10, 10, w - 10, h - 10, fill="#d1d1d1", outline="#666")
#     else:
#         self.draw_canvas(self.canvas_right, self.label_right, p, st, g, 2)


def save_clean_json(self):
    if not self.json_full_path or not self.all_projects:
        self.update_status("未加载数据，无法保存")
        return
    new_data = copy.deepcopy({"projects": self.all_projects})
    projects = new_data["projects"]
    for proj in projects:
        # 清理合同截图
        for c in proj["contracts"]:
            c["snapshots"] = [f for f in c["snapshots"] if f not in self.marked_file_set]
        # 清理订单
        for group in proj["orders"]:
            for order in group:
                order["snapshots"] = [f for f in order["snapshots"] if f not in self.marked_file_set]
        # 清理发票
        for group in proj["invoices"]:
            for inv in group:
                inv["snapshots"] = [f for f in inv["snapshots"] if f not in self.marked_file_set]
    try:
        with open(self.json_full_path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        self.marked_file_set.clear()
        self.refresh_all_view()
        self.update_status("JSON保存完成，已清除标记截图")
    except Exception as e:
        self.update_status(f"保存失败：{str(e)}")


if __name__ == "__main__":
    app = MainViewer()
    app.mainloop()
