import argparse
import json
import os.path
import shutil
import traceback
from pathlib import Path
from typing import List, Dict, Any

from uitls.excel_utils import read_excel_sheet_values, json_fix_pd_timestamp
from uitls.log import get_log
from uitls.pdf_utils import snap_pdf_all_page
from uitls.utils import clear_directory

IMAGE_SIZE = 150

#
# def get_last_by_filename_glob(directory, pattern="*"):
#     dir_path = Path(directory)
#     # 获取所有匹配的文件（排除子目录）
#     files = [f for f in dir_path.glob(pattern)]
#
#     if not files:
#         print("未找到匹配的文件")
#         return None
#
#     # 按文件名（字符串）升序排序，取最后一个
#     files_sorted = sorted(files, key=lambda f: f.name)
#     return files_sorted


def read_all_contract_subpath(contract_base_path: Path) -> List[
    str]:
    # 获取所有匹配的文件（排除子目录）
    # files = [f for f in contract_base_path.glob(pattern)]

    log =get_log()
    all_path = [f for f in contract_base_path.iterdir() if f.is_dir()]

    if not all_path:
        log.error (f"未找到 {contract_base_path} 下的二級目錄")
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
    def __init__(self, title: str):
        self.title = title
        self.images: List[str] = []

    def add_image_file(self, image_file: str):
        self.images.append(image_file)

    def add_all_images(self, image_file_list: List[str]):
        for image_file in image_file_list:
            self.images.append(image_file)


class ContractObj:
    def __init__(self, contract_id: str):
        self.contract_id = contract_id
        self.orders = []
        self.meta: Dict[str, Any] = {}  # 存放 合同的其他信息，例如 客户，签署日期
        self.main_file: List[ContractSnapshotFile] = []
        self.order_files: List[List[ContractSnapshotFile]] = []
        self.invoice_files: List[List[ContractSnapshotFile]] = []

    def add_order(self, order):
        self.orders.append(order)

    def reorder(self):
        self.orders.sort()

    def set_main_file(self, main_file: List[ContractSnapshotFile]):
        self.main_file = main_file

    def set_order_files(self, order_files: List[List[ContractSnapshotFile]]):
        self.order_files = order_files

    def set_invoice_files(self, invoice_files: List[List[ContractSnapshotFile]]):
        self.invoice_files = invoice_files

    def set_meta(self, meta):
        self.meta = meta


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


IGNORE_NAMES = ["核定表", "登记证明", "会议纪要"]
ACCEPT_SUFFIX_CONTRACT = [".pdf"]
ACCEPT_SUFFIX_ORDERS = [".pdf", ".jpg", ".png"]


def ignore_files(filename: str):
    for ignore in IGNORE_NAMES:
        if ignore in filename:
            return True
    return False


# 在 合同的子目录中，找到所以的正式文件
def get_contract_file_in_path(contract_base_path: Path, accept_suffix):
    # contract_sub_path = contract_base_path / subpath

    log = get_log()

    if not contract_base_path.exists():
        return None
    all_file = [f for f in contract_base_path.iterdir() if f.is_file()]
    files = []
    for f in all_file:
        if ignore_files(f.stem):
            continue
        file_suffix = f.suffix.lower()
        if file_suffix not in accept_suffix:
            log.error (f"warn: get contract not accept suffix, {f.name} , {accept_suffix}")
            continue
        files.append(f)
    return files


def make_contract_file_snapshots(output_image_path: Path, prefix: str, file: Path,
                                 contract_id: str) -> ContractSnapshotFile:
    log = get_log()

    suffix = file.suffix.lower()

    out = ContractSnapshotFile(file.stem)

    if suffix == ".pdf":
        # page_num, doc.page_count, pdf_filename)
        def gen_contract_image_file_name(page_num: int, page_count: int, pdf_filename: str):
            # image_name = f"{contract_id}-合同截图-{prefix}-{file.stem}-{page_num:02}.jpg"
            image_name1 = f"{contract_id}-{prefix}-{page_num:03}.jpg"
            # image_full_name = output_image_path / image_name
            return image_name1

        file_list = snap_pdf_all_page(output_image_path, file, contract_id, gen_contract_image_file_name, 30)
        out.add_all_images(file_list)
    else:
        image_name2 = f"{contract_id}-{prefix}-000{suffix}"
        image_full_name = output_image_path / image_name2

        try:
            shutil.copy2(file, image_full_name)
            log.debug (f"已复制：{contract_id} ,  {str(image_full_name)[-30:]}")
            out.add_image_file(image_name2)
        except Exception as e:
            log.error (f"复制失败 {file}  {image_full_name}: {e}")

    return out


def process_contract_simple_path(contract_base_path: Path, output_image_path: Path,
                                 target_contract_id: str,
                                 contract_id: str, contract_type: str, accept_suffix) -> List[ContractSnapshotFile]:
    log = get_log()

    contract_snapshot_file_list = []
    contract_parent_path = contract_base_path / contract_id
    if not contract_parent_path.exists():
        log.warning (f"Contract path not exist , {contract_parent_path}")
        return contract_snapshot_file_list
    contract_files = get_contract_file_in_path(contract_parent_path, accept_suffix)
    if contract_files is None:
        log.warning(f"Not found contract file in path : {contract_parent_path}")
        return contract_snapshot_file_list

    index = 0

    for file in contract_files:
        index = index + 1
        contract_snapshot_file = make_contract_file_snapshots(output_image_path, f"{contract_type}-{index:02}", file,
                                                              target_contract_id)
        contract_snapshot_file_list.append(contract_snapshot_file)

    return contract_snapshot_file_list


# 处理一个 合同对象（ 框架+订单 或者 单独合同 ）
def process_contract_obj(contract_base_path: Path, invoice_base_path: Path | None, output_image_path: Path,
                         contract: ContractObj):
    # snap_pdf_all_pagecontract_base_path: Path,

    # 合同 PDF 文件
    main_file_list = process_contract_simple_path(contract_base_path, output_image_path,
                                                  contract.contract_id,
                                                  contract.contract_id,
                                                  "合同-MAIN", ACCEPT_SUFFIX_CONTRACT)

    contract.set_main_file(main_file_list)

    invoice_snapshot_files: List[List[ContractSnapshotFile]] = []
    # 合同发票
    if invoice_base_path is not None:
        main_invoice_file_list = process_contract_simple_path(invoice_base_path, output_image_path,
                                                              contract.contract_id,
                                                              contract.contract_id,
                                                              "合同发票-INV-M", ACCEPT_SUFFIX_ORDERS)
        if main_invoice_file_list is not None and len(main_invoice_file_list) > 0:
            invoice_snapshot_files.append(main_invoice_file_list)

    # 合同的订单
    order_snapshot_files: List[List[ContractSnapshotFile]] = []
    index = 1
    for order_file in contract.orders:
        # 订单有的时候是 截图 JPG ，有的时候是 PDF
        order_snapshot_file = process_contract_simple_path(contract_base_path, output_image_path,
                                                           contract.contract_id,
                                                           order_file,
                                                           f"订单-ORDER-{index}", ACCEPT_SUFFIX_ORDERS)
        if order_snapshot_file is not None and len(order_snapshot_file) > 0:
            order_snapshot_files.append(order_snapshot_file)

        # 订单发票
        if invoice_base_path is not None:
            order_invoice_file_list = process_contract_simple_path(invoice_base_path, output_image_path,
                                                                   contract.contract_id,
                                                                   order_file,
                                                                   f"订单发票-INV-O-{index}", ACCEPT_SUFFIX_ORDERS)

            if order_invoice_file_list is not None and len(order_invoice_file_list) > 0:
                invoice_snapshot_files.append(order_invoice_file_list)
        index += 1

    contract.set_order_files(order_snapshot_files)
    contract.set_invoice_files(invoice_snapshot_files)


def read_contracts_cases(
        contract_base_root,
        invoice_base_root,
        output_image_dir,
        excel_file_name,
        cb_info = None,
        contract_sheet_name="Contract",
        col_contract_id="项目编号",
        col_contract_name="合同名称"
) -> List[ContractObj] | None:

    log = get_log()

    contract_base_path = Path(contract_base_root)
    if not contract_base_path.exists():
        log .error (f"Base contract path, not exist , {contract_base_root}")
        return None

    invoice_base_path = None
    if invoice_base_root is not None and invoice_base_root != "":
        invoice_base_path = Path(invoice_base_root)
        if not invoice_base_path.exists():
            log .error (f"Base invoice path, not exist , {invoice_base_root}")
            return None

    output_image_path = Path(output_image_dir)
    if not output_image_path.exists():
        output_image_path.mkdir(parents=True)
    else:
        clear_directory(output_image_dir)

    all_contract_paths = read_all_contract_subpath(contract_base_path)

    project_list = read_excel_sheet_values(excel_file_name, contract_sheet_name)
    project_contract_obj_list = []
    for project in project_list:
        contract_id = project[col_contract_id]
        project_contract_name = project[col_contract_name]
        if contract_id is None or contract_id == "":
            continue

        contract_id = str(contract_id)

        if cb_info :
            result2 = cb_info( contract_id, project_contract_name )
            if result2 == True :
                return  None

        project_contract_obj = find_contract_and_orders(all_contract_paths, contract_id)
        if project_contract_obj is None:
            log .error (f"Not found contract id {contract_id} in root:{contract_base_path}")
            continue

        project_contract_obj.set_meta(project)

        try:
            log .info  (f"Process contract , {contract_id} - {project_contract_name}")
            process_contract_obj(contract_base_path, invoice_base_path, output_image_path, project_contract_obj)
            project_contract_obj_list.append(project_contract_obj)
        except Exception as e:
            log .error (f"Process contract, {contract_id} error:{e}")

    return project_contract_obj_list


def dump_snapshot_files(files: List[ContractSnapshotFile]) -> List[Dict[str, Any]]:
    if files is None:
        return []
    # self.main_pdf_file = main_pdf_file
    # self.title = main_pdf_file.stem
    # self.image_file_list: List[SnapshotAndInlineImage] = []
    output: List[Dict[str, Any]] = []
    for pmf in files:
        out: Dict[str, Any] = {"name": pmf.title}
        pmf_images = []
        for one in pmf.images:
            pmf_images.append(one)
        out["snapshots"] = pmf_images
        # ,"snapshots": pmf_images}
        output.append(out)

    return output


def dump_project_contract_obj_list(project_contract_obj_list: List[ContractObj]):
    projects = []
    for project in project_contract_obj_list:

        output = {}
        contract_id = project.contract_id
        # contract_name = project.contract_name
        main_file = dump_snapshot_files(project.main_file)
        order_files = []
        if project.order_files is not None:
            for ofs in project.order_files:
                order_f = dump_snapshot_files(ofs)
                order_files.append(order_f)

        invoice_files = []
        if project.invoice_files is not None:
            for ifs in project.invoice_files:
                invoice_f = dump_snapshot_files(ifs)
                invoice_files.append(invoice_f)

        output["contractId"] = contract_id
        output["contracts"] = main_file
        output["orders"] = order_files
        output["invoices"] = invoice_files

        output["meta"] = json_fix_pd_timestamp(project.meta)
        projects.append(output)

    obj = {"projects": projects}
    return obj


def convert_contract_snapshots(args, cb_info ):

    log = get_log()

    if args.input_xlsx is None or args.input_xlsx == "":
        log.error ("--input-xlsx 空")
        return False

    if not os.path.exists(args.input_xlsx):
        log.error ("file not exist , {args.input_xlsx}")
        return False

    if args.contract_base_root is None or args.contract_base_root == "":
        log.error ("--contract-base-root 空")
        return False

    invoice_base_root = None
    if args.invoice_base_root is None or args.invoice_base_root == "":
        log.error ("--invoice-base-root 空")
        return False

    excel_file_name = args.input_xlsx
    # excel_file_name = "test.input.xlsx"
    contract_base_root = args.contract_base_root

    invoice_base_root = args.invoice_base_root
    output_images_dir = args.output_image_root  # "./test.images"



    contract_sheet_name = args.sheet_name_contract# "Contract",
    col_contract_id = args.col_project_id # "项目编号",
    col_contract_name = args.col_contract_name # "合同名称"

    project_contract_obj_list = read_contracts_cases(contract_base_root,
                                                     invoice_base_root,
                                                     output_images_dir,
                                                     excel_file_name,
                                                     cb_info,
                                                     contract_sheet_name,
                                                     col_contract_id,
                                                     col_contract_name
                                                     )
    if project_contract_obj_list is None:
        return False
    json_path = args.output_file
    dump_obj1 = dump_project_contract_obj_list(project_contract_obj_list)
    with open(json_path, "w", encoding="utf-8") as f:
        # s = to_json_str(dump_obj1)
        # f.write(s)
        json.dump(dump_obj1, f, ensure_ascii=False, indent=4)
        log.info  (f"save json file {json_path}")

    return True

