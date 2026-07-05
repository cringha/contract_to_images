import tkinter as tk
import math
from PIL import Image, ImageTk
class RectDrawApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("图片矩形标注工具")
        self.geometry("1000x700")

        self.canvas = tk.Canvas(self, bg="#333")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 缩放配置
        self.scale = 1.0
        self.scale_step = 0.1
        self.min_scale = 0.2
        self.max_scale = 5.0

        # 背景图（换成你自己的图片路径）
        self.bg_img = None
        try:

            im = Image.open("./test.jpg")
            # im.thumbnail((w_can - 30, h_can - 40), Image.Resampling.LANCZOS)
            # img_tk = ImageTk.PhotoImage(im)

            self.bg_img = img_tk = ImageTk.PhotoImage(im)
            # self.bg_img = tk.PhotoImage(im )
            self.canvas.create_image(0, 0, image=self.bg_img, anchor=tk.NW)
        except Exception as ee:
            print(f"背景图加载失败，使用纯色背景 {ee}")

        # 绘制状态
        self.start_pos = None
        self.temp_rect = None

        # 矩形列表
        self.rects = []
        self.selected_rect = None

        # 拖拽手柄
        self.dragging_handle = False
        self.drag_rect = None
        self.drag_idx = None

        # 绑定事件
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

        # 以鼠标为中心缩放
        self.scale = new_scale
        nx, ny = self.to_canvas(rx, ry)
        dx = mx - nx
        dy = my - ny
        self.canvas.scale("all", 0, 0, new_scale/self.scale, new_scale/self.scale)
        self.canvas.move("all", dx, dy)

    # 鼠标按下
    def on_press(self, e):
        x, y = self.to_img(e.x, e.y)

        # 先检查是否点中手柄
        for rect in self.rects:
            corners = self.get_corners(rect)
            for i, (cx, cy) in enumerate(corners):
                if math.hypot(x - cx, y - cy) < 10 / self.scale:
                    self.dragging_handle = True
                    self.drag_rect = rect
                    self.drag_idx = i
                    self.selected_rect = rect
                    self.refresh_selected()
                    return

        # 点击矩形本体（选中）
        for rect in self.rects:
            x1, y1, x2, y2 = self.rect_order(rect)
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.selected_rect = rect
                self.refresh_selected()
                return

        # 否则开始绘制新矩形
        self.selected_rect = None
        self.refresh_selected()
        self.start_pos = (x, y)
        cx, cy = self.to_canvas(x, y)
        self.temp_rect = self.canvas.create_rectangle(cx, cy, cx, cy, outline="lime", width=2)

    # 鼠标拖动
    def on_drag(self, e):
        x, y = self.to_img(e.x, e.y)

        # 拖动手柄调整矩形
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

        # 绘制新矩形预览
        if self.start_pos and self.temp_rect:
            sx, sy = self.start_pos
            cx1, cy1 = self.to_canvas(sx, sy)
            cx2, cy2 = self.to_canvas(x, y)
            self.canvas.coords(self.temp_rect, cx1, cy1, cx2, cy2)

    # 鼠标松开
    def on_release(self, e):
        # 结束手柄拖动
        if self.dragging_handle:
            self.dragging_handle = False
            self.drag_rect = None
            self.drag_idx = None
            return

        # 结束绘制，创建正式矩形
        if self.start_pos and self.temp_rect:
            sx, sy = self.start_pos
            ex, ey = self.to_img(e.x, e.y)
            self.add_rect(sx, sy, ex, ey)
            self.canvas.delete(self.temp_rect)
            self.temp_rect = None
            self.start_pos = None

    # 矩形工具方法
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
        self.update_handles(rect)

    def update_handles(self, rect):
        for h in rect['handles']:
            self.canvas.delete(h)
        rect['handles'].clear()
        corners = self.get_corners(rect)
        s = 6 / self.scale
        for x, y in corners:
            cx, cy = self.to_canvas(x, y)
            h = self.canvas.create_rectangle(cx-s, cy-s, cx+s, cy+s, fill="blue", outline="white")
            rect['handles'].append(h)

    def refresh_selected(self):
        for r in self.rects:
            self.canvas.itemconfig(r['id'], outline="red", width=2)
        if self.selected_rect:
            self.canvas.itemconfig(self.selected_rect['id'], outline="yellow", width=3)

    def on_delete(self, e):
        if self.selected_rect in self.rects:
            self.canvas.delete(self.selected_rect['id'])
            for h in self.selected_rect['handles']:
                self.canvas.delete(h)
            self.rects.remove(self.selected_rect)
            self.selected_rect = None

if __name__ == "__main__":
    app = RectDrawApp()
    app.mainloop()
