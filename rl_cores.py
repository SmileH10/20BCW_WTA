from copy import deepcopy
from entity import Missile
from util import calc_object_dist

from collections import deque
import itertools
import random


class Memory:
    def __init__(self, max_size):
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)

    def push(self, state_action, reward, t, next_state, next_t):
        experience = [state_action, reward, t, next_state, next_t]
        self.buffer.append(experience)

    def sample(self, batch_size):
        return random.sample(self.buffer, batch_size)

    def __len__(self):
        return len(self.buffer)


class State(object):
    def __init__(self, env):
        self.sim_t = env.sim_t
        self.map_width = env.map_width
        self.flight = deepcopy(env.flight)
        self.battery = deepcopy(env.battery)
        self.missile = deepcopy(env.missile)


def get_afteraction_state(state, actions):
    # action (어떤 포대가 어느 전투기로 "미사일"을 발사했다) 을 반영. 시간 경과 없음
    copy_state = State(state)
    for a in actions:
        if a != 'DoNothing':
            action_bid = a[0]
            action_fid = a[1]
            new_missile = Missile(launching_battery=copy_state.battery[action_bid], target_flight=copy_state.flight[action_fid])  # 미사일 생성
            copy_state.missile[new_missile.id] = new_missile  # 미사일 딕셔너리에 추가
            copy_state.battery[action_bid].init_reload()  # 포대 재장전시간 초기화
            copy_state.flight[action_fid].surv_prob = copy_state.flight[action_fid].multiply(
                [(1 - m.kill_prob) for m in copy_state.missile.values() if m.flight.id == a[1]])  # 변경된 전투기 생존확률 반영
    return copy_state


def get_actionset(state, use_delay):
    """
    현재 상태 받아서, 가능한 모든 actions의 종류를 담은 집합 actionset 을 반환.
    single_action: 어떤 포대가 어느 전투기로 미사일을 쏜다. e.g.) (battery object, flight object)
    actions: 모든 포대의 의사결정들의 집합. e.g.) [(battery1 object, one of flight objects), (battery2 object, one of flight objects), ...]
    actionset = 가능한 모든 actions 의 집합. e.g.) [actions1, actions2, ...]
    :param state: 현재 시뮬레이션 상태 class
    :return: actionset (type: list)
    """
    actionset_of_battery = {}
    for b in state.battery.values():
        actionset_of_battery[b.id] = []
        for f in state.flight.values():
            if calc_object_dist(b, f) <= b.radius and b.radar_capa > 0 and b.reload == 0:
                # 사정거리 안에 있음 + radar 용량 있음 + 재장전시간 조건 만족
                actionset_of_battery[b.id].append((b.id, f.id))
        actionset_of_battery[b.id].append("DoNothing")
    actionset = list(itertools.product(*[actionset_of_battery[b.id] for b in state.battery.values()]))
    if not use_delay:
        actionset.remove(tuple(["DoNothing" for _ in state.battery.keys()]))
    return actionset
