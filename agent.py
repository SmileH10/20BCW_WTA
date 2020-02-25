from random import random
from util import calc_object_dist, calc_bf_kill_prob


def get_actionset(env, b):
    """
    현재 상태 받아서, 가능한 모든 action의 종류를 담은 action 집합을 반환.
    action = (battery object, flight object)
    :param env: 현재 시뮬레이션 상태
    :param b: battery object
    :return: [(battery object1, flight object1), (b2, f2), (b3, f3), ... ]
    """
    action_set = []
    for f in env.flight:
        if calc_object_dist(b, f) <= b.radius and b.radar_capa > 0 and b.reload == 0:
            # 사정거리 안에 있음 + radar 용량 있음 + 재장전시간 조건 만족
            # 먼 미래에 수정! 사정거리 안에 있다가 밖으로 나가도 격추 가능 가정.
            # 먼 미래에 수정! 사정거리 안으로 들어올 것을 미리 예상해서 쏘는 것 불가능 가정.
            action_set.append((b, f))
    return action_set


class Greedy(object):
    def __init__(self):
        self.name = 'greedy'

    @staticmethod
    def select_action(env, battery):
        actionset = get_actionset(env, battery)
        best_kill_prob = float("-inf")
        best_a = "DoNothing"
        # Greedy는 쏠 수 있는 데 안 쏘는 거 없다고 가정.
        for a in actionset:
            temp_kill_prob = calc_bf_kill_prob(a[0], a[1])
            if temp_kill_prob > best_kill_prob:
                best_kill_prob = temp_kill_prob
                best_a = a
        return best_a


class RL(object):
    def __init__(self):
        self.name = "rl"
        self.num_features = 3
        self.weight = [random() for _ in range(self.num_features)]  # 초기 가중치 0~1 사이 임의값 지정.

    def select_action(self, env, battery):
        actionset = get_actionset(env, battery)  # (1) 선택 가능한 action set 불러오기
        best_a = "DoNothing"
        if not actionset:  # 가능한 action 이 없으면
            return best_a
        else:  # 가능한 action 이 있으면
            # action="아무 것도 안 함=DoNothing" 을 default 로 두고 비교함.
            best_q = self.get_qvalue(env, action="DoNothing")
            self.best_reward = 0

            for a in actionset:  # (2) action set에 있는 모든 action들에 대해 q-value 계산하기
                temp_q = self.get_qvalue(env, a)
                if temp_q > best_q:  # (3) q-value가 가장 좋은(=큰) action 선택하기
                    best_q = temp_q
                    best_a = a
                    # 중요!! 이거 reward 나중에 memory에 저장해서 weight update 할 때 써야돼...
                    # 근데!!! 같은 시점에 행동 여러 개 하네!! 이거 업데이트 어떻게 할까????????? 수정해야 함!!! 중요!
                    self.best_reward = best_a[1].surv_prob - best_a[1].surv_prob * (1 - calc_bf_kill_prob(best_a[0], best_a[1]))
        return best_a

    def get_qvalue(self, env, action):
        """
        weight * feature value 계산해서 q-value 반환하는 함수
        """
        qvalue = 0
        features = self.get_features(env, action)
        for f in range(len(features)):
            qvalue += self.weight[f] * features[f]
        return qvalue

    def get_features(self, env, action):
        """
        :INPUT: 현재 전투기/레이더/포대/미사일 등 상태 정보 (env에 정보가 있음.)
        :return: 계산된 feature 값들의 리스트?
        """
        if action == "DoNothing":
            pass
        else:
            pass

        features = [-1 for _ in range(self.num_features)]
        features[0] = 1
        features[1] = 0
        # features[1] 계산식 넣기
        features[2] = 0
        # ...
        return features

    def get_reward(self, env, action):
        # 이 함수는 안 써도 될 듯. 지우려다가 혹시 몰라서 일단 남겨 둠. 지금은 쓰는 곳 없음.
        pass

    def update_weight(self):
        """
        저장된 (S[t], a[t], R[t], S[t+1]) 을 이용해서
        Q(S[t], a[t])
        Q_hat(S, a) = R[t] + max Q(S[t+1], a)
        (Q(S[t], a[t]) - Q_hat(S[t], a[t]) )**2 를 최소화하도록 가중치 update
        * 가중치 업데이트할 때 지난 memory 이용해도 됨

        memory에 저장 (self.save_memory)
        """
        """
        (1)
            <1> 1) 에서 얻었던 "q-value(state x action) = self.get_qvalue(state, best_action)" 와
            <2> 2) 에서 얻었던 next_state를 이용해 계산한 "reward + max q-value(next_state, best_next_action)" 의
            차이의 제곱을 최소화하도록 가중치 업데이트하기. (함수 self.update_weight 이용)

            * <2>의 q-value(next_state, best_next_action)는 self.get_qvalue(next_state, self.select_action(next_state))로 구하면 됨.

        (2) state, action, reward, next_state를 self.memory 변수에 저장하기. (함수 self.save_memory 이용)
            가중치 업데이트 할 때 지난 기록들을 이용하면 저장해놨다가 self.update_weight 함수에서 써먹으면 됨.    
        """

    def save_memory(self):
        # self.memory = [[S0, a0, r0, S1], [S1, a1, r1, S2], [S2, a2, r2, S3], ...]
        """
        self.memory에 state, action, reward, next_state, next_action 저장
        :return:
        """
