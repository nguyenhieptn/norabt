
# This is an auto-generated model wrapper singleton develope by LIN.
# This wrapper allow you to:
# - Set defaul using
# - Auto-fill the field of the model
# - Define some SQL relation over Register (preDropRegister)
# Feel free to rename the models, but don't rename db_table values or field names. 

from Console.Models.Wrappers.Model import Model
from Console.Models.Coin_testnet import *


class AuthenticationWrapper(Model):
    
    authen_id = 'authen_id'
    authen_username = 'authen_username'
    authen_email = 'authen_email'
    authen_phone = 'authen_phone'
    authen_pass = 'authen_pass'
    authen_token = 'authen_token'
    authen_group = 'authen_group'
    authen_note = 'authen_note'
    authen_parent = 'authen_parent'
    authen_time = 'authen_time'
    authen_online = 'authen_online'
    authen_active = 'authen_active'
    authen_status = 'authen_status'
    authen_img = 'authen_img'
    
    def __init__(self):
        super().__init__(Authentication, 'testnet')


class Candle15MWrapper(Model):
    
    candle_15m_id = 'candle_15m_id'
    candle_15m_symbol = 'candle_15m_symbol'
    candle_15m_open_time = 'candle_15m_open_time'
    candle_15m_close_time = 'candle_15m_close_time'
    candle_15m_open = 'candle_15m_open'
    candle_15m_close = 'candle_15m_close'
    candle_15m_high = 'candle_15m_high'
    candle_15m_low = 'candle_15m_low'
    candle_15m_trades = 'candle_15m_trades'
    candle_15m_volume = 'candle_15m_volume'
    candle_15m_ema5 = 'candle_15m_ema5'
    candle_15m_ema9 = 'candle_15m_ema9'
    candle_15m_ema12 = 'candle_15m_ema12'
    candle_15m_ema13 = 'candle_15m_ema13'
    candle_15m_ema26 = 'candle_15m_ema26'
    candle_15m_macd = 'candle_15m_macd'
    candle_15m_signal = 'candle_15m_signal'
    candle_15m_histogram = 'candle_15m_histogram'
    candle_15m_signal7 = 'candle_15m_signal7'
    candle_15m_histogram7 = 'candle_15m_histogram7'
    candle_15m_signal4 = 'candle_15m_signal4'
    candle_15m_histogram4 = 'candle_15m_histogram4'
    candle_15m_signal5 = 'candle_15m_signal5'
    candle_15m_histogram5 = 'candle_15m_histogram5'
    candle_15m_signal6 = 'candle_15m_signal6'
    candle_15m_histogram6 = 'candle_15m_histogram6'
    candle_15m_signal2 = 'candle_15m_signal2'
    candle_15m_histogram2 = 'candle_15m_histogram2'
    candle_15m_signal3 = 'candle_15m_signal3'
    candle_15m_histogram3 = 'candle_15m_histogram3'
    candle_15m_avgu14 = 'candle_15m_avgu14'
    candle_15m_avgd14 = 'candle_15m_avgd14'
    candle_15m_rsi14 = 'candle_15m_rsi14'
    candle_15m_rsi_ema9 = 'candle_15m_rsi_ema9'
    candle_15m_rsi_ema5 = 'candle_15m_rsi_ema5'
    candle_15m_rsi_ema4 = 'candle_15m_rsi_ema4'
    candle_15m_rsi_wma = 'candle_15m_rsi_wma'
    
    def __init__(self):
        super().__init__(Candle15M, 'testnet')


class Candle1DWrapper(Model):
    
    candle_1d_id = 'candle_1d_id'
    candle_1d_symbol = 'candle_1d_symbol'
    candle_1d_open_time = 'candle_1d_open_time'
    candle_1d_close_time = 'candle_1d_close_time'
    candle_1d_open = 'candle_1d_open'
    candle_1d_close = 'candle_1d_close'
    candle_1d_high = 'candle_1d_high'
    candle_1d_low = 'candle_1d_low'
    candle_1d_trades = 'candle_1d_trades'
    candle_1d_volume = 'candle_1d_volume'
    candle_1d_ema5 = 'candle_1d_ema5'
    candle_1d_ema9 = 'candle_1d_ema9'
    candle_1d_ema12 = 'candle_1d_ema12'
    candle_1d_ema13 = 'candle_1d_ema13'
    candle_1d_ema26 = 'candle_1d_ema26'
    candle_1d_macd = 'candle_1d_macd'
    candle_1d_signal = 'candle_1d_signal'
    candle_1d_histogram = 'candle_1d_histogram'
    candle_1d_signal7 = 'candle_1d_signal7'
    candle_1d_histogram7 = 'candle_1d_histogram7'
    candle_1d_signal4 = 'candle_1d_signal4'
    candle_1d_histogram4 = 'candle_1d_histogram4'
    candle_1d_signal5 = 'candle_1d_signal5'
    candle_1d_histogram5 = 'candle_1d_histogram5'
    candle_1d_signal6 = 'candle_1d_signal6'
    candle_1d_histogram6 = 'candle_1d_histogram6'
    candle_1d_signal2 = 'candle_1d_signal2'
    candle_1d_histogram2 = 'candle_1d_histogram2'
    candle_1d_signal3 = 'candle_1d_signal3'
    candle_1d_histogram3 = 'candle_1d_histogram3'
    candle_1d_avgu14 = 'candle_1d_avgu14'
    candle_1d_avgd14 = 'candle_1d_avgd14'
    candle_1d_rsi14 = 'candle_1d_rsi14'
    candle_1d_rsi_ema9 = 'candle_1d_rsi_ema9'
    candle_1d_rsi_ema5 = 'candle_1d_rsi_ema5'
    candle_1d_rsi_ema4 = 'candle_1d_rsi_ema4'
    candle_1d_rsi_wma = 'candle_1d_rsi_wma'
    
    def __init__(self):
        super().__init__(Candle1D, 'testnet')


class Candle1HWrapper(Model):
    
    candle_1h_id = 'candle_1h_id'
    candle_1h_symbol = 'candle_1h_symbol'
    candle_1h_open_time = 'candle_1h_open_time'
    candle_1h_close_time = 'candle_1h_close_time'
    candle_1h_open = 'candle_1h_open'
    candle_1h_close = 'candle_1h_close'
    candle_1h_high = 'candle_1h_high'
    candle_1h_low = 'candle_1h_low'
    candle_1h_trades = 'candle_1h_trades'
    candle_1h_volume = 'candle_1h_volume'
    candle_1h_ema5 = 'candle_1h_ema5'
    candle_1h_ema9 = 'candle_1h_ema9'
    candle_1h_ema12 = 'candle_1h_ema12'
    candle_1h_ema13 = 'candle_1h_ema13'
    candle_1h_ema26 = 'candle_1h_ema26'
    candle_1h_macd = 'candle_1h_macd'
    candle_1h_signal = 'candle_1h_signal'
    candle_1h_histogram = 'candle_1h_histogram'
    candle_1h_signal7 = 'candle_1h_signal7'
    candle_1h_histogram7 = 'candle_1h_histogram7'
    candle_1h_signal4 = 'candle_1h_signal4'
    candle_1h_histogram4 = 'candle_1h_histogram4'
    candle_1h_signal5 = 'candle_1h_signal5'
    candle_1h_histogram5 = 'candle_1h_histogram5'
    candle_1h_signal6 = 'candle_1h_signal6'
    candle_1h_histogram6 = 'candle_1h_histogram6'
    candle_1h_signal2 = 'candle_1h_signal2'
    candle_1h_histogram2 = 'candle_1h_histogram2'
    candle_1h_signal3 = 'candle_1h_signal3'
    candle_1h_histogram3 = 'candle_1h_histogram3'
    candle_1h_avgu14 = 'candle_1h_avgu14'
    candle_1h_avgd14 = 'candle_1h_avgd14'
    candle_1h_rsi14 = 'candle_1h_rsi14'
    candle_1h_rsi_ema9 = 'candle_1h_rsi_ema9'
    candle_1h_rsi_ema5 = 'candle_1h_rsi_ema5'
    candle_1h_rsi_ema4 = 'candle_1h_rsi_ema4'
    candle_1h_rsi_wma = 'candle_1h_rsi_wma'
    
    def __init__(self):
        super().__init__(Candle1H, 'testnet')


class Candle1MWrapper(Model):
    
    candle_1m_id = 'candle_1m_id'
    candle_1m_symbol = 'candle_1m_symbol'
    candle_1m_open_time = 'candle_1m_open_time'
    candle_1m_close_time = 'candle_1m_close_time'
    candle_1m_open = 'candle_1m_open'
    candle_1m_close = 'candle_1m_close'
    candle_1m_high = 'candle_1m_high'
    candle_1m_low = 'candle_1m_low'
    candle_1m_trades = 'candle_1m_trades'
    candle_1m_volume = 'candle_1m_volume'
    candle_1m_ema5 = 'candle_1m_ema5'
    candle_1m_ema9 = 'candle_1m_ema9'
    candle_1m_ema12 = 'candle_1m_ema12'
    candle_1m_ema13 = 'candle_1m_ema13'
    candle_1m_ema26 = 'candle_1m_ema26'
    candle_1m_macd = 'candle_1m_macd'
    candle_1m_signal = 'candle_1m_signal'
    candle_1m_histogram = 'candle_1m_histogram'
    candle_1m_signal7 = 'candle_1m_signal7'
    candle_1m_histogram7 = 'candle_1m_histogram7'
    candle_1m_signal4 = 'candle_1m_signal4'
    candle_1m_histogram4 = 'candle_1m_histogram4'
    candle_1m_signal5 = 'candle_1m_signal5'
    candle_1m_histogram5 = 'candle_1m_histogram5'
    candle_1m_signal6 = 'candle_1m_signal6'
    candle_1m_histogram6 = 'candle_1m_histogram6'
    candle_1m_signal2 = 'candle_1m_signal2'
    candle_1m_histogram2 = 'candle_1m_histogram2'
    candle_1m_signal3 = 'candle_1m_signal3'
    candle_1m_histogram3 = 'candle_1m_histogram3'
    candle_1m_avgu14 = 'candle_1m_avgu14'
    candle_1m_avgd14 = 'candle_1m_avgd14'
    candle_1m_rsi14 = 'candle_1m_rsi14'
    candle_1m_rsi_ema9 = 'candle_1m_rsi_ema9'
    candle_1m_rsi_ema5 = 'candle_1m_rsi_ema5'
    candle_1m_rsi_ema4 = 'candle_1m_rsi_ema4'
    candle_1m_rsi_wma = 'candle_1m_rsi_wma'
    
    def __init__(self):
        super().__init__(Candle1M, 'testnet')


class Candle1WWrapper(Model):
    
    candle_1w_id = 'candle_1w_id'
    candle_1w_symbol = 'candle_1w_symbol'
    candle_1w_open_time = 'candle_1w_open_time'
    candle_1w_close_time = 'candle_1w_close_time'
    candle_1w_open = 'candle_1w_open'
    candle_1w_close = 'candle_1w_close'
    candle_1w_high = 'candle_1w_high'
    candle_1w_low = 'candle_1w_low'
    candle_1w_trades = 'candle_1w_trades'
    candle_1w_volume = 'candle_1w_volume'
    candle_1w_ema5 = 'candle_1w_ema5'
    candle_1w_ema9 = 'candle_1w_ema9'
    candle_1w_ema12 = 'candle_1w_ema12'
    candle_1w_ema13 = 'candle_1w_ema13'
    candle_1w_ema26 = 'candle_1w_ema26'
    candle_1w_macd = 'candle_1w_macd'
    candle_1w_signal = 'candle_1w_signal'
    candle_1w_histogram = 'candle_1w_histogram'
    candle_1w_signal7 = 'candle_1w_signal7'
    candle_1w_histogram7 = 'candle_1w_histogram7'
    candle_1w_signal4 = 'candle_1w_signal4'
    candle_1w_histogram4 = 'candle_1w_histogram4'
    candle_1w_signal5 = 'candle_1w_signal5'
    candle_1w_histogram5 = 'candle_1w_histogram5'
    candle_1w_signal6 = 'candle_1w_signal6'
    candle_1w_histogram6 = 'candle_1w_histogram6'
    candle_1w_signal2 = 'candle_1w_signal2'
    candle_1w_histogram2 = 'candle_1w_histogram2'
    candle_1w_signal3 = 'candle_1w_signal3'
    candle_1w_histogram3 = 'candle_1w_histogram3'
    candle_1w_avgu14 = 'candle_1w_avgu14'
    candle_1w_avgd14 = 'candle_1w_avgd14'
    candle_1w_rsi14 = 'candle_1w_rsi14'
    candle_1w_rsi_ema9 = 'candle_1w_rsi_ema9'
    candle_1w_rsi_ema5 = 'candle_1w_rsi_ema5'
    candle_1w_rsi_ema4 = 'candle_1w_rsi_ema4'
    candle_1w_rsi_wma = 'candle_1w_rsi_wma'
    
    def __init__(self):
        super().__init__(Candle1W, 'testnet')


class Candle3MWrapper(Model):
    
    candle_3m_id = 'candle_3m_id'
    candle_3m_symbol = 'candle_3m_symbol'
    candle_3m_open_time = 'candle_3m_open_time'
    candle_3m_close_time = 'candle_3m_close_time'
    candle_3m_open = 'candle_3m_open'
    candle_3m_close = 'candle_3m_close'
    candle_3m_high = 'candle_3m_high'
    candle_3m_low = 'candle_3m_low'
    candle_3m_trades = 'candle_3m_trades'
    candle_3m_volume = 'candle_3m_volume'
    candle_3m_ema5 = 'candle_3m_ema5'
    candle_3m_ema9 = 'candle_3m_ema9'
    candle_3m_ema12 = 'candle_3m_ema12'
    candle_3m_ema13 = 'candle_3m_ema13'
    candle_3m_ema26 = 'candle_3m_ema26'
    candle_3m_macd = 'candle_3m_macd'
    candle_3m_signal = 'candle_3m_signal'
    candle_3m_histogram = 'candle_3m_histogram'
    candle_3m_signal7 = 'candle_3m_signal7'
    candle_3m_histogram7 = 'candle_3m_histogram7'
    candle_3m_signal4 = 'candle_3m_signal4'
    candle_3m_histogram4 = 'candle_3m_histogram4'
    candle_3m_signal5 = 'candle_3m_signal5'
    candle_3m_histogram5 = 'candle_3m_histogram5'
    candle_3m_signal6 = 'candle_3m_signal6'
    candle_3m_histogram6 = 'candle_3m_histogram6'
    candle_3m_signal2 = 'candle_3m_signal2'
    candle_3m_histogram2 = 'candle_3m_histogram2'
    candle_3m_signal3 = 'candle_3m_signal3'
    candle_3m_histogram3 = 'candle_3m_histogram3'
    candle_3m_avgu14 = 'candle_3m_avgu14'
    candle_3m_avgd14 = 'candle_3m_avgd14'
    candle_3m_rsi14 = 'candle_3m_rsi14'
    candle_3m_rsi_ema9 = 'candle_3m_rsi_ema9'
    candle_3m_rsi_ema5 = 'candle_3m_rsi_ema5'
    candle_3m_rsi_ema4 = 'candle_3m_rsi_ema4'
    candle_3m_rsi_wma = 'candle_3m_rsi_wma'
    
    def __init__(self):
        super().__init__(Candle3M, 'testnet')


class Candle4HWrapper(Model):
    
    candle_4h_id = 'candle_4h_id'
    candle_4h_symbol = 'candle_4h_symbol'
    candle_4h_open_time = 'candle_4h_open_time'
    candle_4h_close_time = 'candle_4h_close_time'
    candle_4h_open = 'candle_4h_open'
    candle_4h_close = 'candle_4h_close'
    candle_4h_high = 'candle_4h_high'
    candle_4h_low = 'candle_4h_low'
    candle_4h_trades = 'candle_4h_trades'
    candle_4h_volume = 'candle_4h_volume'
    candle_4h_ema5 = 'candle_4h_ema5'
    candle_4h_ema9 = 'candle_4h_ema9'
    candle_4h_ema12 = 'candle_4h_ema12'
    candle_4h_ema13 = 'candle_4h_ema13'
    candle_4h_ema26 = 'candle_4h_ema26'
    candle_4h_macd = 'candle_4h_macd'
    candle_4h_signal = 'candle_4h_signal'
    candle_4h_histogram = 'candle_4h_histogram'
    candle_4h_signal7 = 'candle_4h_signal7'
    candle_4h_histogram7 = 'candle_4h_histogram7'
    candle_4h_signal4 = 'candle_4h_signal4'
    candle_4h_histogram4 = 'candle_4h_histogram4'
    candle_4h_signal5 = 'candle_4h_signal5'
    candle_4h_histogram5 = 'candle_4h_histogram5'
    candle_4h_signal6 = 'candle_4h_signal6'
    candle_4h_histogram6 = 'candle_4h_histogram6'
    candle_4h_signal2 = 'candle_4h_signal2'
    candle_4h_histogram2 = 'candle_4h_histogram2'
    candle_4h_signal3 = 'candle_4h_signal3'
    candle_4h_histogram3 = 'candle_4h_histogram3'
    candle_4h_avgu14 = 'candle_4h_avgu14'
    candle_4h_avgd14 = 'candle_4h_avgd14'
    candle_4h_rsi14 = 'candle_4h_rsi14'
    candle_4h_rsi_ema9 = 'candle_4h_rsi_ema9'
    candle_4h_rsi_ema5 = 'candle_4h_rsi_ema5'
    candle_4h_rsi_ema4 = 'candle_4h_rsi_ema4'
    candle_4h_rsi_wma = 'candle_4h_rsi_wma'
    
    def __init__(self):
        super().__init__(Candle4H, 'testnet')


class Change24HWrapper(Model):
    
    change24h_id = 'change24h_id'
    change24h_time = 'change24h_time'
    change24h_total = 'change24h_total'
    change24h_down = 'change24h_down'
    change24h_up = 'change24h_up'
    change24h_up50 = 'change24h_up50'
    change24h_down50 = 'change24h_down50'
    change24h_keep50 = 'change24h_keep50'
    change24h_keep = 'change24h_keep'
    change24h_btc_change = 'change24h_btc_change'
    change24h_btc_up = 'change24h_btc_up'
    change24h_btc_down = 'change24h_btc_down'
    change24h_btc_keep = 'change24h_btc_keep'
    change24h_up_10 = 'change24h_up_10'
    change24h_up_7_10 = 'change24h_up_7_10'
    change24h_up_5_7 = 'change24h_up_5_7'
    change24h_up_3_5 = 'change24h_up_3_5'
    change24h_up_0_3 = 'change24h_up_0_3'
    change24h_down_0_3 = 'change24h_down_0_3'
    change24h_down_3_5 = 'change24h_down_3_5'
    change24h_down_5_7 = 'change24h_down_5_7'
    change24h_down_7_10 = 'change24h_down_7_10'
    change24h_down_10 = 'change24h_down_10'
    change24h_data = 'change24h_data'
    change24h_5m_up = 'change24h_5m_up'
    change24h_5m_down = 'change24h_5m_down'
    change24h_15m_up = 'change24h_15m_up'
    change24h_15m_down = 'change24h_15m_down'
    change24h_1h_up = 'change24h_1h_up'
    change24h_1h_down = 'change24h_1h_down'
    change24h_4h_up = 'change24h_4h_up'
    change24h_4h_down = 'change24h_4h_down'
    change24h_up_ema5 = 'change24h_up_ema5'
    change24h_up_ema9 = 'change24h_up_ema9'
    change24h_up_ema13 = 'change24h_up_ema13'
    change24h_up50_ema5 = 'change24h_up50_ema5'
    change24h_up50_ema9 = 'change24h_up50_ema9'
    change24h_up50_ema13 = 'change24h_up50_ema13'
    
    def __init__(self):
        super().__init__(Change24H, 'testnet')


class CoinmarketWrapper(Model):
    
    coinmarket_id = 'coinmarket_id'
    coinmarket_symbol = 'coinmarket_symbol'
    coinmarket_price = 'coinmarket_price'
    coinmarket_percent_change_1h = 'coinmarket_percent_change_1h'
    coinmarket_percent_change_24h = 'coinmarket_percent_change_24h'
    coinmarket_percent_change_7d = 'coinmarket_percent_change_7d'
    coinmarket_percent_change_30d = 'coinmarket_percent_change_30d'
    coinmarket_market_cap = 'coinmarket_market_cap'
    coinmarket_volume_24h = 'coinmarket_volume_24h'
    coinmarket_rank = 'coinmarket_rank'
    coinmarket_last_updated = 'coinmarket_last_updated'
    
    def __init__(self):
        super().__init__(Coinmarket, 'testnet')


class EventLogsWrapper(Model):
    
    elog_id = 'elog_id'
    elog_symbol = 'elog_symbol'
    elog_time = 'elog_time'
    elog_chart = 'elog_chart'
    elog_result = 'elog_result'
    elog_matched = 'elog_matched'
    elog_base = 'elog_base'
    
    def __init__(self):
        super().__init__(EventLogs, 'testnet')


class EventsWrapper(Model):
    
    event_id = 'event_id'
    event_symbol = 'event_symbol'
    event_time = 'event_time'
    event_chart = 'event_chart'
    event_price = 'event_price'
    event_type = 'event_type'
    event_base = 'event_base'
    event_params = 'event_params'
    
    def __init__(self):
        super().__init__(Events, 'testnet')


class FearWrapper(Model):
    
    fear_id = 'fear_id'
    fear_time = 'fear_time'
    fear_value = 'fear_value'
    fear_class = 'fear_class'
    
    def __init__(self):
        super().__init__(Fear, 'testnet')


class OrderTrackWrapper(Model):
    
    order_track_id = 'order_track_id'
    order_track_symbol = 'order_track_symbol'
    order_track_price = 'order_track_price'
    order_track_low = 'order_track_low'
    order_track_high = 'order_track_high'
    order_track_up = 'order_track_up'
    order_track_down = 'order_track_down'
    order_track_close = 'order_track_close'
    order_track_change = 'order_track_change'
    order_track_1h_up = 'order_track_1h_up'
    order_track_1h_down = 'order_track_1h_down'
    order_track_15m_up = 'order_track_15m_up'
    order_track_15m_down = 'order_track_15m_down'
    order_track_3m_down = 'order_track_3m_down'
    order_track_3m_up = 'order_track_3m_up'
    order_track_rsi4h_0 = 'order_track_rsi4h_0'
    order_track_rsi4h_1 = 'order_track_rsi4h_1'
    order_track_rsi_ema9 = 'order_track_rsi_ema9'
    order_track_rsi1h_0 = 'order_track_rsi1h_0'
    order_track_rsi1h_1 = 'order_track_rsi1h_1'
    order_track_1d_rsi_wma = 'order_track_1d_rsi_wma'
    order_track_1w_rsi_wma = 'order_track_1w_rsi_wma'
    order_track_1d_up = 'order_track_1d_up'
    order_track_1d_down = 'order_track_1d_down'
    
    def __init__(self):
        super().__init__(OrderTrack, 'testnet')


class RankHistoryWrapper(Model):
    
    rank_his_id = 'rank_his_id'
    rank_his_year = 'rank_his_year'
    rank_his_time = 'rank_his_time'
    rank_his_symbol = 'rank_his_symbol'
    rank_his_value = 'rank_his_value'
    rank_his_market_cap = 'rank_his_market_cap'
    rank_his_price = 'rank_his_price'
    rank_his_volume_24h = 'rank_his_volume_24h'
    
    def __init__(self):
        super().__init__(RankHistory, 'testnet')


class ScheduleAlertWrapper(Model):
    
    schedule_al_id = 'schedule_al_id'
    schedule_al_name = 'schedule_al_name'
    schedule_al_groupid = 'schedule_al_groupid'
    schedule_al_botid = 'schedule_al_botid'
    schedule_al_icon = 'schedule_al_icon'
    schedule_al_time = 'schedule_al_time'
    schedule_al_content = 'schedule_al_content'
    schedule_al_before = 'schedule_al_before'
    schedule_al_note = 'schedule_al_note'
    schedule_al_done = 'schedule_al_done'
    
    def __init__(self):
        super().__init__(ScheduleAlert, 'testnet')


class StrategiesWrapper(Model):
    
    strategy_id = 'strategy_id'
    strategy_name = 'strategy_name'
    strategy_content = 'strategy_content'
    strategy_note = 'strategy_note'
    strategy_takeprofit = 'strategy_takeprofit'
    strategy_stoploss = 'strategy_stoploss'
    strategy_baseprofit = 'strategy_baseprofit'
    strategy_stepprofit = 'strategy_stepprofit'
    strategy_backprofit = 'strategy_backprofit'
    strategy_baseprofit_baseon = 'strategy_baseprofit_baseon'
    strategy_timelife = 'strategy_timelife'
    strategy_interval = 'strategy_interval'
    strategy_margin = 'strategy_margin'
    strategy_container = 'strategy_container'
    
    def __init__(self):
        super().__init__(Strategies, 'testnet')


class StrategyContainerWrapper(Model):
    
    stra_con_id = 'stra_con_id'
    stra_con_container = 'stra_con_container'
    stra_con_child = 'stra_con_child'
    stra_con_weight = 'stra_con_weight'
    stra_con_slot = 'stra_con_slot'
    stra_con_blacklist = 'stra_con_blacklist'
    
    def __init__(self):
        super().__init__(StrategyContainer, 'testnet')


class TestnetAccountWrapper(Model):
    
    testnet_account_id = 'testnet_account_id'
    testnet_account_name = 'testnet_account_name'
    testnet_account_balance = 'testnet_account_balance'
    testnet_account_reserve = 'testnet_account_reserve'
    testnet_account_compound = 'testnet_account_compound'
    testnet_account_note = 'testnet_account_note'
    testnet_account_margin_type = 'testnet_account_margin_type'
    testnet_account_runtime = 'testnet_account_runtime'
    
    def __init__(self):
        super().__init__(TestnetAccount, 'testnet')


class TestnetCampaignWrapper(Model):
    
    testnet_id = 'testnet_id'
    testnet_name = 'testnet_name'
    testnet_symbol = 'testnet_symbol'
    testnet_param = 'testnet_param'
    testnet_side = 'testnet_side'
    testnet_strategy = 'testnet_strategy'
    testnet_start_time = 'testnet_start_time'
    testnet_stop_time = 'testnet_stop_time'
    testnet_note = 'testnet_note'
    testnet_budget = 'testnet_budget'
    testnet_reserve = 'testnet_reserve'
    testnet_money = 'testnet_money'
    testnet_compound = 'testnet_compound'
    testnet_profit = 'testnet_profit'
    testnet_tele_bot = 'testnet_tele_bot'
    testnet_tele_gr_notice = 'testnet_tele_gr_notice'
    testnet_tele_gr_error = 'testnet_tele_gr_error'
    testnet_tele_gr_summary = 'testnet_tele_gr_summary'
    testnet_group = 'testnet_group'
    testnet_priority = 'testnet_priority'
    testnet_account = 'testnet_account'
    testnet_active_budget = 'testnet_active_budget'
    testnet_active = 'testnet_active'

    TESTNET_PARAM_LOG = 'testnet_param_log'
    TESTNET_PARAM_LOG_ORDER = 'testnet_param_log_order'
    
    def __init__(self):
        super().__init__(TestnetCampaign, 'testnet')


class TestnetEnterbaseWrapper(Model):
    
    enterbase_id = 'enterbase_id'
    enterbase_campaign = 'enterbase_campaign'
    enterbase_symbol = 'enterbase_symbol'
    enterbase_action = 'enterbase_action'
    enterbase_time = 'enterbase_time'
    enterbase_price = 'enterbase_price'
    enterbase_value = 'enterbase_value'
    enterbase_event = 'enterbase_event'

    ENTERBASE_EVENT_MAKESTEP=1
    ENTERBASE_EVENT_MAKEORDER=2
    ENTERBASE_EVENT_CANCLE=3
    ENTERBASE_EVENT_WAITTING=4
    
    def __init__(self):
        super().__init__(TestnetEnterbase, 'testnet')


class TestnetEventLogsWrapper(Model):
    
    testnet_elog_id = 'testnet_elog_id'
    testnet_elog_campaign = 'testnet_elog_campaign'
    testnet_elog_symbol = 'testnet_elog_symbol'
    testnet_elog_time = 'testnet_elog_time'
    testnet_elog_chart = 'testnet_elog_chart'
    testnet_elog_result = 'testnet_elog_result'
    testnet_elog_maxprofit = 'testnet_elog_maxprofit'
    testnet_elog_minprofit = 'testnet_elog_minprofit'
    testnet_elog_profit = 'testnet_elog_profit'
    testnet_elog_baseprofit = 'testnet_elog_baseprofit'
    testnet_elog_status = 'testnet_elog_status'
    testnet_elog_matched = 'testnet_elog_matched'
    testnet_elog_base = 'testnet_elog_base'
    
    def __init__(self):
        super().__init__(TestnetEventLogs, 'testnet')


class TestnetEventsWrapper(Model):
    
    testnet_events_id = 'testnet_events_id'
    testnet_events_symbol = 'testnet_events_symbol'
    testnet_events_time = 'testnet_events_time'
    testnet_events_icon = 'testnet_events_icon'
    testnet_events_profit = 'testnet_events_profit'
    testnet_events_content = 'testnet_events_content'
    testnet_events_strategy = 'testnet_events_strategy'
    testnet_events_campaign = 'testnet_events_campaign'
    
    def __init__(self):
        super().__init__(TestnetEvents, 'testnet')


class TestnetOrderWrapper(Model):
    
    testnet_order_id = 'testnet_order_id'
    testnet_order_time = 'testnet_order_time'
    testnet_order_action = 'testnet_order_action'
    testnet_order_symbol = 'testnet_order_symbol'
    testnet_order_qty = 'testnet_order_qty'
    testnet_order_price = 'testnet_order_price'
    testnet_order_commit = 'testnet_order_commit'
    testnet_order_pnl = 'testnet_order_pnl'
    testnet_order_baseon = 'testnet_order_baseon'
    testnet_order_type = 'testnet_order_type'
    testnet_order_phase = 'testnet_order_phase'
    testnet_order_account = 'testnet_order_account'
    
    def __init__(self):
        super().__init__(TestnetOrder, 'testnet')


class TestnetProfitbaseWrapper(Model):
    
    profitbase_id = 'profitbase_id'
    profitbase_campaign = 'profitbase_campaign'
    profitbase_symbol = 'profitbase_symbol'
    profitbase_action = 'profitbase_action'
    profitbase_time = 'profitbase_time'
    profitbase_price = 'profitbase_price'
    profitbase_value = 'profitbase_value'
    profitbase_event = 'profitbase_event'

    PROFITBASE_EVENT_MAKESTEP = 1
    PROFITBASE_EVENT_MAKEORDER = 2
    PROFITBASE_EVENT_CANCLE = 3
    PROFITBASE_EVENT_WAITTING = 4
    
    def __init__(self):
        super().__init__(TestnetProfitbase, 'testnet')


class TestnetResultsWrapper(Model):
    
    testnet_result_id = 'testnet_result_id'
    testnet_result_campaign = 'testnet_result_campaign'
    testnet_result_strategy = 'testnet_result_strategy'
    testnet_result_group = 'testnet_result_group'
    testnet_result_container = 'testnet_result_container'
    testnet_result_symbol = 'testnet_result_symbol'
    testnet_result_chart = 'testnet_result_chart'
    testnet_result_enter_time = 'testnet_result_enter_time'
    testnet_result_enter_price = 'testnet_result_enter_price'
    testnet_result_order_time = 'testnet_result_order_time'
    testnet_result_order_price = 'testnet_result_order_price'
    testnet_result_order_qty = 'testnet_result_order_qty'
    testnet_result_order_phase = 'testnet_result_order_phase'
    testnet_result_order_release = 'testnet_result_order_release'
    testnet_result_high = 'testnet_result_high'
    testnet_result_low = 'testnet_result_low'
    testnet_result_type = 'testnet_result_type'
    testnet_result_base = 'testnet_result_base'
    testnet_result_params = 'testnet_result_params'
    testnet_result_start_reason = 'testnet_result_start_reason'
    testnet_result_status = 'testnet_result_status'
    testnet_result_matched_ema5 = 'testnet_result_matched_ema5'
    testnet_result_matched_price = 'testnet_result_matched_price'
    testnet_result_first_price = 'testnet_result_first_price'
    testnet_result_matched_time = 'testnet_result_matched_time'
    testnet_result_matched_qty = 'testnet_result_matched_qty'
    testnet_result_last_price = 'testnet_result_last_price'
    testnet_result_sell_price = 'testnet_result_sell_price'
    testnet_result_sell_time = 'testnet_result_sell_time'
    testnet_result_profit = 'testnet_result_profit'
    testnet_result_commit = 'testnet_result_commit'
    testnet_result_eventprofit = 'testnet_result_eventprofit'
    testnet_result_realprofit = 'testnet_result_realprofit'
    testnet_result_realpnl = 'testnet_result_realpnl'
    testnet_result_baseprofit = 'testnet_result_baseprofit'
    testnet_result_pending = 'testnet_result_pending'
    testnet_result_phase = 'testnet_result_phase'
    testnet_result_budget = 'testnet_result_budget'
    testnet_result_nextphase_note = 'testnet_result_nextphase_note'
    testnet_result_phase_note = 'testnet_result_phase_note'
    testnet_result_flow = 'testnet_result_flow'
    testnet_result_interval = 'testnet_result_interval'
    testnet_result_margin = 'testnet_result_margin'
    testnet_result_account = 'testnet_result_account'
    testnet_result_close_time = 'testnet_result_close_time'
    testnet_result_chart_price = 'testnet_result_chart_price'

    TESTNET_RESULT_TYPE_LONG=1
    TESTNET_RESULT_TYPE_SHORT=2

    TESTNET_RESULT_STATUS_PENDING=0
    TESTNET_RESULT_STATUS_MATCHED=1
    TESTNET_RESULT_STATUS_TAKEPROFIT=2
    TESTNET_RESULT_STATUS_STOPLOSS=3
    TESTNET_RESULT_STATUS_CANCLE=4
    TESTNET_RESULT_STATUS_STOP_PENDING=5
    TESTNET_RESULT_STATUS_ENTER_WAITTING=6
    TESTNET_RESULT_STATUS_MATCHED_PART=7
    TESTNET_RESULT_STATUS_PHASE_PENDING=8
    TESTNET_RESULT_STATUS_RELEASE_WAITTING=9
    TESTNET_RESULT_STATUS_RELEASE_PENDING=10
    
    def __init__(self):
        super().__init__(TestnetResults, 'testnet')


class TestnetTrackBalanceWrapper(Model):
    
    testnet_track_bl_id = 'testnet_track_bl_id'
    testnet_track_bl_account = 'testnet_track_bl_account'
    testnet_track_bl_time = 'testnet_track_bl_time'
    testnet_track_bl_margin_bl = 'testnet_track_bl_margin_bl'
    testnet_track_bl_invest = 'testnet_track_bl_invest'
    testnet_track_bl_unrealize = 'testnet_track_bl_unrealize'
    testnet_track_bl_balance = 'testnet_track_bl_balance'
    
    def __init__(self):
        super().__init__(TestnetTrackBalance, 'testnet')


class VolatilityWrapper(Model):
    
    volatility_id = 'volatility_id'
    volatility_symbol = 'volatility_symbol'
    volatility_time = 'volatility_time'
    volatility_1d_high_low_avg3d_value = 'volatility_1d_high_low_avg3d_value'
    volatility_1d_high_high_avg3d_value = 'volatility_1d_high_high_avg3d_value'
    volatility_1d_low_low_avg3d_value = 'volatility_1d_low_low_avg3d_value'
    volatility_1d_high_low_avg7d_value = 'volatility_1d_high_low_avg7d_value'
    volatility_1d_high_high_avg7d_value = 'volatility_1d_high_high_avg7d_value'
    volatility_1d_low_low_avg7d_value = 'volatility_1d_low_low_avg7d_value'
    volatility_4h_high_low_avg3d_value = 'volatility_4h_high_low_avg3d_value'
    volatility_4h_high_high_avg3d_value = 'volatility_4h_high_high_avg3d_value'
    volatility_4h_low_low_avg3d_value = 'volatility_4h_low_low_avg3d_value'
    volatility_4h_high_low_avg7d_value = 'volatility_4h_high_low_avg7d_value'
    volatility_4h_high_high_avg7d_value = 'volatility_4h_high_high_avg7d_value'
    volatility_4h_low_low_avg7d_value = 'volatility_4h_low_low_avg7d_value'
    volatility_1d_high_low_avg3d_rank = 'volatility_1d_high_low_avg3d_rank'
    volatility_1d_high_high_avg3d_rank = 'volatility_1d_high_high_avg3d_rank'
    volatility_1d_low_low_avg3d_rank = 'volatility_1d_low_low_avg3d_rank'
    volatility_1d_high_low_avg7d_rank = 'volatility_1d_high_low_avg7d_rank'
    volatility_1d_high_high_avg7d_rank = 'volatility_1d_high_high_avg7d_rank'
    volatility_1d_low_low_avg7d_rank = 'volatility_1d_low_low_avg7d_rank'
    volatility_4h_high_low_avg3d_rank = 'volatility_4h_high_low_avg3d_rank'
    volatility_4h_high_high_avg3d_rank = 'volatility_4h_high_high_avg3d_rank'
    volatility_4h_low_low_avg3d_rank = 'volatility_4h_low_low_avg3d_rank'
    volatility_4h_high_low_avg7d_rank = 'volatility_4h_high_low_avg7d_rank'
    volatility_4h_high_high_avg7d_rank = 'volatility_4h_high_high_avg7d_rank'
    volatility_4h_low_low_avg7d_rank = 'volatility_4h_low_low_avg7d_rank'
    volatility_4h_close_low_avg3d_value = 'volatility_4h_close_low_avg3d_value'
    volatility_4h_close_low_avg7d_value = 'volatility_4h_close_low_avg7d_value'
    volatility_1d_close_low_avg3d_value = 'volatility_1d_close_low_avg3d_value'
    volatility_1d_close_low_avg7d_value = 'volatility_1d_close_low_avg7d_value'
    volatility_4h_close_low_avg3d_rank = 'volatility_4h_close_low_avg3d_rank'
    volatility_4h_close_low_avg7d_rank = 'volatility_4h_close_low_avg7d_rank'
    volatility_1d_close_low_avg3d_rank = 'volatility_1d_close_low_avg3d_rank'
    volatility_1d_close_low_avg7d_rank = 'volatility_1d_close_low_avg7d_rank'
    
    def __init__(self):
        super().__init__(Volatility, 'testnet')


class VolatilityHistoryWrapper(Model):
    
    volatility_id = 'volatility_id'
    volatility_symbol = 'volatility_symbol'
    volatility_time = 'volatility_time'
    volatility_4h_highlow_t0_value = 'volatility_4h_highlow_t0_value'
    volatility_4h_highlow_t1_value = 'volatility_4h_highlow_t1_value'
    volatility_4h_highlow_t2_value = 'volatility_4h_highlow_t2_value'
    volatility_4h_highhigh_t0_value = 'volatility_4h_highhigh_t0_value'
    volatility_4h_highhigh_t1_value = 'volatility_4h_highhigh_t1_value'
    volatility_4h_highhigh_t2_value = 'volatility_4h_highhigh_t2_value'
    volatility_1d_highlow_t0_value = 'volatility_1d_highlow_t0_value'
    volatility_1d_highlow_t1_value = 'volatility_1d_highlow_t1_value'
    volatility_1d_highlow_t2_value = 'volatility_1d_highlow_t2_value'
    volatility_1d_highhigh_t0_value = 'volatility_1d_highhigh_t0_value'
    volatility_1d_highhigh_t1_value = 'volatility_1d_highhigh_t1_value'
    volatility_1d_highhigh_t2_value = 'volatility_1d_highhigh_t2_value'
    volatility_4h_highlow_t0_rank = 'volatility_4h_highlow_t0_rank'
    volatility_4h_highlow_t1_rank = 'volatility_4h_highlow_t1_rank'
    volatility_4h_highlow_t2_rank = 'volatility_4h_highlow_t2_rank'
    volatility_4h_highhigh_t0_rank = 'volatility_4h_highhigh_t0_rank'
    volatility_4h_highhigh_t1_rank = 'volatility_4h_highhigh_t1_rank'
    volatility_4h_highhigh_t2_rank = 'volatility_4h_highhigh_t2_rank'
    volatility_1d_highlow_t0_rank = 'volatility_1d_highlow_t0_rank'
    volatility_1d_highlow_t1_rank = 'volatility_1d_highlow_t1_rank'
    volatility_1d_highlow_t2_rank = 'volatility_1d_highlow_t2_rank'
    volatility_1d_highhigh_t0_rank = 'volatility_1d_highhigh_t0_rank'
    volatility_1d_highhigh_t1_rank = 'volatility_1d_highhigh_t1_rank'
    volatility_1d_highhigh_t2_rank = 'volatility_1d_highhigh_t2_rank'
    
    def __init__(self):
        super().__init__(VolatilityHistory, 'testnet')


class WatchlistWrapper(Model):
    
    wl_id = 'wl_id'
    wl_symbol = 'wl_symbol'
    wl_note = 'wl_note'
    wl_uid = 'wl_uid'
    wl_time = 'wl_time'
    wl_stoptime = 'wl_stoptime'
    wl_icon = 'wl_icon'
    
    def __init__(self):
        super().__init__(Watchlist, 'testnet')

