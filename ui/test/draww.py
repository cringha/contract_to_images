import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import json
import math
import copy
import os
from PIL import Image, ImageDraw, ImageTk


class VectorShape:
    """矢量形状基类"""

    def __init__(self, color, line_width=2, fill_color=None):
        self.color = color
        self.line_width = line_width
        self.fill_color = fill_color
        self.selected = False
        self.id = None

    def to_dict(self):
        return {
            'type': self.__class__.__name__,
            'color': self.color,
            'line_width': self.line_width,
            'fill_color': self.fill_color
        }

    def draw(self, canvas, offset_x=0, offset_y=0, scale=1):
        pass

    def get_bounds(self):
        pass

    def contains_point(self, x, y):
        return False

    def move(self, dx, dy):
        pass


class RectangleShape(VectorShape):
    def __init__(self, x, y, width, height, color, line_width=2, fill_color=None):
        super().__init__(color, line_width, fill_color)
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def to_dict(self):
        data = super().to_dict()
        data.update({'x': self.x, 'y': self.y, 'width': self.width, 'height': self.height})
        return data

    def draw(self, canvas, offset_x=0, offset_y=0, scale=1):
        x1 = (self.x + offset_x) * scale
        y1 = (self.y + offset_y) * scale
        x2 = (self.x + self.width + offset_x) * scale
        y2 = (self.y + self.height + offset_y) * scale

        outline = '#FF0000' if self.selected else self.color
        fill = self.fill_color if self.fill_color else ''

        if fill:
            canvas.create_rectangle(x1, y1, x2, y2, outline=outline, width=self.line_width, fill=fill)
        else:
            canvas.create_rectangle(x1, y1, x2, y2, outline=outline, width=self.line_width, fill='')

    def get_bounds(self):
        return self.x, self.y, self.x + self.width, self.y + self.height

    def contains_point(self, x, y):
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

    def move(self, dx, dy):
        self.x += dx
        self.y += dy


class CircleShape(VectorShape):
    def __init__(self, x, y, radius, color, line_width=2, fill_color=None):
        super().__init__(color, line_width, fill_color)
        self.x = x
        self.y = y
        self.radius = radius

    def to_dict(self):
        data = super().to_dict()
        data.update({'x': self.x, 'y': self.y, 'radius': self.radius})
        return data

    def draw(self, canvas, offset_x=0, offset_y=0, scale=1):
        cx = (self.x + offset_x) * scale
        cy = (self.y + offset_y) * scale
        r = self.radius * scale

        outline = '#FF0000' if self.selected else self.color
        fill = self.fill_color if self.fill_color else ''

        if fill:
            canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=outline, width=self.line_width, fill=fill)
        else:
            canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=outline, width=self.line_width, fill='')

    def get_bounds(self):
        return self.x - self.radius, self.y - self.radius, self.x + self.radius, self.y + self.radius

    def contains_point(self, x, y):
        distance = math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)
        return distance <= self.radius

    def move(self, dx, dy):
        self.x += dx
        self.y += dy


class LineShape(VectorShape):
    def __init__(self, x1, y1, x2, y2, color, line_width=2):
        super().__init__(color, line_width)
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def to_dict(self):
        data = super().to_dict()
        data.update({'x1': self.x1, 'y1': self.y1, 'x2': self.x2, 'y2': self.y2})
        return data

    def draw(self, canvas, offset_x=0, offset_y=0, scale=1):
        x1 = (self.x1 + offset_x) * scale
        y1 = (self.y1 + offset_y) * scale
        x2 = (self.x2 + offset_x) * scale
        y2 = (self.y2 + offset_y) * scale

        outline = '#FF0000' if self.selected else self.color
        canvas.create_line(x1, y1, x2, y2, fill=outline, width=self.line_width)

    def get_bounds(self):
        return min(self.x1, self.x2), min(self.y1, self.y2), max(self.x1, self.x2), max(self.y1, self.y2)

    def contains_point(self, x, y):
        dx = self.x2 - self.x1
        dy = self.y2 - self.y1
        if dx == 0 and dy == 0:
            return math.sqrt((x - self.x1) ** 2 + (y - self.y1) ** 2) <= 5

        t = ((x - self.x1) * dx + (y - self.y1) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))
        proj_x = self.x1 + t * dx
        proj_y = self.y1 + t * dy
        distance = math.sqrt((x - proj_x) ** 2 + (y - proj_y) ** 2)
        return distance <= 5

    def move(self, dx, dy):
        self.x1 += dx
        self.y1 += dy
        self.x2 += dx
        self.y2 += dy


class EllipseShape(VectorShape):
    def __init__(self, x, y, rx, ry, color, line_width=2, fill_color=None):
        super().__init__(color, line_width, fill_color)
        self.x = x
        self.y = y
        self.rx = rx
        self.ry = ry

    def to_dict(self):
        data = super().to_dict()
        data.update({'x': self.x, 'y': self.y, 'rx': self.rx, 'ry': self.ry})
        return data

    def draw(self, canvas, offset_x=0, offset_y=0, scale=1):
        cx = (self.x + offset_x) * scale
        cy = (self.y + offset_y) * scale
        rx = self.rx * scale
        ry = self.ry * scale

        outline = '#FF0000' if self.selected else self.color
        fill = self.fill_color if self.fill_color else ''

        if fill:
            canvas.create_oval(cx - rx, cy - ry, cx + rx, cy + ry, outline=outline, width=self.line_width, fill=fill)
        else:
            canvas.create_oval(cx - rx, cy - ry, cx + rx, cy + ry, outline=outline, width=self.line_width, fill='')

    def get_bounds(self):
        return self.x - self.rx, self.y - self.ry, self.x + self.rx, self.y + self.ry

    def contains_point(self, x, y):
        return ((x - self.x) ** 2 / self.rx ** 2 + (y - self.y) ** 2 / self.ry ** 2) <= 1

    def move(self, dx, dy):
        self.x += dx
        self.y += dy


class PolygonShape(VectorShape):
    def __init__(self, points, color, line_width=2, fill_color=None):
        super().__init__(color, line_width, fill_color)
        self.points = points

    def to_dict(self):
        data = super().to_dict()
        data.update({'points': self.points})
        return data

    def draw(self, canvas, offset_x=0, offset_y=0, scale=1):
        scaled_points = []
        for x, y in self.points:
            scaled_points.append((x + offset_x) * scale)
            scaled_points.append((y + offset_y) * scale)

        outline = '#FF0000' if self.selected else self.color
        fill = self.fill_color if self.fill_color else ''

        if fill:
            canvas.create_polygon(scaled_points, outline=outline, width=self.line_width, fill=fill)
        else:
            canvas.create_polygon(scaled_points, outline=outline, width=self.line_width, fill='')

    def get_bounds(self):
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return min(xs), min(ys), max(xs), max(ys)

    def contains_point(self, x, y):
        inside = False
        n = len(self.points)
        for i in range(n):
            x1, y1 = self.points[i]
            x2, y2 = self.points[(i + 1) % n]
            if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1):
                inside = not inside
        return inside

    def move(self, dx, dy):
        self.points = [(x + dx, y + dy) for x, y in self.points]


class TextShape(VectorShape):
    def __init__(self, x, y, text, font_size=12, color='#000000'):
        super().__init__(color, 1)
        self.x = x
        self.y = y
        self.text = text
        self.font_size = font_size

    def to_dict(self):
        data = super().to_dict()
        data.update({'x': self.x, 'y': self.y, 'text': self.text, 'font_size': self.font_size})
        return data

    def draw(self, canvas, offset_x=0, offset_y=0, scale=1):
        x = (self.x + offset_x) * scale
        y = (self.y + offset_y) * scale
        font = ('Arial', int(self.font_size * scale))
        outline = '#FF0000' if self.selected else self.color
        canvas.create_text(x, y, text=self.text, font=font, fill=outline, anchor='nw')

    def get_bounds(self):
        return self.x, self.y, self.x + len(self.text) * self.font_size * 0.6, self.y + self.font_size

    def contains_point(self, x, y):
        return self.x <= x <= self.x + len(self.text) * 10 and self.y - 10 <= y <= self.y + self.font_size

    def move(self, dx, dy):
        self.x += dx
        self.y += dy


class VectorEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("矢量图编辑器 - 完整版")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1a1a2e')

        # 画布参数
        self.canvas_width = 1000
        self.canvas_height = 700
        self.offset_x = 0
        self.offset_y = 0
        self.scale = 1
        self.show_grid = True
        self.grid_size = 20
        self.snap_to_grid = False
        self.show_rulers = True

        # 形状列表
        self.shapes = []
        self.selected_shape = None
        self.selected_index = -1
        self.clipboard = None
        self.bitmap_images = []  # 存储位图

        # 当前工具
        self.current_tool = 'select'
        self.current_color = '#FF0000'
        self.current_fill_color = None
        self.line_width = 2
        self.font_size = 12
        self.use_fill = False

        # 绘制临时变量
        self.start_x = None
        self.start_y = None
        self.temp_shape = None
        self.polygon_points = []
        self.is_drawing_polygon = False

        # 历史记录
        self.history = []
        self.history_index = -1
        self.save_to_history()

        # 创建界面
        self.setup_ui()
        self.draw_canvas()

        # 绑定键盘事件
        self.root.bind('<Delete>', lambda e: self.delete_selected())
        self.root.bind('<Control-z>', lambda e: self.undo())
        self.root.bind('<Control-y>', lambda e: self.redo())
        self.root.bind('<Control-c>', lambda e: self.copy_selected())
        self.root.bind('<Control-v>', lambda e: self.paste())
        self.root.bind('<Control-a>', lambda e: self.select_all())
        self.root.bind('<Escape>', lambda e: self.cancel_drawing())

        # 加载示例
        self.load_demo()

        print("=" * 60)
        print("矢量图编辑器 - 完整版已启动")
        print("快捷键：")
        print("  Delete - 删除选中图形")
        print("  Ctrl+Z - 撤销")
        print("  Ctrl+Y - 重做")
        print("  Ctrl+C - 复制")
        print("  Ctrl+V - 粘贴")
        print("  Ctrl+A - 全选")
        print("  Esc - 取消绘制")
        print("=" * 60)

    def setup_ui(self):
        """创建界面"""
        # 主容器
        main_container = tk.Frame(self.root, bg='#1a1a2e')
        main_container.pack(fill=tk.BOTH, expand=True)

        # 顶部工具栏
        top_toolbar = tk.Frame(main_container, bg='#16213e', height=50)
        top_toolbar.pack(fill=tk.X, side=tk.TOP, padx=0, pady=0)
        top_toolbar.pack_propagate(False)

        # 文件操作按钮
        file_frame = tk.Frame(top_toolbar, bg='#16213e')
        file_frame.pack(side=tk.LEFT, padx=10, pady=5)

        tk.Button(file_frame, text="📁 新建", command=self.new_file,
                  bg='#3498db', fg='white', padx=8).pack(side=tk.LEFT, padx=2)
        tk.Button(file_frame, text="💾 保存", command=self.save_file,
                  bg='#2ecc71', fg='white', padx=8).pack(side=tk.LEFT, padx=2)
        tk.Button(file_frame, text="📂 打开", command=self.open_file,
                  bg='#3498db', fg='white', padx=8).pack(side=tk.LEFT, padx=2)
        tk.Button(file_frame, text="🖼️ 导入图片", command=self.import_image,
                  bg='#9b59b6', fg='white', padx=8).pack(side=tk.LEFT, padx=2)
        tk.Button(file_frame, text="📸 导出图片", command=self.export_image_formats,
                  bg='#e67e22', fg='white', padx=8).pack(side=tk.LEFT, padx=2)

        # 左侧工具栏
        left_toolbar = tk.Frame(main_container, bg='#16213e', width=120)
        left_toolbar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)
        left_toolbar.pack_propagate(False)

        # 标题
        title = tk.Label(left_toolbar, text="绘图工具", bg='#0f3460', fg='white', font=('Arial', 12, 'bold'), pady=10)
        title.pack(fill=tk.X)

        # 工具按钮
        tools = [
            ('🔍 选择', 'select'),
            ('⬛ 矩形', 'rect'),
            ('⚪ 圆形', 'circle'),
            ('🔵 椭圆', 'ellipse'),
            ('📏 直线', 'line'),
            ('🔺 多边形', 'polygon'),
            ('📝 文字', 'text')
        ]

        self.tool_buttons = {}
        for text, tool_id in tools:
            btn = tk.Button(left_toolbar, text=text, command=lambda t=tool_id: self.set_tool(t),
                            bg='#0f3460', fg='white', font=('Arial', 10), pady=8,
                            relief=tk.FLAT, activebackground='#1a5a8a')
            btn.pack(fill=tk.X, padx=10, pady=3)
            self.tool_buttons[tool_id] = btn
        self.tool_buttons['select'].config(bg='#1a5a8a')

        # 分隔线
        tk.Frame(left_toolbar, height=2, bg='#0f3460').pack(fill=tk.X, pady=10)

        # 编辑操作
        tk.Label(left_toolbar, text="编辑操作", bg='#0f3460', fg='white', font=('Arial', 10, 'bold'), pady=5).pack(
            fill=tk.X)

        tk.Button(left_toolbar, text="↩️ 撤销", command=self.undo,
                  bg='#0f3460', fg='white', font=('Arial', 10), pady=5,
                  relief=tk.FLAT).pack(fill=tk.X, padx=10, pady=2)
        tk.Button(left_toolbar, text="🔄 重做", command=self.redo,
                  bg='#0f3460', fg='white', font=('Arial', 10), pady=5,
                  relief=tk.FLAT).pack(fill=tk.X, padx=10, pady=2)
        tk.Button(left_toolbar, text="🗑️ 删除", command=self.delete_selected,
                  bg='#e74c3c', fg='white', font=('Arial', 10), pady=5,
                  relief=tk.FLAT).pack(fill=tk.X, padx=10, pady=2)

        # 排列操作
        tk.Frame(left_toolbar, height=2, bg='#0f3460').pack(fill=tk.X, pady=10)
        tk.Label(left_toolbar, text="排列", bg='#0f3460', fg='white', font=('Arial', 10, 'bold'), pady=5).pack(
            fill=tk.X)

        tk.Button(left_toolbar, text="⬆️ 置于顶层", command=self.bring_to_front,
                  bg='#0f3460', fg='white', font=('Arial', 10), pady=5,
                  relief=tk.FLAT).pack(fill=tk.X, padx=10, pady=2)
        tk.Button(left_toolbar, text="⬇️ 置于底层", command=self.send_to_back,
                  bg='#0f3460', fg='white', font=('Arial', 10), pady=5,
                  relief=tk.FLAT).pack(fill=tk.X, padx=10, pady=2)

        # 视图控制
        tk.Frame(left_toolbar, height=2, bg='#0f3460').pack(fill=tk.X, pady=10)
        tk.Label(left_toolbar, text="视图", bg='#0f3460', fg='white', font=('Arial', 10, 'bold'), pady=5).pack(
            fill=tk.X)

        tk.Button(left_toolbar, text="🔍 放大", command=self.zoom_in,
                  bg='#0f3460', fg='white', font=('Arial', 10), pady=5,
                  relief=tk.FLAT).pack(fill=tk.X, padx=10, pady=2)
        tk.Button(left_toolbar, text="🔍 缩小", command=self.zoom_out,
                  bg='#0f3460', fg='white', font=('Arial', 10), pady=5,
                  relief=tk.FLAT).pack(fill=tk.X, padx=10, pady=2)
        tk.Button(left_toolbar, text="🖼️ 适应窗口", command=self.fit_to_window,
                  bg='#0f3460', fg='white', font=('Arial', 10), pady=5,
                  relief=tk.FLAT).pack(fill=tk.X, padx=10, pady=2)

        # 网格控制
        self.grid_var = tk.BooleanVar(value=True)
        tk.Checkbutton(left_toolbar, text="显示网格", variable=self.grid_var, command=self.toggle_grid,
                       bg='#16213e', fg='white', selectcolor='#16213e', font=('Arial', 10)).pack(pady=5)

        self.snap_var = tk.BooleanVar(value=False)
        tk.Checkbutton(left_toolbar, text="吸附网格", variable=self.snap_var, command=self.toggle_snap,
                       bg='#16213e', fg='white', selectcolor='#16213e', font=('Arial', 10)).pack(pady=5)

        # 右侧属性面板
        right_panel = tk.Frame(main_container, bg='#16213e', width=250)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=0, pady=0)
        right_panel.pack_propagate(False)

        # 颜色设置
        color_frame = tk.LabelFrame(right_panel, text="颜色设置", bg='#16213e', fg='white', font=('Arial', 10, 'bold'))
        color_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(color_frame, text="边框颜色:", bg='#16213e', fg='white').pack(anchor=tk.W, padx=10, pady=5)
        self.color_btn = tk.Button(color_frame, bg=self.current_color, width=20, height=2,
                                   command=self.choose_color)
        self.color_btn.pack(padx=10, pady=5)

        self.use_fill_var = tk.BooleanVar(value=False)
        tk.Checkbutton(color_frame, text="使用填充", variable=self.use_fill_var, command=self.toggle_fill,
                       bg='#16213e', fg='white', selectcolor='#16213e').pack(anchor=tk.W, padx=10, pady=5)

        tk.Label(color_frame, text="填充颜色:", bg='#16213e', fg='white').pack(anchor=tk.W, padx=10, pady=5)
        self.fill_btn = tk.Button(color_frame, bg='#FFFFFF', width=20, height=2,
                                  command=self.choose_fill_color, state=tk.DISABLED)
        self.fill_btn.pack(padx=10, pady=5)

        # 线宽设置
        tk.Label(color_frame, text="线宽:", bg='#16213e', fg='white').pack(anchor=tk.W, padx=10, pady=5)
        self.width_spin = tk.Spinbox(color_frame, from_=1, to=20, width=10,
                                     command=self.change_line_width)
        self.width_spin.delete(0, tk.END)
        self.width_spin.insert(0, str(self.line_width))
        self.width_spin.pack(padx=10, pady=5)

        # 文字设置
        text_frame = tk.LabelFrame(right_panel, text="文字设置", bg='#16213e', fg='white', font=('Arial', 10, 'bold'))
        text_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(text_frame, text="字体大小:", bg='#16213e', fg='white').pack(anchor=tk.W, padx=10, pady=5)
        self.font_spin = tk.Spinbox(text_frame, from_=8, to=72, width=10,
                                    command=self.change_font_size)
        self.font_spin.delete(0, tk.END)
        self.font_spin.insert(0, str(self.font_size))
        self.font_spin.pack(padx=10, pady=5)

        tk.Label(text_frame, text="文字内容:", bg='#16213e', fg='white').pack(anchor=tk.W, padx=10, pady=5)
        self.text_entry = tk.Entry(text_frame, width=20)
        self.text_entry.pack(padx=10, pady=5)
        tk.Button(text_frame, text="添加文字", command=self.add_text,
                  bg='#2ecc71', fg='white').pack(padx=10, pady=5)

        # 形状列表
        list_frame = tk.LabelFrame(right_panel, text="形状列表", bg='#16213e', fg='white', font=('Arial', 10, 'bold'))
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        list_container = tk.Frame(list_frame, bg='#16213e')
        list_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = tk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.shape_listbox = tk.Listbox(list_container, bg='#0f3460', fg='white',
                                        font=('Courier', 9), yscrollcommand=scrollbar.set)
        self.shape_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.shape_listbox.yview)

        self.shape_listbox.bind('<<ListboxSelect>>', self.on_shape_select)

        btn_frame = tk.Frame(list_frame, bg='#16213e')
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(btn_frame, text="删除", command=self.delete_selected,
                  bg='#e74c3c', fg='white').pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        tk.Button(btn_frame, text="清空", command=self.clear_all,
                  bg='#f39c12', fg='white').pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)

        # 中央画布区域
        canvas_container = tk.Frame(main_container, bg='#2c3e50')
        canvas_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 画布包装器
        canvas_wrapper = tk.Frame(canvas_container, bg='#95a5a6')
        canvas_wrapper.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 滚动条
        h_scroll = tk.Scrollbar(canvas_wrapper, orient=tk.HORIZONTAL)
        v_scroll = tk.Scrollbar(canvas_wrapper, orient=tk.VERTICAL)

        self.canvas_frame = tk.Canvas(canvas_wrapper, bg='#95a5a6',
                                      xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        h_scroll.config(command=self.canvas_frame.xview)
        v_scroll.config(command=self.canvas_frame.yview)

        self.canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 绘图画布
        self.drawing_canvas = tk.Canvas(self.canvas_frame, bg='white',
                                        width=self.canvas_width, height=self.canvas_height,
                                        highlightthickness=0)
        self.drawing_canvas.place(x=0, y=0)

        # 绑定事件
        self.drawing_canvas.bind('<Button-1>', self.on_mouse_down)
        self.drawing_canvas.bind('<B1-Motion>', self.on_mouse_move)
        self.drawing_canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.drawing_canvas.bind('<Control-Button-1>', self.on_drag_start)
        self.drawing_canvas.bind('<Control-B1-Motion>', self.on_drag_move)
        self.drawing_canvas.bind('<MouseWheel>', self.on_mousewheel)

        # 状态栏
        self.status_bar = tk.Label(self.root, text="就绪 | 工具: 选择 | 颜色: 红色",
                                   bg='#16213e', fg='#eee', anchor=tk.W, padx=10)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def draw_canvas(self):
        """绘制画布"""
        self.drawing_canvas.delete('all')

        # 绘制网格
        if self.show_grid:
            step = self.grid_size * self.scale
            offset_x = self.offset_x * self.scale % step
            offset_y = self.offset_y * self.scale % step

            for x in range(int(offset_x), self.canvas_width, int(step)):
                self.drawing_canvas.create_line(x, 0, x, self.canvas_height, fill='#E0E0E0', width=0.5)
            for y in range(int(offset_y), self.canvas_height, int(step)):
                self.drawing_canvas.create_line(0, y, self.canvas_width, y, fill='#E0E0E0', width=0.5)

        # 绘制所有形状
        for shape in self.shapes:
            shape.draw(self.drawing_canvas, self.offset_x, self.offset_y, self.scale)

        # 绘制临时形状
        if self.temp_shape:
            self.temp_shape.draw(self.drawing_canvas, self.offset_x, self.offset_y, self.scale)

        # 绘制多边形临时点
        if self.polygon_points and self.is_drawing_polygon:
            for x, y in self.polygon_points:
                sx = (x + self.offset_x) * self.scale
                sy = (y + self.offset_y) * self.scale
                self.drawing_canvas.create_oval(sx - 3, sy - 3, sx + 3, sy + 3, fill='blue')

        self.update_shape_list()

    def update_shape_list(self):
        """更新形状列表"""
        self.shape_listbox.delete(0, tk.END)
        for i, shape in enumerate(self.shapes):
            shape_type = shape.__class__.__name__.replace('Shape', '')
            if shape.selected:
                self.shape_listbox.insert(tk.END, f"▶ {i + 1}. {shape_type}")
                self.shape_listbox.selection_set(i)
            else:
                self.shape_listbox.insert(tk.END, f"  {i + 1}. {shape_type}")

    def on_shape_select(self, event):
        selection = self.shape_listbox.curselection()
        if selection:
            index = selection[0]
            if 0 <= index < len(self.shapes):
                self.select_shape(index)

    def select_shape(self, index):
        if self.selected_index >= 0 and self.selected_index < len(self.shapes):
            self.shapes[self.selected_index].selected = False
        self.selected_index = index
        self.selected_shape = self.shapes[index]
        self.selected_shape.selected = True
        self.draw_canvas()
        self.status_bar.config(text=f"已选择形状 {index + 1}")

    def set_tool(self, tool_id):
        self.current_tool = tool_id
        for tid, btn in self.tool_buttons.items():
            if tid == tool_id:
                btn.config(bg='#1a5a8a')
            else:
                btn.config(bg='#0f3460')
        self.cancel_drawing()
        self.status_bar.config(text=f"工具: {tool_id}")

    def choose_color(self):
        color = colorchooser.askcolor(title="选择边框颜色", initialcolor=self.current_color)
        if color:
            self.current_color = color[1]
            self.color_btn.config(bg=self.current_color)

    def choose_fill_color(self):
        color = colorchooser.askcolor(title="选择填充颜色", initialcolor=self.current_fill_color or '#FFFFFF')
        if color:
            self.current_fill_color = color[1]
            self.fill_btn.config(bg=self.current_fill_color)

    def toggle_fill(self):
        self.use_fill = self.use_fill_var.get()
        if self.use_fill:
            self.fill_btn.config(state=tk.NORMAL)
            if not self.current_fill_color:
                self.current_fill_color = '#FFFFFF'
                self.fill_btn.config(bg='#FFFFFF')
        else:
            self.fill_btn.config(state=tk.DISABLED)
            self.current_fill_color = None

    def change_line_width(self):
        try:
            self.line_width = int(self.width_spin.get())
        except:
            pass

    def change_font_size(self):
        try:
            self.font_size = int(self.font_spin.get())
        except:
            pass

    def add_text(self):
        text = self.text_entry.get().strip()
        if text:
            shape = TextShape(100, 100, text, self.font_size, self.current_color)
            self.shapes.append(shape)
            self.save_to_history()
            self.draw_canvas()
            self.status_bar.config(text=f"已添加文字: {text}")
            self.text_entry.delete(0, tk.END)

    def zoom_in(self):
        if self.scale < 5:
            self.scale *= 1.2
            self.draw_canvas()

    def zoom_out(self):
        if self.scale > 0.2:
            self.scale /= 1.2
            self.draw_canvas()

    def fit_to_window(self):
        self.scale = min(self.canvas_width / 800, self.canvas_height / 600)
        self.offset_x = 0
        self.offset_y = 0
        self.draw_canvas()

    def toggle_grid(self):
        self.show_grid = self.grid_var.get()
        self.draw_canvas()

    def toggle_snap(self):
        self.snap_to_grid = self.snap_var.get()

    def on_drag_start(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_drag_move(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        self.offset_x -= dx / self.scale
        self.offset_y -= dy / self.scale
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.draw_canvas()

    def on_mousewheel(self, event):
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def get_snapped_point(self, x, y):
        if self.snap_to_grid:
            x = round(x / self.grid_size) * self.grid_size
            y = round(y / self.grid_size) * self.grid_size
        return x, y

    def on_mouse_down(self, event):
        canvas_x = (event.x / self.scale) - self.offset_x
        canvas_y = (event.y / self.scale) - self.offset_y

        if self.current_tool == 'select':
            for i in range(len(self.shapes) - 1, -1, -1):
                if self.shapes[i].contains_point(canvas_x, canvas_y):
                    self.select_shape(i)
                    self.drag_shape_start = (canvas_x, canvas_y)
                    return
            if self.selected_shape:
                self.selected_shape.selected = False
                self.selected_shape = None
                self.selected_index = -1
                self.draw_canvas()
        elif self.current_tool == 'polygon':
            if not self.is_drawing_polygon:
                self.is_drawing_polygon = True
                self.polygon_points = [(canvas_x, canvas_y)]
            else:
                if len(self.polygon_points) > 2 and self.is_close_to_start(canvas_x, canvas_y):
                    self.finish_polygon()
                else:
                    self.polygon_points.append((canvas_x, canvas_y))
            self.draw_canvas()
        else:
            self.start_x, self.start_y = self.get_snapped_point(canvas_x, canvas_y)

    def is_close_to_start(self, x, y):
        if not self.polygon_points:
            return False
        start_x, start_y = self.polygon_points[0]
        distance = math.sqrt((x - start_x) ** 2 + (y - start_y) ** 2)
        return distance < 10

    def finish_polygon(self):
        if len(self.polygon_points) >= 3:
            shape = PolygonShape(self.polygon_points, self.current_color,
                                 self.line_width, self.current_fill_color if self.use_fill else None)
            self.shapes.append(shape)
            self.save_to_history()
        self.cancel_drawing()
        self.draw_canvas()

    def cancel_drawing(self):
        self.is_drawing_polygon = False
        self.polygon_points = []
        self.start_x = None
        self.start_y = None
        self.temp_shape = None

    def on_mouse_move(self, event):
        canvas_x = (event.x / self.scale) - self.offset_x
        canvas_y = (event.y / self.scale) - self.offset_y

        if self.current_tool == 'select' and self.selected_shape and hasattr(self, 'drag_shape_start'):
            dx = canvas_x - self.drag_shape_start[0]
            dy = canvas_y - self.drag_shape_start[1]
            self.selected_shape.move(dx, dy)
            self.drag_shape_start = (canvas_x, canvas_y)
            self.draw_canvas()
        elif self.start_x is not None and self.current_tool != 'select' and self.current_tool != 'polygon':
            snap_x, snap_y = self.get_snapped_point(canvas_x, canvas_y)

            if self.current_tool == 'rect':
                self.temp_shape = RectangleShape(
                    min(self.start_x, snap_x), min(self.start_y, snap_y),
                    abs(snap_x - self.start_x), abs(snap_y - self.start_y),
                    self.current_color, self.line_width,
                    self.current_fill_color if self.use_fill else None
                )
            elif self.current_tool == 'circle':
                radius = math.sqrt((snap_x - self.start_x) ** 2 + (snap_y - self.start_y) ** 2)
                self.temp_shape = CircleShape(
                    self.start_x, self.start_y, radius,
                    self.current_color, self.line_width,
                    self.current_fill_color if self.use_fill else None
                )
            elif self.current_tool == 'ellipse':
                rx = abs(snap_x - self.start_x)
                ry = abs(snap_y - self.start_y)
                cx = self.start_x + (snap_x - self.start_x) / 2
                cy = self.start_y + (snap_y - self.start_y) / 2
                self.temp_shape = EllipseShape(
                    cx, cy, rx, ry,
                    self.current_color, self.line_width,
                    self.current_fill_color if self.use_fill else None
                )
            elif self.current_tool == 'line':
                self.temp_shape = LineShape(
                    self.start_x, self.start_y, snap_x, snap_y,
                    self.current_color, self.line_width
                )
            self.draw_canvas()

    def on_mouse_up(self, event):
        if self.start_x is not None and self.current_tool not in ['select', 'polygon']:
            canvas_x = (event.x / self.scale) - self.offset_x
            canvas_y = (event.y / self.scale) - self.offset_y
            snap_x, snap_y = self.get_snapped_point(canvas_x, canvas_y)

            shape = None
            if self.current_tool == 'rect':
                shape = RectangleShape(
                    min(self.start_x, snap_x), min(self.start_y, snap_y),
                    abs(snap_x - self.start_x), abs(snap_y - self.start_y),
                    self.current_color, self.line_width,
                    self.current_fill_color if self.use_fill else None
                )
            elif self.current_tool == 'circle':
                radius = math.sqrt((snap_x - self.start_x) ** 2 + (snap_y - self.start_y) ** 2)
                shape = CircleShape(
                    self.start_x, self.start_y, radius,
                    self.current_color, self.line_width,
                    self.current_fill_color if self.use_fill else None
                )
            elif self.current_tool == 'ellipse':
                rx = abs(snap_x - self.start_x)
                ry = abs(snap_y - self.start_y)
                cx = self.start_x + (snap_x - self.start_x) / 2
                cy = self.start_y + (snap_y - self.start_y) / 2
                shape = EllipseShape(
                    cx, cy, rx, ry,
                    self.current_color, self.line_width,
                    self.current_fill_color if self.use_fill else None
                )
            elif self.current_tool == 'line':
                shape = LineShape(
                    self.start_x, self.start_y, snap_x, snap_y,
                    self.current_color, self.line_width
                )

            if shape:
                self.shapes.append(shape)
                self.save_to_history()

            self.start_x = None
            self.start_y = None
            self.temp_shape = None
            self.draw_canvas()

    def delete_selected(self):
        if self.selected_index >= 0 and self.selected_index < len(self.shapes):
            self.shapes.pop(self.selected_index)
            self.selected_shape = None
            self.selected_index = -1
            self.save_to_history()
            self.draw_canvas()
            self.status_bar.config(text="已删除选中形状")

    def clear_all(self):
        if messagebox.askyesno("确认", "确定要清空所有形状吗？"):
            self.shapes = []
            self.selected_shape = None
            self.selected_index = -1
            self.save_to_history()
            self.draw_canvas()
            self.status_bar.config(text="已清空所有形状")

    def bring_to_front(self):
        if self.selected_index >= 0:
            shape = self.shapes.pop(self.selected_index)
            self.shapes.append(shape)
            self.selected_index = len(self.shapes) - 1
            self.save_to_history()
            self.draw_canvas()

    def send_to_back(self):
        if self.selected_index >= 0:
            shape = self.shapes.pop(self.selected_index)
            self.shapes.insert(0, shape)
            self.selected_index = 0
            self.save_to_history()
            self.draw_canvas()

    def copy_selected(self):
        if self.selected_shape:
            self.clipboard = copy.deepcopy(self.selected_shape)
            self.status_bar.config(text="已复制")

    def paste(self):
        if self.clipboard:
            new_shape = copy.deepcopy(self.clipboard)
            new_shape.move(20, 20)
            self.shapes.append(new_shape)
            self.select_shape(len(self.shapes) - 1)
            self.save_to_history()
            self.draw_canvas()
            self.status_bar.config(text="已粘贴")

    def select_all(self):
        for shape in self.shapes:
            shape.selected = True
        if self.shapes:
            self.selected_shape = self.shapes[-1]
            self.selected_index = len(self.shapes) - 1
        self.draw_canvas()

    def save_to_history(self):
        self.history = self.history[:self.history_index + 1]
        self.history.append(copy.deepcopy(self.shapes))
        if len(self.history) > 100:
            self.history.pop(0)
        self.history_index = len(self.history) - 1

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.shapes = copy.deepcopy(self.history[self.history_index])
            self.selected_shape = None
            self.selected_index = -1
            self.draw_canvas()
            self.status_bar.config(text="已撤销")

    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.shapes = copy.deepcopy(self.history[self.history_index])
            self.selected_shape = None
            self.selected_index = -1
            self.draw_canvas()
            self.status_bar.config(text="已重做")

    def new_file(self):
        if messagebox.askyesno("新建", "确定要新建文件吗？未保存的内容将丢失。"):
            self.shapes = []
            self.selected_shape = None
            self.selected_index = -1
            self.save_to_history()
            self.draw_canvas()

    def save_file(self):
        filename = filedialog.asksaveasfilename(defaultextension=".vector",
                                                filetypes=[("矢量图文件", "*.vector")])
        if filename:
            data = {
                'shapes': [shape.to_dict() for shape in self.shapes],
                'canvas_width': self.canvas_width,
                'canvas_height': self.canvas_height
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("成功", f"已保存到 {filename}")

    def open_file(self):
        filename = filedialog.askopenfilename(filetypes=[("矢量图文件", "*.vector")])
        if filename:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.shapes = []
            for shape_data in data['shapes']:
                shape = self.shape_from_dict(shape_data)
                if shape:
                    self.shapes.append(shape)

            self.selected_shape = None
            self.selected_index = -1
            self.save_to_history()
            self.draw_canvas()
            messagebox.showinfo("成功", f"已打开 {filename}")

    def shape_from_dict(self, data):
        if data['type'] == 'RectangleShape':
            return RectangleShape(
                data['x'], data['y'], data['width'], data['height'],
                data['color'], data.get('line_width', 2), data.get('fill_color')
            )
        elif data['type'] == 'CircleShape':
            return CircleShape(
                data['x'], data['y'], data['radius'],
                data['color'], data.get('line_width', 2), data.get('fill_color')
            )
        elif data['type'] == 'EllipseShape':
            return EllipseShape(
                data['x'], data['y'], data['rx'], data['ry'],
                data['color'], data.get('line_width', 2), data.get('fill_color')
            )
        elif data['type'] == 'LineShape':
            return LineShape(
                data['x1'], data['y1'], data['x2'], data['y2'],
                data['color'], data.get('line_width', 2)
            )
        elif data['type'] == 'PolygonShape':
            return PolygonShape(
                data['points'], data['color'],
                data.get('line_width', 2), data.get('fill_color')
            )
        elif data['type'] == 'TextShape':
            return TextShape(
                data['x'], data['y'], data['text'],
                data.get('font_size', 12), data['color']
            )
        return None

    def import_image(self):
        """导入图片"""
        filename = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[
                ("所有图片文件", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp"),
                ("PNG图片", "*.png"),
                ("JPEG图片", "*.jpg *.jpeg"),
                ("BMP图片", "*.bmp"),
                ("GIF图片", "*.gif"),
                ("所有文件", "*.*")
            ]
        )
        if not filename:
            return

        try:
            img = Image.open(filename)

            if img.mode != 'RGB':
                img = img.convert('RGB')

            # 缩放图片
            max_size = 400
            if img.width > max_size or img.height > max_size:
                ratio = min(max_size / img.width, max_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # 创建位图形状
            class BitmapShape:
                def __init__(self, x, y, image):
                    self.x = x
                    self.y = y
                    self.image = image
                    self.selected = False
                    self.width = image.width
                    self.height = image.height
                    self.photo = None

                def draw(self, canvas, offset_x=0, offset_y=0, scale=1):
                    sx = (self.x + offset_x) * scale
                    sy = (self.y + offset_y) * scale
                    sw = self.width * scale
                    sh = self.height * scale

                    scaled_img = self.image.resize((int(sw), int(sh)), Image.Resampling.LANCZOS)
                    self.photo = ImageTk.PhotoImage(scaled_img)
                    canvas.create_image(sx, sy, anchor='nw', image=self.photo)

                    if self.selected:
                        canvas.create_rectangle(sx, sy, sx + sw, sy + sh, outline='red', width=2)

                def contains_point(self, px, py):
                    return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height

                def move(self, dx, dy):
                    self.x += dx
                    self.y += dy

            bitmap = BitmapShape(
                (self.canvas_width - img.width) // 2,
                (self.canvas_height - img.height) // 2,
                img
            )
            self.shapes.append(bitmap)
            self.save_to_history()
            self.draw_canvas()
            self.status_bar.config(text=f"✅ 已导入图片: {os.path.basename(filename)}")

        except Exception as e:
            messagebox.showerror("错误", f"导入图片失败: {str(e)}")

    def export_image_formats(self):
        """导出图片"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG图片", "*.png"),
                ("JPEG图片", "*.jpg"),
                ("BMP图片", "*.bmp"),
                ("GIF图片", "*.gif"),
                ("TIFF图片", "*.tiff"),
                ("WEBP图片", "*.webp")
            ]
        )
        if not filename:
            return

        try:
            width = self.canvas_width * 2
            height = self.canvas_height * 2
            img = Image.new('RGB', (width, height), 'white')
            draw = ImageDraw.Draw(img)

            for shape in self.shapes:
                self.draw_shape_to_pil(draw, shape, width, height)

            ext = os.path.splitext(filename)[1].lower()
            if ext == '.jpg' or ext == '.jpeg':
                img.save(filename, 'JPEG', quality=95)
            elif ext == '.gif':
                img.save(filename, 'GIF')
            elif ext == '.bmp':
                img.save(filename, 'BMP')
            elif ext == '.tiff':
                img.save(filename, 'TIFF')
            elif ext == '.webp':
                img.save(filename, 'WEBP', quality=90)
            else:
                img.save(filename, 'PNG')

            messagebox.showinfo("成功", f"图片已保存到 {filename}")

        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")

    def draw_shape_to_pil(self, draw, shape, width, height):
        """绘制形状到PIL图像"""
        scale_x = width / self.canvas_width
        scale_y = height / self.canvas_height

        if isinstance(shape, RectangleShape):
            x1 = shape.x * scale_x
            y1 = shape.y * scale_y
            x2 = (shape.x + shape.width) * scale_x
            y2 = (shape.y + shape.height) * scale_y
            if shape.fill_color:
                draw.rectangle([x1, y1, x2, y2], fill=shape.fill_color, outline=shape.color,
                               width=int(shape.line_width * scale_x))
            else:
                draw.rectangle([x1, y1, x2, y2], outline=shape.color, width=int(shape.line_width * scale_x))
        elif isinstance(shape, CircleShape):
            bbox = [
                (shape.x - shape.radius) * scale_x,
                (shape.y - shape.radius) * scale_y,
                (shape.x + shape.radius) * scale_x,
                (shape.y + shape.radius) * scale_y
            ]
            if shape.fill_color:
                draw.ellipse(bbox, fill=shape.fill_color, outline=shape.color, width=int(shape.line_width * scale_x))
            else:
                draw.ellipse(bbox, outline=shape.color, width=int(shape.line_width * scale_x))
        elif isinstance(shape, EllipseShape):
            bbox = [
                (shape.x - shape.rx) * scale_x,
                (shape.y - shape.ry) * scale_y,
                (shape.x + shape.rx) * scale_x,
                (shape.y + shape.ry) * scale_y
            ]
            if shape.fill_color:
                draw.ellipse(bbox, fill=shape.fill_color, outline=shape.color, width=int(shape.line_width * scale_x))
            else:
                draw.ellipse(bbox, outline=shape.color, width=int(shape.line_width * scale_x))
        elif isinstance(shape, LineShape):
            draw.line([
                shape.x1 * scale_x, shape.y1 * scale_y,
                shape.x2 * scale_x, shape.y2 * scale_y
            ], fill=shape.color, width=int(shape.line_width * scale_x))
        elif isinstance(shape, PolygonShape):
            points = []
            for x, y in shape.points:
                points.extend([x * scale_x, y * scale_y])
            if shape.fill_color:
                draw.polygon(points, fill=shape.fill_color, outline=shape.color, width=int(shape.line_width * scale_x))
            else:
                draw.polygon(points, outline=shape.color, width=int(shape.line_width * scale_x))
        elif isinstance(shape, TextShape):
            from PIL import ImageFont
            try:
                font = ImageFont.truetype("arial.ttf", int(shape.font_size * scale_x))
            except:
                font = ImageFont.load_default()
            draw.text((shape.x * scale_x, shape.y * scale_y), shape.text, fill=shape.color, font=font)
        elif hasattr(shape, 'image'):
            img = shape.image
            new_size = (int(img.width * scale_x), int(img.height * scale_y))
            if new_size[0] > 0 and new_size[1] > 0:
                scaled_img = img.resize(new_size, Image.Resampling.LANCZOS)
                img.paste(scaled_img, (int(shape.x * scale_x), int(shape.y * scale_y)))

    def load_demo(self):
        """加载示例"""
        self.shapes = [
            RectangleShape(100, 100, 150, 100, '#FF0000', 3, '#FFCCCC'),
            CircleShape(400, 200, 60, '#00FF00', 3, '#CCFFCC'),
            EllipseShape(650, 250, 80, 50, '#0000FF', 3, '#CCCCFF'),
            LineShape(100, 400, 500, 400, '#FF8800', 3),
            PolygonShape([(200, 500), (300, 450), (400, 500), (350, 580), (250, 580)],
                         '#8800FF', 3, '#FFCCFF'),
            TextShape(500, 600, "矢量图编辑器", 20, '#333333')
        ]
        self.save_to_history()
        self.draw_canvas()
        self.status_bar.config(text="已加载示例图形")


if __name__ == "__main__":
    root = tk.Tk()
    app = VectorEditor(root)
    root.mainloop()