from entity import Missile
import random
import math
from copy import deepcopy


class Env(object):
    """
    시뮬레이션
    State transition 하는 곳
    """
    def __init__(self, map_width, map_height):
        self.asset = {}
        self.flight = {}  # flight 객체들을 저장하는 딕셔너리
        self.battery = {}  # battery 객체들을 저장하는 딕셔너리
        self.missile = {}  # missile 객체들을 저장하는 딕셔너리
        self.map_width = map_width
        self.map_height = map_height
        self.agent = None
        self.sim_t = 0  # 현재 시뮬레이션 시간
        self.animation = None

    def run_simulation(self, iteration):
        while not self.check_termination():
            for b in self.battery.values():
                best_action = self.agent.select_action(self, b)  # 1) 현재 state에서 가장 좋은 action 선택하기
                self.transit_afteraction_state(best_action)
            if self.animation:
                if self.animation.event_cnt == 0:
                    self.animation.data[iteration][self.animation.event_cnt] = \
                        (self.sim_t, deepcopy(self.flight), deepcopy(self.missile), deepcopy(self.asset), deepcopy(self.battery))
                    self.animation.event_cnt += 1
                else:
                    if self.sim_t % 10 == 0 or self.animation.lenf != len(self.flight) or self.animation.lenm - len(self.missile) != 0:
                        self.animation.data[iteration][self.animation.event_cnt] = (self.sim_t, deepcopy(self.flight), deepcopy(self.missile), deepcopy(self.asset))
                        self.animation.event_cnt += 1
                self.animation.lenf = len(self.flight)
                self.animation.lenm = len(self.missile)
            self.transit_next_state()  # 2) 1)에서 선택한 action을 수행해서 next_state로 이동하기
            if self.agent.name == 'rl':  # 3) Q 함수의 가중치 업데이트하기
                self.agent.update_weight()
        print("[env.py] simulation iter %d ends. print results..." % iteration)
        if self.animation:
            self.animation.event_cnt = 0

    def transit_afteraction_state(self, action):
        # action (어떤 포대가 어느 전투기로 "미사일"을 발사했다) 을 반영. 시간 경과 없음
        if action != 'DoNothing':
            action_b = action[0]
            action_f = action[1]
            new_missile = Missile(launching_battery=action_b, target_flight=action_f)  # 미사일 생성
            self.missile[new_missile.id] = new_missile  # 미사일 딕셔너리에 추가
            action_b.init_reload()  # 포대 재장전시간 초기화
            action_f.surv_prob = action_f.multiply([(1 - m.kill_prob) for m in self.missile.values() if m.flight == action[1]])  # 변경된 전투기 생존확률 반영

    def transit_next_state(self):
        # 시뮬레이션 시간을 1 증가시키기
        self.sim_t += 1

        # 전투기/포대/미사일 시간경과하면서 생긴 변화 반영
        for fkey in list(self.flight.keys()):
            self.flight[fkey].transit_route(self)  # 전투기 1칸 이동. 방향 회전할 수도 있음.
            if self.flight[fkey].kill_asset:
                del(self.asset[self.flight[fkey].target_asset.id])
                del(self.flight[fkey])
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
