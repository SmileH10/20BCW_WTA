from entity import Missile
import random


class Env(object):
    """
    시뮬레이션
    State transition 하는 곳
    """
    def __init__(self, asset, flight, battery):
        self.asset = asset
        self.flight = flight  # flight 객체들을 저장하는 딕셔너리
        self.battery = battery  # battery 객체들을 저장하는 딕셔너리
        self.missile = {}  # missile 객체들을 저장하는 딕셔너리
        self.agent = None
        self.sim_t = 0  # 현재 시뮬레이션 시간

    def run_simulation(self):
        while not self.check_termination():
            # 포대 별로 action 정하게끔 하기. self.state_transition에서 action 직후(시간경과x) 변환과 시간경과 이동을 분리하기.
            best_action = self.agent.select_action(self)  # 1) 현재 state에서 가장 좋은 action 선택하기
            self.state_transition(best_action)  # 2) 1)에서 선택한 action을 수행해서 next_state로 이동하기
            if self.agent.name == 'rl':  # 3) Q 함수의 가중치 업데이트하기
                self.agent.update_weight()
        print("simulation ends. print results...")
        """    
        5) 다 종료되면, 결과 출력하기
            * 중간중간 결과 저장해서 엑셀/그래프... 저장
            * 출력 함수들은 dataIO.py 파일에 만들어도 되고...
        """

    def state_transition(self, action):
        # action (어떤 포대가 어느 전투기로 "미사일"을 발사했다) 을 반영하기.
        if action == 'DoNothing':
            print("Do Nothing")
        else:
            new_missile = Missile(launching_battery=action[0], target_flight=action[1])
            self.missile[new_missile.id] = new_missile  # 미사일 딕셔너리에 추가
            action[0].init_reload()  # 포대 재장전시간 초기화

        # 시뮬레이션 시간을 1 증가시키기
        # 중요! 같은 시간대에 action 여러 개 (이 포대가 이 전투기, 저 포대가 저 전투기를 향해 발사) 할 수 있으니까 수정해야 함.
        self.sim_t += 1

        # 전투기 1칸 이동, 포대 재장전시간 -1, 미사일 이동 & 미사일 예상도착시간/예상파괴확률 조정
        for f in self.flight:
            f.transit_route()
        for b in self.battery:
            b.transit_reload()
        for m in self.missile:
            m.update_info()  # kill_prob, expc_arrt, v 다시 계산
            m.transit_route()

        # 미사일 격추 확인
        m_exploding = [m for m in self.missile if m.expc_arrt <= 0]
        for m in m_exploding:
            if m in self.missile:
                if m.kill_prob > random.random():  # 격추!
                    f_exploded = m.flight.id
                    del(self.flight[f_exploded])  # 비행기 없애기
                    for m2 in self.missile:
                        if m2.flight.id == f_exploded:
                            m2.battery.radar_capa += 1  # 레이더 용량 늘려주기
                            del (self.missile[m2.id])  # 그 비행기로 향하고 있던 모든 미사일 없애기
                else:  # 격추 실패!
                    m.battery.radar_capa += 1  # 레이더 용량 늘려주기
                    del (self.missile[m.id])  # 미사일만 없애기
        # 위에서 계산 제대로 했는지 확인
        for b in self.battery:
            assert b.radar_capa == 2 - len([m for m in self.missile if m.battery == b])
        # 비행기 생존 확률 정보 업데이트 (비행기/미사일 위치 방향 개수 바뀌었을테니까 다시 계산해야 함)
        for f in self.flight:
            f.surv_prob = f.multiply([(1 - m.kill_prob) for m in self.missile if m.flight == action[1]])

    def check_termination(self):
        """
        종료시켜도 되면 return True; else: return False
        남은 비행기 없을 때 종료
        """
        if self.flight == []:  # if not self.flight: 으로 바꿔써도 됨.
            return True
        else:
            return False
