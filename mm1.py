import shutil
import traceback
from pathlib import Path
from typing import List
import json
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage
from jinja2 import Environment

from uitls.excel_utils import read_excel_sheet_values
from uitls.pdf_utils import snap_pdf_all_page

IMAGE_SIZE = 150


def get_last_by_filename_glob(directory, pattern="*"):
    dir_path = Path(directory)
    # 获取所有匹配的文件（排除子目录）
    files = [f for f in dir_path.glob(pattern)]

    if not files:
        print("未找到匹配的文件")
        return None

    # 按文件名（字符串）升序排序，取最后一个
    files_sorted = sorted(files, key=lambda f: f.name)
    return files_sorted


def read_all_contract_subpath(contract_base_path: Path) -> List[
    str]:
    # 获取所有匹配的文件（排除子目录）
    # files = [f for f in contract_base_path.glob(pattern)]
    all_path = [f for f in contract_base_path.iterdir() if f.is_dir()]

    if not all_path:
        print(f"未找到 {contract_base_path} 下的二級目錄")
        return []

    out = []
    for one in all_path:
        out.append(one.name)

    return out


class SnapshotAndInlineImage:
    def __init__(self, image_file: Path):
        self.snapshot = image_file
        self.inline_image = None


# OutputContractFile
class ContractSnapshotFile:
    def __init__(self, title : str ):
        self.title = str
        self.image_file_list: List[str] = []

    def add_image_file(self, image_file: str):
        self.image_file_list.append(SnapshotAndInlineImage(image_file))

    def add_all_images(self, image_file_list: List[Path]):
        for image_file in image_file_list:
            self.image_file_list.append(SnapshotAndInlineImage(image_file))


# class ContractSnapshot:
#     def __init__(self, main_file: Path):
#         self.main_contract_snapshot = []
#         self.order_snapshots = []


class ContractObj:
    def __init__(self, contract_id: str):
        self.contract_id = contract_id
        self.orders = []

        self.main_file: List[ContractSnapshotFile] = []
        self.order_files: List[List[ContractSnapshotFile]] = []

    def add_order(self, order):
        self.orders.append(order)

    def reorder(self):
        self.orders.sort()

    def set_main_file(self, main_file: List[ContractSnapshotFile]):
        self.main_file = main_file

    def set_order_files(self, order_files: List[List[ContractSnapshotFile]]):
        self.order_files = order_files


'''
根据摄入的合同编号，找到合同及其订单
'''


def find_contract_and_orders(all_path: List[str], contract_id: str) -> None | ContractObj:
    one = ContractObj(contract_id)
    find = False
    for path in all_path:
        if contract_id == path:
            find = True
        else:
            if path.startswith(contract_id):
                one.add_order(path)

    if find:

        one.reorder()
        return one
    else:
        return None


IGNORE_NAMES = ["核定表", "登记证明"]


def ignore_files(filename: str):
    for ignore in IGNORE_NAMES:
        if ignore in filename:
            return True
    return False


# 在 合同的子目录中，找到所以的正式文件
def get_contract_file_in_path(contract_base_path: Path):
    # contract_sub_path = contract_base_path / subpath
    if not contract_base_path.exists():
        return None
    all_file = [f for f in contract_base_path.iterdir() if f.is_file()]
    files = []
    for f in all_file:
        filename = f.stem
        if ignore_files(filename):
            continue
        files.append(f)
    return files


def dump_contract_file(output_image_path: Path, prefix: str, file: Path,
                       contract_id: str) -> ContractSnapshotFile:
    suffix = file.suffix.lower()

    out = ContractSnapshotFile(file)

    if suffix == ".pdf":
        # page_num, doc.page_count, pdf_filename)
        def gen_contract_image_file_name(page_num: int, page_count: int, pdf_filename: str):
            # image_name = f"{contract_id}-合同截图-{prefix}-{file.stem}-{page_num:02}.jpg"
            image_name = f"{contract_id}-合同截图-{prefix}-{page_num:03}.jpg"
            image_full_name = output_image_path / image_name
            return str(image_full_name)

        file_list = snap_pdf_all_page(file, contract_id, gen_contract_image_file_name, 30)
        out.add_all_images(file_list)
    else:
        image_name = f"{contract_id}-合同截图-{prefix}-000{suffix}"
        image_full_name = output_image_path / image_name

        try:
            shutil.copy2(file, image_full_name)
            print(f"已复制：{contract_id} ,  {str(image_full_name)[-30:]}")
            out.add_image_file(image_full_name)
        except Exception as e:
            print(f"复制失败 {file}  {image_full_name}: {e}")

    return out


def process_contract_simple_path(contract_base_path: Path, output_image_path: Path,
                                 target_contract_id: str,
                                 contract_id: str, contract_type: str) -> List[ContractSnapshotFile]:
    contract_snapshot_file_list = []
    contract_parent_path = contract_base_path / contract_id
    if not contract_parent_path.exists():
        print(f"Contract path not exist , {contract_parent_path}")
        return contract_snapshot_file_list
    contract_files = get_contract_file_in_path(contract_parent_path)
    if contract_files is None:
        print(f"Not found contract file in path : {contract_parent_path}")
        return contract_snapshot_file_list

    target_contract_parent_path = output_image_path / target_contract_id
    if not target_contract_parent_path.exists():
        target_contract_parent_path.mkdir(parents=True)

    index = 0

    for file in contract_files:
        index = index + 1
        contract_snapshot_file = dump_contract_file(target_contract_parent_path, f"{contract_type}-{index:02}", file,
                                                    target_contract_id)
        contract_snapshot_file_list.append(contract_snapshot_file)

    return contract_snapshot_file_list


def process_contract_obj(contract_base_path: Path, output_image_path: Path, contract: ContractObj):
    # snap_pdf_all_page

    main_file_list = process_contract_simple_path(contract_base_path, output_image_path,
                                                  contract.contract_id,
                                                  contract.contract_id,
                                                  "MAIN")

    contract.set_main_file(main_file_list)
    order_snapshot_files: List[List[ContractSnapshotFile]] = []
    index = 1
    for order_file in contract.orders:
        order_snapshot_file = process_contract_simple_path(contract_base_path, output_image_path,
                                                           contract.contract_id,
                                                           order_file,
                                                           f"ORDER-{index}")
        if order_snapshot_file is not None and len(order_snapshot_file) > 0:
            order_snapshot_files.append(order_snapshot_file)
        index += 1

    contract.set_order_files(order_snapshot_files)


def read_contracts_cases(
        contract_base_root,
        output_image_dir,
        excel_file_name,
        contract_sheet_name="Contract",
        col_contract_id="项目编号", col_contract_name="合同名称",
        col_file_name="File"
) -> List[ContractObj] | None:
    contract_base_path = Path(contract_base_root)
    if not contract_base_path.exists():
        print(f"Base contract path, not exist , {contract_base_root}")
        return None

    output_image_path = Path(output_image_dir)
    if not output_image_path.exists():
        output_image_path.mkdir(parents=True)

    all_contract_paths = read_all_contract_subpath(contract_base_path)

    project_list = read_excel_sheet_values(excel_file_name, contract_sheet_name)
    project_contract_obj_list = []
    for project in project_list:
        contract_id = project[col_contract_id]
        project_contract_name = project[col_contract_name]
        if contract_id is None or contract_id == "":
            continue

        contract_id = str(contract_id)

        project_contract_obj = find_contract_and_orders(all_contract_paths, contract_id)
        if project_contract_obj is None:
            print(f"Not found contract id {contract_id} in root:{contract_base_path}")
            continue

        try:
            print(f"Process contract , {contract_id} - {project_contract_name}")
            process_contract_obj(contract_base_path, output_image_path, project_contract_obj)
            project_contract_obj_list.append(project_contract_obj)
        except Exception as e:
            print(f"Process contract, {contract_id} error:{e}")

    return project_contract_obj_list


"""
    将输入的 用户列表，转换为 WORD 
"""


def pre_process_snap_file(tpl, snap: ContractSnapshotFile):
    if snap is None:
        return
    if snap.image_file_list is None:
        return
    for pmf in snap.image_file_list:
        vv = str(pmf.snapshot)
        pmf.inline_image = InlineImage(tpl, vv, width=Mm(IMAGE_SIZE))


def pre_process_project_image_obj(tpl, project: ContractObj):
    if project.main_file is not None:
        for pmf in project.main_file:
            pre_process_snap_file(tpl, pmf)
    if project.order_files is not None:
        for ofs in project.order_files:
            for pmf in ofs:
                pre_process_snap_file(tpl, pmf)


def convert_user_ss_snapshot_images_to_docx(project_contract_obj_list: List[ContractObj],
                                            template_path,
                                            output_docx_file=""):
    all_users = []

    docx = DocxTemplate(template_path)

    for project in project_contract_obj_list:
        pre_process_project_image_obj(docx, project)

    obj = {"projects": project_contract_obj_list}

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


def dump_snapshot_files(files: List[ContractSnapshotFile]):
    if files is None:
        return []
    # self.main_pdf_file = main_pdf_file
    # self.title = main_pdf_file.stem
    # self.image_file_list: List[SnapshotAndInlineImage] = []
    output = []
    for pmf in files:
        out = {}
        out["main_contract"] = pmf.main_pdf_file.stem
        file_list = []
        for one in pmf.image_file_list:
            name = one.snapshot.name
            file_list.append(name)
        out["snapshots"] = file_list
        output.append(out)


def dump_project_contract_obj_list(project_contract_obj_list: List[ContractObj]):
    output = {}
    contracts = []
    for project in project_contract_obj_list:
        contract_id = project.contract_id
        # contract_name = project.contract_name

        main_file = dump_snapshot_files(project.main_file)
        order_files = []
        if project.order_files is not None:
            for ofs in project.order_files:
                order_f = dump_snapshot_files(ofs)
                order_files.append(order_f)
        output["contract_id"] =  contract_id
        output["main_file"] = main_file
        output["order_files"] = order_files
        contracts.append( output )
    output["contracts"] = contracts
    return output

def main():
    # if args.input_xlsx is None or args.input_xlsx == "":
    #     print("--input-xlsx 空")
    #
    #     return False
    #
    # if args.pdf_root is None or args.pdf_root == "":
    #     print("--pdf-root 空")
    #     return False

    excel_file_name = r"C:\Users\101202304023\Desktop\工作\投标项目\2026-2028年中国联通软研院安全准入与渗透测试安全服务(LK)\案例\2023-2026年合同汇总-恒安嘉新.xlsx"

    contract_base_root = r"C:\Users\101202304023\Desktop\工作\投标项目\2026-2028年中国联通软研院安全准入与渗透测试安全服务(LK)\案例\20260629合同下载"
    output_image_dir = r"C:\Users\101202304023\Desktop\工作\投标项目\2026-2028年中国联通软研院安全准入与渗透测试安全服务(LK)\案例\images"
    project_contract_obj_list = read_contracts_cases(contract_base_root,
                                                     output_image_dir,
                                                     excel_file_name
                                                     )
    docx_template_file = "./template1.docx"
    output_docx_file = "./my-output.docx"
    if project_contract_obj_list is None:
        return
    json_path = "local.project.json"
    dump_obj =  dump_project_contract_obj_list( project_contract_obj_list )
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dump_obj, f, ensure_ascii=False, indent=4)

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
