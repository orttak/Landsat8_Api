from django.contrib.gis.db import models

# Create your models here.
class Landsat8(models.Model):
    gid = models.AutoField(primary_key=True)
    area = models.FloatField(blank=True, null=True)
    perimeter = models.FloatField( blank=True, null=True)
    pr_field = models.FloatField(db_column='pr_',  blank=True, null=True)  # Field renamed because it ended with '_'.
    pr_id = models.FloatField( blank=True, null=True)
    rings_ok = models.FloatField( blank=True, null=True)
    rings_nok = models.FloatField( blank=True, null=True)
    path = models.FloatField( blank=True, null=True)
    row = models.FloatField( blank=True, null=True)
    mode = models.CharField(max_length=1, blank=True, null=True)
    sequence = models.FloatField( blank=True, null=True)
    wrspr = models.CharField(max_length=50, blank=True, null=True)
    pr = models.CharField(max_length=50, blank=True, null=True)
    acqdayl7 = models.CharField(max_length=50, blank=True, null=True)
    acqdayl8 = models.CharField(max_length=50, blank=True, null=True)
    geom = models.MultiPolygonField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'landsat8'

class AmazonLandsatlist(models.Model):
    index = models.BigIntegerField(primary_key=True)
    productid = models.TextField(db_column='productId', blank=True, null=True)  # Field name made lowercase.
    entityid = models.TextField(db_column='entityId', blank=True, null=True)  # Field name made lowercase.
    acquisitiondate = models.TextField(db_column='acquisitionDate', blank=True, null=True)  # Field name made lowercase.
    cloudcover = models.FloatField(db_column='cloudCover', blank=True, null=True)  # Field name made lowercase.
    processinglevel = models.TextField(db_column='processingLevel', blank=True, null=True)  # Field name made lowercase.
    path = models.BigIntegerField(blank=True, null=True)
    row = models.BigIntegerField(blank=True, null=True)
    min_lat = models.FloatField(blank=True, null=True)
    min_lon = models.FloatField(blank=True, null=True)
    max_lat = models.FloatField(blank=True, null=True)
    max_lon = models.FloatField(blank=True, null=True)
    download_url = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'amazon_landsatlist_index'

