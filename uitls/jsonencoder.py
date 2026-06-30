import base64
import datetime
import json
import threading
from typing import List

from pandas import to_datetime

from uitls.syncutils import locked


class ObjectJsonEncoder:
    def get_class(self):
        """
        interface virtual function
        :return:
        """
        pass

    def match(self, clazz) -> bool:
        """
        interface virtual function
        :return:
        """
        return False

    def convert(self, obj):
        return None


class DefaultEncoder(ObjectJsonEncoder):


    def match(self, clazz) -> bool:
        return issubclass(clazz, (list, set))

    def convert(self, obj):
        if isinstance(obj, list):
            return obj
        if isinstance(obj, set):
            return list(obj)
        return None


class DatetimeEncoder(ObjectJsonEncoder):

    def match(self, clazz) -> bool:
        return issubclass(clazz, datetime.datetime)

    def convert(self, obj) -> dict:
        return obj.strftime('%Y-%m-%d %H:%M:%S.%f')


_datetimeEncoder = DatetimeEncoder()
_defaultEncoder = DefaultEncoder()


class EncoderCache:
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()

    @locked(lock="_lock")
    def get_encoder(self, clazz):
        if clazz in self._cache:
            return self._cache[clazz]
        return None

    @locked(lock="_lock")
    def set_encoder(self, clazz, encoder):
        self._cache[clazz] = encoder


class ComplexEncoderHelper:

    def __init__(self):
        self._cache = EncoderCache()
        self.registers: List[ObjectJsonEncoder] = []

    def register(self, encoder: ObjectJsonEncoder):
        self.registers.append(encoder)

    def _find_encoder(self, clazz):
        for r in self.registers:
            if r.match(clazz):
                return r

        return None

    def find_encoder(self, clazz) -> ObjectJsonEncoder:
        global _datetimeEncoder
        global _defaultEncoder

        if _defaultEncoder.match(clazz):
            return _defaultEncoder
        if _datetimeEncoder.match(clazz):
            return _datetimeEncoder

        return self._find_encoder(clazz)

    def convert(self, obj) -> any:
        clazz = obj.__class__
        encoder = self._cache.get_encoder(clazz)
        if encoder is None:
            encoder = self.find_encoder(clazz)
            if encoder is not None:
                self._cache.set_encoder(clazz, encoder)
            else:
                return None

        return encoder.convert(obj)


_complexEncoderHelper = ComplexEncoderHelper()


def register_encoder(encoder: ObjectJsonEncoder):
    global _complexEncoderHelper
    _complexEncoderHelper.register(encoder)


#
class ComplexEncoderEx(json.JSONEncoder):
    def default(self, obj):
        # print(" in default , ", obj.__class__, obj);
        global _complexEncoderHelper
        val = _complexEncoderHelper.convert(obj)
        if val is not None:
            return val
        else:
            if obj.__dict__ is not None:
                return obj.__dict__
            else:
                return super().default(obj)


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):

        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S.%f')
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, list):
            return obj
        elif isinstance(obj, bytes):
            # return f'base64:{base64.b64encode(obj).decode("utf-8")}'
            return base64.b64encode(obj).decode("utf-8")

        elif isinstance(obj, object):
            return obj.__dict__
        else:
            return super().default(obj)



def to_json_str2(obj):
    s = json.dumps(obj, cls=ComplexEncoderEx)
    return s


def to_json_str(obj):
    s = json.dumps(obj, cls=ComplexEncoder)
    return s


def json_to_dict(buff):
    return json.loads(buff)



def read_dict_val (obj, name):
    if name in obj:
        return obj[name]
    return None

def read_as_bytes (obj, name, encode="base64"):

    val = read_dict_val(obj, name)
    if val is None:
        return None

    if isinstance(val,bytes )  :
        return val

    if isinstance(val,str ):
        if encode == "base64":
            if val.startswith("base64:") :
                val = val[7:]
            return base64.b64decode( val )



    return val


def read_datetime(obj, name):
    start = read_dict_val(obj, name)
    if start is not None and len(start) > 0:
        return to_datetime(start)

    return None


def is_not_blank(value):
    pass


def read_int(obj, name):
    value = read_dict_val(obj, name)
    if is_not_blank(value):
        return int(value)

    return None


