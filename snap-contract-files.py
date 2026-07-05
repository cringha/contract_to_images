import argparse
import traceback

from enties.task_convert_contract_snapshots import convert_contract_snapshots
from uitls.log import init_with_conf, get_log, LogConfig

IMAGE_SIZE = 150


if __name__ == "__main__":
    init_with_conf(LogConfig())
    logger = get_log()
    logger.info("Convert contract to snapshots ")

    # contract_sheet_name="Contract",
    #         col_contract_id="项目编号", col_contract_name="合同名称",
    parser = argparse.ArgumentParser(description="转换合同发票截图工具")
    parser.add_argument("-i", "--input-xlsx", help="输入Xlsx文件")
    parser.add_argument("-c", "--contract-base-root", help="输入合同文件根目录")
    parser.add_argument("-v", "--invoice-base-root", help="输入发票文件根目录")
    parser.add_argument("--output-image-root", help="输出截图图片文件根目录, default: %(default)s",
                        default="./local.images")

    parser.add_argument("--sheet-name-contract", help="Contract sheet name; default: %(default)s", default="Contract")
    parser.add_argument("--col-project-id", help="project id column name in `Contract sheet`; default: %(default)s",
                        default="项目编号")
    parser.add_argument("--col-contract-name",
                        help="contract name column name in `Contract sheet`; default: %(default)s",
                        default="合同名称")
    parser.add_argument("-o", "--output-file", help="输出的JSON文件; default: %(default)s",
                        default="./local-contracts.json")


    try:
        args = parser.parse_args()

        def cb_info( project_id, project_name):
            logger.info(f"project_id: {project_id}, project_name: {project_name}")
            return False

        result = convert_contract_snapshots(args, cb_info)
        if not result:
            parser.print_help()
    except Exception as e:
        logger.error ("Exec main error ", e)
        traceback.print_exc()
