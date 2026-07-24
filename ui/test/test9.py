import tkinter as tk
import math
import json
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

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

# 矩形元素：内部存储【原图像素坐标】
class Rect:
    def __init__(self, canvas: tk.Canvas, img_x1: float, img_y1: float, img_x2: float, img_y2: float):
        self.canvas = canvas
        self.img_x1 = img_x1
        self.img_y1 = img_y1
        self.img_x2 = img_x2
        self.img_y2 = img_y2
        self.item_id = None
        self.handles = [Handle(canvas) for _ in range(4)]
        self.selected = False

    def get_canvas_bbox(self, img2canvas_func):
        c_x1, c_y1 = img2canvas_func(self.img_x1, self.img_y1)
        c_x2, c_y2 = img2canvas_func(self.img_x2, self.img_y2)
        return min(c_x1, c_x2), min(c_y1, c_y2), max(c_x1, c_x2), max(c_y1, c_y2)

    def update_handles(self, img2canvas_func):
        x1, y1, x2, y2 = self.get_canvas_bbox(img2canvas_func)
        self.handles[0].set_pos(x1, y1)
        self.handles[1].set_pos(x2, y1)
        self.handles[2].set_pos(x2, y2)
        self.handles[3].set_pos(x1, y2)

    def draw(self, scale: float, img2canvas_func):
        x1, y1, x2, y2 = self.get_canvas_bbox(img2canvas_func)
        if self.item_id:
            self.canvas.coords(self.item_id, x1, y1, x2, y2)
        else:
            self.item_id = self.canvas.create_rectangle(
                x1, y1, x2, y2, outline="red", width=2
            )
        self.update_handles(img2canvas_func)
        for h in self.handles:
            h.draw(scale, self.selected)

    def delete(self):
        if self.item_id:
            self.canvas.delete(self.item_id)
        for h in self.handles:
            h.delete()

    def hit_handle(self, x: float, y: float, scale: float) -> int:
        for idx, h in enumerate(self.handles):
            if h.is_point_inside(x, y, scale):
                return idx
        return -1

    def is_point_inside_canvas(self, x: float, y: float, img2canvas_func) -> bool:
        x1, y1, x2, y2 = self.get_canvas_bbox(img2canvas_func)
        return x1 <= x <= x2 and y1 <= y <= y2

    def intersect_canvas_box(self, sx1, sy1, sx2, sy2, img2canvas_func) -> bool:
        x1, y1, x2, y2 = self.get_canvas_bbox(img2canvas_func)
        if x2 < sx1 or x1 > sx2:
            return False
        if y2 < sy1 or y1 > sy2:
            return False
        return True

    def to_dict(self):
        return {
            "img_x1": self.img_x1,
            "img_y1": self.img_y1,
            "img_x2": self.img_x2,
            "img_y2": self.img_y2
        }

# 画布控制器
class CanvasController:
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.rects: list[Rect] = []
        self.selected_rects: list[Rect] = []
        self.scale = 1.0
        self.is_drawing = False
        self.draw_start = (0.0, 0.0)
        self.temp_rect = None
        self.is_selecting = False
        self.select_start = (0.0, 0.0)
        self.select_rect = None
        self.is_dragging_handle = False
        self.drag_rect = None
        self.drag_handle_idx = -1
        self.is_moving_rect = False
        self.move_logic_start = (0.0, 0.0)
        self.rect_origins_img = {}

    def set_scale(self, scale: float):
        self.scale = max(0.2, min(5.0, scale))

    def start_drawing(self, x: float, y: float):
        self.clear_selection()
        self.is_drawing = True
        self.draw_start = (x, y)
        self.temp_rect = self.canvas.create_rectangle(x, y, x, y, outline="red", width=2)

    def on_drag_draw(self, x: float, y: float):
        if self.is_drawing and self.temp_rect:
            sx, sy = self.draw_start
            self.canvas.coords(self.temp_rect, sx, sy, x, y)

    def cancel_drawing(self):
        """取消当前绘制，删除临时框"""
        if self.is_drawing and self.temp_rect:
            self.canvas.delete(self.temp_rect)
            self.temp_rect = None
        self.is_drawing = False

    def finish_drawing(self, x: float, y: float, canvas2img_func, img2canvas_func):
        if not self.is_drawing:
            return
        self.is_drawing = False
        sx, sy = self.draw_start
        self.canvas.delete(self.temp_rect)
        self.temp_rect = None
        screen_w = abs(x - sx)
        screen_h = abs(y - sy)
        if screen_w < 5 or screen_h < 5:
            return
        ix1, iy1 = canvas2img_func(sx, sy)
        ix2, iy2 = canvas2img_func(x, y)
        rect = Rect(self.canvas, ix1, iy1, ix2, iy2)
        self.rects.append(rect)
        self.redraw_all(img2canvas_func)

    def start_select_box(self, x: float, y: float):
        self.is_selecting = True
        self.select_start = (x, y)
        self.select_rect = self.canvas.create_rectangle(
            x, y, x, y, outline="gray", dash=(4, 2)
        )

    def on_drag_select_box(self, x: float, y: float):
        if self.is_selecting and self.select_rect:
            sx, sy = self.select_start
            self.canvas.coords(self.select_rect, sx, sy, x, y)

    def finish_select_box(self, x: float, y: float, img2canvas_func):
        if not self.is_selecting:
            return
        self.is_selecting = False
        self.canvas.delete(self.select_rect)
        self.select_rect = None
        sx, sy = self.select_start
        x1, y1 = min(sx, x), min(sy, y)
        x2, y2 = max(sx, x), max(sy, y)
        self.selected_rects.clear()
        for r in self.rects:
            if r.intersect_canvas_box(x1, y1, x2, y2, img2canvas_func):
                self.selected_rects.append(r)
        self.redraw_all(img2canvas_func)

    def try_start_drag_handle(self, x: float, y: float, img2canvas_func) -> bool:
        for r in self.rects:
            idx = r.hit_handle(x, y, self.scale)
            if idx != -1:
                self.clear_selection()
                self.selected_rects.append(r)
                self.is_dragging_handle = True
                self.drag_rect = r
                self.drag_handle_idx = idx
                self.redraw_all(img2canvas_func)
                return True
        return False

    def try_start_move_rect(self, x: float, y: float, img2canvas_func) -> bool:
        if not self.selected_rects:
            return False
        for r in self.selected_rects:
            if r.is_point_inside_canvas(x, y, img2canvas_func):
                self._start_move()
                return True
        return False

    def _start_move(self):
        self.is_moving_rect = True
        self.rect_origins_img.clear()
        for rect in self.selected_rects:
            self.rect_origins_img[rect] = (rect.img_x1, rect.img_y1, rect.img_x2, rect.img_y2)

    def drag_handle(self, x: float, y: float, canvas2img_func, img2canvas_func):
        if not self.is_dragging_handle or not self.drag_rect:
            return
        r = self.drag_rect
        i = self.drag_handle_idx
        mx, my = canvas2img_func(x, y)
        if i == 0:
            r.img_x1, r.img_y1 = mx, my
        elif i == 1:
            r.img_x2, r.img_y1 = mx, my
        elif i == 2:
            r.img_x2, r.img_y2 = mx, my
        elif i == 3:
            r.img_x1, r.img_y2 = mx, my
        self.redraw_all(img2canvas_func)

    def move_rect(self, x: float, y: float, canvas2img_func, img2canvas_func):
        if not self.is_moving_rect or not self.selected_rects:
            return
        start_cx, start_cy = self.move_logic_start
        dx = x - start_cx
        dy = y - start_cy
        for rect in self.selected_rects:
            ox1, oy1, ox2, oy2 = self.rect_origins_img[rect]
            c1x, c1y = img2canvas_func(ox1, oy1)
            c2x, c2y = img2canvas_func(ox2, oy2)
            nx1, ny1 = canvas2img_func(c1x + dx, c1y + dy)
            nx2, ny2 = canvas2img_func(c2x + dx, c2y + dy)
            rect.img_x1, rect.img_y1 = nx1, ny1
            rect.img_x2, rect.img_y2 = nx2, ny2
        self.redraw_all(img2canvas_func)

    def stop_drag(self):
        self.is_dragging_handle = False
        self.is_moving_rect = False
        self.drag_rect = None
        self.drag_handle_idx = -1
        self.rect_origins_img.clear()

    def click_rect_and_start_drag(self, x: float, y: float, img2canvas_func):
        self.clear_selection()
        hit_rect = None
        for r in self.rects:
            if r.is_point_inside_canvas(x, y, img2canvas_func):
                hit_rect = r
                break
        if hit_rect:
            self.selected_rects.append(hit_rect)
            self.move_logic_start = (x, y)
            self._start_move()
        self.redraw_all(img2canvas_func)

    def clear_selection(self):
        self.selected_rects.clear()

    def delete_selected(self, img2canvas_func):
        for r in list(self.selected_rects):
            if r in self.rects:
                r.delete()
                self.rects.remove(r)
        self.clear_selection()
        self.redraw_all(img2canvas_func)

    def redraw_all(self, img2canvas_func):
        for r in self.rects:
            r.selected = r in self.selected_rects
            r.draw(self.scale, img2canvas_func)

    def export_json(self, path, img_w, img_h):
        data = {
            "image_size": {"w": img_w, "h": img_h},
            "boxes": [r.to_dict() for r in self.rects]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def import_json(self, path):
        for r in self.rects:
            r.delete()
        self.rects.clear()
        self.clear_selection()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        box_list = data.get("boxes", [])
        for item in box_list:
            ix1 = item["img_x1"]
            iy1 = item["img_y1"]
            ix2 = item["img_x2"]
            iy2 = item["img_y2"]
            rect = Rect(self.canvas, ix1, iy1, ix2, iy2)
            self.rects.append(rect)
        return data.get("image_size", None)

# 主窗口
class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("标注工具-Ctrl临时绘图")
        self.geometry("1000x700")
        # 工具栏
        self.frame = tk.Frame(self)
        self.frame.pack(fill=tk.X, padx=5, pady=5)
        self.draw_mode = tk.BooleanVar(value=False)
        tk.Checkbutton(self.frame, text="固定绘制矩形模式", variable=self.draw_mode).pack(side=tk.LEFT)
        tk.Label(self.frame, text="| 按住Ctrl临时绘图，松开取消绘制").pack(side=tk.LEFT, padx=10)
        tk.Button(self.frame, text="导出JSON", command=self.export_json).pack(side=tk.LEFT, padx=5)
        tk.Button(self.frame, text="导入JSON", command=self.import_json).pack(side=tk.LEFT, padx=5)
        # 画布
        self.canvas = tk.Canvas(self, bg="#f0f0f0")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.ctl = CanvasController(self.canvas)
        # 背景图变量
        self.bg_origin = None
        self.bg_scaled = None
        self.bg_tk = None
        self.bg_img_id = None
        self.img_origin_w = 0
        self.img_origin_h = 0
        self.bg_offset_x = 0.0
        self.bg_offset_y = 0.0
        self.base_fit_scale = 1.0
        # Ctrl标记
        self.ctrl_pressed = False
        # 延迟加载图片
        self.after(100, self.load_background)
        # 绑定鼠标事件
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.canvas.bind("<Button-3>", self.right_click_exit_draw)
        self.bind("<Delete>", lambda e: self.delete_selected())
        self.canvas.bind("<Configure>", self.resize_bg)
        # 绑定Ctrl按键
        self.bind("<KeyPress-Control_L>", self.on_ctrl_down)
        self.bind("<KeyPress-Control_R>", self.on_ctrl_down)
        self.bind("<KeyRelease-Control_L>", self.on_ctrl_up)
        self.bind("<KeyRelease-Control_R>", self.on_ctrl_up)

    def on_ctrl_down(self, event):
        self.ctrl_pressed = True

    def on_ctrl_up(self, event):
        self.ctrl_pressed = False
        # 松开Ctrl，取消正在绘制的临时框
        self.ctl.cancel_drawing()

    def load_background(self):
        try:
            self.bg_origin = Image.open("test.png")
            self.img_origin_w, self.img_origin_h = self.bg_origin.size
        except Exception as e:
            print("无test.png图片，仅画布绘图可用:", e)
            self.bg_origin = None
            self.img_origin_w = 0
            self.img_origin_h = 0
        self.update_background()

    def update_background(self):
        self.canvas.delete("bg")
        if not self.bg_origin or self.img_origin_w <= 0 or self.img_origin_h <= 0:
            return
        cw = max(self.canvas.winfo_width(), 10)
        ch = max(self.canvas.winfo_height(), 10)
        img_w = self.img_origin_w
        img_h = self.img_origin_h
        self.base_fit_scale = min(cw / img_w, ch / img_h)
        final_scale = self.base_fit_scale * self.ctl.scale
        new_w = max(int(img_w * final_scale), 1)
        new_h = max(int(img_h * final_scale), 1)
        self.bg_scaled = self.bg_origin.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.bg_tk = ImageTk.PhotoImage(self.bg_scaled)
        self.bg_offset_x = (cw - new_w) / 2
        self.bg_offset_y = (ch - new_h) / 2
        self.bg_img_id = self.canvas.create_image(
            self.bg_offset_x, self.bg_offset_y, image=self.bg_tk, anchor=tk.NW, tags="bg"
        )
        self.canvas.tag_lower("bg")

    # 画布坐标 → 原图像素
    def canvas_to_img(self, cx, cy):
        if self.img_origin_w == 0 or self.bg_scaled is None:
            return cx, cy
        rel_x = cx - self.bg_offset_x
        rel_y = cy - self.bg_offset_y
        total_scale = self.base_fit_scale * self.ctl.scale
        ix = rel_x / total_scale
        iy = rel_y / total_scale
        return ix, iy

    # 原图像素 → 画布坐标
    def img_to_canvas(self, ix, iy):
        if self.img_origin_w == 0 or self.bg_scaled is None:
            return ix, iy
        total_scale = self.base_fit_scale * self.ctl.scale
        rel_x = ix * total_scale
        rel_y = iy * total_scale
        cx = rel_x + self.bg_offset_x
        cy = rel_y + self.bg_offset_y
        return cx, cy

    def right_click_exit_draw(self, event):
        if self.draw_mode.get():
            self.draw_mode.set(False)
            self.ctl.cancel_drawing()

    def export_json(self):
        if self.img_origin_w == 0 or self.img_origin_h == 0:
            messagebox.showwarning("警告", "未加载背景图片，无法导出！")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            title="保存标注JSON"
        )
        if path:
            try:
                self.ctl.export_json(path, self.img_origin_w, self.img_origin_h)
                messagebox.showinfo("成功", "导出完成！")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败：{e}")

    def import_json(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            title="选择标注JSON"
        )
        if path:
            try:
                img_size = self.ctl.import_json(path)
                self.update_background()
                self.ctl.redraw_all(self.img_to_canvas)
                messagebox.showinfo("成功", f"导入完成，原图尺寸：{img_size}")
            except Exception as e:
                messagebox.showerror("错误", f"导入失败：{e}")

    def delete_selected(self):
        self.ctl.delete_selected(self.img_to_canvas)

    def to_real(self, cx: int, cy: int) -> tuple[float, float]:
        return float(cx), float(cy)

    def on_press(self, e: tk.Event):
        x, y = self.to_real(e.x, e.y)
        self.ctl.move_logic_start = (x, y)
        # 固定绘制模式 或 按住Ctrl，都进入绘图
        if self.draw_mode.get() or self.ctrl_pressed:
            self.ctl.start_drawing(x, y)
        else:
            if self.ctl.try_start_drag_handle(x, y, self.img_to_canvas):
                return
            if self.ctl.try_start_move_rect(x, y, self.img_to_canvas):
                return
            hit_box = False
            for r in self.ctl.rects:
                if r.is_point_inside_canvas(x, y, self.img_to_canvas):
                    hit_box = True
                    break
            if hit_box:
                self.ctl.click_rect_and_start_drag(x, y, self.img_to_canvas)
            else:
                self.ctl.start_select_box(x, y)

    def on_drag(self, e: tk.Event):
        x, y = self.to_real(e.x, e.y)
        if self.draw_mode.get() or self.ctrl_pressed:
            self.ctl.on_drag_draw(x, y)
        else:
            if self.ctl.is_dragging_handle:
                self.ctl.drag_handle(x, y, self.canvas_to_img, self.img_to_canvas)
            elif self.ctl.is_moving_rect:
                self.ctl.move_rect(x, y, self.canvas_to_img, self.img_to_canvas)
            else:
                self.ctl.on_drag_select_box(x, y)

    def on_release(self, e: tk.Event):
        x, y = self.to_real(e.x, e.y)
        self.ctl.stop_drag()
        if self.draw_mode.get() or self.ctrl_pressed:
            self.ctl.finish_drawing(x, y, self.canvas_to_img, self.img_to_canvas)
        else:
            self.ctl.finish_select_box(x, y, self.img_to_canvas)

    def on_wheel(self, e: tk.Event):
        delta = 0.1 if e.delta > 0 else -0.1
        self.ctl.set_scale(self.ctl.scale + delta)
        self.update_background()
        self.ctl.redraw_all(self.img_to_canvas)

    def resize_bg(self, event):
        self.update_background()
        self.ctl.redraw_all(self.img_to_canvas)

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()