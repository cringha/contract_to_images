import argparse
import os
import traceback
from pathlib import Path
from typing import Dict, Any

from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage
from jinja2 import Environment
from uitls.log import get_log
from uitls.jsonencoder import load_json_file

IMAGE_SIZE = 150

ACCEPT_SUFFIX = [".jpg", ".jpeg", ".png"]

"""
    将输入的 用户列表，转换为 WORD 
"""


class SnapshotInline:
    def __init__(self, image: Path):
        self.image_path = image
        self.inline_image = None


# 在 合同的子目录中，找到所以的正式文件
def get_images_file_in_path(image_base_path: Path, accept_suffix) -> Dict[str, SnapshotInline] | None:
    if not image_base_path.exists():
        return None
    all_file = [f for f in image_base_path.iterdir() if f.is_file()]
    files = {}

    logger = get_log()

    for f in all_file:
        file_suffix = f.suffix.lower()
        if file_suffix not in accept_suffix:
            logger.warning (f"warn: get image not accept suffix, {f.name} , {accept_suffix}")
            continue
        files[f.name] = SnapshotInline(f)
    return files


def pre_process_snap_file(tpl, image_files: Dict[str, SnapshotInline]):
    if image_files is None:
        return []
    if len(image_files) == 0:
        return []
    output = {}

    logger = get_log()

    for key, snap_img in image_files.items():
        snap_img.inline_image = None
        vv = str(snap_img.image_path)
        snap_img.inline_image = InlineImage(tpl, vv, width=Mm(IMAGE_SIZE))
        output[key] = snap_img
        logger.info (f"proc inline , {key}")
    return output


def load_inline_image(inline_images, img_file):
    if inline_images is None or img_file is None:
        return None

    if img_file == "":
        return None
    #
    #
    #
    # inlines = get_dict_val(inline_images, "inlines")
    # if inlines is None:
    #     return None

    logger = get_log()

    if img_file in inline_images:
        fz = inline_images[img_file]
        return fz.inline_image
    else:
        logger.warning (f"warn: get inline image file empty {img_file} ")
        return None


def convert_project_snapshot_images_to_docx(project_snapshots: Dict[str, Any],
                                            image_base_path: Path,
                                            template_path,
                                            output_docx_file=""):
    all_users = []
    logger = get_log()
    image_file_list = get_images_file_in_path(image_base_path, ACCEPT_SUFFIX)
    if image_file_list is None:
        logger.error(f"get image empty in {image_base_path}, {ACCEPT_SUFFIX}")
        return False
    docx = DocxTemplate(template_path)

    inline_images = pre_process_snap_file(docx, image_file_list)

    # context = { 'inlines' : inline_images , 'projects': project_snapshots}
    project_snapshots['inline_images'] = inline_images

    jinja_env = Environment()
    jinja_env.globals['load_inline_image'] = load_inline_image

    # 获取要插入到文档中的数据
    # 渲染文档
    docx.render(project_snapshots, jinja_env)
    # 保存生成的文档

    dest_file = Path(output_docx_file)
    file_name = dest_file.stem
    base_path = dest_file.parent
    counter = 1
    while dest_file.exists():
        dest_file = dest_file.parent / f"{file_name}_{counter}{dest_file.suffix}"
        counter += 1


    logger.info ("save docx : {dest_file}".format(dest_file=dest_file))
    docx.save(dest_file)


def task_convert_docx(args):

    logger = get_log()

    if args.input_json is None or args.input_json == "":
        logger.error("--input-json 空")
        return False

    if not os.path.exists(args.input_json):
        logger.error(f"input json file not exist , {args.input_json}")
        return False

    if args.input_image_root is None or args.input_image_root == "":
        logger.error("--input-image-root 空")
        return False

    if not os.path.exists(args.input_image_root):
        logger.error(f"image path not exist , {args.input_image_root}")
        return False

    if args.docx_template_file is None or args.docx_template_file == "":
        logger.error(f"--docx-template-file 空")
        return False

    if not os.path.exists(args.docx_template_file):
        logger.error(f"template file not exist , {args.docx_template_file}")
        return False

    output_images_dir = args.input_image_root

    json_path = args.input_json

    docx_template_file = args.docx_template_file

    output_docx_file = args.output_docx_file

    project_snapshots = load_json_file(json_path)
    if project_snapshots is None:
        logger.error(f"Input json empty")
        return False

    image_base_path = Path(output_images_dir)

    convert_project_snapshot_images_to_docx(project_snapshots, image_base_path, docx_template_file, output_docx_file)

    return True
