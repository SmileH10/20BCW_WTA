from entity import *
from rl_cores import State
import random


class Env(object):
    """
    시뮬레이션
    State transition 하는 곳
    """
    def __init__(self, map_width, map_height, battery_num, flight_num, flight_time_interval):
        self.asset = {}
        self.flight = {}  # flight 객체들을 저장하는 딕셔너리
        self.battery = {}  # battery 객체들을 저장하는 딕셔너리
        self.missile = {}  # missile 객체들을 저장하는 딕셔너리

        self.map_width = map_width
        self.map_height = map_height
        self.b_num = battery_num
        self.f_num = flight_num
        self.f_interval = flight_time_interval  # 첫 출발 flight ~ 마지막 출발 flight 의 시간 간격 (unit_time)

        self.sim_t = 0  # 현재 시뮬레이션 시간
        self.animation = None  # tkinter class
        self.animation_autosave = True
        self.num_f_survived = 0

    def init_env(self, task, num_iter):
        """
        매 iteration 마다 sim_t 초기화 / battery 초기화 / asset 새로 생성 / flight 새로 생성
        """
        self.sim_t = 0
        self.num_f_survived = 0
        if task.lower() == 'test':
            random.seed(num_iter + 910814)
        elif task.lower() == 'train':  # 로딩한 agent 이어서 학습할 때 예전 꺼 그대로 반복하지 않도록...
            random.seed(num_iter)

        """
        flight 출발좌표: (x, map_height - 10)
        battery 위치좌표: (x, 사거리 * 2.5)
        asset 위치좌표: (x, 5)
        """
        del self.battery, self.flight, self.asset
        self.battery = {}
        self.asset = {}
        self.flight = {}

        # battery 생성
        temp_x = self.map_width / 2 / self.b_num
        for b in range(self.b_num):
            # 일단 위치는 균등하게 퍼트려놓음.
            self.battery[b] = Battery(b_id=b, x=temp_x, y=100)
            temp_x += self.map_width / self.b_num

        # asset 생성
        asset_num = self.f_num
        temp_x = [random.random() for _ in range(asset_num)]
        temp_x.sort()
        for a in range(asset_num):
            self.asset[a] = Asset(a_id=a, x=temp_x[a] * self.map_width, y=5, value=1)

        # flight 생성
        temp_x = [random.random() for _ in range(self.f_num)]
        temp_x.sort()
        for f in range(self.f_num):
            # 일단 출발위치는 uniform 분포, 목표자산 아무거나 설정
            self.flight[f] = Flight(f_id=f, init_x=temp_x[f] * self.map_width, init_y=self.map_height - 10, target_asset=self.asset[f],
                                    start_t=random.randint(0, self.f_interval))

    def step(self, actions):
        reward = self.transit_afteraction_state(actions)
        self.transit_next_state()
        next_state = State(self)
        return next_state, reward

    def transit_afteraction_state(self, actions):
        # action (어떤 포대가 어느 전투기로 "미사일"을 발사했다) 을 반영. 시간 경과 없음
        f_surv_prob_before = sum([f.surv_prob for f in self.flight.values()])
        for a in actions:
            if a != 'DoNothing':
                action_bid = a[0]
                action_fid = a[1]
                new_missile = Missile(launching_battery=self.battery[action_bid], target_flight=self.flight[action_fid])  # 미사일 생성
                self.missile[new_missile.id] = new_missile  # 미사일 딕셔너리에 추가
                self.battery[action_bid].init_reload()  # 포대 재장전시간 초기화
                self.flight[action_fid].surv_prob = self.flight[action_fid].multiply([(1 - m.kill_prob) for m in self.missile.values() if m.flight.id == a[1]])  # 변경된 전투기 생존확률 반영
        reward = f_surv_prob_before - sum([f.surv_prob for f in self.flight.values()])
        return reward

    def transit_next_state(self):
        # 시뮬레이션 시간을 1 증가시키기
        self.sim_t += 1
        # 전투기/포대/미사일 시간경과하면서 생긴 변화 반영
        for fkey in list(self.flight.keys()):
            self.flight[fkey].transit_route(self)  # 전투기 1칸 이동. 방향 회전할 수도 있음.
            if self.flight[fkey].kill_asset:
                del(self.asset[self.flight[fkey].target_asset.id])
                del(self.flight[fkey])
                self.num_f_survived += 1  # 결과출력용
        for b in self.battery.values():
            b.transit_reload()  # 포대 재장전 시간 -1
        for m in self.missile.values():
            m.update_info()  # 만약 전투기가 방향 틀었으면, 예상파괴확률(kill_prob), 예상도착시간(expc_arrt), 속도(v_x,v_y) 방향 다시 계산
            m.transit_route()  # 미사일 이동, 누적비행시간 +1, 예상도착시간 -1

        # 미사일 격추 확인
        m_exploding = [m for m in self.missile.values() if m.expc_arrt <= 0]  # 이번 시점에 충돌하는 미사일들의 리스트
        for m in m_exploding:
            if m.id in self.missile.keys():
                if m.kill_prob > random.random():  # 격추!
                    f_exploded_id = m.flight.id  # 격추한 비행기 id 기록
                    del(self.flight[f_exploded_id])  # 그 비행기 없애기
                    m_exploded = [m2 for m2 in self.missile.values() if m2.flight.id == f_exploded_id]  # 그 비행기로 향하고 있던 모든 미사일 찾기
                    for m2 in m_exploded:
                        m2.battery.radar_capa += 1  # 레이더 용량 늘려주기
                        del(self.missile[m2.id])  # 그 미사일 없애기
                else:  # 격추 실패!
                    f_survived = m.flight  # 살아남은 비행기 기록
                    m.battery.radar_capa += 1  # 레이더 용량 늘려주기
                    del (self.missile[m.id])  # 미사일만 없애기
                    # 살아남은(격추실패한) 전투기의 생존확률 업데이트
                    f_survived.surv_prob = f_survived.multiply([(1 - m2.kill_prob) for m2 in self.missile.values() if m2.flight == f_survived])
        # 위에서 계산 제대로 했는지 확인
        for b in self.battery.values():
            assert b.radar_capa == 2 - len([m for m in self.missile.values() if m.battery == b])

    def check_termination(self):
        """
        종료시켜도 되면 return True; else: return False
        남은 비행기 없을 때 종료
        """
        if not self.flight:  # if self.flight == {}: 으로 바꿔써도 됨.
            return True
        else:
            return False
