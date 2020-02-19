from rest_framework import serializers
from .models import Landsat8,AmazonLandsatlist

class Landsat8Serializer(serializers.ModelSerializer):
    class Meta:
        model = Landsat8
        fields = ['gid', 'area', 'perimeter', 'pr_field', 'pr_id', 'rings_ok', 'rings_nok', 'path', 'row', 'mode', 'sequence', 'wrspr', 'pr', 'acqdayl7', 'acqdayl8']
        #fields=__all__
class AmazonLandsatlistSerializer(serializers.ModelSerializer):
    class Meta:
        model=AmazonLandsatlist
        fields=['productid','path','row','min_lat','min_lon','max_lat','max_lon']
