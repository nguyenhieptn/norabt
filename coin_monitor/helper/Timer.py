from dateutil import tz
from datetime import datetime, timedelta

holiday = [
]

maturity = [
]

afterMaturity = [
]


def timeInDate(timestamp=None):
    if(timestamp is None):
        today = datetime.now()
    else:
        today = datetime.fromtimestamp(timestamp)
    value = today.strftime('%H:%M:%S')
    return value



def is_maturity_date(timestamp=None):
    if(timestamp is None):
        date = datetime.now()
    else:
        date = datetime.fromtimestamp(timestamp)
    # Kiểm tra xem ngày hiện tại có phải là ngày thứ 6 cuối cùng của quý hay không
    if date.weekday() == 4 and date.month % 3 == 0 and date.day > 24:
        return True
    else:
        return False

def is_maturity_after(timestamp = None):
    if(timestamp is None):
        date = datetime.now()
    else:
        date = datetime.fromtimestamp(timestamp)
    
    timeString = date.strftime('%d/%m/%Y')
    if(timeString in afterMaturity): return True
    yesterday = date - timedelta(days=1)
    return is_maturity_date(yesterday.timestamp())


ms_per_unit = {"s": 1000, "m": 60000, "h": 3600000, "d": 86400000, "w": 604800000}
def str2ms(s):
    return int(s[:-1]) * ms_per_unit[s[-1]]
        

    


