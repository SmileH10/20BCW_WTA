from env import Env
from agent import RL, Greedy
from entity import Asset, Flight, Battery
from util import calc_object_dist

import random
import numpy as np


if __name__ == '__main__':
    random.seed(0)

    # map 생성
    map_width = 100.0  # (km)
    map_height = 300.0  # (km)
    """
    flight 출발좌표: (x, map_height)
    battery 위치좌표: (x, 사거리 + 10)
    asset 위치좌표: (x, 0)
    """

    # asset 생성
    asset_num = 3
    asset = {}
    for a in range(asset_num):
        asset[a] = Asset(x=random.random() * map_width, y=0, value=1)

    # flight 생성
    flight_num = 20  # 전체 flight 대수
    flight_time = 30  # 첫 출발 flight ~ 마지막 출발 flight의 시간 간격 (unit_time)
    flight = {}
    for f in range(flight_num):
        # 일단 출발위치는 uniform 분포, 목표자산은 가장 가까운 거 할당하도록 생성
        flight[f] = Flight(id=f, init_x=random.random() * map_width, init_y=map_height, target_asset=None)
        temp_target_asset = np.argmin([calc_object_dist(asset[a], flight[f]) for a in range(asset_num)])
        flight[f].target_asset = asset[int(temp_target_asset)]

    # battery 생성
    battery_num = 3
    battery = {}
    temp_x = map_width/2/battery_num
    for b in range(battery_num):
        # 일단 위치는 균등하게 퍼트려놓음.
        battery[b] = Battery(id=b, x=temp_x, y=2*map_width/battery_num)

    rl = RL()
    greedy = Greedy()

    env = Env(asset, flight, battery)
    env.agent = rl  # rl 과 greedy 중에 선택

    env.run_simulation()
