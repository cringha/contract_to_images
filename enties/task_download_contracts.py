import json
import os
import time
import uuid
import zipfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import requests
from tqdm import tqdm

from uitls.excel_utils import read_excel_sheet_values
from uitls.log import get_log

CACHE_FILE = ".ec4-password.json"

PATH_CONTRACTS = "contracts"
PATH_INVOICES = "invoices"

DOWNLOAD_TYPE_ALL = "ALL"
DOWNLOAD_TYPE_CONTRACT = "CONTRACT"
DOWNLOAD_TYPE_INVOICE = "INVOICE"
DOWNLOAD_TYPE = [DOWNLOAD_TYPE_ALL, DOWNLOAD_TYPE_CONTRACT, DOWNLOAD_TYPE_INVOICE]

# 配置文件
CONFIG_DOWNLOAD_CONTRACT_FILE = ".config-download-contracts.json"


def get_cache_password_file():
    home_path = Path.home()
    return home_path / CACHE_FILE

    # # 方法二：os.path（经典写法，返回字符串）
    # import os
    # home_path = os.path.expanduser("~")
    # print(home_path)


def clear_cache_password_file():
    file = get_cache_password_file()
    file.unlink()


# ---------- 工具函数：加载/保存缓存 ----------
def load_cached_password() -> Optional[Tuple[str, str, str, str]]:
    """尝试加载缓存，返回 (modulus_hex, exponent_hex, encrypted_hex)，失败返回 None"""

    file = get_cache_password_file()

    if not file.exists():
        return None
    try:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("username"), data.get("modulus"), data.get("exponent"), data.get("encrypted")
    except:
        return None


def save_cached_password(username: str, modulus_hex: str, exponent_hex: str, encrypted_hex: str):
    file = get_cache_password_file()
    with open(file, 'w', encoding='utf-8') as f:
        json.dump({"username": username, "modulus": modulus_hex, "exponent": exponent_hex, "encrypted": encrypted_hex},
                  f, indent=2)


# ---------- 1. 获取 RSA 公钥 ----------
def get_rsa_public_key() -> Tuple[int, int, str, str]:
    url = "http://everoffice.cn/service/sso/keyPair"
    params = {"t": int(time.time() * 1000)}
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Referer": "http://everoffice.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0"
    }
    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 200:
        raise RuntimeError(f"获取公钥失败: {data}")
    body = data["body"]
    modulus_hex = body["modulus"]
    exponent_hex = body["exponent"]
    modulus = int(modulus_hex, 16)
    exponent = int(exponent_hex, 16)
    return modulus, exponent, modulus_hex, exponent_hex


# ---------- 2. RSA 加密（无填充，小端序） ----------
def rsa_encrypt_password(password: str, modulus: int, exponent: int) -> str:
    n_bytes = (modulus.bit_length() + 7) // 8
    plain_bytes = password.encode('latin-1')
    remainder = len(plain_bytes) % n_bytes
    if remainder:
        plain_bytes += b'\x00' * (n_bytes - remainder)
    encrypted_blocks = []
    for i in range(0, len(plain_bytes), n_bytes):
        block = plain_bytes[i:i + n_bytes]
        m = int.from_bytes(block, 'little')
        c = pow(m, exponent, modulus)
        encrypted_blocks.append(format(c, 'x'))
    return encrypted_blocks[0]


# ---------- 3. 登录 ----------
def login(username: str, encrypted_password: str) -> None | requests.Session:
    session = requests.Session()
    url = "http://everoffice.cn/service/sso/login"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "http://everoffice.cn",
        "Pragma": "no-cache",
        "Referer": "http://everoffice.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0"
    }
    data = {
        "userName": username,
        "password": encrypted_password,
        "code": "",
        "appKey": "eo-workbench"
    }
    resp = session.post(url, headers=headers, data=data)
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 200:
        log = get_log()
        msg = result.get("message", str(result))
        log.error(f"登录失败: {msg}")
        # raise RuntimeError(f"登录失败: {msg}")
        return None
    return session


# ---------- 4. 获取项目列表 ----------
def get_project_list(session: requests.Session, initial_nos: List[str], file_type: int = 1) -> List[str]:
    log = get_log()
    url = "http://everoffice.cn/service/eo-pms-service/pmsProjects/filePorjectslist"
    pno_str = ','.join(initial_nos) + ','
    params = {
        "t": int(time.time() * 1000),
        "startPosition": 0,
        "maxResult": 100,
        "PNo": pno_str,
        "PName": "",
        "PType": "",
        "startActual": "",
        "endActual": "",
        "treaty": "",
        "signNo": "",
        "fileType": file_type,
        "accBeginTime": "",
        "accEndTime": "",
        "contractBeginTime": "",
        "contractEndTime": ""
    }
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Referer": "http://everoffice.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0"
    }
    resp = session.get(url, params=params, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 200:
        raise RuntimeError(f"获取项目列表失败: {data}")
    body = data.get("body", {})
    datalist = body.get("datalist", [])
    all_nos = set()
    for item in datalist:
        pno = item.get("pno")
        if pno:
            all_nos.add(pno)
    if not all_nos:
        log.warning("警告：未从 datalist 中提取到项目编号，使用初始列表")
        all_nos = set(initial_nos)
    return list(all_nos)


# ---------- 5. 获取文件 ID 映射 ----------
def get_file_id_map(session: requests.Session, project_nos: List[str], file_type: int = 1) -> Dict[str, str]:
    log = get_log()
    url = "http://everoffice.cn/service/eo-pms-service/pmsProjects/filePorjectsDownload"
    pno_str = ','.join(project_nos) + ','
    params = {
        "t": int(time.time() * 1000),
        "PNo": pno_str,
        "PName": "",
        "PType": "",
        "startActual": "",
        "endActual": "",
        "treaty": "",
        "signNo": "",
        "fileType": file_type,
        "accBeginTime": "",
        "accEndTime": "",
        "contractBeginTime": "",
        "contractEndTime": ""
    }
    params["pNos"] = project_nos
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Referer": "http://everoffice.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0"
    }
    resp = session.get(url, params=params, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 200:
        raise RuntimeError(f"获取文件映射失败: {data}")
    return data.get("body", {}).get("returnMap", {})


# ---------- 6. 下载 ZIP ----------
def download_zip_old(base_path: str, session: requests.Session, file_map: Dict[str, str],
                     zip_name: str = "下载") -> str:
    log = get_log()
    tx_id = "S02000A02001" + uuid.uuid4().hex.upper() + uuid.uuid4().hex[:8].upper()
    url = "http://everoffice.cn/service/eo-klm-service/documentUpload/downloadDocumentsMap"
    params = {"transactionId": tx_id, "zipName": zip_name}
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "http://everoffice.cn",
        "Pragma": "no-cache",
        "Referer": "http://everoffice.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
        "transactionId": tx_id
    }
    resp = session.post(url, params=params, headers=headers, json=file_map)
    resp.raise_for_status()
    if 'application/json' in resp.headers.get('Content-Type', ''):
        err = resp.json()
        raise RuntimeError(f"下载失败: {err}")
    filename = f"{zip_name}_{int(time.time())}.zip"
    fullname = os.path.join(base_path, filename)
    with open(fullname, 'wb') as f:
        f.write(resp.content)
    log.debug(f"下载成功，文件保存为: {filename}")
    return filename


# ---------- 6. 下载 ZIP 带回调百分比 + 绿色进度条 ----------
def download_zip(base_path: str, session: requests.Session, file_map: Dict[str, str], zip_name: str = "下载",
                 progress_callback=None) -> str:
    log = get_log()
    tx_id = "S02000A02001" + uuid.uuid4().hex.upper() + uuid.uuid4().hex[:8].upper()
    url = "http://everoffice.cn/service/eo-klm-service/documentUpload/downloadDocumentsMap"
    params = {"transactionId": tx_id, "zipName": zip_name}
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "http://everoffice.cn",
        "Pragma": "no-cache",
        "Referer": "http://everoffice.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
        "transactionId": tx_id
    }
    resp = session.post(url, params=params, headers=headers, json=file_map, stream=True)
    resp.raise_for_status()
    if 'application/json' in resp.headers.get('Content-Type', ''):
        err = resp.json()
        raise RuntimeError(f"下载失败: {err}")

    filename = f"{zip_name}_{int(time.time())}.zip"
    fullname = os.path.join(base_path, filename)
    total_size = int(resp.headers.get("content-length", 0))
    chunk_size = 1024 * 1024
    downloaded = 0

    # 绿色进度条
    with open(fullname, 'wb') as f, tqdm(
            desc=f"正在下载 {filename}",
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            colour="green",
            leave=True
    ) as pbar:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                chunk_len = len(chunk)
                downloaded += chunk_len
                pbar.update(chunk_len)
                # 回调输出百分比
                if progress_callback and total_size > 0:
                    percent = downloaded / total_size * 100
                    progress_callback(downloaded, total_size, percent)

    log.debug(f"下载成功，文件保存为: {filename}")
    return filename


file_types = {1: "合同", 2: "发票"}


# ---------- 封装：按类型下载 ----------
def download_by_type(base_path: str, session: requests.Session, initial_nos: List[str], file_type: int,
                     zip_name_prefix: str):
    log = get_log()

    log.info(f"开始下载 {file_types[file_type]} ({zip_name_prefix})")
    all_nos = get_project_list(session, initial_nos, file_type)
    log.info(f"获取到 {len(all_nos)} 个项目编号")
    file_map = get_file_id_map(session, all_nos, file_type)
    log.info(f"获取到 {len(file_map)} 个项目的文件映射")
    if file_map:
        return download_zip(base_path, session, file_map, zip_name_prefix)
    else:
        log.info("警告：文件映射为空，跳过下载")
    return None


# ---------- 主流程 ----------


def read_project_ids(args) -> List[str]:
    log = get_log()
    if args.project_id is not None and args.project_id != "":
        out = args.project_id.split(',')
        return [p.strip() for p in out if p != ""]

    if args.input_xlsx is not None and args.input_xlsx != "":
        input_xlsx_path = Path(args.input_xlsx)
        if not input_xlsx_path or not input_xlsx_path.exists():
            log.error(f"input-xlsx {args.input_xlsx} , 文件不存在")
            return []
        contract_sheet_name = args.sheet_name_contract
        col_contract_id = args.col_project_id  # "项目编号",
        project_list = read_excel_sheet_values(input_xlsx_path, contract_sheet_name)
        project_contract_obj_list = []
        for project in project_list:
            contract_id = project[col_contract_id]
            if contract_id is None or contract_id == "":
                continue

            contract_id = str(contract_id)
            project_contract_obj_list.append(contract_id)

        return project_contract_obj_list

    log.error("Input project id empty")
    return []


import getpass


def ask_password(args, username):
    if args.password is None or args.password == "":
        password = getpass.getpass("Enter your password: ")
    else:
        password = args.password

    if password is None or password == "":
        log = get_log()
        log.error("Please input password")
        return ""

    modulus, exponent, mod_hex, exp_hex = get_rsa_public_key()
    encrypted_pwd = rsa_encrypt_password(password, modulus, exponent)
    save_cached_password(username, mod_hex, exp_hex, encrypted_pwd)
    return encrypted_pwd


def unzip_file(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)


def save_config(input_xlsx: str, contract_base_root: str, invoice_base_root: str,
                sheet_name_contract: str,
                col_project_id: str):
    logger = get_log()
    """从界面读取并保存到配置文件"""
    cfg = {
        "input-xlsx": input_xlsx,
        "contract-base-root": contract_base_root,
        "invoice-base-root": invoice_base_root,
        "sheet-name-contract": sheet_name_contract,
        "col-project-id": col_project_id
    }
    try:
        with open(CONFIG_DOWNLOAD_CONTRACT_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        logger.info("配置已保存")
    except Exception as e:
        logger.error(f"保存配置失败: {e}")


# 使用示例

def download_contracts(args, cb_info):
    username = ""  # input("请输入用户名: ").strip()

    log = get_log()

    download_contract = False
    download_invoice = False

    if args.download_type != "":
        download_types = args.download_type.upper().split(',')
        for tt in download_types:
            if tt != DOWNLOAD_TYPE_ALL and tt not in DOWNLOAD_TYPE:
                cb_info(False, f"download_type value , wanted , {DOWNLOAD_TYPE} ")
                return False
        if DOWNLOAD_TYPE_ALL in download_types:
            download_contract = True
            download_invoice = True
        if DOWNLOAD_TYPE_CONTRACT in download_types:
            download_contract = True
        if DOWNLOAD_TYPE_INVOICE in download_types:
            download_invoice = True
    else:
        download_contract = True
        download_invoice = True

    if download_invoice == False and download_contract == False:
        cb_info(False, f"至少下载合同或发票一项")
        return False

    project_ids = read_project_ids(args)
    if project_ids is None or len(project_ids) == 0:
        return False

    cached = load_cached_password()

    if args.user is None or args.user == "":
        if cached:
            username, *_ = cached

        if username is None or username == "":
            username = input("请输入用户名: ").strip()

    else:
        username = args.user

    if username is None or username == "":
        cb_info(False, "Please input user name")
        return False

    log.info(f"User: {username}")
    log.info(f"Project IDs: {project_ids}")

    # 尝试从缓存加载加密密码，并校验公钥是否一致
    cached = load_cached_password()
    if cached:
        _, mod_hex, exp_hex, enc_pwd = cached
        # 获取最新公钥，比较
        try:
            _, _, new_mod_hex, new_exp_hex = get_rsa_public_key()
            if mod_hex == new_mod_hex and exp_hex == new_exp_hex:
                log.info("使用缓存的加密密码")
                encrypted_pwd = enc_pwd
            else:
                log.info("公钥已变化，重新加密...")
                raise ValueError("公钥变化")
        except Exception as _:
            # 公钥变化或网络问题，重新加密
            log.info("重新获取公钥并加密...")
            encrypted_pwd = ask_password(args, username)
    else:
        log.info("首次使用，获取公钥并加密...")
        encrypted_pwd = ask_password(args, username)

    log.info(f"登录中..., {username}")
    session = login(username, encrypted_pwd)
    if session is None:
        # 密码输错误了
        clear_cache_password_file()
        cb_info(True, "无效的密码")
        return True

    base_path = args.base_path
    base_path_path = Path(base_path)
    if not base_path_path.exists():
        base_path_path.mkdir(parents=True, exist_ok=True)

    contract_base_root = ""

    # 下载合同
    if download_contract:
        contract_zip = download_by_type(base_path, session, project_ids, file_type=1, zip_name_prefix="合同下载")
        log.info(f"合同： {contract_zip}")
        if args.extract:
            if contract_zip is not None and contract_zip != "":
                full_contract_zip = base_path_path / contract_zip
                target_contract_path = base_path_path / PATH_CONTRACTS
                log.info(f"解压合同： {contract_zip}, 到目录 {target_contract_path}")
                unzip_file(full_contract_zip, target_contract_path)
                contract_base_root = str(target_contract_path)

    invoice_base_root = ""
    if download_invoice:
        # 下载发票
        invoice_zip = download_by_type(base_path, session, project_ids, file_type=2, zip_name_prefix="发票下载")
        log.info(f"发票： {invoice_zip}")
        if args.extract:
            if invoice_zip is not None and invoice_zip != "":
                full_invoice_zip = base_path_path / invoice_zip
                target_invoice_path = base_path_path / PATH_INVOICES
                log.info(f"解压发票： {invoice_zip}, 到目录 {target_invoice_path}")
                unzip_file(full_invoice_zip, target_invoice_path)
                invoice_base_root = str(target_invoice_path)

    save_config(args.input_xlsx, contract_base_root, invoice_base_root, args.sheet_name_contract, args.col_project_id)
    cb_info(True, "下载执行完毕")
    return True

#
# if __name__ == "__main__":
#     init_with_conf(LogConfig("./logs/download.log"))
#     logger = get_log()
#     logger.info("  ")
#
#     parser = argparse.ArgumentParser(description="合同发票下载工具")
#     parser.add_argument("-u", "--user", help="输入EO账号", default="")
#     parser.add_argument("-p", "--password", help="EO密码。 或保持为空，则交互式输入", default="")
#     parser.add_argument("-b", "--base-path", help="存放合同文件根目录, default: %(default)s", default="./local.data")
#     parser.add_argument("-j", "--project-id", help="输入的项目编码，多个项目编码以','分割。 ", default="")
#     parser.add_argument("-i", "--input-xlsx", help="输入Xlsx文件", default="")
#     parser.add_argument("--sheet-name-contract", help="Contract sheet name; default: %(default)s", default="Contract")
#     parser.add_argument("--col-project-id", help="project id column name in `Contract sheet`; default: %(default)s",
#                         default="项目编号")
#
#     parser.add_argument("-t", "--download_type", help="下载类型， ALL, CONTRACT, INVOICE，default: %(default)s ",
#                         default="ALL")
#     parser.add_argument("-x", "--extract", action="store_true", help="解压合同、发票压缩文件，放到 --base-path 目录下")
#     # max_pages_per_pdf
#     try:
#         args = parser.parse_args()
#
#
#         def cb_info(project_id, project_name):
#             logger.info(f"project_id: {project_id}, project_name: {project_name}")
#             return False
#
#
#         result = main(args)
#         if not result:
#             parser.print_help()
#     except Exception as e:
#         logger.error("Exec main error ", e)
#         traceback.print_exc()
