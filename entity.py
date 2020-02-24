from util import calc_object_dist


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
        self.v = 1  # 속도. 아직 쓰는 곳 없음. kill prob 계산 때 쓸 듯?
        self.direction = 0  # 진행 방향 (세 방향 중 하나. 60도, 0도, -60도)
        self.target_asset = target_asset  # 목표 자산 객체 넣기. route 계산할 때 쓸 듯. 목표 자산을 향하도록 routing.
        self.surv_prob = 1.0  # 초기 생존확률 = 1

    def transit_route(self):
        """
        공격 알고리즘(전투기의 공격 패턴)에 따라 수정해야 하는 블록.
        방어 알고리즘이 여기서 작성된 routing 확률분포를 학습함.
        각 전투기의 출발시간도 여기서 조절함
        """

        """
        Step 1) 진행 방향 정하기 (가던 방향? 방향 전환?)
        Step 2) 1 시점이 지났을 때의 x좌표, y좌표 update 하기
                예시) self.x += cosine(direction) * 1
        """

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
        self.v = 10  # 미사일 속도 (kill prob 등 계산 편하게 하려고 여기서 씀. 같은 포대에서 발사된 미사일 속도 동일 가정)
        self.radar_capa = 2  # 레이더 용량. 동시 조준 가능한 미사일 개수
        self.radius = 30  # 사정거리
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
        # self.v_x = ?  전투기 향해 직진으로 출발? 전투기 방향 고려해서 출발?
        # self.v_y = ?  전투기 향해 직진으로 출발? 전투기 방향 고려해서 출발?
        # assert self.v_x ** 2 + self.v_y ** 2 == self.battery.v ** 2  # 검산
        self.battery.total_launching += 1
        self.id = [self.battery, self.flight, self.battery.total_launching]  # 같은 포대에서 같은 전투기로 여러 미사일 쏠 수 있어서, id[-1]로 구분.

        self.expc_arrt = self.calc_expc_arrt(target_flight)  # 전투기 타격까지 남은 예상 시간
        self.kill_prob = self.calc_mf_kill_prob(target_flight)  # 예상 파괴확률

    def calc_expc_arrt(self, flight):
        # (간소화 버전) 예상 도착시간 = 미사일-전투기 간 직선거리 / 미사일속도
        expected_arrt = calc_object_dist(self, flight) / self.battery.v
        return expected_arrt

    def calc_mf_kill_prob(self, flight):
        # 미사일-전투기 현재 정보에 따른 kill prob 계산해야 함.
        return 0.5

    def transit_expc_arrt(self):
        self.expc_arrt = self.calc_expc_arrt(self.flight)

    def transit_kill_prob(self):
        self.kill_prob = self.calc_mf_kill_prob(self.flight)

    def transit_route(self):
        # 시간 1단위 지났을 때, 전투기를 향해 날아가는 이 미사일의 self.x, self.y, self.v_x, self.v_y 업데이트하는 곳. 만들어야 함.
        pass