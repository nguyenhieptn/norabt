# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


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
    testnet_result_chart_price = models.FloatField(blank=True, null=True)
    testnet_result_close_time = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'testnet_results'


class TestnetOrder(models.Model):
    testnet_order_id = models.AutoField(primary_key=True)
    testnet_order_time = models.BigIntegerField(blank=True, null=True)
    testnet_order_account = models.IntegerField(blank=True, null=True)
    testnet_order_action = models.BigIntegerField(blank=True, null=True)
    testnet_order_symbol = models.CharField(max_length=150, blank=True, null=True)
    testnet_order_qty = models.FloatField(blank=True, null=True)
    testnet_order_price = models.FloatField(blank=True, null=True)
    testnet_order_commit = models.FloatField(blank=True, null=True)
    testnet_order_pnl = models.FloatField(blank=True, null=True)
    testnet_order_baseon = models.TextField(blank=True, null=True)
    testnet_order_type = models.IntegerField(blank=True, null=True)
    testnet_order_phase = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'testnet_order'



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
    testnet_active = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'testnet_campaign'



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
