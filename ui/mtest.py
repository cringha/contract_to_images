import copy
import json
import os
import tkinter as tk
from tkinter import ttk, filedialog
from typing import List, Literal
import winsound
from PIL import Image, ImageTk
import traceback
from ui.uisnaps.uisnapmodels import ProjectModelManager, ProjectModel, SnapshotModel, OutputFilter
from uitls.utils import save_to_json

UI_TK_LEFT: Literal["left"] = "left"
UI_TK_X: Literal["x"] = "x"
UI_TK_BOTH: Literal["both"] = "both"
UI_TK_RIGHT: Literal["right"] = "right"
UI_TK_SUNKEN: Literal["sunken"] = "sunken"
CANVAS_BACKGROUND_COLOR = "#e2e2e2"


class MainViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("项目合同订单发票截图清理工具")
        self.geometry("1600x980")
        self.minsize(1300, 750)

        # 全局数据
        self.json_full_path = ""
        self.image_root = r"D:\dev\pytools\project1\image_root"
        self.all_projects: ProjectModelManager = ProjectModelManager()
        self.marked_file_set = set()  # 待删除截图文件名

        # 当前浏览指针
        self.cur_proj_idx = 0
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
        top_frame.pack(fill=UI_TK_X, padx=12, pady=8)

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
        btn_frame.pack(fill=UI_TK_X, padx=12, pady=4)
        ttk.Button(btn_frame, text="选择截图根目录", command=self.set_img_root).pack(side=UI_TK_LEFT, padx=4)
        ttk.Button(btn_frame, text="加载local.project.json", command=self.load_json).pack(side=UI_TK_LEFT, padx=4)
        ttk.Button(btn_frame, text="上一张", command=self.do_prev_img).pack(side=UI_TK_LEFT, padx=4)
        ttk.Button(btn_frame, text="下一张", command=self.do_next_img).pack(side=UI_TK_LEFT, padx=4)
        ttk.Button(btn_frame, text="跳到头部", command=self.jump_head).pack(side=UI_TK_LEFT, padx=4)
        ttk.Button(btn_frame, text="跳到尾部", command=self.jump_tail).pack(side=UI_TK_LEFT, padx=4)
        ttk.Button(btn_frame, text="标记/取消", command=self.toggle_mark).pack(side=UI_TK_LEFT, padx=4)
        ttk.Button(btn_frame, text="标记到末尾", command=self.mark_to_end).pack(side=UI_TK_LEFT, padx=4)

        ttk.Button(btn_frame, text="上一个文件", command=self.do_pre_snap).pack(side=UI_TK_LEFT, padx=4)
        ttk.Button(btn_frame, text="下一个文件", command=self.do_next_snap).pack(side=UI_TK_LEFT, padx=4)

        ttk.Button(btn_frame, text="保存JSON", command=self.save_clean_json).pack(side=UI_TK_RIGHT, padx=4)

        # 三图容器
        img_box = ttk.Frame(self)
        img_box.pack(expand=True, fill=UI_TK_BOTH, padx=12, pady=10)

        # 左图
        left_wrap = ttk.Frame(img_box)
        left_wrap.pack(side=UI_TK_LEFT, expand=True, fill=UI_TK_BOTH, padx=5)
        self.label_left = ttk.Label(left_wrap, text="上一页")
        self.label_left.pack(fill=UI_TK_X)
        self.canvas_left = tk.Canvas(left_wrap, bg=CANVAS_BACKGROUND_COLOR, bd=2, relief=UI_TK_SUNKEN)
        self.canvas_left.pack(expand=True, fill=UI_TK_BOTH)
        self.canvas_left.bind("<Button-1>", lambda e: self.do_prev_img())

        # 中图
        mid_wrap = ttk.Frame(img_box)
        mid_wrap.pack(side=UI_TK_LEFT, expand=True, fill=UI_TK_BOTH, padx=5)
        self.label_mid = ttk.Label(mid_wrap, text="当前页")
        self.label_mid.pack(fill=UI_TK_X)
        self.canvas_mid = tk.Canvas(mid_wrap, bg=CANVAS_BACKGROUND_COLOR, bd=2, relief=UI_TK_SUNKEN)
        self.canvas_mid.pack(expand=True, fill=UI_TK_BOTH)
        self.canvas_mid.bind("<Button-1>", lambda e: self.toggle_mark())

        # 右图
        right_wrap = ttk.Frame(img_box)
        right_wrap.pack(side=UI_TK_LEFT, expand=True, fill=UI_TK_BOTH, padx=5)
        self.label_right = ttk.Label(right_wrap, text="下一页")
        self.label_right.pack(fill=UI_TK_X)
        self.canvas_right = tk.Canvas(right_wrap, bg=CANVAS_BACKGROUND_COLOR, bd=2, relief=UI_TK_SUNKEN)
        self.canvas_right.pack(expand=True, fill=UI_TK_BOTH)
        self.canvas_right.bind("<Button-1>", lambda e: self.do_next_img())

        # 底部状态栏
        self.status_label = ttk.Label(self, anchor="w", relief=UI_TK_SUNKEN)
        self.status_label.pack(fill=UI_TK_X, padx=1, pady=1)

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
            self.cur_proj_idx = -1
            self.cur_img_pos = -1
            self.refresh_proj_combo()
            self.refresh_all_view()
            self.update_status("JSON加载完成")
        except Exception as e:
            msg = traceback.format_stack()
            print(msg)
            # traceback.print_stack()
            self.update_status(f"加载失败：{str(e)}")

    def refresh_proj_combo(self):
        if self.all_projects.is_empty():
            self.cb_proj["values"] = []
            return
        names = self.all_projects.get_all_project_names()  # [p["meta"]["项目名称"] for p in self.all_projects]
        self.cb_proj["values"] = names

        # TODO: here
        # self.cb_proj.current(self.cur_proj_idx)
        self.set_cur_proj_idx(0)
        self.refresh_item_combo()

    def get_current_project(self) -> None | ProjectModel:
        proj = self.all_projects.get_project(self.cur_proj_idx)
        if proj is None:
            # ????
            assert False, f"Why proj is not , cur: {self.cur_proj_idx}, total: {self.all_projects.get_project_count()}"
        return proj

    def refresh_item_combo(self):
        if self.all_projects.is_empty():
            self.cb_item["values"] = []
            self.cb_item.set('')
            return

        proj = self.get_current_project()
        if proj is None:
            return

        item_list = proj.get_item_names()
        self.cb_item["values"] = item_list
        if item_list:
            self.cur_img_pos = 0
            self.set_cur_snapshot_idx(0)
        else:
            self.cb_item.set('')

    def on_proj_switch(self, event):
        old_idx = self.cur_proj_idx
        self.cur_proj_idx = self.cb_proj.current()
        # self.cur_img_pos = 0
        if old_idx != self.cur_proj_idx:
            self.refresh_item_combo()
            self.refresh_all_view()

    def on_item_switch(self, event):
        idx = self.cb_item.current()
        # proj = self.all_projects[self.cur_proj_idx]

        proj = self.get_current_project()

        self.cur_snapshot_idx = idx
        self.cur_img_pos = 0
        self.refresh_all_view()

    def set_cur_proj_idx(self, new_pos):
        old_idx = self.cur_proj_idx
        self.cur_proj_idx = new_pos
        # 设定下拉列表的显示
        if old_idx != self.cur_proj_idx:
            self.cb_proj.current(self.cur_proj_idx)
            self.refresh_item_combo()

    def set_cur_snapshot_idx(self, new_pos):
        if new_pos <0:
            self.cur_snapshot_idx = new_pos
            self.cb_item["values"] = []
        else:
            self.cur_snapshot_idx = new_pos
            # 设定下拉列表的显示
            self.cb_item.current(new_pos)

    def get_current_snap_obj(self) -> SnapshotModel | None:
        proj = self.get_current_project()
        if proj is None:
            return None

        idx = self.cur_snapshot_idx

        snapshot = proj.get_snapshot_by_index(idx)
        if snapshot is None:
            # 没有找到
            print(f"Not found snapshot by index {idx}")
            return None
        return snapshot

    # 移到上一个 SNAPSHOT
    def goto_pre_snapshot(self):
        proj = self.get_current_project()
        if proj is None:
            return False

        idx = self.cur_snapshot_idx
        if idx < 0:
            # 这个项目没有 截图
            winsound.Beep(600, 150)
            return False
        snapshot = proj.get_snapshot_by_index(idx - 1)
        if snapshot is None:
            # 已经是第一个
            assert idx == 0, f"Index of snapshot should == 0 , {idx}"
            proj1 = self.goto_pre_project()
            if proj1 is None:
                # 第一个项目了，
                winsound.Beep(600, 150)
                return False
            count = proj1.get_snapshot_count()
            if count > 0:
                snap_pos = count - 1
                snapshot1 = proj1.get_snapshot_by_index(snap_pos)
                self.cur_img_pos = snapshot1.get_last_pos()
                self.set_cur_snapshot_idx(snap_pos)
                return True
            else:

                self.cur_img_pos = 0
                self.set_cur_snapshot_idx(-1)
                # assert False, f"Project snaps empty  {proj1.get_project_name()}"
                return True

        else:
            # 移到上一个，并且图片显示最后一个
            self.set_cur_snapshot_idx(idx - 1)
            self.cur_img_pos = snapshot.get_last_pos()
            return True

    # 移到下一个 SNAPSHOT
    def goto_next_snapshot(self):
        proj = self.get_current_project()
        if proj is None:
            return False

        idx = self.cur_snapshot_idx
        if idx < 0:
            # 这个项目 没有截图， 直接去
            proj1 = self.goto_next_project()
            return proj1 is not None

        snapshot = proj.get_snapshot_by_index(idx + 1)
        if snapshot is None:
            # 已经是最后一个
            assert idx >= 0, f"Index of snapshot should >= 0 , {idx}"
            proj1 = self.goto_next_project()
            return proj1 is not None
        else:

            self.cur_img_pos = 0
            self.set_cur_snapshot_idx(self.cur_snapshot_idx + 1)
            return True

    def goto_next_project(self):

        proj = self.all_projects.get_project(self.cur_proj_idx + 1)
        if proj is None:
            # 已经是最后一个，不动
            return None
        else:

            self.set_cur_proj_idx(self.cur_proj_idx + 1)
            self.cur_img_pos = 0
            self.set_cur_snapshot_idx(0)
            return proj

    def goto_pre_project(self):
        proj = self.all_projects.get_project(self.cur_proj_idx - 1)
        if proj is None:
            # 已经是第一个
            return None
        else:
            self.set_cur_proj_idx(self.cur_proj_idx - 1)
            # self.cur_img_pos = 0
            # self.set_cur_snapshot_idx(0)
            return proj

    def go_next_snap(self):
        p_idx = self.cur_proj_idx
        proj = self.all_projects[p_idx]

        assert not self.all_projects.is_empty()
        proj = self.get_current_project()
        assert proj is not None

        idx = self.cur_snapshot_idx

    def do_next_snap(self):
        if self.all_projects.is_empty():
            winsound.Beep(600, 150)
            return
        try:
            need_update = self.goto_next_snapshot()
            if need_update:
                self.refresh_all_view()

        except Exception as e:
            self.update_status(f"浏览错误：{str(e)}")
            winsound.Beep(800, 200)
            return
    def do_pre_snap(self):
        if self.all_projects.is_empty():
            winsound.Beep(600, 150)
            return
        try:
            need_update = self.goto_pre_snapshot()
            if need_update:
                self.refresh_all_view()

        except Exception as e:
            self.update_status(f"浏览错误：{str(e)}")
            winsound.Beep(800, 200)
            return


    def do_next_img(self):

        if self.all_projects.is_empty():
            winsound.Beep(600, 150)
            return

        need_update = False
        try:
            snap = self.get_current_snap_obj()
            if snap is None:
                # 切换到下一个SNAP
                need_update = self.goto_next_snapshot()

            else:
                cur_pos = self.cur_img_pos
                total = snap.get_snapshot_count()

                end_pos = total - 1
                if cur_pos < end_pos:
                    cur_pos += 1
                    self.cur_img_pos = cur_pos
                    need_update = True
                elif cur_pos == end_pos:  # 最后一个位置
                    # 切换到下一个SNAP
                    need_update = self.goto_next_snapshot()

                else:
                    winsound.Beep(600, 150)


        except Exception as e:
            self.update_status(f"浏览错误：{str(e)}")
            winsound.Beep(800, 200)
            return

        if need_update:
            self.refresh_all_view()

    def do_prev_img(self):

        if self.all_projects.is_empty():
            winsound.Beep(600, 150)
            return

        need_update = False
        try:
            snap = self.get_current_snap_obj()
            if snap is None:
                # 切换到上一个SNAP
                need_update = self.goto_pre_snapshot()
            else:
                cur_pos = self.cur_img_pos
                if cur_pos > 0:
                    cur_pos -= 1
                    self.cur_img_pos = cur_pos
                    need_update = True
                elif cur_pos == 0:  # 第一个图片了
                    # 切换到上一个SNAP
                    need_update = self.goto_pre_snapshot()
                else:
                    winsound.Beep(600, 150)


        except Exception as e:
            traceback.print_exc()
            self.update_status(f"浏览错误：{str(e)}")
            winsound.Beep(800, 200)
            return

        if need_update:
            # self.sync_combo_select()

            self.refresh_all_view()

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
        try:
            snap = self.get_current_snap_obj()
            if snap is None:
                return

            cur = self.cur_img_pos
            end_pos = snap.get_last_pos()
            for i in range(cur, end_pos + 1):
                filename = snap.get_snapshot_url(i)
                if filename is None:
                    assert False, f"why filename is empty , {i} , {snap.name}?"
                    continue
                if filename in self.marked_file_set:
                    self.marked_file_set.remove(filename)
                else:
                    self.marked_file_set.add(filename)

            self.refresh_all_view()
        except Exception as e:
            self.update_status(f"标记失败：{str(e)}")


    def _draw_one_canvas(self, name: str, snap: SnapshotModel, cur_img: int,
                         tk_canvas: tk.Canvas,
                         tk_label: ttk.Label, cache_idx: int):
        # 左画布
        image_url = snap.get_snapshot_url(cur_img)
        if image_url is None:
            tk_canvas.delete("all")
            tk_label.config(text="无")
            w = tk_canvas.winfo_width()
            h = tk_canvas.winfo_height()
            tk_canvas.create_rectangle(10, 10, w - 10, h - 10, fill="#d1d1d1", outline="#666")
        else:
            label_text = f'{cur_img + 1}/{snap.get_snapshot_count()}'
            tk_canvas.delete("all")
            tk_label.config(text=label_text)
            full_path = os.path.join(self.image_root, image_url)
            im = Image.open(full_path)

            w_can = tk_canvas.winfo_width()
            h_can = tk_canvas.winfo_height()
            print(f"in canvas {name}, w : {w_can}, h: {h_can}")
            im.thumbnail((w_can - 30, h_can - 40), Image.Resampling.LANCZOS)
            img_tk = ImageTk.PhotoImage(im)
            self.img_cache[cache_idx] = img_tk
            tk_canvas.create_image(w_can // 2, h_can // 2, image=img_tk, anchor=tk.CENTER)
            if image_url in self.marked_file_set:
                tk_canvas.create_rectangle(0, 0, w_can, h_can, fill="#ff4444", stipple="gray50", outline="")

    def show_error(self, msg):
        self.update_status(msg)


    def _clear_canvas(self):
        self.canvas_left.delete("all")
        self.canvas_mid.delete("all")
        self.canvas_right.delete("all")

        self.label_left.config(text="无")
        self.label_mid.config(text="无")
        self.label_right.config(text="无")

    def refresh_all_view(self):
        # 么有初始化
        if self.all_projects.is_empty():
            self._clear_canvas()
            return

        cur_img = self.cur_img_pos
        try:

            snap = self.get_current_snap_obj()
            if snap is None:
                self._clear_canvas()
                return
            # 左画布
            self._draw_one_canvas("left", snap, cur_img - 1, self.canvas_left, self.label_left, 0)
            self._draw_one_canvas("min", snap, cur_img, self.canvas_mid, self.label_mid, 1)
            self._draw_one_canvas("right", snap, cur_img + 1, self.canvas_right, self.label_right, 2)

        except Exception as e:
            self.canvas_left.delete("all")
            self.canvas_mid.delete("all")
            self.canvas_right.delete("all")
            self.label_left.config(text="数据异常")
            self.label_mid.config(text="数据异常")
            self.label_right.config(text="数据异常")
            self.show_error(f'{e}')
        return

    def save_clean_json(self):
        if not self.json_full_path or not self.all_projects:
            self.update_status("未加载数据，无法保存")
            return

        class MyFilter(OutputFilter):
            def accept(self1, name: str) -> bool:
                if name not in self.marked_file_set:
                    return True
                return False

        output = self.all_projects.to_json(MyFilter())

        try:
            save_to_json(self.json_full_path, output)
            self.marked_file_set.clear()
            self.refresh_all_view()
            self.update_status("JSON保存完成，已清除标记截图")
        except Exception as e:
            self.update_status(f"保存失败：{str(e)}")


if __name__ == "__main__":
    app = MainViewer()
    app.mainloop()
