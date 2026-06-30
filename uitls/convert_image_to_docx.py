import os
from docx.shared import Mm
from jinja2 import Environment
from pathlib import Path


from docxtpl import DocxTemplate, InlineImage
IMAGE_SIZE = 150

class UserSSImages:
    def __init__(self, name: str):
        self.name = name
        self.images = []
        self.ssImages = []

    def add(self, v):
        self.images.append(v)


def enum_all_user_snapshot_images(user: UserSSImages, source_dir: str = "./", suffix=".png"):
    # 转换为Path对象，方便路径操作
    dir_path = Path(source_dir)
    # 筛选目录下所有PNG文件（不区分大小写，如.png/.PNG）
    png_files = [
        file
        for file in dir_path.iterdir()
        if file.is_file() and file.suffix.lower() == suffix
    ]

    # 按文件名排序（确保ID顺序固定）
    png_files.sort(key=lambda x: x.name)

    user_images = {}

    # 遍历文件并添加ID重命名
    for idx, file in enumerate(png_files, start=1):  # ID从1开始递增
        full_name = os.path.join(source_dir, file.name)
        user.add(full_name)
        # # cert_name = tp[0:-1]
    return user_images





def pre_process_user_image_obj(tpl, user):

    for u in user.images:
        image = InlineImage(tpl, u, width=Mm(IMAGE_SIZE))
        user.ssImages.append(image)


def enum_all_users(source_dir: str = "./"):
    # 转换为Path对象，方便路径操作
    dir_path = Path(source_dir)
    # 筛选目录下所有PNG文件（不区分大小写，如.png/.PNG）
    user_dirs = [file.name for file in dir_path.iterdir() if file.is_dir()]
    return user_dirs



"""
    将输入的 用户列表，转换为 WORD 
"""
def convert_user_ss_snapshot_images_to_docx(users, output_image_root, template_path, output_docx_file=""):

    all_users = []

    docx = DocxTemplate(template_path)

    for user in users:
        u = UserSSImages(user)
        all_users.append(u)

        user_image_base = os.path.join(output_image_root, u.name)
        enum_all_user_snapshot_images(u, user_image_base)
        pre_process_user_image_obj(docx, u)
    obj = {"users": all_users}

    jinja_env = Environment()
    # jinja_env.globals['user_project_exp'] = user_project_exp

    # 获取要插入到文档中的数据
    # 渲染文档
    docx.render(obj, jinja_env)
    # 保存生成的文档


    dest_file = Path(output_docx_file)
    file_name = dest_file.stem
    base_path = dest_file.parent
    counter = 1
    while dest_file.exists():
        dest_file = dest_file.parent / f"{file_name}_{counter}{dest_file.suffix}"
        counter += 1

    print("save docx : {dest_file}".format(dest_file=dest_file))
    docx.save(dest_file)


# if __name__ == "__main__":
#     OUTPUT_DIR = "screenshots"
#     names = ["白首骏", "安京玲", "倪永哲", "晋林涛"]
#
#     names = enum_all_users(OUTPUT_DIR)
#
#     output_file = "./output-user-ss-images.docx"
#     template_file_name = "./data/user_ss_template.docx"
#     read_user_ss_images_to_docx(
#         names, OUTPUT_DIR, template_path=template_file_name, output_file=output_file
#     )
