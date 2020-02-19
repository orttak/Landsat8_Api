from django.shortcuts import render
from L8_application.serializers import Landsat8Serializer,AmazonLandsatlistSerializer
from L8_application.models import Landsat8,AmazonLandsatlist
from rest_framework import viewsets
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
import json 
from django.contrib.gis.geos import Polygon
from ast import literal_eval
import os, shutil
import requests
#pip install rio-color
#pip install rio-toa
#pip install rio-l8qa
#pip install rasterio==1.1.0
from l8qa.qa import write_cloud_mask
from rio_toa import reflectance
from rio_toa import sun_utils, toa_utils
from rio_toa.toa_utils import rescale, _parse_bands_from_filename
from rio_toa.reflectance import calculate_landsat_reflectance
#from rio_toa.brightness_temp import calculate_landsat_brightness_temperature
from rio_color.operations import parse_operations
import numpy
from osgeo import gdal,gdalnumeric,osr,ogr
from dotenv import load_dotenv
load_dotenv()


class Landsat8List(viewsets.ModelViewSet):
    #view all data in DB
    queryset = Landsat8.objects.all()
    serializer_class = Landsat8Serializer

class LandsatPostView(APIView):
    def intersect_pathrow(self,geo):
        try:
            #convert str geo to tuple
            geo = literal_eval(geo)
            return Landsat8.objects.filter(geom__intersects=Polygon(geo))
        except Landsat8.DoesNotExist:
            raise Http404
    def landsat_getimage(self,path,row,date_min,date_max,cloud):
        try:
            return AmazonLandsatlist.objects.filter(path=path,
                                                    row=row,
                                                    acquisitiondate__gte=date_min,
                                                    acquisitiondate__lte=date_max,
                                                    cloudcover__lte=cloud).values()
        except AmazonLandsatlist.DoesNotExist:
            raise Http404

    def get(self, request, format=None):
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        geo = body['geo']
        date_min=body['date_min']
        date_max=body['date_max']
        cloud_cover=body['cloud_cover']
        intersect = self.intersect_pathrow(geo)
        selected_images=[]
        for i in intersect:
            path, row=i.path,i.row            
            l8=self.landsat_getimage(path,row,date_min,date_max,cloud_cover)
            #print(i.geom)
            best_image=l8.order_by('cloudcover').first()
            if best_image==None:
                continue
            selected_images.append(best_image)
            #for image in l8:
                #print('goruntu')
                #print(image['path'])
            #serializer_den = AmazonLandsatlistSerializer(l8)
        return Response((selected_images))

class LandsatNdviView(APIView):
    

    
    def createDownloadPath(self,download_path,ImageproductID):
        if os.path.exists(download_path+ImageproductID)==False:
            os.makedirs(download_path+ImageproductID+'/')
            image_path=download_path+ImageproductID+'/'
            return image_path
        else:
            image_path=download_path+ImageproductID+'/'
            return image_path
    def downloadImage(self,url,image_path):
        response = requests.get(url, stream=True)
        with open(os.path.join(image_path), 'wb') as output:
            shutil.copyfileobj(response.raw, output)            
        del response
        return image_path
    
    
    def create_toa(self,image_path,dst_path,mtl):
        creation_options = {'nodata': 0,'compress': 'deflate','predict': 2}
        try:
            bandnum = _parse_bands_from_filename([image_path], '.*/LC08.*\_B{b}.TIF')
            print(bandnum)
            
            calculate_landsat_reflectance([image_path], mtl, dst_path,rescale_factor = 55000,
            creation_options= creation_options,bands=bandnum, dst_dtype = 'uint16', processes = 4,
            pixel_sunangle=True,)
            
            return dst_path            
        except ValueError:
            pass
    def calculate_ndvi(self,red_path,nir_path,output_path):
        g = gdal.Open(red_path)        
        red = g.ReadAsArray().astype('float')
        g = gdal.Open(nir_path)        
        nir = g.ReadAsArray().astype('float')
  
        numpy.seterr(divide='ignore', invalid='ignore')
        ndvi = numpy.where(((nir+red)==0.),-32768,(nir-red)/(nir+red))
        ndvi_scale=ndvi*10000
        print(output_path)
        #raw image ul coordinate  e.g (348285.0, 30.0, 0.0, 4265115.0, 0.0, -30.0)  
        s_srs = g.GetProjectionRef()
        osng = osr.SpatialReference ()
        osng.SetFromUserInput ( s_srs )
        geo_t = g.GetGeoTransform ()
        x_size = g.RasterXSize # Raster xsize
        y_size = g.RasterYSize # Raster ysize
        mem_drv = gdal.GetDriverByName( 'MEM' )
        dest = mem_drv.Create('', x_size,y_size, 1, gdal.GDT_Int16)
        dest.SetGeoTransform( geo_t )
        dest.SetProjection ( osng.ExportToWkt() )
        dest.GetRasterBand(1).SetNoDataValue(-32768)
        dest.GetRasterBand(1).WriteArray(ndvi_scale)
        gdal.Warp(output_path, dest, format = 'GTiff', dstSRS = 'EPSG:4326 ')   
        dst_ds=None
        
        return output_path
    
    def get (self,request,format=None):
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        print(body)
        import uuid
        output_folder = str(uuid.uuid4().hex)
        
        for img in body:
            if img== 'None':
                continue
            response = requests.get(img['download_url'])
    
            if response.status_code == 200:               
                image_dir=self.createDownloadPath(download_path='../../geoserver_data/'+output_folder+'/',ImageproductID=img['productid'])
                print(image_dir)
                url = img['download_url'][:-10]
                red = img['productid']+'_B4.TIF'
                nir = img['productid']+'_B5.TIF'
                metadata = img['productid']+'_MTL.json'          
                
                red=self.downloadImage(url+red,image_dir+red)
                nir=self.downloadImage(url+nir,image_dir+nir)
                mtl=self.downloadImage(url+metadata,image_dir+metadata)
                
                red_toa_name = 'TOA_'+img['productid']+'_B4.TIF'
                nir_toa_name = 'TOA_'+img['productid']+'_B5.TIF'
                print(image_dir+nir_toa_name)

                red_toa=self.create_toa(red,image_dir+red_toa_name,mtl)
                nir_toa=self.create_toa(nir,image_dir+nir_toa_name,mtl)

                ndvi_path=self.createDownloadPath(download_path='../../geoserver_data/'+output_folder+'/',ImageproductID='ndvi')
                ndvi_name=img['productid']+'_NDVI.tif'
                
                
                print(ndvi_path+ndvi_name)
                ndvi=self.calculate_ndvi(red_path=red_toa,nir_path=nir_toa,output_path=ndvi_path+ndvi_name)
                
                
        
            else:
                continue
        from geoserver.catalog import Catalog
        GEOSERVER_URL=os.getenv('GEOSERVER_URL')
        GEOSERVER_USERNAME=os.getenv('GEOSERVER_USERNAME')
        GEOSERVER_PASSWORD=os.getenv('GEOSERVER_PASSWORD')
        GEOSERVER_DATADIR=os.getenv('GEOSERVER_DATADIR')
        cat = Catalog(GEOSERVER_URL, username=GEOSERVER_USERNAME, password=GEOSERVER_PASSWORD)
        cat.create_workspace(output_folder,output_folder)
        #path, filename = os.path.split(output_path)
        cat.create_imagemosaic(output_folder,GEOSERVER_DATADIR+output_folder+'/ndvi',
        configure='all',workspace=output_folder)

        return Response(output_folder+':ndvi')


