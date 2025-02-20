# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Authentication(models.Model):
    authen_id = models.AutoField(primary_key=True)
    authen_username = models.CharField(unique=True, max_length=200, blank=True, null=True)
    authen_email = models.CharField(unique=True, max_length=200, blank=True, null=True)
    authen_phone = models.CharField(unique=True, max_length=200, blank=True, null=True)
    authen_pass = models.TextField(blank=True, null=True)
    authen_token = models.TextField(blank=True, null=True)
    authen_group = models.IntegerField(blank=True, null=True)
    authen_note = models.TextField(blank=True, null=True)
    authen_parent = models.IntegerField(blank=True, null=True)
    authen_time = models.IntegerField(blank=True, null=True)
    authen_online = models.IntegerField(blank=True, null=True)
    authen_active = models.IntegerField(blank=True, null=True)
    authen_status = models.IntegerField(blank=True, null=True)
    authen_img = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'authentication'


class Candle15M(models.Model):
    candle_15m_id = models.AutoField(primary_key=True)
    candle_15m_symbol = models.CharField(max_length=150, blank=True, null=True)
    candle_15m_open_time = models.FloatField(blank=True, null=True)
    candle_15m_close_time = models.BigIntegerField()
    candle_15m_open = models.CharField(max_length=150, blank=True, null=True)
    candle_15m_close = models.CharField(max_length=150, blank=True, null=True)
    candle_15m_high = models.CharField(max_length=150, blank=True, null=True)
    candle_15m_low = models.CharField(max_length=150, blank=True, null=True)
    candle_15m_trades = models.CharField(max_length=150, blank=True, null=True)
    candle_15m_volume = models.CharField(max_length=150, blank=True, null=True)
    candle_15m_ema5 = models.FloatField(blank=True, null=True)
    candle_15m_ema9 = models.FloatField(blank=True, null=True)
    candle_15m_ema12 = models.FloatField(blank=True, null=True)
    candle_15m_ema13 = models.FloatField(blank=True, null=True)
    candle_15m_ema26 = models.FloatField(blank=True, null=True)
    candle_15m_macd = models.FloatField(blank=True, null=True)
    candle_15m_signal = models.FloatField(blank=True, null=True)
    candle_15m_histogram = models.FloatField(blank=True, null=True)
    candle_15m_signal7 = models.FloatField(blank=True, null=True)
    candle_15m_histogram7 = models.FloatField(blank=True, null=True)
    candle_15m_signal4 = models.FloatField(blank=True, null=True)
    candle_15m_histogram4 = models.FloatField(blank=True, null=True)
    candle_15m_signal5 = models.FloatField(blank=True, null=True)
    candle_15m_histogram5 = models.FloatField(blank=True, null=True)
    candle_15m_signal6 = models.FloatField(blank=True, null=True)
    candle_15m_histogram6 = models.FloatField(blank=True, null=True)
    candle_15m_signal2 = models.FloatField(blank=True, null=True)
    candle_15m_histogram2 = models.FloatField(blank=True, null=True)
    candle_15m_signal3 = models.FloatField(blank=True, null=True)
    candle_15m_histogram3 = models.FloatField(blank=True, null=True)
    candle_15m_avgu14 = models.FloatField(blank=True, null=True)
    candle_15m_avgd14 = models.FloatField(blank=True, null=True)
    candle_15m_rsi14 = models.FloatField(blank=True, null=True)
    candle_15m_rsi_ema9 = models.FloatField(blank=True, null=True)
    candle_15m_rsi_ema5 = models.FloatField(blank=True, null=True)
    candle_15m_rsi_ema4 = models.FloatField(blank=True, null=True)
    candle_15m_rsi_wma = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'candle_15m'
        unique_together = (('candle_15m_id', 'candle_15m_close_time'),)


class Candle1D(models.Model):
    candle_1d_id = models.AutoField(primary_key=True)
    candle_1d_symbol = models.CharField(max_length=150, blank=True, null=True)
    candle_1d_open_time = models.FloatField(blank=True, null=True)
    candle_1d_close_time = models.BigIntegerField()
    candle_1d_open = models.CharField(max_length=150, blank=True, null=True)
    candle_1d_close = models.CharField(max_length=150, blank=True, null=True)
    candle_1d_high = models.CharField(max_length=150, blank=True, null=True)
    candle_1d_low = models.CharField(max_length=150, blank=True, null=True)
    candle_1d_trades = models.CharField(max_length=150, blank=True, null=True)
    candle_1d_volume = models.CharField(max_length=150, blank=True, null=True)
    candle_1d_ema5 = models.FloatField(blank=True, null=True)
    candle_1d_ema9 = models.FloatField(blank=True, null=True)
    candle_1d_ema12 = models.FloatField(blank=True, null=True)
    candle_1d_ema13 = models.FloatField(blank=True, null=True)
    candle_1d_ema26 = models.FloatField(blank=True, null=True)
    candle_1d_macd = models.FloatField(blank=True, null=True)
    candle_1d_signal = models.FloatField(blank=True, null=True)
    candle_1d_histogram = models.FloatField(blank=True, null=True)
    candle_1d_signal7 = models.FloatField(blank=True, null=True)
    candle_1d_histogram7 = models.FloatField(blank=True, null=True)
    candle_1d_signal4 = models.FloatField(blank=True, null=True)
    candle_1d_histogram4 = models.FloatField(blank=True, null=True)
    candle_1d_signal5 = models.FloatField(blank=True, null=True)
    candle_1d_histogram5 = models.FloatField(blank=True, null=True)
    candle_1d_signal6 = models.FloatField(blank=True, null=True)
    candle_1d_histogram6 = models.FloatField(blank=True, null=True)
    candle_1d_signal2 = models.FloatField(blank=True, null=True)
    candle_1d_histogram2 = models.FloatField(blank=True, null=True)
    candle_1d_signal3 = models.FloatField(blank=True, null=True)
    candle_1d_histogram3 = models.FloatField(blank=True, null=True)
    candle_1d_avgu14 = models.FloatField(blank=True, null=True)
    candle_1d_avgd14 = models.FloatField(blank=True, null=True)
    candle_1d_rsi14 = models.FloatField(blank=True, null=True)
    candle_1d_rsi_ema9 = models.FloatField(blank=True, null=True)
    candle_1d_rsi_ema5 = models.FloatField(blank=True, null=True)
    candle_1d_rsi_ema4 = models.FloatField(blank=True, null=True)
    candle_1d_rsi_wma = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'candle_1d'
        unique_together = (('candle_1d_id', 'candle_1d_close_time'),)


class Candle1H(models.Model):
    candle_1h_id = models.AutoField(primary_key=True)
    candle_1h_symbol = models.CharField(max_length=150, blank=True, null=True)
    candle_1h_open_time = models.FloatField(blank=True, null=True)
    candle_1h_close_time = models.BigIntegerField()
    candle_1h_open = models.CharField(max_length=150, blank=True, null=True)
    candle_1h_close = models.CharField(max_length=150, blank=True, null=True)
    candle_1h_high = models.CharField(max_length=150, blank=True, null=True)
    candle_1h_low = models.CharField(max_length=150, blank=True, null=True)
    candle_1h_trades = models.CharField(max_length=150, blank=True, null=True)
    candle_1h_volume = models.CharField(max_length=150, blank=True, null=True)
    candle_1h_ema5 = models.FloatField(blank=True, null=True)
    candle_1h_ema9 = models.FloatField(blank=True, null=True)
    candle_1h_ema12 = models.FloatField(blank=True, null=True)
    candle_1h_ema13 = models.FloatField(blank=True, null=True)
    candle_1h_ema26 = models.FloatField(blank=True, null=True)
    candle_1h_macd = models.FloatField(blank=True, null=True)
    candle_1h_signal = models.FloatField(blank=True, null=True)
    candle_1h_histogram = models.FloatField(blank=True, null=True)
    candle_1h_signal7 = models.FloatField(blank=True, null=True)
    candle_1h_histogram7 = models.FloatField(blank=True, null=True)
    candle_1h_signal4 = models.FloatField(blank=True, null=True)
    candle_1h_histogram4 = models.FloatField(blank=True, null=True)
    candle_1h_signal5 = models.FloatField(blank=True, null=True)
    candle_1h_histogram5 = models.FloatField(blank=True, null=True)
    candle_1h_signal6 = models.FloatField(blank=True, null=True)
    candle_1h_histogram6 = models.FloatField(blank=True, null=True)
    candle_1h_signal2 = models.FloatField(blank=True, null=True)
    candle_1h_histogram2 = models.FloatField(blank=True, null=True)
    candle_1h_signal3 = models.FloatField(blank=True, null=True)
    candle_1h_histogram3 = models.FloatField(blank=True, null=True)
    candle_1h_avgu14 = models.FloatField(blank=True, null=True)
    candle_1h_avgd14 = models.FloatField(blank=True, null=True)
    candle_1h_rsi14 = models.FloatField(blank=True, null=True)
    candle_1h_rsi_ema9 = models.FloatField(blank=True, null=True)
    candle_1h_rsi_ema5 = models.FloatField(blank=True, null=True)
    candle_1h_rsi_ema4 = models.FloatField(blank=True, null=True)
    candle_1h_rsi_wma = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'candle_1h'
        unique_together = (('candle_1h_id', 'candle_1h_close_time'),)


class Candle1M(models.Model):
    candle_1m_id = models.AutoField(primary_key=True)
    candle_1m_symbol = models.CharField(max_length=150, blank=True, null=True)
    candle_1m_open_time = models.FloatField(blank=True, null=True)
    candle_1m_close_time = models.BigIntegerField()
    candle_1m_open = models.CharField(max_length=150, blank=True, null=True)
    candle_1m_close = models.CharField(max_length=150, blank=True, null=True)
    candle_1m_high = models.CharField(max_length=150, blank=True, null=True)
    candle_1m_low = models.CharField(max_length=150, blank=True, null=True)
    candle_1m_trades = models.CharField(max_length=150, blank=True, null=True)
    candle_1m_volume = models.CharField(max_length=150, blank=True, null=True)
    candle_1m_ema5 = models.FloatField(blank=True, null=True)
    candle_1m_ema9 = models.FloatField(blank=True, null=True)
    candle_1m_ema12 = models.FloatField(blank=True, null=True)
    candle_1m_ema13 = models.FloatField(blank=True, null=True)
    candle_1m_ema26 = models.FloatField(blank=True, null=True)
    candle_1m_macd = models.FloatField(blank=True, null=True)
    candle_1m_signal = models.FloatField(blank=True, null=True)
    candle_1m_histogram = models.FloatField(blank=True, null=True)
    candle_1m_signal7 = models.FloatField(blank=True, null=True)
    candle_1m_histogram7 = models.FloatField(blank=True, null=True)
    candle_1m_signal4 = models.FloatField(blank=True, null=True)
    candle_1m_histogram4 = models.FloatField(blank=True, null=True)
    candle_1m_signal5 = models.FloatField(blank=True, null=True)
    candle_1m_histogram5 = models.FloatField(blank=True, null=True)
    candle_1m_signal6 = models.FloatField(blank=True, null=True)
    candle_1m_histogram6 = models.FloatField(blank=True, null=True)
    candle_1m_signal2 = models.FloatField(blank=True, null=True)
    candle_1m_histogram2 = models.FloatField(blank=True, null=True)
    candle_1m_signal3 = models.FloatField(blank=True, null=True)
    candle_1m_histogram3 = models.FloatField(blank=True, null=True)
    candle_1m_avgu14 = models.FloatField(blank=True, null=True)
    candle_1m_avgd14 = models.FloatField(blank=True, null=True)
    candle_1m_rsi14 = models.FloatField(blank=True, null=True)
    candle_1m_rsi_ema9 = models.FloatField(blank=True, null=True)
    candle_1m_rsi_ema5 = models.FloatField(blank=True, null=True)
    candle_1m_rsi_ema4 = models.FloatField(blank=True, null=True)
    candle_1m_rsi_wma = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'candle_1m'
        unique_together = (('candle_1m_id', 'candle_1m_close_time'),)


class Candle1W(models.Model):
    candle_1w_id = models.AutoField(primary_key=True)
    candle_1w_symbol = models.CharField(max_length=150, blank=True, null=True)
    candle_1w_open_time = models.FloatField(blank=True, null=True)
    candle_1w_close_time = models.BigIntegerField()
    candle_1w_open = models.CharField(max_length=150, blank=True, null=True)
    candle_1w_close = models.CharField(max_length=150, blank=True, null=True)
    candle_1w_high = models.CharField(max_length=150, blank=True, null=True)
    candle_1w_low = models.CharField(max_length=150, blank=True, null=True)
    candle_1w_trades = models.CharField(max_length=150, blank=True, null=True)
    candle_1w_volume = models.CharField(max_length=150, blank=True, null=True)
    candle_1w_ema5 = models.FloatField(blank=True, null=True)
    candle_1w_ema9 = models.FloatField(blank=True, null=True)
    candle_1w_ema12 = models.FloatField(blank=True, null=True)
    candle_1w_ema13 = models.FloatField(blank=True, null=True)
    candle_1w_ema26 = models.FloatField(blank=True, null=True)
    candle_1w_macd = models.FloatField(blank=True, null=True)
    candle_1w_signal = models.FloatField(blank=True, null=True)
    candle_1w_histogram = models.FloatField(blank=True, null=True)
    candle_1w_signal7 = models.FloatField(blank=True, null=True)
    candle_1w_histogram7 = models.FloatField(blank=True, null=True)
    candle_1w_signal4 = models.FloatField(blank=True, null=True)
    candle_1w_histogram4 = models.FloatField(blank=True, null=True)
    candle_1w_signal5 = models.FloatField(blank=True, null=True)
    candle_1w_histogram5 = models.FloatField(blank=True, null=True)
    candle_1w_signal6 = models.FloatField(blank=True, null=True)
    candle_1w_histogram6 = models.FloatField(blank=True, null=True)
    candle_1w_signal2 = models.FloatField(blank=True, null=True)
    candle_1w_histogram2 = models.FloatField(blank=True, null=True)
    candle_1w_signal3 = models.FloatField(blank=True, null=True)
    candle_1w_histogram3 = models.FloatField(blank=True, null=True)
    candle_1w_avgu14 = models.FloatField(blank=True, null=True)
    candle_1w_avgd14 = models.FloatField(blank=True, null=True)
    candle_1w_rsi14 = models.FloatField(blank=True, null=True)
    candle_1w_rsi_ema9 = models.FloatField(blank=True, null=True)
    candle_1w_rsi_ema5 = models.FloatField(blank=True, null=True)
    candle_1w_rsi_ema4 = models.FloatField(blank=True, null=True)
    candle_1w_rsi_wma = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'candle_1w'
        unique_together = (('candle_1w_id', 'candle_1w_close_time'),)


class Candle3M(models.Model):
    candle_3m_id = models.AutoField(primary_key=True)
    candle_3m_symbol = models.CharField(max_length=150, blank=True, null=True)
    candle_3m_open_time = models.FloatField(blank=True, null=True)
    candle_3m_close_time = models.BigIntegerField()
    candle_3m_open = models.CharField(max_length=150, blank=True, null=True)
    candle_3m_close = models.CharField(max_length=150, blank=True, null=True)
    candle_3m_high = models.CharField(max_length=150, blank=True, null=True)
    candle_3m_low = models.CharField(max_length=150, blank=True, null=True)
    candle_3m_trades = models.CharField(max_length=150, blank=True, null=True)
    candle_3m_volume = models.CharField(max_length=150, blank=True, null=True)
    candle_3m_ema5 = models.FloatField(blank=True, null=True)
    candle_3m_ema9 = models.FloatField(blank=True, null=True)
    candle_3m_ema12 = models.FloatField(blank=True, null=True)
    candle_3m_ema13 = models.FloatField(blank=True, null=True)
    candle_3m_ema26 = models.FloatField(blank=True, null=True)
    candle_3m_macd = models.FloatField(blank=True, null=True)
    candle_3m_signal = models.FloatField(blank=True, null=True)
    candle_3m_histogram = models.FloatField(blank=True, null=True)
    candle_3m_signal7 = models.FloatField(blank=True, null=True)
    candle_3m_histogram7 = models.FloatField(blank=True, null=True)
    candle_3m_signal4 = models.FloatField(blank=True, null=True)
    candle_3m_histogram4 = models.FloatField(blank=True, null=True)
    candle_3m_signal5 = models.FloatField(blank=True, null=True)
    candle_3m_histogram5 = models.FloatField(blank=True, null=True)
    candle_3m_signal6 = models.FloatField(blank=True, null=True)
    candle_3m_histogram6 = models.FloatField(blank=True, null=True)
    candle_3m_signal2 = models.FloatField(blank=True, null=True)
    candle_3m_histogram2 = models.FloatField(blank=True, null=True)
    candle_3m_signal3 = models.FloatField(blank=True, null=True)
    candle_3m_histogram3 = models.FloatField(blank=True, null=True)
    candle_3m_avgu14 = models.FloatField(blank=True, null=True)
    candle_3m_avgd14 = models.FloatField(blank=True, null=True)
    candle_3m_rsi14 = models.FloatField(blank=True, null=True)
    candle_3m_rsi_ema9 = models.FloatField(blank=True, null=True)
    candle_3m_rsi_ema5 = models.FloatField(blank=True, null=True)
    candle_3m_rsi_ema4 = models.FloatField(blank=True, null=True)
    candle_3m_rsi_wma = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'candle_3m'
        unique_together = (('candle_3m_id', 'candle_3m_close_time'),)


class Candle4H(models.Model):
    candle_4h_id = models.AutoField(primary_key=True)
    candle_4h_symbol = models.CharField(max_length=150, blank=True, null=True)
    candle_4h_open_time = models.FloatField(blank=True, null=True)
    candle_4h_close_time = models.BigIntegerField()
    candle_4h_open = models.CharField(max_length=150, blank=True, null=True)
    candle_4h_close = models.CharField(max_length=150, blank=True, null=True)
    candle_4h_high = models.CharField(max_length=150, blank=True, null=True)
    candle_4h_low = models.CharField(max_length=150, blank=True, null=True)
    candle_4h_trades = models.CharField(max_length=150, blank=True, null=True)
    candle_4h_volume = models.CharField(max_length=150, blank=True, null=True)
    candle_4h_ema5 = models.FloatField(blank=True, null=True)
    candle_4h_ema9 = models.FloatField(blank=True, null=True)
    candle_4h_ema12 = models.FloatField(blank=True, null=True)
    candle_4h_ema13 = models.FloatField(blank=True, null=True)
    candle_4h_ema26 = models.FloatField(blank=True, null=True)
    candle_4h_macd = models.FloatField(blank=True, null=True)
    candle_4h_signal = models.FloatField(blank=True, null=True)
    candle_4h_histogram = models.FloatField(blank=True, null=True)
    candle_4h_signal7 = models.FloatField(blank=True, null=True)
    candle_4h_histogram7 = models.FloatField(blank=True, null=True)
    candle_4h_signal4 = models.FloatField(blank=True, null=True)
    candle_4h_histogram4 = models.FloatField(blank=True, null=True)
    candle_4h_signal5 = models.FloatField(blank=True, null=True)
    candle_4h_histogram5 = models.FloatField(blank=True, null=True)
    candle_4h_signal6 = models.FloatField(blank=True, null=True)
    candle_4h_histogram6 = models.FloatField(blank=True, null=True)
    candle_4h_signal2 = models.FloatField(blank=True, null=True)
    candle_4h_histogram2 = models.FloatField(blank=True, null=True)
    candle_4h_signal3 = models.FloatField(blank=True, null=True)
    candle_4h_histogram3 = models.FloatField(blank=True, null=True)
    candle_4h_avgu14 = models.FloatField(blank=True, null=True)
    candle_4h_avgd14 = models.FloatField(blank=True, null=True)
    candle_4h_rsi14 = models.FloatField(blank=True, null=True)
    candle_4h_rsi_ema9 = models.FloatField(blank=True, null=True)
    candle_4h_rsi_ema5 = models.FloatField(blank=True, null=True)
    candle_4h_rsi_ema4 = models.FloatField(blank=True, null=True)
    candle_4h_rsi_wma = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'candle_4h'
        unique_together = (('candle_4h_id', 'candle_4h_close_time'),)


class Change24H(models.Model):
    change24h_id = models.AutoField(primary_key=True)
    change24h_time = models.BigIntegerField(blank=True, null=True)
    change24h_total = models.IntegerField(blank=True, null=True)
    change24h_down = models.FloatField(blank=True, null=True)
    change24h_up = models.FloatField(blank=True, null=True)
    change24h_up50 = models.FloatField(blank=True, null=True)
    change24h_down50 = models.FloatField(blank=True, null=True)
    change24h_keep50 = models.FloatField(blank=True, null=True)
    change24h_keep = models.FloatField(blank=True, null=True)
    change24h_btc_change = models.FloatField(blank=True, null=True)
    change24h_btc_up = models.FloatField(blank=True, null=True)
    change24h_btc_down = models.FloatField(blank=True, null=True)
    change24h_btc_keep = models.FloatField(blank=True, null=True)
    change24h_up_10 = models.FloatField(blank=True, null=True)
    change24h_up_7_10 = models.FloatField(blank=True, null=True)
    change24h_up_5_7 = models.FloatField(blank=True, null=True)
    change24h_up_3_5 = models.FloatField(blank=True, null=True)
    change24h_up_0_3 = models.FloatField(blank=True, null=True)
    change24h_down_0_3 = models.FloatField(blank=True, null=True)
    change24h_down_3_5 = models.FloatField(blank=True, null=True)
    change24h_down_5_7 = models.FloatField(blank=True, null=True)
    change24h_down_7_10 = models.FloatField(blank=True, null=True)
    change24h_down_10 = models.FloatField(blank=True, null=True)
    change24h_data = models.TextField()
    change24h_5m_up = models.IntegerField(blank=True, null=True)
    change24h_5m_down = models.IntegerField(blank=True, null=True)
    change24h_15m_up = models.IntegerField(blank=True, null=True)
    change24h_15m_down = models.IntegerField(blank=True, null=True)
    change24h_1h_up = models.IntegerField(blank=True, null=True)
    change24h_1h_down = models.IntegerField(blank=True, null=True)
    change24h_4h_up = models.IntegerField(blank=True, null=True)
    change24h_4h_down = models.IntegerField(blank=True, null=True)
    change24h_up_ema5 = models.FloatField(blank=True, null=True)
    change24h_up_ema9 = models.FloatField(blank=True, null=True)
    change24h_up_ema13 = models.FloatField(blank=True, null=True)
    change24h_up50_ema5 = models.FloatField(blank=True, null=True)
    change24h_up50_ema9 = models.FloatField(blank=True, null=True)
    change24h_up50_ema13 = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'change_24h'


class Coinmarket(models.Model):
    coinmarket_id = models.AutoField(primary_key=True)
    coinmarket_symbol = models.CharField(max_length=150)
    coinmarket_price = models.FloatField()
    coinmarket_percent_change_1h = models.FloatField()
    coinmarket_percent_change_24h = models.FloatField()
    coinmarket_percent_change_7d = models.FloatField()
    coinmarket_percent_change_30d = models.FloatField()
    coinmarket_market_cap = models.FloatField()
    coinmarket_volume_24h = models.FloatField()
    coinmarket_rank = models.IntegerField()
    coinmarket_last_updated = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = 'coinmarket'



class EventLogs(models.Model):
    elog_id = models.AutoField(primary_key=True)
    elog_symbol = models.CharField(max_length=20, blank=True, null=True)
    elog_time = models.IntegerField(blank=True, null=True)
    elog_chart = models.FloatField(blank=True, null=True)
    elog_result = models.JSONField(blank=True, null=True)
    elog_matched = models.IntegerField(blank=True, null=True)
    elog_base = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'event_logs'


class Events(models.Model):
    event_id = models.AutoField(primary_key=True)
    event_symbol = models.CharField(max_length=10, blank=True, null=True)
    event_time = models.IntegerField(blank=True, null=True)
    event_chart = models.FloatField(blank=True, null=True)
    event_price = models.FloatField(blank=True, null=True)
    event_type = models.IntegerField(blank=True, null=True)
    event_base = models.JSONField(blank=True, null=True)
    event_params = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'events'


class Fear(models.Model):
    fear_id = models.AutoField(primary_key=True)
    fear_time = models.BigIntegerField(blank=True, null=True)
    fear_value = models.FloatField(blank=True, null=True)
    fear_class = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'fear'


class OrderTrack(models.Model):
    order_track_id = models.IntegerField(primary_key=True)
    order_track_symbol = models.CharField(max_length=150, blank=True, null=True)
    order_track_price = models.FloatField(blank=True, null=True)
    order_track_low = models.FloatField(blank=True, null=True)
    order_track_high = models.FloatField(blank=True, null=True)
    order_track_up = models.FloatField(blank=True, null=True)
    order_track_down = models.FloatField(blank=True, null=True)
    order_track_close = models.FloatField(blank=True, null=True)
    order_track_change = models.FloatField(blank=True, null=True)
    order_track_1h_up = models.FloatField(blank=True, null=True)
    order_track_1h_down = models.FloatField(blank=True, null=True)
    order_track_15m_up = models.FloatField(blank=True, null=True)
    order_track_15m_down = models.FloatField(blank=True, null=True)
    order_track_3m_down = models.FloatField(blank=True, null=True)
    order_track_3m_up = models.FloatField(blank=True, null=True)
    order_track_rsi4h_0 = models.FloatField(blank=True, null=True)
    order_track_rsi4h_1 = models.FloatField(blank=True, null=True)
    order_track_rsi_ema9 = models.FloatField(blank=True, null=True)
    order_track_rsi1h_0 = models.FloatField(blank=True, null=True)
    order_track_rsi1h_1 = models.FloatField(blank=True, null=True)
    order_track_1d_rsi_wma = models.FloatField(blank=True, null=True)
    order_track_1w_rsi_wma = models.FloatField(blank=True, null=True)
    order_track_1d_up = models.FloatField(blank=True, null=True)
    order_track_1d_down = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'order_track'


class RankHistory(models.Model):
    rank_his_id = models.AutoField(primary_key=True)
    rank_his_year = models.IntegerField(blank=True, null=True)
    rank_his_time = models.BigIntegerField(blank=True, null=True)
    rank_his_symbol = models.CharField(max_length=150, blank=True, null=True)
    rank_his_value = models.IntegerField(blank=True, null=True)
    rank_his_market_cap = models.FloatField(blank=True, null=True)
    rank_his_price = models.FloatField(blank=True, null=True)
    rank_his_volume_24h = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rank_history'


class ScheduleAlert(models.Model):
    schedule_al_id = models.AutoField(primary_key=True)
    schedule_al_name = models.CharField(max_length=150, blank=True, null=True)
    schedule_al_groupid = models.CharField(max_length=150, blank=True, null=True)
    schedule_al_botid = models.CharField(max_length=150, blank=True, null=True)
    schedule_al_icon = models.TextField(blank=True, null=True)
    schedule_al_time = models.IntegerField(blank=True, null=True)
    schedule_al_content = models.TextField(blank=True, null=True)
    schedule_al_before = models.IntegerField(blank=True, null=True)
    schedule_al_note = models.TextField(blank=True, null=True)
    schedule_al_done = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'schedule_alert'


class Strategies(models.Model):
    strategy_id = models.AutoField(primary_key=True)
    strategy_name = models.CharField(max_length=150, blank=True, null=True)
    strategy_content = models.TextField(blank=True, null=True)
    strategy_note = models.TextField(blank=True, null=True)
    strategy_takeprofit = models.CharField(max_length=150, blank=True, null=True)
    strategy_stoploss = models.CharField(max_length=150, blank=True, null=True)
    strategy_baseprofit = models.CharField(max_length=150, blank=True, null=True)
    strategy_stepprofit = models.CharField(max_length=150, blank=True, null=True)
    strategy_backprofit = models.CharField(max_length=150, blank=True, null=True)
    strategy_baseprofit_baseon = models.CharField(max_length=150, blank=True, null=True)
    strategy_timelife = models.CharField(max_length=150, blank=True, null=True)
    strategy_interval = models.CharField(max_length=150, blank=True, null=True)
    strategy_margin = models.CharField(max_length=150, blank=True, null=True)
    strategy_container = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'strategies'


class StrategyContainer(models.Model):
    stra_con_id = models.AutoField(primary_key=True)
    stra_con_container = models.IntegerField(blank=True, null=True)
    stra_con_child = models.IntegerField(blank=True, null=True)
    stra_con_weight = models.IntegerField(blank=True, null=True)
    stra_con_slot = models.IntegerField(blank=True, null=True)
    stra_con_blacklist = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'strategy_container'


class TestnetAccount(models.Model):
    testnet_account_id = models.AutoField(primary_key=True)
    testnet_account_name = models.CharField(unique=True, max_length=150, blank=True, null=True)
    testnet_account_balance = models.FloatField(blank=True, null=True)
    testnet_account_reserve = models.FloatField(blank=True, null=True)
    testnet_account_compound = models.IntegerField(blank=True, null=True)
    testnet_account_note = models.TextField(blank=True, null=True)
    testnet_account_margin_type = models.CharField(max_length=20, blank=True, null=True)
    testnet_account_runtime = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'testnet_account'


class TestnetCampaign(models.Model):
    testnet_id = models.AutoField(primary_key=True)
    testnet_name = models.CharField(max_length=150, blank=True, null=True)
    testnet_symbol = models.CharField(max_length=150, blank=True, null=True)
    testnet_param = models.TextField(blank=True, null=True)
    testnet_side = models.CharField(max_length=10)
    testnet_strategy = models.IntegerField(blank=True, null=True)
    testnet_start_time = models.IntegerField(blank=True, null=True)
    testnet_stop_time = models.IntegerField(blank=True, null=True)
    testnet_note = models.TextField(blank=True, null=True)
    testnet_budget = models.FloatField(blank=True, null=True)
    testnet_reserve = models.FloatField(blank=True, null=True)
    testnet_money = models.FloatField(blank=True, null=True)
    testnet_compound = models.FloatField(blank=True, null=True)
    testnet_profit = models.FloatField(blank=True, null=True)
    testnet_tele_bot = models.CharField(max_length=150, blank=True, null=True)
    testnet_tele_gr_notice = models.CharField(max_length=150, blank=True, null=True)
    testnet_tele_gr_error = models.CharField(max_length=150, blank=True, null=True)
    testnet_tele_gr_summary = models.CharField(max_length=150, blank=True, null=True)
    testnet_group = models.CharField(max_length=150, blank=True, null=True)
    testnet_priority = models.IntegerField(blank=True, null=True)
    testnet_account = models.IntegerField(blank=True, null=True)
    testnet_active_budget = models.FloatField(blank=True, null=True)
    testnet_active = models.IntegerField(blank=True, null=True)

    

    class Meta:
        managed = False
        db_table = 'testnet_campaign'


class TestnetEnterbase(models.Model):
    enterbase_id = models.AutoField(primary_key=True)
    enterbase_campaign = models.IntegerField(blank=True, null=True)
    enterbase_symbol = models.CharField(max_length=150, blank=True, null=True)
    enterbase_action = models.IntegerField(blank=True, null=True)
    enterbase_time = models.BigIntegerField(blank=True, null=True)
    enterbase_price = models.FloatField(blank=True, null=True)
    enterbase_value = models.FloatField(blank=True, null=True)
    enterbase_event = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'testnet_enterbase'


class TestnetEventLogs(models.Model):
    testnet_elog_id = models.AutoField(primary_key=True)
    testnet_elog_campaign = models.IntegerField(blank=True, null=True)
    testnet_elog_symbol = models.CharField(max_length=20, blank=True, null=True)
    testnet_elog_time = models.BigIntegerField(blank=True, null=True)
    testnet_elog_chart = models.FloatField(blank=True, null=True)
    testnet_elog_result = models.JSONField(blank=True, null=True)
    testnet_elog_maxprofit = models.FloatField(blank=True, null=True)
    testnet_elog_minprofit = models.FloatField(blank=True, null=True)
    testnet_elog_profit = models.FloatField(blank=True, null=True)
    testnet_elog_baseprofit = models.FloatField(blank=True, null=True)
    testnet_elog_status = models.CharField(max_length=15, blank=True, null=True)
    testnet_elog_matched = models.IntegerField(blank=True, null=True)
    testnet_elog_base = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'testnet_event_logs'


class TestnetEvents(models.Model):
    testnet_events_id = models.AutoField(primary_key=True)
    testnet_events_symbol = models.CharField(max_length=20, blank=True, null=True)
    testnet_events_time = models.BigIntegerField(blank=True, null=True)
    testnet_events_icon = models.TextField(blank=True, null=True)
    testnet_events_profit = models.FloatField(blank=True, null=True)
    testnet_events_content = models.TextField(blank=True, null=True)
    testnet_events_strategy = models.IntegerField(blank=True, null=True)
    testnet_events_campaign = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'testnet_events'


class TestnetOrder(models.Model):
    testnet_order_id = models.AutoField(primary_key=True)
    testnet_order_time = models.BigIntegerField(blank=True, null=True)
    testnet_order_action = models.BigIntegerField(blank=True, null=True)
    testnet_order_symbol = models.CharField(max_length=150, blank=True, null=True)
    testnet_order_qty = models.FloatField(blank=True, null=True)
    testnet_order_price = models.FloatField(blank=True, null=True)
    testnet_order_commit = models.FloatField(blank=True, null=True)
    testnet_order_pnl = models.FloatField(blank=True, null=True)
    testnet_order_baseon = models.TextField(blank=True, null=True)
    testnet_order_type = models.IntegerField(blank=True, null=True)
    testnet_order_phase = models.IntegerField(blank=True, null=True)
    testnet_order_account = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'testnet_order'


class TestnetProfitbase(models.Model):
    profitbase_id = models.AutoField(primary_key=True)
    profitbase_campaign = models.IntegerField(blank=True, null=True)
    profitbase_symbol = models.CharField(max_length=150, blank=True, null=True)
    profitbase_action = models.IntegerField(blank=True, null=True)
    profitbase_time = models.BigIntegerField(blank=True, null=True)
    profitbase_price = models.FloatField(blank=True, null=True)
    profitbase_value = models.FloatField(blank=True, null=True)
    profitbase_event = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'testnet_profitbase'


class TestnetResults(models.Model):
    testnet_result_id = models.AutoField(primary_key=True)
    testnet_result_campaign = models.IntegerField(blank=True, null=True)
    testnet_result_strategy = models.IntegerField(blank=True, null=True)
    testnet_result_group = models.CharField(max_length=150, blank=True, null=True)
    testnet_result_container = models.IntegerField(blank=True, null=True)
    testnet_result_symbol = models.CharField(max_length=150, blank=True, null=True)
    testnet_result_chart = models.FloatField(blank=True, null=True)
    testnet_result_enter_time = models.BigIntegerField(blank=True, null=True)
    testnet_result_enter_price = models.FloatField(blank=True, null=True)
    testnet_result_order_time = models.BigIntegerField(blank=True, null=True)
    testnet_result_order_price = models.FloatField(blank=True, null=True)
    testnet_result_order_qty = models.FloatField(blank=True, null=True)
    testnet_result_order_phase = models.IntegerField(blank=True, null=True)
    testnet_result_order_release = models.IntegerField(blank=True, null=True)
    testnet_result_high = models.FloatField(blank=True, null=True)
    testnet_result_low = models.FloatField(blank=True, null=True)
    testnet_result_type = models.IntegerField(blank=True, null=True)
    testnet_result_base = models.TextField(blank=True, null=True)
    testnet_result_params = models.TextField(blank=True, null=True)
    testnet_result_start_reason = models.TextField(blank=True, null=True)
    testnet_result_status = models.IntegerField(blank=True, null=True)
    testnet_result_matched_ema5 = models.FloatField(blank=True, null=True)
    testnet_result_matched_price = models.FloatField(blank=True, null=True)
    testnet_result_first_price = models.FloatField(blank=True, null=True)
    testnet_result_matched_time = models.FloatField(blank=True, null=True)
    testnet_result_matched_qty = models.FloatField(blank=True, null=True)
    testnet_result_last_price = models.FloatField(blank=True, null=True)
    testnet_result_sell_price = models.FloatField(blank=True, null=True)
    testnet_result_sell_time = models.FloatField(blank=True, null=True)
    testnet_result_profit = models.FloatField(blank=True, null=True)
    testnet_result_commit = models.FloatField(blank=True, null=True)
    testnet_result_eventprofit = models.FloatField(blank=True, null=True)
    testnet_result_realprofit = models.FloatField(blank=True, null=True)
    testnet_result_realpnl = models.FloatField(blank=True, null=True)
    testnet_result_baseprofit = models.FloatField(blank=True, null=True)
    testnet_result_pending = models.IntegerField(blank=True, null=True)
    testnet_result_phase = models.IntegerField(blank=True, null=True)
    testnet_result_budget = models.FloatField(blank=True, null=True)
    testnet_result_nextphase_note = models.TextField(blank=True, null=True)
    testnet_result_phase_note = models.TextField(blank=True, null=True)
    testnet_result_flow = models.CharField(max_length=150, blank=True, null=True)
    testnet_result_interval = models.BigIntegerField(blank=True, null=True)
    testnet_result_margin = models.FloatField(blank=True, null=True)
    testnet_result_account = models.IntegerField(blank=True, null=True)
    testnet_result_close_time = models.IntegerField(blank=True, null=True)
    testnet_result_chart_price = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'testnet_results'


class TestnetTrackBalance(models.Model):
    testnet_track_bl_id = models.AutoField(primary_key=True)
    testnet_track_bl_account = models.IntegerField(blank=True, null=True)
    testnet_track_bl_time = models.BigIntegerField(blank=True, null=True)
    testnet_track_bl_margin_bl = models.FloatField(blank=True, null=True)
    testnet_track_bl_invest = models.FloatField(blank=True, null=True)
    testnet_track_bl_unrealize = models.FloatField(blank=True, null=True)
    testnet_track_bl_balance = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'testnet_track_balance'


class Volatility(models.Model):
    volatility_id = models.AutoField(primary_key=True)
    volatility_symbol = models.CharField(max_length=150, blank=True, null=True)
    volatility_time = models.BigIntegerField(blank=True, null=True)
    volatility_1d_high_low_avg3d_value = models.FloatField(blank=True, null=True)
    volatility_1d_high_high_avg3d_value = models.FloatField(blank=True, null=True)
    volatility_1d_low_low_avg3d_value = models.FloatField(blank=True, null=True)
    volatility_1d_high_low_avg7d_value = models.FloatField(blank=True, null=True)
    volatility_1d_high_high_avg7d_value = models.FloatField(blank=True, null=True)
    volatility_1d_low_low_avg7d_value = models.FloatField(blank=True, null=True)
    volatility_4h_high_low_avg3d_value = models.FloatField(blank=True, null=True)
    volatility_4h_high_high_avg3d_value = models.FloatField(blank=True, null=True)
    volatility_4h_low_low_avg3d_value = models.FloatField(blank=True, null=True)
    volatility_4h_high_low_avg7d_value = models.FloatField(blank=True, null=True)
    volatility_4h_high_high_avg7d_value = models.FloatField(blank=True, null=True)
    volatility_4h_low_low_avg7d_value = models.FloatField(blank=True, null=True)
    volatility_1d_high_low_avg3d_rank = models.IntegerField(blank=True, null=True)
    volatility_1d_high_high_avg3d_rank = models.IntegerField(blank=True, null=True)
    volatility_1d_low_low_avg3d_rank = models.IntegerField(blank=True, null=True)
    volatility_1d_high_low_avg7d_rank = models.IntegerField(blank=True, null=True)
    volatility_1d_high_high_avg7d_rank = models.IntegerField(blank=True, null=True)
    volatility_1d_low_low_avg7d_rank = models.IntegerField(blank=True, null=True)
    volatility_4h_high_low_avg3d_rank = models.IntegerField(blank=True, null=True)
    volatility_4h_high_high_avg3d_rank = models.IntegerField(blank=True, null=True)
    volatility_4h_low_low_avg3d_rank = models.IntegerField(blank=True, null=True)
    volatility_4h_high_low_avg7d_rank = models.IntegerField(blank=True, null=True)
    volatility_4h_high_high_avg7d_rank = models.IntegerField(blank=True, null=True)
    volatility_4h_low_low_avg7d_rank = models.IntegerField(blank=True, null=True)
    volatility_4h_close_low_avg3d_value = models.FloatField(blank=True, null=True)
    volatility_4h_close_low_avg7d_value = models.FloatField(blank=True, null=True)
    volatility_1d_close_low_avg3d_value = models.FloatField(blank=True, null=True)
    volatility_1d_close_low_avg7d_value = models.FloatField(blank=True, null=True)
    volatility_4h_close_low_avg3d_rank = models.IntegerField(blank=True, null=True)
    volatility_4h_close_low_avg7d_rank = models.IntegerField(blank=True, null=True)
    volatility_1d_close_low_avg3d_rank = models.IntegerField(blank=True, null=True)
    volatility_1d_close_low_avg7d_rank = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'volatility'


class VolatilityHistory(models.Model):
    volatility_id = models.AutoField(primary_key=True)
    volatility_symbol = models.CharField(max_length=100, blank=True, null=True)
    volatility_time = models.BigIntegerField(blank=True, null=True)
    volatility_4h_highlow_t0_value = models.FloatField(blank=True, null=True)
    volatility_4h_highlow_t1_value = models.FloatField(blank=True, null=True)
    volatility_4h_highlow_t2_value = models.FloatField(blank=True, null=True)
    volatility_4h_highhigh_t0_value = models.FloatField(blank=True, null=True)
    volatility_4h_highhigh_t1_value = models.FloatField(blank=True, null=True)
    volatility_4h_highhigh_t2_value = models.FloatField(blank=True, null=True)
    volatility_1d_highlow_t0_value = models.FloatField(blank=True, null=True)
    volatility_1d_highlow_t1_value = models.FloatField(blank=True, null=True)
    volatility_1d_highlow_t2_value = models.FloatField(blank=True, null=True)
    volatility_1d_highhigh_t0_value = models.FloatField(blank=True, null=True)
    volatility_1d_highhigh_t1_value = models.FloatField(blank=True, null=True)
    volatility_1d_highhigh_t2_value = models.FloatField(blank=True, null=True)
    volatility_4h_highlow_t0_rank = models.IntegerField(blank=True, null=True)
    volatility_4h_highlow_t1_rank = models.IntegerField(blank=True, null=True)
    volatility_4h_highlow_t2_rank = models.IntegerField(blank=True, null=True)
    volatility_4h_highhigh_t0_rank = models.IntegerField(blank=True, null=True)
    volatility_4h_highhigh_t1_rank = models.IntegerField(blank=True, null=True)
    volatility_4h_highhigh_t2_rank = models.IntegerField(blank=True, null=True)
    volatility_1d_highlow_t0_rank = models.IntegerField(blank=True, null=True)
    volatility_1d_highlow_t1_rank = models.IntegerField(blank=True, null=True)
    volatility_1d_highlow_t2_rank = models.IntegerField(blank=True, null=True)
    volatility_1d_highhigh_t0_rank = models.IntegerField(blank=True, null=True)
    volatility_1d_highhigh_t1_rank = models.IntegerField(blank=True, null=True)
    volatility_1d_highhigh_t2_rank = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'volatility_history'


class Watchlist(models.Model):
    wl_id = models.AutoField(primary_key=True)
    wl_symbol = models.CharField(unique=True, max_length=150, blank=True, null=True)
    wl_note = models.TextField(blank=True, null=True)
    wl_uid = models.IntegerField(blank=True, null=True)
    wl_time = models.IntegerField(blank=True, null=True)
    wl_stoptime = models.IntegerField(blank=True, null=True)
    wl_icon = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'watchlist'
