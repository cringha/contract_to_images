import tkinter as tk
import math
import json
from tkinter import filedialog, messagebox

# 控制点（矩形四个角）
class Handle:
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.x = 0.0
        self.y = 0.0
        self.item_id = None

    def set_pos(self, x: float, y: float):
        self.x = x
        self.y = y

    def draw(self, scale: float, selected: bool):
        size = 8 / scale if selected else 5 / scale
        color = "yellow" if selected else "blue"
        x1, y1 = self.x - size, self.y - size
        x2, y2 = self.x + size, self.y + size
        if self.item_id:
            self.canvas.coords(self.item_id, x1, y1, x2, y2)
            self.canvas.itemconfig(self.item_id, fill=color)
        else:
            self.item_id = self.canvas.create_rectangle(
                x1, y1, x2, y2, fill=color, outline="white"
            )

    def delete(self):
        if self.item_id:
            self.canvas.delete(self.item_id)
            self.item_id = None

    def is_point_inside(self, x: float, y: float, scale: float) -> bool:
        size = 8 / scale
        return abs(self.x - x) <= size and abs(self.y - y) <= size

# 矩形元素（存储归一化相对原图坐标 0~1）
class Rect:
    def __init__(self, canvas: tk.Canvas, orig_w: float, orig_h: float, img_x1: float, img_y1: float, img_x2: float, img_y2: float):
        self.canvas = canvas
        # 归一化坐标（基准：原始图片宽高）
        self.nx1 = img_x1 / orig_w
        self.ny1 = img_y1 / orig_h
        self.nx2 = img_x2 / orig_w
        self.ny2 = img_y2 / orig_h
        self.item_id = None
        self.handles = [Handle(canvas) for _ in range(4)]
        self.selected = False

    # 归一化 → 画布屏幕坐标
    def get_screen_bbox(self, disp_w: float, disp_h: float, off_x: float, off_y: float):
        sx1 = self.nx1 * disp_w + off_x
        sy1 = self.ny1 * disp_h + off_y
        sx2 = self.nx2 * disp_w + off_x
        sy2 = self.ny2 * disp_h + off_y
        return min(sx1, sx2), min(sy1, sy2), max(sx1, sx2), max(sy2, sy2)

    # 屏幕内图片局部坐标 → 更新归一化
    def set_from_img_coords(self, orig_w: float, orig_h: float, ix1: float, iy1: float, ix2: float, iy2: float):
        self.nx1 = ix1 / orig_w
        self.ny1 = iy1 / orig_h
        self.nx2 = ix2 / orig_w
        self.ny2 = iy2 / orig_h

    def update_handles(self, disp_w, disp_h, off_x, off_y):
        x1, y1, x2, y2 = self.get_screen_bbox(disp_w, disp_h, off_x, off_y)
        self.handles[0].set_pos(x1, y1)
        self.handles[1].set_pos(x2, y1)
        self.handles[2].set_pos(x2, y2)
        self.handles[3].set_pos(x1, y2)

    def draw(self, canvas_scale: float, disp_w, disp_h, off_x, off_y):
        x1, y1, x2, y2 = self.get_screen_bbox(disp_w, disp_h, off_x, off_y)
        if self.item_id:
            self.canvas.coords(self.item_id, x1, y1, x2, y2)
        else:
            self.item_id = self.canvas.create_rectangle(
                x1, y1, x2, y2, outline="red", width=2
            )
        self.update_handles(disp_w, disp_h, off_x, off_y)
        for h in self.handles:
            h.draw(canvas_scale, self.selected)

    def delete(self):
        if self.item_id:
            self.canvas.delete(self.item_id)
        for h in self.handles:
            h.delete()

    def hit_handle(self, screen_x, screen_y, canvas_scale, disp_w, disp_h, off_x, off_y) -> int:
        self.update_handles(disp_w, disp_h, off_x, off_y)
        for idx, h in enumerate(self.handles):
            if h.is_point_inside(screen_x, screen_y, canvas_scale):
                return idx
        return -1

    def point_in_rect(self, screen_x, screen_y, disp_w, disp_h, off_x, off_y) -> bool:
        x1, y1, x2, y2 = self.get_screen_bbox(disp_w, disp_h, off_x, off_y)
        return x1 <= screen_x <= x2 and y1 <= screen_y <= y2

    def intersect_rect(self, s_x1, s_y1, s_x2, s_y2, disp_w, disp_h, off_x, off_y) -> bool:
        x1, y1, x2, y2 = self.get_screen_bbox(disp_w, disp_h, off_x, off_y)
        if x2 < s_x1 or x1 > s_x2:
            return False
        if y2 < s_y1 or y1 > s_y2:
            return False
        return True

    def to_dict(self):
        return {"nx1": self.nx1, "ny1": self.ny1, "nx2": self.nx2, "ny2": self.ny2}

# 画布控制器
class CanvasController:
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.rects: list[Rect] = []
        self.selected_rects: list[Rect] = []
        self.scale = 1.0
        # 绘制模式
        self.is_drawing = False
        self.draw_start_screen = (0.0, 0.0)
        self.temp_draw_rect = None
        # 框选
        self.is_selecting = False
        self.select_start = (0.0, 0.0)
        self.select_box_id = None
        # 拖拽手柄
        self.is_drag_handle = False
        self.drag_target_rect = None
        self.drag_handle_idx = -1
        # 整体移动
        self.is_move_rect = False
        self.move_start_screen = (0.0, 0.0)

    def set_scale(self, val: float):
        self.scale = max(0.2, min(5.0, val))

    # 绘制矩形
    def start_draw(self, sx, sy):
        self.clear_selection()
        self.is_drawing = True
        self.draw_start_screen = (sx, sy)
        self.temp_draw_rect = self.canvas.create_rectangle(sx, sy, sx, sy, outline="red", width=2)

    def drag_draw_update(self, sx, sy):
        if self.is_drawing and self.temp_draw_rect:
            x0, y0 = self.draw_start_screen
            self.canvas.coords(self.temp_draw_rect, x0, y0, sx, sy)

    def finish_draw(self, end_sx, end_sy, orig_w, orig_h, disp_w, disp_h, off_x, off_y):
        if not self.is_drawing or orig_w <= 0 or orig_h <=0:
            self.is_drawing = False
            if self.temp_draw_rect:
                self.canvas.delete(self.temp_draw_rect)
                self.temp_draw_rect = None
            return
        self.is_drawing = False
        s_x0, s_y0 = self.draw_start_screen
        self.canvas.delete(self.temp_draw_rect)
        self.temp_draw_rect = None
        # 屏幕坐标 → 图片内部局部坐标
        i_x0 = s_x0 - off_x
        i_y0 = s_y0 - off_y
        i_x1 = end_sx - off_x
        i_y1 = end_sy - off_y
        # 过滤过小框
        screen_w = abs(end_sx - s_x0)
        screen_h = abs(end_sy - s_y0)
        if screen_w < 5 or screen_h < 5:
            return
        new_rect = Rect(self.canvas, orig_w, orig_h, i_x0, i_y0, i_x1, i_y1)
        self.rects.append(new_rect)

    # 框选逻辑
    def start_select(self, sx, sy):
        self.is_selecting = True
        self.select_start = (sx, sy)
        self.select_box_id = self.canvas.create_rectangle(sx, sy, sx, sy, outline="gray", dash=(4,2))

    def drag_select_update(self, sx, sy):
        if self.is_selecting and self.select_box_id:
            x0, y0 = self.select_start
            self.canvas.coords(self.select_box_id, x0, y0, sx, sy)

    def finish_select(self, end_sx, end_sy, disp_w, disp_h, off_x, off_y):
        if not self.is_selecting:
            return
        self.is_selecting = False
        self.canvas.delete(self.select_box_id)
        self.select_box_id = None
        x0, y0 = self.select_start
        s1x = min(x0, end_sx)
        s1y = min(y0, end_sy)
        s2x = max(x0, end_sx)
        s2y = max(y0, end_sy)
        self.selected_rects.clear()
        for r in self.rects:
            if r.intersect_rect(s1x, s1y, s2x, s2y, disp_w, disp_h, off_x, off_y):
                self.selected_rects.append(r)

    # 拖拽控制点
    def try_drag_handle(self, sx, sy, disp_w, disp_h, off_x, off_y) -> bool:
        for r in self.rects:
            idx = r.hit_handle(sx, sy, self.scale, disp_w, disp_h, off_x, off_y)
            if idx != -1:
                self.clear_selection()
                self.selected_rects.append(r)
                self.is_drag_handle = True
                self.drag_target_rect = r
                self.drag_handle_idx = idx
                return True
        return False

    # 整体移动
    def try_start_move(self, sx, sy, disp_w, disp_h, off_x, off_y) -> bool:
        if not self.selected_rects:
            return False
        for r in self.selected_rects:
            if r.point_in_rect(sx, sy, disp_w, disp_h, off_x, off_y):
                self.is_move_rect = True
                self.move_start_screen = (sx, sy)
                return True
        return False

    def drag_handle_move(self, sx, sy, orig_w, orig_h, disp_w, disp_h, off_x, off_y):
        if not self.is_drag_handle or not self.drag_target_rect:
            return
        r = self.drag_target_rect
        hid = self.drag_handle_idx
        # 当前鼠标图片内坐标
        m_ix = sx - off_x
        m_iy = sy - off_y
        # 获取当前框图片内坐标
        s1x, s1y, s2x, s2y = r.get_screen_bbox(disp_w, disp_h, off_x, off_y)
        i1x = s1x - off_x
        i1y = s1y - off_y
        i2x = s2x - off_x
        i2y = s2y - off_y
        if hid == 0:
            r.set_from_img_coords(orig_w, orig_h, m_ix, m_iy, i2x, i2y)
        elif hid == 1:
            r.set_from_img_coords(orig_w, orig_h, i1x, m_iy, m_ix, i2y)
        elif hid == 2:
            r.set_from_img_coords(orig_w, orig_h, i1x, i1y, m_ix, m_iy)
        elif hid == 3:
            r.set_from_img_coords(orig_w, orig_h, m_ix, i1y, i2x, m_iy)

    def move_all_rect(self, sx, sy, orig_w, orig_h, disp_w, disp_h, off_x, off_y):
        if not self.is_move_rect or not self.selected_rects:
            return
        s0x, s0y = self.move_start_screen
        dx_screen = sx - s0x
        dy_screen = sy - s0y
        # 屏幕偏移 → 图片内偏移
        dx_img = dx_screen
        dy_img = dy_screen
        for r in self.selected_rects:
            s1x, s1y, s2x, s2y = r.get_screen_bbox(disp_w, disp_h, off_x, off_y)
            i1x = s1x - off_x
            i1y = s1y - off_y
            i2x = s2x - off_x
            i2y = s2y - off_y
            r.set_from_img_coords(orig_w, orig_h, i1x + dx_img, i1y + dy_img, i2x + dx_img, i2y + dy_img)

    def stop_all_drag(self):
        self.is_drag_handle = False
        self.is_move_rect = False
        self.drag_target_rect = None
        self.drag_handle_idx = -1

    def click_rect_and_drag(self, sx, sy, disp_w, disp_h, off_x, off_y):
        self.clear_selection()
        hit = None
        for r in self.rects:
            if r.point_in_rect(sx, sy, disp_w, disp_h, off_x, off_y):
                hit = r
                break
        if hit:
            self.selected_rects.append(hit)
            self.is_move_rect = True
            self.move_start_screen = (sx, sy)

    def clear_selection(self):
        self.selected_rects.clear()

    def delete_selected(self):
        for r in list(self.selected_rects):
            if r in self.rects:
                r.delete()
                self.rects.remove(r)
        self.clear_selection()

    def redraw_all(self, disp_w, disp_h, off_x, off_y):
        for r in self.rects:
            r.selected = r in self.selected_rects
            r.draw(self.scale, disp_w, disp_h, off_x, off_y)

    def export_json(self, path):
        data = [r.to_dict() for r in self.rects]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def import_json(self, path, orig_w, orig_h):
        for r in self.rects:
            r.delete()
        self.rects.clear()
        self.clear_selection()
        with open(path, "r", encoding="utf-8") as f:
            arr = json.load(f)
        for d in arr:
            nx1 = d["nx1"]
            ny1 = d["ny1"]
            nx2 = d["nx2"]
            ny2 = d["ny2"]
            ix1 = nx1 * orig_w
            iy1 = ny1 * orig_h
            ix2 = nx2 * orig_w
            iy2 = ny2 * orig_h
            rect = Rect(self.canvas, orig_w, orig_h, ix1, iy1, ix2, iy2)
            self.rects.append(rect)

# 主窗口
class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("修复缩放画图偏移-相对坐标标注工具")
        self.geometry("1000x700")
        # 工具栏
        top_frame = tk.Frame(self)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        self.draw_mode = tk.BooleanVar(False)
        tk.Checkbutton(top_frame, text="绘制矩形模式", variable=self.draw_mode).pack(side=tk.LEFT)
        tk.Button(top_frame, text="导出JSON", command=self.export_json).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="导入JSON", command=self.import_json).pack(side=tk.LEFT, padx=5)
        # 画布
        self.canvas = tk.Canvas(self, bg="#f0f0f0")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.ctl = CanvasController(self.canvas)
        # 图片数据
        self.bg_origin = None
        self.bg_scaled = None
        self.bg_img_id = None
        self.orig_img_w = 0
        self.orig_img_h = 0
        self.disp_w = 0
        self.disp_h = 0
        self.img_off_x = 0
        self.img_off_y = 0
        self.load_bg()
        # 事件
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.canvas.bind("<Button-3>", self.right_quit_draw)
        self.canvas.bind("<Configure>", self.canvas_resize)
        self.bind("<Delete>", lambda e: self.ctl.delete_selected())

    def load_bg(self):
        try:
            self.bg_origin = tk.PhotoImage(file="test.png")
            self.orig_img_w = self.bg_origin.width()
            self.orig_img_h = self.bg_origin.height()
        except Exception:
            self.bg_origin = None
            self.orig_img_w = 0
            self.orig_img_h = 0
        self.refresh_bg()

    def refresh_bg(self):
        self.canvas.delete("bg")
        if not self.bg_origin or self.orig_img_w == 0:
            self.disp_w = self.disp_h = self.img_off_x = self.img_off_y = 0
            self.ctl.redraw_all(0,0,0,0)
            return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 20 or ch < 20:
            return
        # 画布内自适应完整显示图片
        fit_ratio = min(cw / self.orig_img_w, ch / self.orig_img_h)
        final_ratio = fit_ratio * self.ctl.scale
        if final_ratio < 1:
            sub = max(1, int(1 / final_ratio))
            self.bg_scaled = self.bg_origin.subsample(sub, sub)
        else:
            zoom = int(final_ratio)
            self.bg_scaled = self.bg_origin.zoom(zoom, zoom)
        self.disp_w = self.bg_scaled.width()
        self.disp_h = self.bg_scaled.height()
        self.img_off_x = (cw - self.disp_w) / 2
        self.img_off_y = (ch - self.disp_h) / 2
        self.bg_img_id = self.canvas.create_image(self.img_off_x, self.img_off_y, image=self.bg_scaled, anchor="nw", tags="bg")
        self.ctl.redraw_all(self.disp_w, self.disp_h, self.img_off_x, self.img_off_y)

    def canvas_resize(self, ev):
        self.refresh_bg()

    def right_quit_draw(self, ev):
        if self.draw_mode.get():
            self.draw_mode.set(False)
            if self.ctl.temp_draw_rect:
                self.canvas.delete(self.ctl.temp_draw_rect)
                self.ctl.temp_draw_rect = None
            self.ctl.is_drawing = False

    def export_json(self):
        if self.orig_img_w == 0:
            messagebox.showwarning("提示", "请先加载图片！")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            self.ctl.export_json(path)
            messagebox.showinfo("成功", "导出完成")

    def import_json(self):
        if self.orig_img_w == 0:
            messagebox.showwarning("提示", "请先加载图片！")
            return
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            self.ctl.import_json(path, self.orig_img_w, self.orig_img_h)
            self.refresh_bg()
            messagebox.showinfo("成功", "导入完成")

    def on_mouse_down(self, ev):
        sx, sy = ev.x, ev.y
        dw, dh, ox, oy = self.disp_w, self.disp_h, self.img_off_x, self.img_off_y
        ow, oh = self.orig_img_w, self.orig_img_h
        if self.draw_mode.get():
            self.ctl.start_draw(sx, sy)
        else:
            if self.ctl.try_drag_handle(sx, sy, dw, dh, ox, oy):
                return
            if self.ctl.try_start_move(sx, sy, dw, dh, ox, oy):
                return
            hit_flag = False
            for r in self.ctl.rects:
                if r.point_in_rect(sx, sy, dw, dh, ox, oy):
                    hit_flag = True
                    break
            if hit_flag:
                self.ctl.click_rect_and_drag(sx, sy, dw, dh, ox, oy)
            else:
                self.ctl.start_select(sx, sy)

    def on_mouse_drag(self, ev):
        sx, sy = ev.x, ev.y
        dw, dh, ox, oy = self.disp_w, self.disp_h, self.img_off_x, self.img_off_y
        ow, oh = self.orig_img_w, self.orig_img_h
        if self.draw_mode.get():
            self.ctl.drag_draw_update(sx, sy)
        else:
            if self.ctl.is_drag_handle:
                self.ctl.drag_handle_move(sx, sy, ow, oh, dw, dh, ox, oy)
            elif self.ctl.is_move_rect:
                self.ctl.move_all_rect(sx, sy, ow, oh, dw, dh, ox, oy)
            else:
                self.ctl.drag_select_update(sx, sy)
        self.ctl.redraw_all(dw, dh, ox, oy)

    def on_mouse_up(self, ev):
        sx, sy = ev.x, ev.y
        dw, dh, ox, oy = self.disp_w, self.disp_h, self.img_off_x, self.img_off_y
        ow, oh = self.orig_img_w, self.orig_img_h
        self.ctl.stop_all_drag()
        if self.draw_mode.get():
            self.ctl.finish_draw(sx, sy, ow, oh, dw, dh, ox, oy)
        else:
            self.ctl.finish_select(sx, sy, dw, dh, ox, oy)
        self.refresh_bg()

    def on_wheel(self, ev):
        delta = 0.1 if ev.delta > 0 else -0.1
        self.ctl.set_scale(self.ctl.scale + delta)
        self.refresh_bg()

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
