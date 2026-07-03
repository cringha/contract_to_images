import argparse
import json
import os.path
import shutil
import traceback
from pathlib import Path
from typing import List, Dict, Any
import pdfplumber
from pymupdf import pymupdf
from pymupdf import Rect

IMAGE_SIZE = 150



def extra_pdf_content(pdf_file) -> List[str]:
    """
    """
    line_list = []

    # 打开PDF文件
    with pdfplumber.open(pdf_file) as pdf:
        # 逐页读取表格
        for page in pdf.pages:
            # 提取页面内所有表格
            text = page.extract_text()
            if text is not None and len(text) > 0:
                print(text)
    return line_list

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
        out.append(one)

    return out



def loop_all_contracts_files(base_root:Path ,pattern="*.pdf"):
    path_list = read_all_contract_subpath( base_root)
    for dir_path in path_list:
        # 获取所有匹配的文件（排除子目录）
        files = [f for f in dir_path.glob(pattern)]

        if not files:
            print("未找到匹配的文件")
            return None


        for file in files:
            print(f">> {file} ======================================================= ")
            extra_pdf_content(file)



def main( ):
    base_root = r"C:\Tools\Contracts\project1\20260629合同下载"
    loop_all_contracts_files(Path(base_root))



if __name__ == "__main__":



    try:

        result = main( )

    except Exception as e:
        print("Exec main error ", e)
        traceback.print_exc()
