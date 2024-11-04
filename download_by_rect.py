import requests
import fiona
from shapely.geometry import mapping
import os
from shapely.geometry import Polygon
from fiona.crs import from_epsg
import json

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
           }
url = "https://yncx.mnr.gov.cn/dist-app-yn/map/queryResults.json"

params = {"returnContent": "true",
          'token':'Whe67hpdoYaBsTRmdzFkEfWcUyHkFuwQOuKgXDHEOv2deNvj0VbufUWA2w0297kDBDa5T_1V6__VvI1lHY7_fMwl'}
def get_features(x1,y1,x2,y2,n):
    form_data = {
        'queryMode': 'SpatialQuery',
        'queryParameters': {
            'prjCoordSys': {'epsgCode': 4490},
            'expectCount': n,
            'queryParams': [{'name': "pro31@yndk", 'attributeFilter': "1=1", 'fields': ['yjjbntmj','yjjbnttbbh']}],
            'startRecord': 0,
        },
        'geometry': {
            'id': None,
            'style': None,
            'parts': [5],
            'points': [
                {'CLASS_NAME':'SuperMap.Geometry.Point','id': "SuperMap.Geometry_1", 'bounds': None, 'SRID': None, 'x': x1, 'y': y1, 'tag': None, 'type': "Point", 'geometryType': "Point"},
                {'CLASS_NAME':'SuperMap.Geometry.Point','id': "SuperMap.Geometry_2", 'bounds': None, 'SRID': None, 'x': x2, 'y': y1, 'tag': None, 'type': "Point", 'geometryType': "Point"},
                {'CLASS_NAME':'SuperMap.Geometry.Point','id': "SuperMap.Geometry_3", 'bounds': None, 'SRID': None, 'x': x2, 'y': y2, 'tag': None, 'type': "Point", 'geometryType': "Point"},
                {'CLASS_NAME':'SuperMap.Geometry.Point','id': "SuperMap.Geometry_4", 'bounds': None, 'SRID': None, 'x': x1, 'y': y2, 'tag': None, 'type': "Point", 'geometryType': "Point"},
                {'CLASS_NAME':'SuperMap.Geometry.Point','id': "SuperMap.Geometry_5", 'bounds': None, 'SRID': None, 'x': x1, 'y': y1, 'tag': None, 'type': "Point", 'geometryType': "Point"}
            ],
            'type': "REGION",
            'prjCoordSys': {'epsgCode': 4490}
        },
        'spatialQueryMode': "INTERSECT"
    }

    response = requests.post(url, headers=headers, params=params, json=form_data)
    jsondata=response.json()
    # features=jsondata["recordsets"][0]["features"]

    data=jsondata['data']



    return data


from gmssl import sm2

def decrypt_geojson(data,key):

    if data and data.startswith("04"):
        data = data[2:]
    sm2_crypt = sm2.CryptSM2(public_key="", private_key=key,mode=1)
    features = sm2_crypt.decrypt(bytes.fromhex(data))
    features=features.decode('utf-8')
    jsondata=json.loads(features)
    features=jsondata["recordsets"][0]["features"]

    return features



def download_geojson(file_path,features):
    def create_polygon(feature):   #处理单个几何
        parts = feature['geometry']['parts']
        points = feature['geometry']['points']
        start_index = 0
        exterior_ring = []
        interior_rings = []

        for part in parts:
            end_index = start_index + part
            ring = [(points[i]['x'], points[i]['y']) for i in range(start_index, end_index)]

            if not exterior_ring:  # 如果外部边界尚未设置，则这是外部边界
                exterior_ring = ring
            else:  # 否则，这是一个内部边界
                interior_rings.append(ring)
            start_index = end_index

        # 如果没有内部边界，Polygon 只需要外部边界
        if not interior_rings:
            polygon = Polygon(exterior_ring)
        else:
        # 创建Polygon对象，第一个参数是外部边界，第二个参数是一个内部边界的列表
            polygon = Polygon(exterior_ring, holes=interior_rings)

        return polygon

    # 检查文件是否存在，如果不存在则创建文件并写入初始数据
    if not os.path.exists(file_path):
        with fiona.open(file_path, 'w', driver='GeoJSON', crs='EPSG:4490', schema={'geometry': 'Polygon', 'properties': {'ID': 'int'}}) as file:
            for feature in features:
                file.write({
                    'properties': {'ID': feature['ID']},
                    'geometry': mapping(create_polygon(feature))
                })

    # 如果文件已经存在则增量保存，通过ID去重
    else:
        existing_ids = []
        with fiona.open(file_path, 'r') as file:
            for feature in file:
                existing_ids.append(feature['properties']['ID'])
        with fiona.open(file_path, 'a') as file:
            for feature in features:
                if feature['ID'] not in existing_ids:
                    file.write({
                        'properties': {'ID': feature['ID']},
                        'geometry': mapping(create_polygon(feature))
                    })
def convert_geojson_to_shapefile(input_geojson, output_shapefile):
    with fiona.open(input_geojson, 'r') as source:
        with fiona.open(
                output_shapefile, 'w',
                driver='ESRI Shapefile',
                crs=from_epsg(4490),  # 设置坐标系，根据实际情况修改
                schema=source.schema
        ) as sink:
            for feature in source:
                sink.write(feature)


if __name__ == "__main__":
    # 默认最大查询1000片，建议不要修改
    expectCount=1000

    # 保存文件路径
    file_path_geojson = '2.geojson'

    # 默认按矩形查找，传入左上与右下坐标，建议查询范围不要太大，爱护服务器
    x1=120.63954
    y1=32.43703
    x2=120.6456
    y2=32.43089

    key='fe32f6eb62706f559d46f77011474d72a40707135badcfc7a59dad09948895f5'

    fetures=get_features(x1,y1,x2,y2,expectCount)

    fetures=decrypt_geojson(fetures,key)

    download_geojson(file_path_geojson,fetures)

    #输出为shp格式
    # file_path_shp='1.shp'
    # convert_geojson_to_shapefile(file_path_geojson, file_path_shp)

