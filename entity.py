import util
import math


class Asset(object):
    def __init__(self, x, y, value):
        self.x = x
        self.y = y
        self.value = value  # 자산 가치. 일단 넣어놨는데, 이거 안하기로 하지 않았나? 전투기가 어디로 향할지 방어는 모르니까.


class Flight(object):
    def __init__(self, id, init_x, init_y, target_asset):
        self.id = id
        self.x = init_x  # x 좌표
        self.y = init_y  # y 좌표
        self.v = 0.272  # 속력. kill prob 계산 때 사용
        self.v_x = 0  # x축 속도
        self.v_y = -0.272  # y축 속도
        self.direction = -0.5 * math.pi  # 진행 방향 (초기: -90도)
        self.target_asset = target_asset  # 목표 자산 객체 넣기. route 계산할 때 쓸 듯. 목표 자산을 향하도록 routing.
        self.surv_prob = 1.0  # 초기 생존확률 = 1
        self.change_direction_check = False  # 직전 시점에서 방향을 바꿨는지 기록: 미사일의 info를 새로 update 할 지 말 지 고를 때 사용.

    def transit_route(self):
        """
        공격 알고리즘(전투기의 공격 패턴)에 따라 수정해야 하는 블록.
        방어 알고리즘이 여기서 작성된 routing 확률분포를 학습함.
        # 각 전투기의 출발시간도 여기서 조절함
        """
        """
        Step 1) 진행 방향 정하기 (가던 방향? 방향 전환?)
        Step 2) 1 시점이 지났을 때의 x좌표, y좌표 update 하기
                예시) self.x += cosine(direction) * 1
        """
        self.x += self.v_x
        self.y += self.v_y
        # self.v_x, v_y 수정 . rotate 함수 이용
        rotate_theta = 0  # 범위 제한
        if rotate_theta != 0:
            [self.v_x, self.v_y] = util.rotate(rotate_theta, [self.v_x, self.v_y])
            self.direction += rotate_theta
            self.change_direction_check = True
        else:
            self.change_direction_check = False

    @staticmethod
    def multiply(arr):  # 생존확률 계산용 함수. (이 전투기를 향해 날아오는 여러 미사일의 kill prob 곱하는 역할)
        ans = 1.0
        for n in arr:
            if n == 0:
                return 0
            ans *= n
        return ans


class Battery(object):
    def __init__(self, id, x, y):
        self.id = id
        self.x = x  # 포대 x좌표
        self.y = y  # 포대 y좌표
        self.v = 0.816  # 미사일 속도 (kill prob 등 계산 편하게 하려고 여기서 씀. 같은 포대에서 발사된 미사일 속도 동일 가정)
        self.radar_capa = 2  # 레이더 용량. 동시 조준 가능한 미사일 개수
        self.radius = 40  # 사정거리
        self.reload = 0  # 남은 재장전 시간 = 발사가능시간까지 남은 시간
        self.total_launching = 0  # 지금까지 발사한 총 미사일 수. 미사일 id 만들 때 씀.

    def transit_reload(self):
        if self.reload > 0:
            self.reload -= 1
        assert self.radar_capa >= 0 and self.reload >= 0

    def init_reload(self):
        self.reload = 3  # 한 번 쏘고 나면 3초 뒤에 다시 쏠 수 있음.


class Missile(object):
    def __init__(self, launching_battery, target_flight):
        self.battery = launching_battery  # 미사일을 발사한 포대 객체
        self.flight = target_flight  # 맞추려고 향하고 있는 전투기 객체
        self.x = launching_battery.x  # 미사일 생성 시 초기 위치 = 발사한 포대 위치
        self.y = launching_battery.y
        self.battery.total_launching += 1
        self.id = [self.battery, self.flight, self.battery.total_launching]  # 같은 포대에서 같은 전투기로 여러 미사일 쏠 수 있어서, id[-1]로 구분.
        self.flight_t = 0  # 지금까지 비행한 시간
        self.update_info(target_flight, init=True)

    def update_info(self, f, init=False):
        """
        self.expc_arrt: 도착(=충돌)까지 남은 시간 기록
        self.kill_prob: 충돌 시 예상 파괴확률 기록
        self.v_x, self.v_y: 미사일 방향전환
        """
        if f.change_direction_check or init:  # 비행기가 방향 바꿨거나 or 처음 미사일이 생성되었으면, 새로 계산하기
            d_fm = [self.x - f.x, self.y - f.y]  # 전투기->미사일 벡터(d_fm) 생성
            d_fm_enorm = util.calc_object_dist(self, f)  # d_fm의 euclidean norm
            theta_fd = math.acos((f.v_x * d_fm[0] + f.v_y * d_fm[1]) / (f.v * d_fm_enorm))  # 전투기 진행방향 벡터(f)와 전투기->미사일 벡터(d_fm) 간 각도
            theta_md = abs(math.asin(math.sin(theta_fd)/3))  # 미사일 진행방향 벡터(m)와 미사일->전투기 벡터(-d_fm) 간 각도
            if math.asin((d_fm[0]*f.v_y - f.v_x*d_fm[1])/(f.v * d_fm_enorm)) > 0:  # d_fm -> f 가 반시계 방향일 때
                v_m = util.rotate(-theta_md, -1 * d_fm)  # 미사일 방향벡터(v_m)를 시계방향으로 회전
            else:    # d_fm -> f 가 시계 방향일 때
                v_m = util.rotate(theta_md, -1 * d_fm)  # 미사일 방향벡터(v_m)를 반시계방향으로 회전
            v_m /= math.sqrt(v_m[0] ** 2 + v_m[1] ** 2)  # 단위벡터로 만들고
            v_m *= self.battery.v  # v_m 크기를 미사일 속력 크기로 조절
            self.v_x = v_m[0]
            self.v_y = v_m[1]
            theta_mf = math.pi - theta_md - theta_fd  # 미사일(m)과 전투기(f)의 충돌 각도
            self.expc_arrt = d_fm_enorm / math.sqrt((f.v_x - self.v_x)**2 + (f.v_y - self.v_y)**2)  # 남은 도착시간 = fm 간 거리 / (전투기속도벡터 - 미사일 속도벡터)
            # 미사일과 전투기의 충돌지점(p) 검토
            assert [self.x + self.expc_arrt * self.v_x, self.y + self.expc_arrt * self.v_y] \
                   == [f.x + self.expc_arrt * f.v_x, f.y + self.expc_arrt * f.v_y]
            # 파괴확률 = 포대-충돌위치 간 거리(x) 미사일의 총 이동거리(o) 함수 * 충돌각도 함수
            self.kill_prob = util.calc_kill_prob_dist((self.flight_t + self.expc_arrt) * self.battery.v) \
                             * util.calc_kill_prob_angle(theta_mf)

    def transit_route(self):
        # 시간 1단위 지났을 때, 전투기를 향해 날아가는 이 미사일의 self.x, self.y, self.v_x, self.v_y 업데이트하는 곳. 만들어야 함.
        self.x += self.v_x
        self.y += self.v_y
        self.flight_t += 1
        self.expc_arrt -= 1
