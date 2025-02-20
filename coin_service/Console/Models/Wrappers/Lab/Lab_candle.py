
# This is an auto-generated model wrapper develope by LIN.
# This wrapper allow you to:
# - Set defaul using
# - Auto-fill the field of the model
# - Define some SQL relation over Register (preDropRegister)
# Feel free to rename the models, but don't rename db_table values or field names. 

from Console.Helper.Control import Ctrl
from Console.Models.Wrappers.Model import Model
from Console.Models.Lab_candle import *


class LabCandle15MWrapper(Model):
    
    lab_candle_15m_id = 'lab_candle_15m_id'
    lab_candle_15m_time = 'lab_candle_15m_time'
    lab_candle_15m_symbol = 'lab_candle_15m_symbol'
    lab_candle_15m_open_time = 'lab_candle_15m_open_time'
    lab_candle_15m_close_time = 'lab_candle_15m_close_time'
    lab_candle_15m_open = 'lab_candle_15m_open'
    lab_candle_15m_close = 'lab_candle_15m_close'
    lab_candle_15m_high = 'lab_candle_15m_high'
    lab_candle_15m_low = 'lab_candle_15m_low'
    lab_candle_15m_trades = 'lab_candle_15m_trades'
    lab_candle_15m_volume = 'lab_candle_15m_volume'
    lab_candle_15m_ema5 = 'lab_candle_15m_ema5'
    lab_candle_15m_ema9 = 'lab_candle_15m_ema9'
    lab_candle_15m_ema12 = 'lab_candle_15m_ema12'
    lab_candle_15m_ema13 = 'lab_candle_15m_ema13'
    lab_candle_15m_ema26 = 'lab_candle_15m_ema26'
    lab_candle_15m_macd = 'lab_candle_15m_macd'
    lab_candle_15m_signal = 'lab_candle_15m_signal'
    lab_candle_15m_histogram = 'lab_candle_15m_histogram'
    lab_candle_15m_signal7 = 'lab_candle_15m_signal7'
    lab_candle_15m_histogram7 = 'lab_candle_15m_histogram7'
    lab_candle_15m_signal4 = 'lab_candle_15m_signal4'
    lab_candle_15m_histogram4 = 'lab_candle_15m_histogram4'
    lab_candle_15m_signal5 = 'lab_candle_15m_signal5'
    lab_candle_15m_histogram5 = 'lab_candle_15m_histogram5'
    lab_candle_15m_signal6 = 'lab_candle_15m_signal6'
    lab_candle_15m_histogram6 = 'lab_candle_15m_histogram6'
    lab_candle_15m_signal2 = 'lab_candle_15m_signal2'
    lab_candle_15m_histogram2 = 'lab_candle_15m_histogram2'
    lab_candle_15m_signal3 = 'lab_candle_15m_signal3'
    lab_candle_15m_histogram3 = 'lab_candle_15m_histogram3'
    lab_candle_15m_startpoint = 'lab_candle_15m_startpoint'
    lab_candle_15m_avgu14 = 'lab_candle_15m_avgu14'
    lab_candle_15m_avgd14 = 'lab_candle_15m_avgd14'
    lab_candle_15m_rsi14 = 'lab_candle_15m_rsi14'
    lab_candle_15m_rsi_ema9 = 'lab_candle_15m_rsi_ema9'
    lab_candle_15m_rsi_ema5 = 'lab_candle_15m_rsi_ema5'
    lab_candle_15m_rsi_ema4 = 'lab_candle_15m_rsi_ema4'
    lab_candle_15m_rsi_wma = 'lab_candle_15m_rsi_wma'
    
    def __init__(self, using=None):
        if(using is None):
            using = Ctrl.get('control_lab_db', 'coin_lab_1_year')
        super().__init__(LabCandle15M, using)


class LabCandle1DWrapper(Model):
    
    
    lab_candle_1d_id = 'lab_candle_1d_id'
    lab_candle_1d_time = 'lab_candle_1d_time'
    lab_candle_1d_symbol = 'lab_candle_1d_symbol'
    lab_candle_1d_open_time = 'lab_candle_1d_open_time'
    lab_candle_1d_close_time = 'lab_candle_1d_close_time'
    lab_candle_1d_open = 'lab_candle_1d_open'
    lab_candle_1d_close = 'lab_candle_1d_close'
    lab_candle_1d_high = 'lab_candle_1d_high'
    lab_candle_1d_low = 'lab_candle_1d_low'
    lab_candle_1d_trades = 'lab_candle_1d_trades'
    lab_candle_1d_volume = 'lab_candle_1d_volume'
    lab_candle_1d_ema5 = 'lab_candle_1d_ema5'
    lab_candle_1d_ema9 = 'lab_candle_1d_ema9'
    lab_candle_1d_ema12 = 'lab_candle_1d_ema12'
    lab_candle_1d_ema13 = 'lab_candle_1d_ema13'
    lab_candle_1d_ema26 = 'lab_candle_1d_ema26'
    lab_candle_1d_macd = 'lab_candle_1d_macd'
    lab_candle_1d_signal = 'lab_candle_1d_signal'
    lab_candle_1d_histogram = 'lab_candle_1d_histogram'
    lab_candle_1d_signal7 = 'lab_candle_1d_signal7'
    lab_candle_1d_histogram7 = 'lab_candle_1d_histogram7'
    lab_candle_1d_signal4 = 'lab_candle_1d_signal4'
    lab_candle_1d_histogram4 = 'lab_candle_1d_histogram4'
    lab_candle_1d_signal5 = 'lab_candle_1d_signal5'
    lab_candle_1d_histogram5 = 'lab_candle_1d_histogram5'
    lab_candle_1d_signal6 = 'lab_candle_1d_signal6'
    lab_candle_1d_histogram6 = 'lab_candle_1d_histogram6'
    lab_candle_1d_signal2 = 'lab_candle_1d_signal2'
    lab_candle_1d_histogram2 = 'lab_candle_1d_histogram2'
    lab_candle_1d_signal3 = 'lab_candle_1d_signal3'
    lab_candle_1d_histogram3 = 'lab_candle_1d_histogram3'
    lab_candle_1d_startpoint = 'lab_candle_1d_startpoint'
    lab_candle_1d_avgu14 = 'lab_candle_1d_avgu14'
    lab_candle_1d_avgd14 = 'lab_candle_1d_avgd14'
    lab_candle_1d_rsi14 = 'lab_candle_1d_rsi14'
    lab_candle_1d_rsi_ema9 = 'lab_candle_1d_rsi_ema9'
    lab_candle_1d_rsi_ema5 = 'lab_candle_1d_rsi_ema5'
    lab_candle_1d_rsi_ema4 = 'lab_candle_1d_rsi_ema4'
    lab_candle_1d_rsi_wma = 'lab_candle_1d_rsi_wma'
    
    def __init__(self, using=None):
        if(using is None):
            using = Ctrl.get('control_lab_db', 'coin_lab_1_year')
        super().__init__(LabCandle1D, using)


class LabCandle1HWrapper(Model):
    
    
    lab_candle_1h_id = 'lab_candle_1h_id'
    lab_candle_1h_time = 'lab_candle_1h_time'
    lab_candle_1h_symbol = 'lab_candle_1h_symbol'
    lab_candle_1h_open_time = 'lab_candle_1h_open_time'
    lab_candle_1h_close_time = 'lab_candle_1h_close_time'
    lab_candle_1h_open = 'lab_candle_1h_open'
    lab_candle_1h_close = 'lab_candle_1h_close'
    lab_candle_1h_high = 'lab_candle_1h_high'
    lab_candle_1h_low = 'lab_candle_1h_low'
    lab_candle_1h_trades = 'lab_candle_1h_trades'
    lab_candle_1h_volume = 'lab_candle_1h_volume'
    lab_candle_1h_ema5 = 'lab_candle_1h_ema5'
    lab_candle_1h_ema9 = 'lab_candle_1h_ema9'
    lab_candle_1h_ema12 = 'lab_candle_1h_ema12'
    lab_candle_1h_ema13 = 'lab_candle_1h_ema13'
    lab_candle_1h_ema26 = 'lab_candle_1h_ema26'
    lab_candle_1h_macd = 'lab_candle_1h_macd'
    lab_candle_1h_signal = 'lab_candle_1h_signal'
    lab_candle_1h_histogram = 'lab_candle_1h_histogram'
    lab_candle_1h_signal7 = 'lab_candle_1h_signal7'
    lab_candle_1h_histogram7 = 'lab_candle_1h_histogram7'
    lab_candle_1h_signal4 = 'lab_candle_1h_signal4'
    lab_candle_1h_histogram4 = 'lab_candle_1h_histogram4'
    lab_candle_1h_signal5 = 'lab_candle_1h_signal5'
    lab_candle_1h_histogram5 = 'lab_candle_1h_histogram5'
    lab_candle_1h_signal6 = 'lab_candle_1h_signal6'
    lab_candle_1h_histogram6 = 'lab_candle_1h_histogram6'
    lab_candle_1h_signal2 = 'lab_candle_1h_signal2'
    lab_candle_1h_histogram2 = 'lab_candle_1h_histogram2'
    lab_candle_1h_signal3 = 'lab_candle_1h_signal3'
    lab_candle_1h_histogram3 = 'lab_candle_1h_histogram3'
    lab_candle_1h_startpoint = 'lab_candle_1h_startpoint'
    lab_candle_1h_avgu14 = 'lab_candle_1h_avgu14'
    lab_candle_1h_avgd14 = 'lab_candle_1h_avgd14'
    lab_candle_1h_rsi14 = 'lab_candle_1h_rsi14'
    lab_candle_1h_rsi_ema9 = 'lab_candle_1h_rsi_ema9'
    lab_candle_1h_rsi_ema5 = 'lab_candle_1h_rsi_ema5'
    lab_candle_1h_rsi_ema4 = 'lab_candle_1h_rsi_ema4'
    lab_candle_1h_rsi_wma = 'lab_candle_1h_rsi_wma'
    
    def __init__(self, using=None):
        if(using is None):
            using = Ctrl.get('control_lab_db', 'coin_lab_1_year')
        super().__init__(LabCandle1H, using)


class LabCandle1MWrapper(Model):
    
    
    lab_candle_1m_id = 'lab_candle_1m_id'
    lab_candle_1m_time = 'lab_candle_1m_time'
    lab_candle_1m_symbol = 'lab_candle_1m_symbol'
    lab_candle_1m_open_time = 'lab_candle_1m_open_time'
    lab_candle_1m_close_time = 'lab_candle_1m_close_time'
    lab_candle_1m_open = 'lab_candle_1m_open'
    lab_candle_1m_close = 'lab_candle_1m_close'
    lab_candle_1m_high = 'lab_candle_1m_high'
    lab_candle_1m_low = 'lab_candle_1m_low'
    lab_candle_1m_trades = 'lab_candle_1m_trades'
    lab_candle_1m_volume = 'lab_candle_1m_volume'
    lab_candle_1m_ema5 = 'lab_candle_1m_ema5'
    lab_candle_1m_ema9 = 'lab_candle_1m_ema9'
    lab_candle_1m_ema12 = 'lab_candle_1m_ema12'
    lab_candle_1m_ema13 = 'lab_candle_1m_ema13'
    lab_candle_1m_ema26 = 'lab_candle_1m_ema26'
    lab_candle_1m_macd = 'lab_candle_1m_macd'
    lab_candle_1m_signal = 'lab_candle_1m_signal'
    lab_candle_1m_histogram = 'lab_candle_1m_histogram'
    lab_candle_1m_signal7 = 'lab_candle_1m_signal7'
    lab_candle_1m_histogram7 = 'lab_candle_1m_histogram7'
    lab_candle_1m_signal4 = 'lab_candle_1m_signal4'
    lab_candle_1m_histogram4 = 'lab_candle_1m_histogram4'
    lab_candle_1m_signal5 = 'lab_candle_1m_signal5'
    lab_candle_1m_histogram5 = 'lab_candle_1m_histogram5'
    lab_candle_1m_signal6 = 'lab_candle_1m_signal6'
    lab_candle_1m_histogram6 = 'lab_candle_1m_histogram6'
    lab_candle_1m_signal2 = 'lab_candle_1m_signal2'
    lab_candle_1m_histogram2 = 'lab_candle_1m_histogram2'
    lab_candle_1m_signal3 = 'lab_candle_1m_signal3'
    lab_candle_1m_histogram3 = 'lab_candle_1m_histogram3'
    lab_candle_1m_startpoint = 'lab_candle_1m_startpoint'
    lab_candle_1m_avgu14 = 'lab_candle_1m_avgu14'
    lab_candle_1m_avgd14 = 'lab_candle_1m_avgd14'
    lab_candle_1m_rsi14 = 'lab_candle_1m_rsi14'
    lab_candle_1m_rsi_ema9 = 'lab_candle_1m_rsi_ema9'
    lab_candle_1m_rsi_ema5 = 'lab_candle_1m_rsi_ema5'
    lab_candle_1m_rsi_ema4 = 'lab_candle_1m_rsi_ema4'
    lab_candle_1m_rsi_wma = 'lab_candle_1m_rsi_wma'
    
    def __init__(self, using=None):
        if(using is None):
            using = Ctrl.get('control_lab_db', 'coin_lab_1_year')
        super().__init__(LabCandle1M, using)


class LabCandle1WWrapper(Model):
    
    
    lab_candle_1w_id = 'lab_candle_1w_id'
    lab_candle_1w_time = 'lab_candle_1w_time'
    lab_candle_1w_symbol = 'lab_candle_1w_symbol'
    lab_candle_1w_open_time = 'lab_candle_1w_open_time'
    lab_candle_1w_close_time = 'lab_candle_1w_close_time'
    lab_candle_1w_open = 'lab_candle_1w_open'
    lab_candle_1w_close = 'lab_candle_1w_close'
    lab_candle_1w_high = 'lab_candle_1w_high'
    lab_candle_1w_low = 'lab_candle_1w_low'
    lab_candle_1w_trades = 'lab_candle_1w_trades'
    lab_candle_1w_volume = 'lab_candle_1w_volume'
    lab_candle_1w_ema5 = 'lab_candle_1w_ema5'
    lab_candle_1w_ema9 = 'lab_candle_1w_ema9'
    lab_candle_1w_ema12 = 'lab_candle_1w_ema12'
    lab_candle_1w_ema13 = 'lab_candle_1w_ema13'
    lab_candle_1w_ema26 = 'lab_candle_1w_ema26'
    lab_candle_1w_macd = 'lab_candle_1w_macd'
    lab_candle_1w_signal = 'lab_candle_1w_signal'
    lab_candle_1w_histogram = 'lab_candle_1w_histogram'
    lab_candle_1w_signal7 = 'lab_candle_1w_signal7'
    lab_candle_1w_histogram7 = 'lab_candle_1w_histogram7'
    lab_candle_1w_signal4 = 'lab_candle_1w_signal4'
    lab_candle_1w_histogram4 = 'lab_candle_1w_histogram4'
    lab_candle_1w_signal5 = 'lab_candle_1w_signal5'
    lab_candle_1w_histogram5 = 'lab_candle_1w_histogram5'
    lab_candle_1w_signal6 = 'lab_candle_1w_signal6'
    lab_candle_1w_histogram6 = 'lab_candle_1w_histogram6'
    lab_candle_1w_signal2 = 'lab_candle_1w_signal2'
    lab_candle_1w_histogram2 = 'lab_candle_1w_histogram2'
    lab_candle_1w_signal3 = 'lab_candle_1w_signal3'
    lab_candle_1w_histogram3 = 'lab_candle_1w_histogram3'
    lab_candle_1w_startpoint = 'lab_candle_1w_startpoint'
    lab_candle_1w_avgu14 = 'lab_candle_1w_avgu14'
    lab_candle_1w_avgd14 = 'lab_candle_1w_avgd14'
    lab_candle_1w_rsi14 = 'lab_candle_1w_rsi14'
    lab_candle_1w_rsi_ema9 = 'lab_candle_1w_rsi_ema9'
    lab_candle_1w_rsi_ema5 = 'lab_candle_1w_rsi_ema5'
    lab_candle_1w_rsi_ema4 = 'lab_candle_1w_rsi_ema4'
    lab_candle_1w_rsi_wma = 'lab_candle_1w_rsi_wma'
    
    def __init__(self, using=None):
        if(using is None):
            using = Ctrl.get('control_lab_db', 'coin_lab_1_year')
        super().__init__(LabCandle1W, using)


class LabCandle3MWrapper(Model):
    
    
    lab_candle_3m_id = 'lab_candle_3m_id'
    lab_candle_3m_time = 'lab_candle_3m_time'
    lab_candle_3m_symbol = 'lab_candle_3m_symbol'
    lab_candle_3m_open_time = 'lab_candle_3m_open_time'
    lab_candle_3m_close_time = 'lab_candle_3m_close_time'
    lab_candle_3m_open = 'lab_candle_3m_open'
    lab_candle_3m_close = 'lab_candle_3m_close'
    lab_candle_3m_high = 'lab_candle_3m_high'
    lab_candle_3m_low = 'lab_candle_3m_low'
    lab_candle_3m_trades = 'lab_candle_3m_trades'
    lab_candle_3m_volume = 'lab_candle_3m_volume'
    lab_candle_3m_ema5 = 'lab_candle_3m_ema5'
    lab_candle_3m_ema9 = 'lab_candle_3m_ema9'
    lab_candle_3m_ema12 = 'lab_candle_3m_ema12'
    lab_candle_3m_ema13 = 'lab_candle_3m_ema13'
    lab_candle_3m_ema26 = 'lab_candle_3m_ema26'
    lab_candle_3m_macd = 'lab_candle_3m_macd'
    lab_candle_3m_signal = 'lab_candle_3m_signal'
    lab_candle_3m_histogram = 'lab_candle_3m_histogram'
    lab_candle_3m_signal7 = 'lab_candle_3m_signal7'
    lab_candle_3m_histogram7 = 'lab_candle_3m_histogram7'
    lab_candle_3m_signal4 = 'lab_candle_3m_signal4'
    lab_candle_3m_histogram4 = 'lab_candle_3m_histogram4'
    lab_candle_3m_signal5 = 'lab_candle_3m_signal5'
    lab_candle_3m_histogram5 = 'lab_candle_3m_histogram5'
    lab_candle_3m_signal6 = 'lab_candle_3m_signal6'
    lab_candle_3m_histogram6 = 'lab_candle_3m_histogram6'
    lab_candle_3m_signal2 = 'lab_candle_3m_signal2'
    lab_candle_3m_histogram2 = 'lab_candle_3m_histogram2'
    lab_candle_3m_signal3 = 'lab_candle_3m_signal3'
    lab_candle_3m_histogram3 = 'lab_candle_3m_histogram3'
    lab_candle_3m_startpoint = 'lab_candle_3m_startpoint'
    lab_candle_3m_avgu14 = 'lab_candle_3m_avgu14'
    lab_candle_3m_avgd14 = 'lab_candle_3m_avgd14'
    lab_candle_3m_rsi14 = 'lab_candle_3m_rsi14'
    lab_candle_3m_rsi_ema9 = 'lab_candle_3m_rsi_ema9'
    lab_candle_3m_rsi_ema5 = 'lab_candle_3m_rsi_ema5'
    lab_candle_3m_rsi_ema4 = 'lab_candle_3m_rsi_ema4'
    lab_candle_3m_rsi_wma = 'lab_candle_3m_rsi_wma'
    
    def __init__(self, using=None):
        if(using is None):
            using = Ctrl.get('control_lab_db', 'coin_lab_1_year')
        super().__init__(LabCandle3M, using)


class LabCandle4HWrapper(Model):
    
    
    lab_candle_4h_id = 'lab_candle_4h_id'
    lab_candle_4h_time = 'lab_candle_4h_time'
    lab_candle_4h_symbol = 'lab_candle_4h_symbol'
    lab_candle_4h_open_time = 'lab_candle_4h_open_time'
    lab_candle_4h_close_time = 'lab_candle_4h_close_time'
    lab_candle_4h_open = 'lab_candle_4h_open'
    lab_candle_4h_close = 'lab_candle_4h_close'
    lab_candle_4h_high = 'lab_candle_4h_high'
    lab_candle_4h_low = 'lab_candle_4h_low'
    lab_candle_4h_trades = 'lab_candle_4h_trades'
    lab_candle_4h_volume = 'lab_candle_4h_volume'
    lab_candle_4h_ema5 = 'lab_candle_4h_ema5'
    lab_candle_4h_ema9 = 'lab_candle_4h_ema9'
    lab_candle_4h_ema12 = 'lab_candle_4h_ema12'
    lab_candle_4h_ema13 = 'lab_candle_4h_ema13'
    lab_candle_4h_ema26 = 'lab_candle_4h_ema26'
    lab_candle_4h_macd = 'lab_candle_4h_macd'
    lab_candle_4h_signal = 'lab_candle_4h_signal'
    lab_candle_4h_histogram = 'lab_candle_4h_histogram'
    lab_candle_4h_signal7 = 'lab_candle_4h_signal7'
    lab_candle_4h_histogram7 = 'lab_candle_4h_histogram7'
    lab_candle_4h_signal4 = 'lab_candle_4h_signal4'
    lab_candle_4h_histogram4 = 'lab_candle_4h_histogram4'
    lab_candle_4h_signal5 = 'lab_candle_4h_signal5'
    lab_candle_4h_histogram5 = 'lab_candle_4h_histogram5'
    lab_candle_4h_signal6 = 'lab_candle_4h_signal6'
    lab_candle_4h_histogram6 = 'lab_candle_4h_histogram6'
    lab_candle_4h_signal2 = 'lab_candle_4h_signal2'
    lab_candle_4h_histogram2 = 'lab_candle_4h_histogram2'
    lab_candle_4h_signal3 = 'lab_candle_4h_signal3'
    lab_candle_4h_histogram3 = 'lab_candle_4h_histogram3'
    lab_candle_4h_startpoint = 'lab_candle_4h_startpoint'
    lab_candle_4h_avgu14 = 'lab_candle_4h_avgu14'
    lab_candle_4h_avgd14 = 'lab_candle_4h_avgd14'
    lab_candle_4h_rsi14 = 'lab_candle_4h_rsi14'
    lab_candle_4h_rsi_ema9 = 'lab_candle_4h_rsi_ema9'
    lab_candle_4h_rsi_ema5 = 'lab_candle_4h_rsi_ema5'
    lab_candle_4h_rsi_ema4 = 'lab_candle_4h_rsi_ema4'
    lab_candle_4h_rsi_wma = 'lab_candle_4h_rsi_wma'
    
    def __init__(self, using=None):
        if(using is None):
            using = Ctrl.get('control_lab_db', 'coin_lab_1_year')
        super().__init__(LabCandle4H, using)

