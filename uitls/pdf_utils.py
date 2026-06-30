from pathlib import Path
from typing import Any, List

import pymupdf

# import fitz  # PyMuPDF，用于PDF处理

BORDER_WIDTH = 4


def snapshot(basepath:Path, doc: Any, page_num: int, filename: str, info: str, pdf_filename: str | Path):
    # 2. 截取首页（第一个包含目标人员的页面）
    first_page = doc[page_num]
    # 将页面转为图片（分辨率300dpi，保证清晰度）
    # mat = pymupdf.Matrix(300 / 72, 300 / 72)
    # mat = pymupdf.Matrix(2, 2)
    mat = pymupdf.Matrix(1.2, 1.2)
    first_pix = first_page.get_pixmap(matrix=mat, alpha=False)

    full_filename = basepath / filename
    first_pix.save(full_filename)
    print(f"已保存：{info}, {filename[-30:]}, {str(pdf_filename)[-30:0]}")
    return filename
#
# def snap_pdf_page(pdf_filename: str, user_name: str, cb_filename):
#     # print("Process ", pdf_path)
#
#     # 打开PDF文件
#     # pymupdf.open
#     doc = pymupdf.open(pdf_filename)
#     if doc.page_count == 0:
#         print("PDF文件为空，无法处理, {pdf_path}")
#         return False
#
#     # 1. 遍历PDF页面，查找目标人员并添加红色框
#     for page_num in range(doc.page_count):
#         file_name = cb_filename(user_name, page_num, doc.page_count, pdf_filename)
#         if file_name is not None:
#             snapshot(doc, page_num, file_name, user_name, pdf_filename)
#         else:
#             print(f"文件不符合策略没有保存：{user_name}, page_num: {page_num}, {pdf_filename}")
#
#     return True


def snap_pdf_all_page( basepath:Path, pdf_filename: str | Path, info: str, cb_filename, max_pages: int=0) -> List[str]:
    # 打开PDF文件
    # pymupdf.open

    output_file_list = []

    doc = pymupdf.open(pdf_filename)
    if doc.page_count == 0:
        print("PDF文件为空，  {pdf_path}")
        return output_file_list
    index = 0
    for page_num in range(doc.page_count):
        if max_pages>0:
            if index >= max_pages:
                return output_file_list
        file_name = cb_filename(page_num, doc.page_count, pdf_filename)
        if file_name is not None:
            snapshot(basepath, doc, page_num, file_name, info, pdf_filename)
            output_file_list.append(file_name)
        else:
            print(f"文件不符合, ：{info}, page_num: {page_num}, {pdf_filename}")
        index += 1
    return output_file_list
