import logging
import os
import sys
from pathlib import Path

from uitls import utils

_nameToLevel = {
    'CRITICAL': logging.CRITICAL,
    'FATAL': logging.FATAL,
    'ERROR': logging.ERROR,
    'WARN': logging.WARNING,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'NOTSET': logging.NOTSET,
}



DEFAULT_LOG_FILE="./logs/tools.log"
DEFAULT_LOG_LEVEL = "debug"
class LogConfig:

    def __init__(self,logfile=DEFAULT_LOG_FILE,loglevel=DEFAULT_LOG_LEVEL, console=True):
        self.logfile = logfile
        self.level = loglevel
        self.console = console

    def update_args(self, args):
        if utils.is_not_empty(args.logfile):
            self.logfile = args.logfile
        if utils.is_not_empty(args.loglevel):
            self.level = args.loglevel

        self.console = args.logstdout


        return self


def logging_level(level: str) -> int:
    if hasattr(logging, "getLevelNamesMapping"):  # Python3 . 7 low version no getLevelNamesMapping impl
        levels = logging.getLevelNamesMapping()
    else:
        levels = _nameToLevel
    level = level.upper()
    if level not in levels:
        lv = levels[level]
    else:
        lv = logging.DEBUG
    return lv


def init_log(conf: LogConfig):
    # 创建logger对象

    lv = logging_level(conf.level)

    lg = logging.getLogger('tools')
    lg.setLevel(lv)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if utils.is_not_empty(conf.logfile):
        file_path = Path(conf.logfile).resolve()
        dir_path = file_path.parent

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        # 创建FileHandler对象
        fh = logging.FileHandler(conf.logfile)
        fh.setLevel(lv)

        # 创建Formatter对象

        fh.setFormatter(formatter)

        # 将FileHandler对象添加到Logger对象中
        lg.addHandler(fh)

    if conf.console:
        sh = logging.StreamHandler(stream=sys.stdout)
        sh.setLevel(lv)
        sh.setFormatter(formatter)
        lg.addHandler(sh)
    return lg


#
# # 记录日志信息
# logger.debug('debug message')
# logger.info('info message')
# logger.warning('warning message')
# logger.error('error message')
# logger.critical('critical message')


logger = None


def init_with_conf(conf: LogConfig) -> None:
    global logger
    logger = init_log(conf)


def get_log():
    return logger
