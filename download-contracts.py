import argparse
import traceback

from enties.task_download_contracts import download_contracts, DOWNLOAD_TYPE
from uitls.log import init_with_conf, get_log, LogConfig
#
# CACHE_FILE = ".ec4-password.json"
#
# PATH_CONTRACTS = "contracts"
# PATH_INVOICES = "invoices"
#
# DOWNLOAD_TYPE_ALL = "ALL"
# DOWNLOAD_TYPE_CONTRACT = "CONTRACT"
# DOWNLOAD_TYPE_INVOICE = "INVOICE"
# DOWNLOAD_TYPE = [DOWNLOAD_TYPE_ALL, DOWNLOAD_TYPE_CONTRACT, DOWNLOAD_TYPE_INVOICE]
#
# # 配置文件
# CONFIG_FILE = ".config-download-contracts.json"

if __name__ == "__main__":
    init_with_conf(LogConfig("./logs/download.log"))
    logger = get_log()
    logger.info("  ")

    parser = argparse.ArgumentParser(description="合同发票下载工具")
    parser.add_argument("-u", "--user", help="输入EO账号", default="")
    parser.add_argument("-p", "--password", help="EO密码。 或保持为空，则交互式输入", default="")
    parser.add_argument("-b", "--base-path", help="存放合同文件根目录, default: %(default)s", default="./local.data")
    parser.add_argument("-j", "--project-id", help="输入的项目编码，多个项目编码以','分割。 ", default="")
    parser.add_argument("-i", "--input-xlsx", help="输入Xlsx文件", default="")
    parser.add_argument("--sheet-name-contract", help="Contract sheet name; default: %(default)s", default="Contract")
    parser.add_argument("--col-project-id", help="project id column name in `Contract sheet`; default: %(default)s",
                        default="项目编号")

    parser.add_argument("-t", "--download_type", help=f"下载类型，{DOWNLOAD_TYPE}，default: %(default)s ",
                        default="ALL")
    parser.add_argument("-x", "--extract", action="store_true", help="解压合同、发票压缩文件，放到 --base-path 目录下")
    # max_pages_per_pdf
    try:
        args = parser.parse_args()


        def cb_info(status, msg):
            logger.info(f" {status}, : {msg}")
            return False


        result = download_contracts(args, cb_info)
        if not result:
            parser.print_help()
    except Exception as e:
        logger.error("Exec main error ", e)
        traceback.print_exc()
