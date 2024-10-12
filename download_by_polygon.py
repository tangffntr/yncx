import time
import random
import geopandas as gpd
from shapely.geometry import box
import numpy as np
from geopy.distance import geodesic
import download_by_rect
import json

#传入多边形，按最大边界坐标切割为指定大小格网分别下载
def download_by_girds(polygon,grid_size,savefile_path):

    # 计算多边形的边界
    min_x, min_y, max_x, max_y = polygon.bounds

    # 计算栅格的数量
    width=geodesic((min_y, min_x), (min_y, max_x)).meters
    height=geodesic((min_y,min_x),(max_y,min_x)).meters
    num_cols = int(np.ceil(width/ grid_size))
    num_rows = int(np.ceil(height / grid_size))

    #计算每个栅格的宽度和高度，换算为度数
    width_per_grid = (max_x-min_x) / num_cols
    height_per_grid = (max_y-min_y) / num_rows

    failure_grids=[]
    for row in range(num_rows):
        for col in range(num_cols):
            # 计算当前栅格的左上角和右下角坐标
            x1 = min_x + col * width_per_grid
            y1 = max_y - row * height_per_grid
            x2 = x1 + width_per_grid
            y2 = y1 - height_per_grid


            # 检查栅格和多边形是否相交
            rectangle=box(x1,y1,x2,y2)
            is_intersect = rectangle.intersects(polygon)

            if is_intersect:
                max_retries = 3
                retries = 0
                while retries < max_retries:
                    try:
                        fetures = download_by_rect.get_features(x1, y1, x2, y2, 1000)
                        download_by_rect.download_geojson(savefile_path,fetures)
                        print(f'栅格总数{num_rows}行X{num_cols}列，{row + 1}行{col + 1}列下载成功')
                        break
                    except Exception as e:
                        print(f'栅格总数{num_rows}行X{num_cols}列，{row + 1}行{col + 1}列下载失败，第{retries + 1}次重试: {e}')
                        retries += 1
                        if retries < max_retries:
                            time.sleep(5)  # 等待5秒后重试
                        else:
                            failure_grids.append([x1, y1, x2, y2])

                time.sleep(random.randint(3, 5))

    return failure_grids

if __name__ == '__main__':
    # 读取GeoJSON文件，获取第一个多边形，多个自行遍历
    file_path = 'example.geojson'
    gdf = gpd.read_file(file_path)
    polygon = gdf.geometry.iloc[0]

    # 定义栅格大小,限制面积500亩,这里设置为500*500米
    grid_size = 500

    # 设置保存路径
    savefile_path = 'download_example.geojson'

    #下载栅格
    failure_grids=download_by_girds(polygon, grid_size, savefile_path)

    #保存下载失败栅格坐标，后续可以直接使用矩形查找增加
    with open('failure_girds', 'w') as file:
        json.dump(failure_grids, file)


