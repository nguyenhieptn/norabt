# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from django.db.models.signals import pre_delete

class Table1(models.Model):
    id1 = models.IntegerField(primary_key=True)
    name1 = models.CharField(max_length=11)

    class Meta:
        managed = False
        db_table = 'table1'


class Table2(models.Model):
    id2 = models.IntegerField(primary_key=True)
    name2 = models.CharField(max_length=11)

    class Meta:
        managed = False
        db_table = 'table2'
