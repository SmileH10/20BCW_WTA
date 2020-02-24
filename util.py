from math import sqrt


def calc_object_dist(object1, object2):
    """
    :param object1, object2: 거리 측정할 두 객체
    :return: 두 객체 사이의 직선거리
    """
    return sqrt((object1.x - object2.x) ** 2 + (object1.y - object2.y) ** 2)


def calc_bf_kill_prob(battery_object, flight_object):
    """
    battery에서 flight을 쏜다면 kill_prob가 얼마일지 계산하는 함수.

    flight.x, flight.y, flight.direction, 비행기 정보와
    battery.x, battery.y 포대 정보
    를 이용해서, 각도랑 거리랑 뭐... 그런 거 여기서 계산해서 kill prob 반환
    """
    kill_prob = 0.5
    return kill_prob