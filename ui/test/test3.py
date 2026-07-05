import tkinter as tk
import math

class RectDrawApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("图片矩形标注工具")
        self.geometry("1000x700")

        self.canvas = tk.Canvas(self, bg="#333")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 缩放
        self.scale = 1.0
        self.scale_step = 0.1
        self.min_scale = 0.2
        self.max_scale = 5.0

        # 背景图（换成你自己的路径）
        self.bg_img = None
        try:
            self.bg_img = tk.PhotoImage(file="test.png")
            self.canvas.create_image(0, 0, image=self.bg_img, anchor=tk.NW)
        except:
            print("背景图加载失败，使用纯色背景")

        # 绘制状态
        self.start_pos = None
        self.temp_rect = None

        self.rects = []
        self.selected_rect = None

        # 拖拽手柄
        self.dragging_handle = False
        self.drag_rect = None
        self.drag_idx = None

        # 事件绑定
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.bind("<Delete>", self.on_delete)

    # 坐标转换
    def to_img(self, x, y):
        return x / self.scale, y / self.scale

    def to_canvas(self, x, y):
        return x * self.scale, y * self.scale

    # 滚轮缩放
    def on_wheel(self, e):
        mx, my = e.x, e.y
        rx, ry = self.to_img(mx, my)

        if e.delta > 0:
            new_scale = self.scale + self.scale_step
        else:
            new_scale = self.scale - self.scale_step

        new_scale = max(self.min_scale, min(self.max_scale, new_scale))
        if new_scale == self.scale:
            return

        self.scale = new_scale
        nx, ny = self.to_canvas(rx, ry)
        dx = mx - nx
        dy = my - ny
        self.canvas.scale("all", 0, 0, new_scale/self.scale, new_scale/self.scale)
        self.canvas.move("all", dx, dy)

    # 按下
    def on_press(self, e):
        x, y = self.to_img(e.x, e.y)

        # 检查是否拖动手柄
        for rect in self.rects:
            corners = self.get_corners(rect)
            for i, (cx, cy) in enumerate(corners):
                if math.hypot(x - cx, y - cy) < 10 / self.scale:
                    self.dragging_handle = True
                    self.drag_rect = rect
                    self.drag_idx = i
                    self.selected_rect = rect
                    self.refresh_handles()
                    return

        # 点击矩形内部 → 选中
        for rect in self.rects:
            x1, y1, x2, y2 = self.rect_order(rect)
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.selected_rect = rect
                self.refresh_handles()
                return

        # 准备画新矩形
        self.selected_rect = None
        self.refresh_handles()
        self.start_pos = (x, y)
        cx, cy = self.to_canvas(x, y)
        self.temp_rect = self.canvas.create_rectangle(cx, cy, cx, cy, outline="red", width=2)

    # 拖动
    def on_drag(self, e):
        x, y = self.to_img(e.x, e.y)

        # 拖手柄
        if self.dragging_handle and self.drag_rect:
            r = self.drag_rect
            i = self.drag_idx
            x1, y1, x2, y2 = r['x1'], r['y1'], r['x2'], r['y2']

            if i == 0:
                x1, y1 = x, y
            elif i == 1:
                x2, y1 = x, y
            elif i == 2:
                x2, y2 = x, y
            elif i == 3:
                x1, y2 = x, y

            self.update_rect(r, x1, y1, x2, y2)
            return

        # 画预览矩形
        if self.start_pos and self.temp_rect:
            sx, sy = self.start_pos
            cx1, cy1 = self.to_canvas(sx, sy)
            cx2, cy2 = self.to_canvas(x, y)
            self.canvas.coords(self.temp_rect, cx1, cy1, cx2, cy2)

    # 松开
    def on_release(self, e):
        if self.dragging_handle:
            self.dragging_handle = False
            self.drag_rect = None
            self.drag_idx = None
            return

        # 只有拖动有位移才创建矩形
        if self.start_pos and self.temp_rect:
            sx, sy = self.start_pos
            ex, ey = self.to_img(e.x, e.y)

            # 微小拖动不创建
            if abs(ex - sx) > 1 / self.scale and abs(ey - sy) > 1 / self.scale:
                self.add_rect(sx, sy, ex, ey)

            self.canvas.delete(self.temp_rect)
            self.temp_rect = None
            self.start_pos = None

    # 矩形工具
    def rect_order(self, r):
        x1 = min(r['x1'], r['x2'])
        x2 = max(r['x1'], r['x2'])
        y1 = min(r['y1'], r['y2'])
        y2 = max(r['y1'], r['y2'])
        return x1, y1, x2, y2

    def get_corners(self, r):
        x1, y1, x2, y2 = self.rect_order(r)
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]

    def add_rect(self, x1, y1, x2, y2):
        cx1, cy1 = self.to_canvas(x1, y1)
        cx2, cy2 = self.to_canvas(x2, y2)
        rid = self.canvas.create_rectangle(cx1, cy1, cx2, cy2, outline="red", width=2)
        rect = {
            'id': rid,
            'x1': x1, 'y1': y1,
            'x2': x2, 'y2': y2,
            'handles': []
        }
        self.rects.append(rect)
        self.update_rect(rect, x1, y1, x2, y2)

    def update_rect(self, rect, x1, y1, x2, y2):
        rect['x1'], rect['y1'], rect['x2'], rect['y2'] = x1, y1, x2, y2
        cx1, cy1 = self.to_canvas(x1, y1)
        cx2, cy2 = self.to_canvas(x2, y2)
        self.canvas.coords(rect['id'], cx1, cy1, cx2, cy2)
        self.refresh_handles()

    # 刷新所有手柄：选中的变大变黄
    def refresh_handles(self):
        # 删除旧手柄
        for r in self.rects:
            for h in r['handles']:
                self.canvas.delete(h)
            r['handles'].clear()

        # 重绘
        for r in self.rects:
            corners = self.get_corners(r)
            if r == self.selected_rect:
                size = 8
                color = "yellow"
            else:
                size = 5
                color = "blue"

            size = size / self.scale
            for x, y in corners:
                cx, cy = self.to_canvas(x, y)
                h = self.canvas.create_rectangle(
                    cx - size, cy - size,
                    cx + size, cy + size,
                    fill=color, outline="white"
                )
                r['handles'].append(h)

    def on_delete(self, e):
        if self.selected_rect in self.rects:
            self.canvas.delete(self.selected_rect['id'])
            for h in self.selected_rect['handles']:
                self.canvas.delete(h)
            self.rects.remove(self.selected_rect)
            self.selected_rect = None
            self.refresh_handles()

if __name__ == "__main__":
    app = RectDrawApp()
    app.mainloop()
