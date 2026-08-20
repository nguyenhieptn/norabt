# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class LabNode(models.Model):
    lab_node_id = models.AutoField(primary_key=True)
    lab_node_name = models.CharField(unique=True, max_length=150, blank=True, null=True)
    lab_node_ip = models.CharField(max_length=150, blank=True, null=True)
    lab_node_port = models.IntegerField(blank=True, null=True)
    lab_node_sid = models.CharField(unique=True, max_length=150, blank=True, null=True)
    lab_node_status = models.CharField(max_length=150, blank=True, null=True)
    lab_node_ram = models.FloatField(blank=True, null=True)
    lab_node_ram_total = models.FloatField(blank=True, null=True)
    lab_node_cpu = models.FloatField(blank=True, null=True)
    lab_node_cpu_core = models.FloatField(blank=True, null=True)
    lab_node_disk = models.FloatField(blank=True, null=True)
    lab_node_disk_total = models.FloatField(blank=True, null=True)
    lab_node_note = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lab_node'


class LabOptimization(models.Model):
    lab_opt_id = models.AutoField(primary_key=True)
    lab_opt_name = models.CharField(max_length=150, blank=True, null=True)
    lab_opt_account = models.IntegerField(blank=True, null=True)
    lab_opt_params = models.TextField(blank=True, null=True)
    lab_opt_thread = models.IntegerField(blank=True, null=True)
    lab_opt_data_leng = models.IntegerField(blank=True, null=True, default=15)
    lab_opt_note = models.TextField(blank=True, null=True)
    lab_opt_log = models.TextField(blank=True, null=True)
    lab_opt_start_time = models.IntegerField(blank=True, null=True)
    lab_opt_stop_time = models.IntegerField(blank=True, null=True)
    lab_opt_processed = models.TextField(blank=True, null=True)
    lab_opt_server = models.CharField(max_length=150, blank=True, null=True, default="localhost")

    class Meta:
        managed = False
        db_table = 'lab_optimization'

class LabAccount(models.Model):
    lab_account_id = models.AutoField(primary_key=True)
    lab_account_name = models.CharField(unique=True, max_length=150, blank=True, null=True)
    lab_account_balance = models.FloatField(blank=True, null=True)
    lab_account_margin_balance = models.FloatField(blank=True, null=True)
    lab_account_reserve = models.FloatField(blank=True, null=True)
    lab_account_compound = models.IntegerField(blank=True, null=True)
    lab_account_note = models.TextField(blank=True, null=True)
    lab_account_log = models.TextField(blank=True, null=True)
    lab_account_params = models.TextField(blank=True, null=True)
    lab_account_margin_type = models.CharField(max_length=20, blank=True, null=True)
    lab_account_track_balance = models.IntegerField(blank=True, null=True)
    lab_account_running = models.IntegerField(blank=True, null=True)
    lab_account_sync = models.IntegerField(blank=True, null=True, default=1)
    lab_account_leap = models.IntegerField(blank=True, null=True, default=0)
    lab_account_db = models.TextField(blank=True, null=True)
    lab_account_data_type = models.CharField(max_length=150, blank=True, null=True)
    lab_account_data_length = models.IntegerField(blank=True, null=True)
    lab_account_server = models.CharField(max_length=150, blank=True, null=True)
    lab_account_choice_strategy = models.IntegerField(blank=True, null=True)
    lab_account_choice_period = models.IntegerField(blank=True, null=True)
    lab_account_choice_result = models.TextField(blank=True, null=True)
    lab_account_choice_condition = models.TextField(blank=True, null=True)
    lab_account_tele_bot = models.CharField(max_length=150, blank=True, null=True)
    lab_account_tele_group_notice = models.CharField(max_length=150, blank=True, null=True)
    lab_account_tele_group_summary = models.CharField(max_length=150, blank=True, null=True)
    lab_account_tele_group_error = models.CharField(max_length=150, blank=True, null=True)
    lab_account_user = models.IntegerField(blank=True, null=True)
    lab_account_group = models.CharField(max_length=150, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lab_account'
