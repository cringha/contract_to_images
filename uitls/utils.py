import random
import re
import shutil
import string
import tempfile
import time
import os
import tarfile

import json
from datetime import datetime
import os
from pathlib import Path

# import yaml


def is_array(arr):
    return isinstance(arr, list) or isinstance(arr, tuple)


# 将 yyyyMMddHHmmss 格式的字符串转换为 时间类型
def to_datetime(s: str) -> datetime:
    if is_blank(s):
        return None
    ln = len(s)
    if ln == 14:
        tm = datetime.strptime(s, '%Y%m%d%H%M%S')
    elif ln == 12:
        tm = datetime.strptime(s, '%Y%m%d%H%M')  # yyyyMMddHHmm
    elif ln == 10:
        tm = datetime.strptime(s, '%Y%m%d%H')  # yyyyMMddhh
    elif ln == 8:
        tm = datetime.strptime(s, '%Y%m%d')  # yyyyMMdd
    else:
        raise Exception('Unknown time {}'.format(s))

    return tm


def get_timestamp():
    nw = datetime.now()
    return nw.strftime('%Y_%m_%d_%H_%M_%S')


def is_num(s):
    if s is None:
        return False

    return isinstance(s, int)


def is_not_num(s):
    if s is None:
        return True

    return not isinstance(s, int)


def is_not_blank(s):
    if s is None:
        return False
    if isinstance(s, str):
        return bool(s and s.strip())
    return True


def is_blank(s):
    if s is None:
        return True

    if isinstance(s, str):
        if not bool(s):
            return True
        if not bool(s.strip()):
            return True

        return False
    return False


def convert_bytes(num):
    """
	this function will convert bytes to MB.... GB... etc
	"""
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0


def file_size(file_path):
    """
	this function will return the file size
	"""
    if os.path.isfile(file_path):
        file_info = os.stat(file_path)
        return convert_bytes(file_info.st_size)


def get_dict_val(obj, name):
    if name in obj:
        return obj[name]
    return None


def get_extension(filename):
    return Path(filename).suffix


def get_extension(file_path):
    # return Path(filename).
    return os.path.splitext(file_path)


def read_dict(obj, fullname, def_val=None):
    if obj is None:
        return def_val

    if is_blank(fullname):
        raise Exception(f"Invalid name : `{fullname}`")

    names = fullname.split('.')
    # if len(names) == 1:
    #     if is_blank(fullname):
    #         raise Exception(f"Invalid name : `{fullname}`")
    #
    #     if fullname in obj:
    #         return obj[fullname]
    # else:
    one = obj
    for name in names:
        if is_blank(name):
            raise Exception(f'Invalid name , `{name}` in `{fullname}`')

        if name in one:
            one = one[name]
        else:
            return def_val
    return one


def json_to_dict(buff):
    return json.loads(buff)


def remove_file(filename, mute=True, throws=False):
    try:
        os.remove(filename)
    except Exception as e:
        if throws:
            raise e
        else:
            if not mute:
                print("remove file err ", filename, str(e));


def beans_to_arrays(beans, names):
    _out = {}
    for bean in beans:
        for name in names:
            val = read_dict(bean, name)
            if name not in _out:
                _out[name] = []

            array = _out[name]
            array.append(val)

    out = []
    for name in names:
        val = read_dict(_out, name)
        out.append(val)

    return out


def read_datetime(obj, name):
    start = get_dict_val(obj, name)
    if start is not None and len(start) > 0:
        return to_datetime(start)

    return None


def read_int(obj, name):
    value = get_dict_val(obj, name)
    if is_not_blank(value):
        return int(value)

    return None


def get_sys_tick():
    # a = win32api.GetTickCount()
    return int(time.time() * 1000)

    # return a
    # return int(time.time() * 1000)


def get_local_time_ms():
    return int(time.time() * 1000)


K1 = 1024
M1 = 1024 * 1024


def cal_buff_size(s):
    if s < K1:
        return "{}B".format(s)
    elif K1 <= s < M1:
        return "{:.1f}K".format(s / K1)
    else:
        return "{:.1f}M".format(s / M1)


def convert_bool(v: str) -> bool:
    if v is None or len(v) == 0:
        return False
    if len(v.strip()) == 0:
        return False

    sm = v.lower()
    if sm == "1" or sm == "true" or sm == "y" or sm == "yes":
        return True
    elif sm == "0" or sm == "false" or sm == "n" or sm == "no":
        return False
    else:
        raise Exception("un wanted bool str: " + v)


class Struct(object):
    def __init__(self, data):
        for name, value in data.items():
            setattr(self, name, self._wrap(value))

    def _wrap(self, value):
        if isinstance(value, (tuple, list, set, frozenset)):
            return type(value)([self._wrap(v) for v in value])
        else:
            return Struct(value) if isinstance(value, dict) else value


def load_json_file_as_dict(fname):
    with open(fname, "r", encoding="utf-8") as f:
        return json.load(f)


def load_file(fname):
    with open(fname, "r", encoding="utf-8") as f:
        return f.read()


'''

replace {base_path} in value ,e.g.
  base_path = c:\\abc\\efg 
  "${base_path}\\a.cmd" ==> "c:\\abc\\efg\\a.cmd" 

'''

# def replace_base_path(base_path: str, value: str) -> str:
#     if value is None:
#         return None

#     if is_blank(base_path):
#         return value

#     if value.find("{base_path}") >= 0:
#         return value.replace("${base_path}", base_path)

#     return value

# if os.path.isabs( value ):
#     return value
#
# return os.path.join(base_path, value)


'''
Backup source_file to target directory `base_path` 
'''


def backup_file(source_file: str, base_path: str):
    config_base_path = os.path.dirname(source_file)
    basename = os.path.basename(source_file)
    filename, extension = os.path.splitext(basename)
    ts = get_timestamp()
    new_name = f'{filename}_{ts}{extension}'
    fullname = os.path.join(base_path, new_name)

    return shutil.copyfile(source_file, fullname)


def save_file(filename, buff):
    with open(filename, "wb") as f:
        f.write(buff)


def sanitize_filename(filename, replacement=''):
    """
     replace unsafe char in filename
    """
    # 使用正则表达式来匹配不安全的字符
    unsafe_chars = r'[/\?<>\\:*\|"\"]'
    # pattern = re.compile(f"[{unsafe_chars}]")

    return re.sub(unsafe_chars, replacement, filename)


def get_file_list(parent):
    out = []
    # parent not exist
    if not os.path.exists(parent):
        return out

    for filename in os.listdir(parent):
        file = os.path.join(parent, filename)
        isdir = os.path.isdir(file)
        if not isdir:
            t = os.path.getmtime(file)
            tt = datetime.fromtimestamp(t)
            size = file_size(file)
            out.append({"name": filename, "type": "file", "size": size, "modified": tt})
    return out


def read_process_stdout(process, lines):
    stdout_list = []
    i = 0
    while i < lines:
        if process.poll():
            break

        line = process.stdout.readline()
        # Check if the line is empty, indicating that the subprocess has finished
        if len(line) > 0:
            stdout_list.append(str(line))
            i = i + 1
    return stdout_list


def read_process_stderr(process, lines):
    stdout_list = []
    i = 0
    while i < lines:
        if process.poll():
            break

        line = process.stderr.readline()
        # Check if the line is empty, indicating that the subprocess has finished
        # if not line:
        if len(line) > 0:
            stdout_list.append(str(line))
            i = i + 1
    return stdout_list


def is_simple_type(var):
    return isinstance(var, (int, float, str, bool))


def dump_list(vals, rep=0):
    prefix = ' ' * rep
    for value in vals:
        if is_simple_type(value):
            print("{} - {}".format(prefix, value))
        elif isinstance(value, (list, set)):
            print("{} - ".format(prefix, ))
        elif isinstance(value, (dict)):
            print("{} - ".format(prefix))
            dump_dict(value, rep + 2)
        else:
            print("{} - {}".format(prefix, value))


def dump_dict(val, rep=0):
    prefix = ' ' * rep
    for name, value in val.items():
        if is_simple_type(value):
            print("{}{} : {}".format(prefix, name, value))
        elif isinstance(value, (list, set)):
            dump_list(value, rep + 2)
        elif isinstance(value, (dict)):
            print("{}{} :".format(prefix, name))
            dump_dict(value, rep + 2)
        else:
            print("{}{} : {}".format(prefix, name, value))


# def load_yaml_config(filename):
#     with open(filename, "r", encoding="utf-8") as f:
#         data = yaml.safe_load(f)
#         return data


def compress_folder(folder_path, output_filename):
    # 创建.tar.gz压缩包
    with tarfile.open(output_filename, 'w:gz') as tar:
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                tar.add(file_path, arcname=filename)


def get_tmp_dir():
    tempdir = tempfile.gettempdir()
    pathname = os.path.join(tempdir, 'backend-service')

    if not os.path.exists(pathname):
        os.makedirs(pathname)

    return pathname;

def get_user_home():
    user_home = os.environ.get('USERPROFILE', os.environ.get('HOME'))
    return user_home


tables = string.ascii_letters + string.digits


def get_rand_str(k=20) -> str:
    res = ''.join(random.choices(tables, k=k))
    return res



import shutil
import os

def clear_directory(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)  # 删除文件
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)  # 删除非空目录（慎用，会递归删除）
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')


