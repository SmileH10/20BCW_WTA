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
    d_fm_enorm = calc_object_dist(battery, flight)  # d_fm의 euclidean norm
    theta_fd = math.acos((flight.v_x * d_fm[0] + flight.v_y * d_fm[1]) / (flight.v * d_fm_enorm))  # 전투기 진행방향 벡터(f)와 전투기->미사일 벡터(d_fm) 간 각도
    theta_md = abs(math.asin(math.sin(theta_fd) / 3))  # 미사일 진행방향 벡터(m)와 미사일->전투기 벡터(-d_fm) 간 각도. 3은 미사일/전투기 속력비
    if math.asin((d_fm[0] * flight.v_y - flight.v_x * d_fm[1]) / (flight.v * d_fm_enorm)) > 0:  # d_fm -> f 가 반시계 방향일 때
        v_m = rotate(-theta_md, -1 * d_fm)  # 미사일 방향벡터(v_m)를 시계방향으로 회전
    else:  # d_fm -> f 가 시계 방향일 때
        v_m = rotate(theta_md, -1 * d_fm)  # 미사일 방향벡터(v_m)를 반시계방향으로 회전
    v_m /= math.sqrt(v_m[0] ** 2 + v_m[1] ** 2)  # 단위벡터로 만들고
    v_m *= battery.v  # v_m 크기를 미사일 속력 크기로 조절
    theta_mf = math.pi - theta_md - theta_fd  # 미사일(m)과 전투기(f)의 충돌 각도
    expc_arrt = d_fm_enorm / math.sqrt((flight.v_x - v_m[0]) ** 2 + (flight.v_y - v_m[1]) ** 2)  # 예상 도착(충돌) 소요시간
    p = [battery.x + expc_arrt * v_m[0], battery.y + expc_arrt * v_m[1]]  # 충돌위치(p) 좌표
    assert p == [flight.x + expc_arrt * flight.v_x, flight.y + expc_arrt * flight.v_y]  # 충돌위치 검산
    # 파괴확률 = 포대-충돌위치 간 거리 함수 * 충돌각도 함수
    kill_prob = calc_kill_prob_dist(math.sqrt((battery.x - p[0]) ** 2 + (battery.y - p[1]) ** 2)) \
                * calc_kill_prob_angle(theta_mf)
    return kill_prob


def calc_kill_prob_dist(dist):
    # 작성해야 함. 거리에 따른 파괴 확률. 엑셀에서 불러오게 해야 할까? 겠지?
    return 1 - dist / 60.0


def calc_kill_prob_angle(theta):
    """
    :param theta: 충돌 각도
    :return: 각도에 따른 파괴 확률
    조건 3개 만족해야 함: (1) alpha & beta >= 0; (2) -1 * alpha + beta >= 0; (3) alpha + beta <=1
    """
    alpha = 0.5
    beta = 0.5
    return -1 * alpha * math.cos(theta) + beta


def rotate(theta, vector):
    """
    :param theta: 반시계방향으로 회전시킬 각도
    :param vector: 회전시킬 2D vector
    :type vector: list
    :return: 회전된 2D vector 리스트
    """
    rotated_vector_x = math.cos(theta) * vector[0] - math.sin(theta) * vector[1]
    rotated_vector_y = math.sin(theta) * vector[0] + math.cos(theta) * vector[1]
    return [rotated_vector_x, rotated_vector_y]