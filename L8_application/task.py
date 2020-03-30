from celery import shared_task,task
import json 
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
import uuid

# NDVI calculation class. We aim to develop this class to more flexible 
# according to different indices which user's define 
@task()
def createDownloadPath(download_path,ImageproductID):
    # This function is creating image folder. ImageproductID means child folder name.
    # ImageproductID, it could be index name or Landsat8 image's name
    
    if os.path.exists(download_path+ImageproductID)==False:
        os.makedirs(download_path+ImageproductID+'/')
        image_path=download_path+ImageproductID+'/'
        return image_path
    else:
        image_path=download_path+ImageproductID+'/'
        return image_path
@task()
def downloadImage(url,image_path):
    # This function was created for download image which is defined by 'landsat_getimage' function
    response = requests.get(url, stream=True)
    with open(os.path.join(image_path), 'wb') as output:
        shutil.copyfileobj(response.raw, output)            
    del response
    return image_path
@task()
def create_toa(image_path,dst_path,mtl):
    # In this function we use rasterio library to calculate Landsat8 Top of atmosphere images    
    creation_options = {'nodata': 0,'compress': 'deflate','predict': 2}
    try:
        #define which band
        bandnum = _parse_bands_from_filename([image_path], '.*/LC08.*\_B{b}.TIF')
        print(bandnum)
        
        calculate_landsat_reflectance([image_path], mtl, dst_path,rescale_factor = 55000,
        creation_options= creation_options,bands=bandnum, dst_dtype = 'uint16', processes = 1,
        pixel_sunangle=True,)        
        return dst_path            
    except ValueError:
        pass
@task()
def calculate_ndvi(red_path,nir_path,output_path):
    g = gdal.Open(red_path)        
    red = g.ReadAsArray().astype('float')
    g = gdal.Open(nir_path)        
    nir = g.ReadAsArray().astype('float')

    numpy.seterr(divide='ignore', invalid='ignore')
    # with numpy.where function, we can define no data value of image
    ndvi = numpy.where(((nir+red)==0.),-32768,(nir-red)/(nir+red))
    #scale the index to store it like 'int16'
    ndvi_scale=ndvi*10000
    #raw image ul coordinate  e.g (348285.0, 30.0, 0.0, 4265115.0, 0.0, -30.0)  
    s_srs = g.GetProjectionRef()
    osng = osr.SpatialReference ()
    osng.SetFromUserInput ( s_srs )
    geo_t = g.GetGeoTransform ()
    x_size = g.RasterXSize # Raster xsize
    y_size = g.RasterYSize # Raster ysize
    #create gdal memory file to convert image to EPSG:4326
    mem_drv = gdal.GetDriverByName( 'MEM' )
    dest = mem_drv.Create('', x_size,y_size, 1, gdal.GDT_Int16)
    dest.SetGeoTransform( geo_t )
    dest.SetProjection ( osng.ExportToWkt() )
    dest.GetRasterBand(1).SetNoDataValue(-32768)
    dest.GetRasterBand(1).WriteArray(ndvi_scale)
    gdal.Warp(output_path, dest, format = 'GTiff', dstSRS = 'EPSG:4326 ')   
    dst_ds=None
    mem_drv=None
    
    return output_path
@task()
def mainfunction(img,output_folder):
    #for img in body:
    if img == 'None':
        print('hey')
    response = requests.get(img['download_url'])
    if response.status_code == 200:
        #in production level, we should define download path to .env file               
        image_dir=createDownloadPath(download_path='../../geoserver_data/'+output_folder+'/',ImageproductID=img['productid'])
        print(image_dir)
        url = img['download_url'][:-10]
        red = img['productid']+'_B4.TIF'
        nir = img['productid']+'_B5.TIF'
        metadata = img['productid']+'_MTL.json'          
        
        red=downloadImage(url+red,image_dir+red)
        nir=downloadImage(url+nir,image_dir+nir)
        mtl=downloadImage(url+metadata,image_dir+metadata)
        
        red_toa_name = 'TOA_'+img['productid']+'_B4.TIF'
        nir_toa_name = 'TOA_'+img['productid']+'_B5.TIF'
        
        #calculate toa images
        red_toa=create_toa(red,image_dir+red_toa_name,mtl)
        nir_toa=create_toa(nir,image_dir+nir_toa_name,mtl)
        ndvi_path=createDownloadPath(download_path='../../geoserver_data/'+output_folder+'/',ImageproductID='ndvi')
        ndvi_name=img['productid']+'_NDVI.tif'        
        
        print(ndvi_path+ndvi_name)
        ndvi=calculate_ndvi.delay(red_path=red_toa,nir_path=nir_toa,output_path=ndvi_path+ndvi_name)

    else:
        print('hey')
        
@shared_task()   
def defineindex(body):
    if body[0]['index']=='ndvi':
        #create random folder name
        output_folder = str(uuid.uuid4().hex)
        for img in body[1:]:
            mainfunction.delay(img,output_folder)      
        
        return output_folder
# Pust the data to geoserver, we use geoserver rest-api library
    '''
    from geoserver.catalog import Catalog
    GEOSERVER_URL=os.getenv('GEOSERVER_URL')
    GEOSERVER_USERNAME=os.getenv('GEOSERVER_USERNAME')
    GEOSERVER_PASSWORD=os.getenv('GEOSERVER_PASSWORD')
    GEOSERVER_DATADIR=os.getenv('GEOSERVER_DATADIR')
    cat = Catalog(GEOSERVER_URL, username=GEOSERVER_USERNAME, password=GEOSERVER_PASSWORD)
    # when we use token that include user information, we can define new folder policy
    # datapath/userfolder/sessionid etc.
    cat.create_workspace(output_folder,output_folder)
    #path, filename = os.path.split(output_path)
    cat.create_imagemosaic(output_folder,GEOSERVER_DATADIR+output_folder+'/ndvi',
    configure='all',workspace=output_folder)
    '''