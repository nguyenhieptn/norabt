import re
import string
from unicodedata import numeric


def isset(array, index):
    try:
        val = array[index]
        if(val is None): return False
        return True
    except Exception:
        return False

def get(array, index, default=None):
    if(isset(array,index)):
        return array[index]
    else:
        return default

def isNumeric(val):
    try:
        float(val)
        return True
    except Exception:
        return False

def isInterger(val):
    if(type(val) is float): return False
    try:
        int(val)
        return True
    except Exception:
        return False

def Number(val):
    if(type(val) is int): return val
    if(type(val) is float): return val
    if(val is None): return 0
    if(val == ""): return 0
    if(isInterger(val)): return int(val)
    if(isNumeric(val)): return float(val)

def Round(val, demical=0):
    val = Number(val)
    if(demical>0): val = val*10**demical
    if(val % 1 >= 0.5): 
        val = int(val) + 1
    else:
        val = int(val)
    if(demical > 0): val = val/(10**demical)
    return val
    

def str2num(exp:str):
    regex = r"^[\d\+\-\*\/\(\)\.\ ]+$"
    matches = re.search(regex, exp)
    if(matches is None):
        raise Exception('Input string is dangerous')
    else:
        return(Number(eval(matches[0])))


def exceptionInfo(e:Exception):
    tb = e.__traceback__
    errorInfo = None
    while tb is not None:
        errorInfo = {
            "message": str(e),
            "file": tb.tb_frame.f_code.co_filename,
            "name": tb.tb_frame.f_code.co_name,
            "line": tb.tb_lineno
        }
        tb = tb.tb_next
    return errorInfo


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
    