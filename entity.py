import util
import math
from random import random


class Asset(object):
    def __init__(self, x, y, value):
        self.x = x
        self.y = y
        self.value = value  # 자산 가치. 일단 넣어놨는데, 이거 안하기로 하지 않았나? 전투기가 어디로 향할지 방어는 모르니까.


class Flight(object):
    def __init__(self, f_id, init_x, init_y, target_asset, start_t=0):
        self.id = f_id
        self.x = init_x  # x 좌표
        self.y = init_y  # y 좌표
        self.start_t = start_t  # 출발 시점
        self.v = 0.272  # 속력. kill prob 계산 때 사용
        self.v_x = 0  # x축 초기 속도
        self.v_y = -0.272  # y축 초기 속도
        self.direction = -0.5 * math.pi  # 진행 방향 (초기: -90도)
        self.target_asset = target_asset  # 목표 자산 객체 넣기. route 계산할 때 쓸 듯. 목표 자산을 향하도록 routing.
        self.surv_prob = 1.0  # 초기 생존확률 = 1
        self.change_direction_check = False  # 직전 시점에서 방향을 바꿨는지 기록: 미사일의 info를 새로 update 할 지 말 지 고를 때 사용.
        self.kill_asset = False  # 자산에 도달해서 파괴성공했는지 체크. 자산에 도달한 비행기 없앨 때 사용.

    def transit_route(self, env):
        if env.sim_t < self.start_t:  # 전투기 출발시간이 아직 안됐으면
            return  # 움직이지 않음
        else:  # 출발시간이 지났으면 움직임 반영하기.
            self.x += self.v_x
            self.y += self.v_y
            # 목표 자산에 도달했는지 확인
            if self.y <= self.target_asset.y:
                # 결과 기록 함수 만들기!!!
                self.kill_asset = True
                return
            # 방향 전환하는 지 계산
            rotate_theta = self.calc_rotate_theta(env)
            if rotate_theta != 0:  # 방향 전환하면
                [self.v_x, self.v_y] = util.rotate_vector(rotate_theta, [self.v_x, self.v_y])
                self.direction += rotate_theta
                self.change_direction_check = True
            else:  # 방향 전환 없으면 (=직진하면)
                self.change_direction_check = False

    def calc_rotate_theta(self, env):
        # 중요! 수정해야 함! 범위 제한
        # 1) theta_fa 찾기
        v_f = [self.v_x, self.v_y]  # 전투기 속도 벡터
        v_fa = [self.target_asset.x - self.x, self.target_asset.y - self.y]  # 전투기(f)->자산(a) 벡터
        theta_fa = util.calc_theta(v_f, v_fa)  # 전투기(f)와 전투기-자산(a) 간 각도 차이

        # 2) theta_fb1, theta_fb2 찾기
        # # 가장 가까운 포대 2개 찾기
        battery_sort = [b for b in env.battery].sort(key=lambda x: util.calc_object_dist(self, x))
        b1 = battery_sort[0]
        b2 = battery_sort[1]
        v_fb1 = [b1.x - self.x, b1.y - self.y]
        v_fb2 = [b2.x - self.x, b2.y - self.y]
        theta_fb1 = util.calc_theta(v_f, v_fb1)
        theta_fb2 = util.calc_theta(v_f, v_fb2)

        # 3) 계산!
        w_m = 2 + random()  # 관성 가중치 (현재 진행방향 유지하는 것에 대한 가중치). range: [2, 3]
        w_a = max(0.0, random() + 20 / math.sqrt(util.enorm(v_fa)) - 2)  # 자산 방향 가중치. 가까울수로 크게. range: (0, inf). 난수 0일 때 거리100일때 0, 거리45일때 1
        w_b1 = -0.7 - random()  # 가장 가까운 포대 중심 피하는 경로 가중치. 음수값이어야 하며, 작을수록(절대값이 클수록) 더 열심히 피함. range: [-0.7,-1.7]
        w_b2 = -2 - w_b1    # 두 번째로 가까운 포대 중심 피하는 경로 가중치. w_b1 + w_b2 = -2. range[-0.3, -1.3]
        rotate_theta = (w_a * theta_fa + w_b1 * theta_fb1 + w_b2 * theta_fb2)/(w_m + w_a + w_b1 + w_b2)
        assert w_m + w_a + w_b1 + w_b2 > 0

        # 4) 너무 회전각 작으면 그냥 직진하기
        if abs(rotate_theta) < 1 * math.pi / 180.0:
            rotate_theta = 0
            return rotate_theta

        # 5) 1초 최대 회전 각도를 -4 ~ 4도로 제한
        if rotate_theta > 4 * math.pi / 180.0:
            rotate_theta = 4 * math.pi / 180.0
        elif rotate_theta < - 4 * math.pi / 180.0:
            rotate_theta = - 4 * math.pi / 180.0

        # 6) 진행방향을 항상 아래로 제한. 즉, -pi ~ 0로 제한.
        if self.direction + rotate_theta > 0:
            rotate_theta = - self.direction
        elif self.direction + rotate_theta < - math.pi:
            rotate_theta = - math.pi - self.direction

        return rotate_theta

    @staticmethod
    def multiply(arr):  # 생존확률 계산용 함수. (이 전투기를 향해 날아오는 여러 미사일의 kill prob 곱하는 역할)
        ans = 1.0
        for n in arr:
            if n == 0:
                return 0
            ans *= n
        return ans


class Battery(object):
    def __init__(self, b_id, x, y):
        self.id = b_id
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
        self.battery.radar_capa -= 1
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
            v_f = [f.v_x, f.v_y]  # 전투기 속도 벡터
            theta_fd = util.calc_theta(v_f, d_fm)  # 전투기 벡터(f)와 전투기->미사일 벡터(d_fm) 간 각도 (-pi~pi)
            theta_md = math.asin(math.sin(theta_fd) / 3)  # 미사일->전투기 벡터(-d_fm)와 미사일 속도 벡터(m) 간 각도 (-0.5pi~0.5pi)
            v_m = util.rotate_vector(theta_md, -1 * d_fm)  # 미사일 벡터(v_m)를 시계방향으로 회전
            v_m /= math.sqrt(v_m[0] ** 2 + v_m[1] ** 2)  # 단위벡터로 만들고
            v_m *= self.battery.v  # v_m 크기를 미사일 속력 크기로 조절
            self.v_x = v_m[0]
            self.v_y = v_m[1]
            theta_mf = math.pi - abs(theta_md + theta_fd)  # 미사일(m)과 전투기(f)의 충돌 각도
            self.expc_arrt = util.enorm(d_fm) / util.enorm([v_f[0] - v_m[0], v_f[1] - v_m[1]])  # 남은 도착시간 = fm 간 거리 / (전투기속도벡터 - 미사일 속도벡터)
            # 미사일과 전투기의 충돌지점(p) 검토
            assert [self.x + self.expc_arrt * self.v_x, self.y + self.expc_arrt * self.v_y] \
                   == [f.x + self.expc_arrt * f.v_x, f.y + self.expc_arrt * f.v_y]
            # 파괴확률 = 포대-충돌위치 간 거리(x) 미사일의 총 이동거리(o) 함수 * 충돌각도 함수
            self.kill_prob = util.calc_kill_prob_dist((self.flight_t + self.expc_arrt) * self.battery.v) \
                             * util.calc_kill_prob_angle(theta_mf)

    def transit_route(self):
        """
        시간 1단위 지났을 때, 이 미사일의 위치 및 시간 정보 업데이트.
        """
        self.x += self.v_x
        self.y += self.v_y
        self.flight_t += 1
        self.expc_arrt -= 1
