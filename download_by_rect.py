import requests
import fiona
from shapely.geometry import mapping
import os
from shapely.geometry import Polygon
from fiona.crs import from_epsg


headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
           }
url = "https://yncx.mnr.gov.cn/7H8i9J0k1L2m3N4o5p6Q7R8s9T0u1V2w3X4y5Z6/queryResults.json"

params = {"returnContent": "true"}
def get_features(x1,y1,x2,y2,n):
    form_data = {
        'queryMode': 'SpatialQuery',
        'queryParameters': {
            'customParams': None,
            'prjCoordSys': {'epsgCode': 4490},
            'expectCount': n,
            'networkType': "LINE",
            'queryOption': "ATTRIBUTEANDGEOMETRY",
            'queryParams': [{'name': "pro31@yndk", 'attributeFilter': "1=1", 'fields': None}],
            'startRecord': 0,
            'holdTime': 10,
            'returnCustomResult': False,
            'returnFeatureWithFieldCaption': False
        },
        'geometry': {
            'id': 0,
            'style': None,
            'parts': [5],
            'points': [
                {'id': "SuperMap.Geometry_1", 'bounds': None, 'SRID': None, 'x': x1, 'y': y1, 'tag': None, 'type': "Point", 'geometryType': "Point"},
                {'id': "SuperMap.Geometry_2", 'bounds': None, 'SRID': None, 'x': x2, 'y': y1, 'tag': None, 'type': "Point", 'geometryType': "Point"},
                {'id': "SuperMap.Geometry_3", 'bounds': None, 'SRID': None, 'x': x2, 'y': y2, 'tag': None, 'type': "Point", 'geometryType': "Point"},
                {'id': "SuperMap.Geometry_4", 'bounds': None, 'SRID': None, 'x': x1, 'y': y2, 'tag': None, 'type': "Point", 'geometryType': "Point"},
                {'id': "SuperMap.Geometry_5", 'bounds': None, 'SRID': None, 'x': x1, 'y': y1, 'tag': None, 'type': "Point", 'geometryType': "Point"}
            ],
            'type': "REGION",
            'prjCoordSys': {'epsgCode': None}
        },
        'spatialQueryMode': "INTERSECT"
    }

    response = requests.post(url, headers=headers, params=params, json=form_data)
    jsondata=response.json()
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
    file_path_geojson = '1.geojson'

    # 默认按矩形查找，传入左上与右下坐标，建议查询范围不要太大，爱护服务器
    x1=120.63954
    y1=32.43703
    x2=120.6456
    y2=32.43089

    fetures=get_features(x1,y1,x2,y2,expectCount)
    download_geojson(file_path_geojson,fetures)

    #输出为shp格式
    # file_path_shp='1.shp'
    # convert_geojson_to_shapefile(file_path_geojson, file_path_shp)