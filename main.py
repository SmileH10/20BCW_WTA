from env import Env
from agent import RL, Greedy
from entity import Asset, Flight, Battery
from sim_GUI import GraphicDisplay

import random


if __name__ == '__main__':
    random.seed(0)

    # map 생성
    map_width = 100.0  # (km)
    map_height = 250.0  # (km)
    """
    flight 출발좌표: (x, map_height)
    battery 위치좌표: (x, 사거리 + 10)
    asset 위치좌표: (x, 0)
    """

    # asset 생성
    asset_num = 20
    asset = {}
    for a in range(asset_num):
        asset[a] = Asset(x=random.random() * map_width, y=0, value=1)

    # flight 생성
    flight_num = asset_num  # 전체 flight 대수
    time_interval = 30  # 첫 출발 flight ~ 마지막 출발 flight의 시간 간격 (unit_time)
    flight = {}
    for f in range(flight_num):
        # 일단 출발위치는 uniform 분포, 목표자산 아무거나 설정
        flight[f] = Flight(f_id=f, init_x=random.random() * map_width, init_y=map_height, target_asset=asset[f],
                           start_t=random.randint(0, time_interval))
        # temp_target_asset = np.argmin([calc_object_dist(asset[a], flight[f]) for a in range(asset_num)])
        # flight[f].target_asset = asset[int(temp_target_asset)]

    # battery 생성
    battery_num = 3
    battery = {}
    temp_x = map_width/2/battery_num
    for b in range(battery_num):
        # 일단 위치는 균등하게 퍼트려놓음.
        battery[b] = Battery(b_id=b, x=temp_x, y=120)
        temp_x += map_width/battery_num

    rl = RL()
    greedy = Greedy()
    gui = GraphicDisplay(map_height, map_width, unit_pixel=5)

    env = Env(asset, flight, battery)
    env.agent = greedy  # rl 과 greedy 중에 선택
    env.gui = gui

    env.run_simulation()
    gui.mainloop()

    # # Load GUI
    # gui = GraphicDisplay(map_height, map_width, unit_pixel=5, load_file=True)
    # gui.mainloop()