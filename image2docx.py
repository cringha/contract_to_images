import shutil
import traceback
from pathlib import Path
from typing import List, Dict, Any
import json
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage
from jinja2 import Environment

from uitls.excel_utils import read_excel_sheet_values
from uitls.jsonencoder import to_json_str, load_json_file
from uitls.pdf_utils import snap_pdf_all_page
from uitls.utils import get_dict_val

IMAGE_SIZE = 150

ACCEPT_SUFFIX= [".jpg",".jpeg",".png"]

"""
    将输入的 用户列表，转换为 WORD 
"""

class SnapshotInline:
    def __init__(self, image:Path ):
        self.image_path = image
        self.inline_image = None



# 在 合同的子目录中，找到所以的正式文件
def get_images_file_in_path(image_base_path: Path, accept_suffix) -> Dict[str, SnapshotInline]:

    if not image_base_path.exists():
        return None
    all_file = [f for f in image_base_path.iterdir() if f.is_file()]
    files = {}
    for f in all_file:
        file_suffix = f.suffix.lower()
        if file_suffix not in accept_suffix:
            print(f"warn: get image not accept suffix, {f.name} , {accept_suffix}")
            continue
        files[f.name] = SnapshotInline(f)
    return files

def pre_process_snap_file(tpl, image_files : Dict[str, SnapshotInline]):
    if image_files is None:
        return []
    if len(image_files) == 0:
        return []
    output ={}

    for key, snap_img in image_files.items():
        snap_img.inline_image = None
        vv = str( snap_img.image_path)
        snap_img.inline_image = InlineImage(tpl, vv, width=Mm(IMAGE_SIZE))
        output[key] = snap_img
    return output





def load_inline_image( inline_images, img_file ):
    if inline_images is None or img_file is None:
        return None

    if img_file =="":
        return None
    #
    #
    #
    # inlines = get_dict_val(inline_images, "inlines")
    # if inlines is None:
    #     return None


    if img_file in inline_images:
        fz = inline_images[img_file]
        return fz.inline_image
    else:
        print("warn: get inline image file empty ", img_file)
        return None




def convert_project_snapshot_images_to_docx(project_snapshots: Dict[str,Any] ,
                                            image_base_path: Path,
                                            template_path,
                                            output_docx_file=""):
    all_users = []

    image_file_list = get_images_file_in_path( image_base_path, ACCEPT_SUFFIX )

    docx = DocxTemplate(template_path)


    inline_images = pre_process_snap_file( docx, image_file_list )

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

    print("save docx : {dest_file}".format(dest_file=dest_file))
    docx.save(dest_file)






def main():
    # if args.input_xlsx is None or args.input_xlsx == "":
    #     print("--input-xlsx 空")
    #
    #     return False
    #
    # if args.pdf_root is None or args.pdf_root == "":
    #     print("--pdf-root 空")
    #     return False

    # excel_file_name = r"C:\Users\101202304023\Desktop\工作\投标项目\2026-2028年中国联通软研院安全准入与渗透测试安全服务(LK)\案例\2023-2026年合同汇总-恒安嘉新.xlsx"
    excel_file_name = "test.input.xlsx"
    # contract_base_root = r"C:\Users\101202304023\Desktop\工作\投标项目\2026-2028年中国联通软研院安全准入与渗透测试安全服务(LK)\案例\20260629合同下载"
    contract_base_root = r".\test.data1"
    # output_image_dir = r"C:\Users\101202304023\Desktop\工作\投标项目\2026-2028年中国联通软研院安全准入与渗透测试安全服务(LK)\案例\images"
    output_images_dir = "./test.images"

    json_path = "local.project.json"

    project_snapshots = load_json_file(json_path)

    docx_template_file = "./template1.docx"
    output_docx_file = "./my-output.docx"
    if project_snapshots is None:
        return


    image_base_path = Path(output_images_dir)

    convert_project_snapshot_images_to_docx( project_snapshots , image_base_path , docx_template_file , output_docx_file )

    #
    # convert_user_ss_snapshot_images_to_docx(project_contract_obj_list, docx_template_file, output_docx_file)

    # if args.convert:
    #     convert_user_ss_snapshot_images_to_docx(user_list, args.snapshot_images, args.docx_template_file,
    #                                             args.output_docx_file)
    return True


if __name__ == "__main__":

    #
    # parser = argparse.ArgumentParser(description="社保PDF转用户截图工具")
    # parser.add_argument("-i", "--input-xlsx", help="输入Xlsx文件")
    # parser.add_argument("-p", "--pdf-root", help="输入PDF文件根目录")
    # parser.add_argument("-s", "--snapshot-images", help="输出截图文件根目录; default: %(default)s", default="./output")
    # parser.add_argument("--sheet-name-user", help="User sheet name; default: %(default)s", default="Users")
    # parser.add_argument("--sheet-name-file", help="File sheet name; default: %(default)s", default="Files")
    # parser.add_argument("--col-user-name", help="user column name in `User sheet`; default: %(default)s",
    #                     default="Name")
    # parser.add_argument("--col-city-name", help="city column name in `User sheet and File sheet`; default: %(default)s",
    #                     default="City")
    # parser.add_argument("--col-file-name", help="file column name in `File sheet`; default: %(default)s",
    #                     default="File")
    #
    # parser.add_argument("-c", "--convert", action="store_true", help="将截图转换为DOCX文档")
    # parser.add_argument("-t", "--docx-template-file", help="docx template filename; default: %(default)s",
    #                     default="./data/user_ss_template.docx")
    # parser.add_argument("-o", "--output-docx-file", help="输出docx文件; default: %(default)s",
    #                     default="./user-ss-snapshot.docx")
    # # parser.add_argument("-h", "--help", help="打印参数信息")
    #
    # args = parser.parse_args()

    try:
        result = main()
        # if not result: args
        #     parser.print_help()
    except Exception as e:
        print("Exec main error ", e)
        traceback.print_exc()
