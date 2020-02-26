import math


def calc_object_dist(object1, object2):
    """
    :type object1: class
    :type object2: class
    :return: 두 객체 사이 거리 반환
    """
    return math.sqrt((object1.x - object2.x) ** 2 + (object1.y - object2.y) ** 2)


def calc_bf_kill_prob(battery, flight):
    """
    battery에서 flight을 쏜다면 kill_prob가 얼마일지 계산하는 함수.
    """
    d_fm = [battery.x - flight.x, battery.y - flight.y]  # 전투기->미사일 벡터(d_fm) 생성
    v_f = [flight.v_x, flight.v_y]  # 전투기 속도벡터
    theta_fd = calc_theta(v_f, d_fm)  # 전투기 벡터(f)와 전투기->미사일 벡터(d_fm) 간 각도 (-pi~pi)
    theta_md = math.asin(math.sin(theta_fd) / 3)  # 미사일->전투기 벡터(-d_fm)와 미사일 속도 벡터(m) 간 각도 (-0.5pi~0.5pi)
    v_m = rotate_vector(theta_md, [-1 * d_fm[i] for i in range(len(d_fm))])  # 미사일->전투기 벡터(-d_fm)를 theta_md만큼 회전해서 미사일 벡터(v_m)를 만듦
    v_m = [v_m[i] * battery.v / enorm(v_m) for i in range(len(v_m))]  # v_m 크기를 미사일 속력 크기로 조절
    theta_mf = math.pi - abs(theta_md + theta_fd)  # 미사일(m)과 전투기(f)의 충돌 각도
    expc_arrt = enorm(d_fm) / enorm([v_f[0] - v_m[0], v_f[1] - v_m[1]])  # 남은 도착시간 = fm 간 거리 / (전투기속도벡터 - 미사일 속도벡터)
    p = [battery.x + expc_arrt * v_m[0], battery.y + expc_arrt * v_m[1]]  # 미사일과 전투기의 충돌지점(p)
    # p2는 임시로 코드 잘 작성되었는지 검산용.
    p2 = [flight.x + expc_arrt * flight.v_x, flight.y + expc_arrt * flight.v_y]
    assert math.sqrt((p[0]-p2[0])**2+(p[1]-p2[1])**2) < 0.00001  # 충돌지점 검산
    # 파괴확률 = 포대-충돌위치 간 거리 함수 * 충돌각도 함수
    kill_prob = calc_kill_prob_dist(enorm([battery.x - p[0], battery.y - p[1]]))\
                * calc_kill_prob_angle(theta_mf)
    return kill_prob


def calc_kill_prob_dist(dist):
    # 거리에 따른 파괴 확률. 작성해야 함. 일단 대충 해놓음. 엑셀에서 불러오게 해야 할까? 겠지?
    return 1 - dist / 40.0


def calc_kill_prob_angle(theta):
    """
    :param theta: 충돌 각도
    :return: 각도에 따른 파괴 확률
    조건 3개 만족해야 함: (1) alpha & beta >= 0; (2) -1 * alpha + beta >= 0; (3) alpha + beta <=1
    """
    alpha = 0.5
    beta = 0.5
    return -1 * alpha * math.cos(theta) + beta


def rotate_vector(theta, vector):
    """
    :param theta: 반시계방향으로 회전시킬 각도
    :param vector: 회전시킬 2D vector
    :type vector: list
    :return: 회전된 2D vector 리스트
    """
    rotated_vector_x = math.cos(theta) * vector[0] - math.sin(theta) * vector[1]
    rotated_vector_y = math.sin(theta) * vector[0] + math.cos(theta) * vector[1]
    return [rotated_vector_x, rotated_vector_y]


def enorm(vector):
    """
    :param vector: 2D list
    :return:euclidean norm
    """
    return math.sqrt(vector[0] ** 2 + vector[1] ** 2)


def calc_theta(v1, v2):
    """
    :param v1: 2D vector list (from)
    :param v2: 2D vector list (to)
    :return: angle from v1 to v2. 범위: [-pi, pi]
    """
    theta_cos = math.acos((v1[0] * v2[0] + v1[1] * v2[1]) / (enorm(v1) * enorm(v2)))  # v1->v2 벡터 각도 (0 ~ pi)
    theta = math.asin((v1[0] * v2[1] - v2[0] * v1[1]) / (enorm(v1) * enorm(v2)))  # v1->v2 벡터 각도 (-0.5pi ~ 0.5pi)
    if theta_cos < 0:
        if theta >= 0:
            theta = math.pi - theta
        else:
            theta = - math.pi + theta
    return theta
