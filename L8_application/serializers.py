from rest_framework import serializers
from .models import Landsat8,AmazonLandsatlist
'''
Serializers allow complex data such as querysets and model instances to be converted to native
Python datatypes that can then be easily rendered into JSON, XML or other content types.
Serializers also provide deserialization, allowing parsed data to be converted back into complex types,
after first validating the incoming data. 

With the 'fields' area that define parameters which talk with database.
'''

class Landsat8Serializer(serializers.ModelSerializer):
    class Meta:
        model = Landsat8
        fields = ['gid', 'area', 'perimeter', 'pr_field', 'pr_id', 'rings_ok', 'rings_nok', 'path', 'row', 'mode', 'sequence', 'wrspr', 'pr', 'acqdayl7', 'acqdayl8']
        #fields=__all__
class AmazonLandsatlistSerializer(serializers.ModelSerializer):
    class Meta:
        model=AmazonLandsatlist
        fields=['productid','path','row','min_lat','min_lon','max_lat','max_lon']
