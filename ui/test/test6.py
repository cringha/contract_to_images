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

# 矩形元素
class Rect:
    def __init__(self, canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float):
        self.canvas = canvas
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.item_id = None
        self.handles = [Handle(canvas) for _ in range(4)]
        self.selected = False

    def get_bbox(self):
        x1 = min(self.x1, self.x2)
        x2 = max(self.x1, self.x2)
        y1 = min(self.y1, self.y2)
        y2 = max(self.y1, self.y2)
        return x1, y1, x2, y2

    def set_bbox(self, x1: float, y1: float, x2: float, y2: float):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def move_by(self, dx: float, dy: float):
        self.x1 += dx
        self.y1 += dy
        self.x2 += dx
        self.y2 += dy

    def update_handles(self):
        x1, y1, x2, y2 = self.get_bbox()
        self.handles[0].set_pos(x1, y1)
        self.handles[1].set_pos(x2, y1)
        self.handles[2].set_pos(x2, y2)
        self.handles[3].set_pos(x1, y2)

    def draw(self, scale: float):
        x1, y1, x2, y2 = self.get_bbox()
        if self.item_id:
            self.canvas.coords(self.item_id, x1, y1, x2, y2)
        else:
            self.item_id = self.canvas.create_rectangle(
                x1, y1, x2, y2, outline="red", width=2
            )
        self.update_handles()
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

    def is_point_inside(self, x: float, y: float) -> bool:
        x1, y1, x2, y2 = self.get_bbox()
        return x1 <= x <= x2 and y1 <= y <= y2

    def intersect_box(self, sx1, sy1, sx2, sy2) -> bool:
        x1, y1, x2, y2 = self.get_bbox()
        if x2 < sx1 or x1 > sx2:
            return False
        if y2 < sy1 or y1 > sy2:
            return False
        return True

    # 序列化导出JSON
    def to_dict(self):
        return {"x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2}

# 画布控制器
class CanvasController:
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.rects: list[Rect] = []
        self.selected_rects: list[Rect] = []
        self.scale = 1.0
        # 绘制状态
        self.is_drawing = False
        self.draw_start = (0.0, 0.0)
        self.temp_rect = None
        # 框选状态
        self.is_selecting = False
        self.select_start = (0.0, 0.0)
        self.select_rect = None
        # 拖拽手柄
        self.is_dragging_handle = False
        self.drag_rect = None
        self.drag_handle_idx = -1
        # 整体移动矩形
        self.is_moving_rect = False
        self.move_logic_start = (0.0, 0.0)
        self.rect_origins = {}

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

    def finish_drawing(self, x: float, y: float):
        if not self.is_drawing:
            return
        self.is_drawing = False
        sx, sy = self.draw_start
        self.canvas.delete(self.temp_rect)
        self.temp_rect = None
        screen_w = abs(x - sx) * self.scale
        screen_h = abs(y - sy) * self.scale
        if screen_w < 5 or screen_h < 5:
            return
        rect = Rect(self.canvas, sx, sy, x, y)
        self.rects.append(rect)
        self.redraw_all()

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

    def finish_select_box(self, x: float, y: float):
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
            if r.intersect_box(x1, y1, x2, y2):
                self.selected_rects.append(r)
        self.redraw_all()

    def try_start_drag_handle(self, x: float, y: float) -> bool:
        for r in self.rects:
            idx = r.hit_handle(x, y, self.scale)
            if idx != -1:
                self.clear_selection()
                self.selected_rects.append(r)
                self.is_dragging_handle = True
                self.drag_rect = r
                self.drag_handle_idx = idx
                self.redraw_all()
                return True
        return False

    def try_start_move_rect(self, x: float, y: float) -> bool:
        if not self.selected_rects:
            return False
        for r in self.selected_rects:
            if r.is_point_inside(x, y):
                self._start_move(x, y)
                return True
        return False

    def _start_move(self, x, y):
        self.is_moving_rect = True
        self.move_logic_start = (x, y)
        self.rect_origins.clear()
        for rect in self.selected_rects:
            self.rect_origins[rect] = (rect.x1, rect.y1, rect.x2, rect.y2)

    def drag_handle(self, x: float, y: float):
        if not self.is_dragging_handle or not self.drag_rect:
            return
        r = self.drag_rect
        i = self.drag_handle_idx
        if i == 0:
            r.set_bbox(x, y, r.x2, r.y2)
        elif i == 1:
            r.set_bbox(r.x1, y, x, r.y2)
        elif i == 2:
            r.set_bbox(r.x1, r.y1, x, y)
        elif i == 3:
            r.set_bbox(x, r.y1, r.x2, y)
        self.redraw_all()

    def move_rect(self, x: float, y: float):
        if not self.is_moving_rect or not self.selected_rects:
            return
        start_x, start_y = self.move_logic_start
        dx = x - start_x
        dy = y - start_y
        for rect in self.selected_rects:
            ox1, oy1, ox2, oy2 = self.rect_origins[rect]
            rect.set_bbox(ox1 + dx, oy1 + dy, ox2 + dx, oy2 + dy)
        self.redraw_all()

    def stop_drag(self):
        self.is_dragging_handle = False
        self.is_moving_rect = False
        self.drag_rect = None
        self.drag_handle_idx = -1
        self.rect_origins.clear()

    def click_rect_and_start_drag(self, x: float, y: float):
        self.clear_selection()
        hit_rect = None
        for r in self.rects:
            if r.is_point_inside(x, y):
                hit_rect = r
                break
        if hit_rect:
            self.selected_rects.append(hit_rect)
            self._start_move(x, y)
        self.redraw_all()

    def clear_selection(self):
        self.selected_rects.clear()

    def delete_selected(self):
        for r in list(self.selected_rects):
            if r in self.rects:
                r.delete()
                self.rects.remove(r)
        self.clear_selection()
        self.redraw_all()

    def redraw_all(self):
        for r in self.rects:
            r.selected = r in self.selected_rects
            r.draw(self.scale)

    # 导出所有矩形JSON
    def export_json(self, path):
        data = [r.to_dict() for r in self.rects]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # 导入JSON重建矩形
    def import_json(self, path):
        # 清空现有框
        for r in self.rects:
            r.delete()
        self.rects.clear()
        self.clear_selection()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            x1 = item["x1"]
            y1 = item["y1"]
            x2 = item["x2"]
            y2 = item["y2"]
            rect = Rect(self.canvas, x1, y1, x2, y2)
            self.rects.append(rect)
        self.redraw_all()

# 主窗口
class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("标注工具-居中背景+导入导出+右键退出绘图")
        self.geometry("1000x700")
        # 工具栏
        self.frame = tk.Frame(self)
        self.frame.pack(fill=tk.X, padx=5, pady=5)
        self.draw_mode = tk.BooleanVar(value=False)
        tk.Checkbutton(self.frame, text="绘制矩形模式", variable=self.draw_mode).pack(side=tk.LEFT)

        # 新增导入导出按钮
        tk.Button(self.frame, text="导出JSON", command=self.export_json).pack(side=tk.LEFT, padx=5)
        tk.Button(self.frame, text="导入JSON", command=self.import_json).pack(side=tk.LEFT, padx=5)

        # 画布
        self.canvas = tk.Canvas(self, bg="#f0f0f0")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.ctl = CanvasController(self.canvas)

        # 背景图相关
        self.bg_origin = None  # 原始PhotoImage
        self.bg_scaled = None  # 缩放后图片
        self.bg_img_id = None
        self.load_background()

        # 事件绑定
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        # 需求1：鼠标右键退出绘图模式
        self.canvas.bind("<Button-3>", self.right_click_exit_draw)
        self.bind("<Delete>", lambda e: self.ctl.delete_selected())

    def load_background(self):
        try:
            self.bg_origin = tk.PhotoImage(file="test.png")
        except Exception:
            self.bg_origin = None
        self.update_background()

    def update_background(self):
        """需求3：背景图居中、自适应铺满画布，跟随scale缩放"""
        self.canvas.delete("bg")
        if not self.bg_origin:
            return
        scale = self.ctl.scale
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        img_w = self.bg_origin.width()
        img_h = self.bg_origin.height()

        # 计算缩放，保证图片完整显示在画布内
        fit_scale = min(cw / img_w, ch / img_h)
        final_scale = fit_scale * scale

        # tk PhotoImage缩放
        if final_scale < 1:
            sub = max(1, int(1 / final_scale))
            self.bg_scaled = self.bg_origin.subsample(sub, sub)
        else:
            zoom = int(final_scale)
            self.bg_scaled = self.bg_origin.zoom(zoom, zoom)

        # 居中坐标
        sw = self.bg_scaled.width()
        sh = self.bg_scaled.height()
        x = (cw - sw) / 2
        y = (ch - sh) / 2
        self.bg_img_id = self.canvas.create_image(x, y, image=self.bg_scaled, anchor=tk.NW, tags="bg")

    def right_click_exit_draw(self, event):
        """需求1：右键取消绘制模式"""
        if self.draw_mode.get():
            self.draw_mode.set(False)
            # 如果正在绘制，清除临时矩形
            if self.ctl.is_drawing and self.ctl.temp_rect:
                self.canvas.delete(self.ctl.temp_rect)
                self.ctl.temp_rect = None
            self.ctl.is_drawing = False

    def export_json(self):
        """导出按钮逻辑"""
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            title="保存标注JSON"
        )
        if path:
            try:
                self.ctl.export_json(path)
                messagebox.showinfo("成功", "导出完成！")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败：{e}")

    def import_json(self):
        """导入按钮逻辑"""
        path = filedialog.askopenfilename(
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            title="选择标注JSON"
        )
        if path:
            try:
                self.ctl.import_json(path)
                messagebox.showinfo("成功", "导入完成！")
            except Exception as e:
                messagebox.showerror("错误", f"导入失败：{e}")

    def to_real(self, cx: int, cy: int) -> tuple[float, float]:
        return cx / self.ctl.scale, cy / self.ctl.scale

    def on_press(self, e: tk.Event):
        x, y = self.to_real(e.x, e.y)
        if self.draw_mode.get():
            self.ctl.start_drawing(x, y)
        else:
            if self.ctl.try_start_drag_handle(x, y):
                return
            if self.ctl.try_start_move_rect(x, y):
                return
            hit_box = False
            for r in self.ctl.rects:
                if r.is_point_inside(x, y):
                    hit_box = True
                    break
            if hit_box:
                self.ctl.click_rect_and_start_drag(x, y)
            else:
                self.ctl.start_select_box(x, y)

    def on_drag(self, e: tk.Event):
        x, y = self.to_real(e.x, e.y)
        if self.draw_mode.get():
            self.ctl.on_drag_draw(x, y)
        else:
            if self.ctl.is_dragging_handle:
                self.ctl.drag_handle(x, y)
            elif self.ctl.is_moving_rect:
                self.ctl.move_rect(x, y)
            else:
                self.ctl.on_drag_select_box(x, y)

    def on_release(self, e: tk.Event):
        x, y = self.to_real(e.x, e.y)
        self.ctl.stop_drag()
        if self.draw_mode.get():
            self.ctl.finish_drawing(x, y)
        else:
            self.ctl.finish_select_box(x, y)

    def on_wheel(self, e: tk.Event):
        delta = 0.1 if e.delta > 0 else -0.1
        self.ctl.set_scale(self.ctl.scale + delta)
        self.update_background()  # 缩放同步更新背景
        self.ctl.redraw_all()

if __name__ == "__main__":
    app = MainApp()
    # 窗口大小变化时刷新背景居中
    def resize_bg(event):
        app.update_background()
    app.canvas.bind("<Configure>", resize_bg)
    app.mainloop()
