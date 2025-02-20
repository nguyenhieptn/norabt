import math
import numpy as np

def ema(pre_ema, value, N, values=None):
    if(pre_ema is None or math.isnan(pre_ema)): 
        if(values is None): return value
        if(len(values) < N): return None
        calList = values[-N:]
        if(None in calList): return None
        return sum(calList)/N
        
    multiplier = 2.0/(N+1)

    return pre_ema*(1.0-multiplier) + value*multiplier


def rsi(periodValue, periodAvgU, periodAvgD, value, N, values=None):

    '''
    @return 
        `'avgU': 0,
        'avgD': 0,
        'rsi': 100
        `
    '''
    if(periodValue is not None and periodAvgD is not None and periodAvgU is not None):
        Ut = 0
        Dt = 0
        if(value > periodValue):
            Ut = value - periodValue
        else:
            Dt = periodValue - value
        avgU = 1 / N * Ut + (1 - 1 / N) * periodAvgU
        avgD = 1 / N * Dt + (1 - 1 / N) * periodAvgD
        

    else:
        if(values is None):
            return {
                'avgU': 0,
                'avgD': 0,
                'rsi': 100
            }
        if(len(values) <= N): 
            return {
                'avgU': None,
                'avgD': None,
                'rsi': None
            }
        calList = values[-N-1:]
        if(None in calList): 
            return {
                'avgU': None,
                'avgD': None,
                'rsi': None
            }
        tempNp = np.array(calList)
        tempNpDiff = np.diff(tempNp)
        avgU = tempNpDiff[tempNpDiff > 0].sum()/N
        avgD = tempNpDiff[tempNpDiff < 0].sum()/-N
        

    if (not avgD == 0):
        RS = avgU / avgD
        RSI = 100 - 100 / (1 + RS)
    else:
        RSI = 100
    
    return {
        'avgU': avgU,
        'avgD': avgD,
        'rsi': RSI
    }


def wma(N, values):
    if(len(values) < N): return None
    calList = values[-N:]
    if(None in calList): return None
    bottom = np.arange(1, N + 1, 1)
    top = bottom * calList
    wma = (top.sum()) / (bottom.sum())
    return wma

        