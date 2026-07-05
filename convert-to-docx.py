import argparse
import os
import traceback

from enties.task_convert_to_docx import task_convert_docx
from uitls.log import init_with_conf, get_log, LogConfig

IMAGE_SIZE = 150

ACCEPT_SUFFIX = [".jpg", ".jpeg", ".png"]

"""
    将输入的 用户列表，转换为 WORD 
"""

if __name__ == "__main__":

    init_with_conf(LogConfig())
    logger = get_log()
    logger.debug("Convert user info to docx")

    # contract_sheet_name="Contract",
    #         col_contract_id="项目编号", col_contract_name="合同名称",
    parser = argparse.ArgumentParser(description="合同发票截图转DOCX")
    parser.add_argument("-i", "--input-json", help="输入Json文件")
    parser.add_argument("-j", "--input-image-root", help="输入截图图片文件根目录, default: %(default)s",
                        default="./local.images")

    parser.add_argument("-t", "--docx-template-file", help="docx template filename; default: %(default)s",
                        default="./templates/default-template.docx")
    parser.add_argument("-o", "--output-docx-file", help="输出docx文件; default: %(default)s",
                        default="./contract-order-and-invoices.docx")

    try:
        args = parser.parse_args()
        result = task_convert_docx(args)
        if not result:
            parser.print_help()
    except Exception as e:
        print("Exec main error ", e)
        traceback.print_exc()
