from util import calc_object_dist, calc_bf_kill_prob
from env import FakeEnv
from sklearn import linear_model
import numpy as np
import pandas as pd
import random
import os
import pickle
import itertools
# pyinstaller import error 때문에 추가
import sklearn.utils._cython_blas
import sklearn.neighbors.typedefs
import sklearn.neighbors.quad_tree
import sklearn.tree
import sklearn.tree._utils


def get_actionset(env):
    """
    현재 상태 받아서, 가능한 모든 actions의 종류를 담은 집합 actionset 을 반환.
    single_action: 어떤 포대가 어느 전투기로 미사일을 쏜다. e.g.) (battery object, flight object)
    actions: 모든 포대의 의사결정들의 집합. e.g.) [(battery1 object, one of flight objects), (battery2 object, one of flight objects), ...]
    actionset = 가능한 모든 actions 의 집합. e.g.) [actions1, actions2, ...]
    :param env: 현재 시뮬레이션 상태 class
    :return: actionset (type: list)
    """
    actionset_of_battery = {}
    for b in env.battery.values():
        actionset_of_battery[b.id] = []
        for f in env.flight.values():
            if calc_object_dist(b, f) <= b.radius and b.radar_capa > 0 and b.reload == 0:
                # 사정거리 안에 있음 + radar 용량 있음 + 재장전시간 조건 만족
                # 먼 미래에 수정! 사정거리 안에 있다가 밖으로 나가도 격추 가능 가정.
                # 먼 미래에 수정! 사정거리 안으로 들어올 것을 미리 예상해서 쏘는 것 불가능 가정.
                actionset_of_battery[b.id].append((b.id, f.id))
        actionset_of_battery[b.id].append("DoNothing")
    actionset = list(itertools.product(*[actionset_of_battery[b.id] for b in env.battery.values()]))
    return actionset


class Greedy(object):
    def __init__(self):
        self.name = 'greedy'

    @staticmethod
    def select_action(env, task='Test'):
        # 가능한 모든 actions 불러오기
        actionset = get_actionset(env)
        # 가장 좋은 행동 선택하기
        best_surv_probs = float("inf")
        if len(actionset) == 1:
            best_a = actionset[0]
        else:
            best_a = None
            for actions in actionset:  # e.g.) actions: [(b1, f1), (b2, f3), (b3, f1)]
                # 전투기를 향해 날아가고 있는 미사일이 있다면, 그 전투기에게 또 쏘지 않음.
                valid_action = True
                for fid in env.flight.keys():
                    if sum([1 for m in env.missile.values() if m.flight.id == fid]) + sum([1 for a in actions if a[1] == fid]) >= 2:
                        valid_action = False
                if not valid_action:
                    continue
                # 생존확률을 가장 낮게하는 행동을 고름
                surv_probs = {f.id: f.surv_prob for f in env.flight.values()}
                for a in actions:  # e.g.) a: (b1, f1)
                    if a != "DoNothing":
                        bid, fid = a[0], a[1]
                        surv_probs[fid] *= (1 - calc_bf_kill_prob(env.battery[bid], env.flight[fid]))
                temp_surv_probs = sum(surv_probs[f.id] for f in env.flight.values())
                if temp_surv_probs < best_surv_probs:
                    best_surv_probs = temp_surv_probs
                    best_a = actions
        return best_a, best_a


class RL(object):
    def __init__(self):
        self.name = "rl"
        self.epsilon = 1
        self.gamma = 1.0
        self.num_features = 3
        self.lm = linear_model.LinearRegression()

        # 가중치 업데이트할 때 사용
        self.previous_features, self.previous_reward, self.previous_sim_t = None, None, None
        # self.memory = pd.DataFrame(data=[], columns=['X', 'y'])
        self.memory = np.array([])
        self.memory_capa = 10000

        # 결과 출력할 때 사용
        self.cumulative_rewards = 0.0
        self.memory_for_record = np.array([[]])

    def select_action(self, env, task):
        # 가능한 모든 actions 불러오기
        actionset = get_actionset(env)
        # 행동 선택하기
        if len(actionset) == 1:  # 가능한 행동이 1개일 때 [("DoNothing", "DoNothing", "DoNothing")]
            best_a = actionset[0]
        else:  # 가능한 행동이 여러 개일 때
            fake_env = FakeEnv(env)  # 행동 전 상태  # self.fake_env = deepcopy(env) 는 env.flight 까지 복사하지 못함.
            best_q, best_a, best_features, reward = self.max_qval(fake_env, actionset)
            self.cumulative_rewards += reward
            # 가중치 업데이트
            if task.lower() == 'train':
                self.save_memory(fake_env, reward, env.sim_t, best_features)
                self.update_weight()
        # epsilon 확률로 임의의 action 선택
        if random.random() < self.epsilon:
            what_really_do = random.choice(actionset)
        else:
            what_really_do = best_a
        return what_really_do, best_a

    def max_qval(self, env, actionset):
        best_q = float("-inf")
        surv_probs = sum([f.surv_prob for f in env.flight.values()])
        for actions in actionset:
            temp_env = env
            # 행동 전 상태
            temp_env.transit_afteraction_state(actions)  # 행동 후 상태
            temp_features = self.get_features(temp_env)
            temp_q = self.get_qvalue(temp_features)  # 행동 후 상태에 대한 q-value 계산
            if temp_q > best_q:  # 기존 행동보다 q-value가 큰 지?
                best_a = actions
                best_q = temp_q
                best_features = temp_features
                reward = surv_probs - sum([f.surv_prob for f in temp_env.flight.values()])  # 보상 = 생존확률 감소량 = 파괴확률 증가량 (현재 살아있는 전투기에 대해서만)
        return best_q, best_a, best_features, reward

    def save_memory(self, next_env, reward, sim_t, best_features):
        # x, y를 메모리에 저장
        # if self.memory.size != 0:
        if self.previous_reward != None:
            x = np.array([self.previous_features, self.previous_reward, self.previous_sim_t, next_env, sim_t])
            if self.memory.size == 0:
                self.memory = np.array([x])
            else:
                self.memory = np.concatenate((self.memory, [x]), axis=0)
            if self.memory.shape[0] > self.memory_capa:
                self.memory = np.delete(self.memory, 0, axis=0)
        self.previous_features = best_features
        self.previous_reward = reward
        self.previous_sim_t = sim_t

    def update_weight(self, print_memory=False):
        """
        self.previous_features: (S[t], a[t])
        self.previous_reward: r[t]
        best_q: max_a[t+1]( Q(S[t+1], a[t+1]) )
        Q(S[t], a[t]) = r[t] + max_a[t+1]( Q(S[t+1], a[t+1]) ) 가 되도록 가중치 업데이트.
        Q(S[t], a[t]) = linear model (S[t], a[t]) = lm.predict(self.previous_features)
        """
        first = True
        if self.memory.shape[0] != 0:
            for experience in self.memory:  # [self.previous_features, self.previous_reward, self.previous_sim_t, next_env, sim_t]
                actionset = get_actionset(experience[3])
                max_qval, _, _, _ = self.max_qval(experience[3], actionset)
                y = experience[1] + self.gamma ** (experience[4] - experience[2]) * max_qval
                if first:
                    xdata = np.array([experience[0]])
                    ydata = np.array([y])
                    first = False
                else:
                    xdata = np.concatenate((xdata, [experience[0]]), axis=0)
                    ydata = np.append(ydata, y)
            if print_memory:  # iteration 끝나면 결과 출력용
                score = self.lm.score(xdata, ydata)
                ydata = ydata.reshape(len(ydata), 1)
                data_features_qhat = np.append(xdata, ydata, axis=1)
                return data_features_qhat, score
            # 메모리에 있는 데이터들로 가중치 업데이트
            # self.lm.fit([self.memory['X'].to_numpy()], [self.memory['y'].to_numpy()])
            self.lm.fit(xdata, ydata)
            # self.lm.fit([[1, 3, 4, 12], [1, 3, 4, 12], [1, 3, 4, 12], [1, 3, 4, 12]], [5, 1, 5, 6])

    def get_qvalue(self, features):
        """
        :returns q-value  # qvalue = sum(self.weight[f] * features[f] for f in range(len(features))
        """
        # if self.memory.empty:
        if self.memory.shape[0] <= 1:
            return 0
        else:
            return self.lm.predict([features])[0]

    def get_features(self, env):
        """
        :INPUT: 현재 전투기/레이더/포대/미사일 등 상태 정보 (env에 정보가 있음.)
        :return: list of features' values (계산된 feature 값들의 리스트)
        """
        features = np.array([-1 for _ in range(self.num_features)])
        features[0] = sum(f.surv_prob for f in env.flight.values())  # 예시) 모든 비행기 생존확률의 합
        features[1] = 0
        # features[1] 계산식 넣기
        features[2] = 0
        # ...
        assert self.num_features == len(features)
        return features

    def save_file(self, log_dir, iteration):
        save_dir = log_dir
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        for old_file in os.scandir(save_dir):  # 파일 삭제하기.
            if os.path.splitext(old_file)[1] == '.pkl':  # [0]: 파일경로+이름까지, [1]: 확장자
                os.remove(old_file)
        with open(save_dir + 'rl_iter%d.pkl' % iteration, 'wb') as file:  # james.p 파일을 바이너리 쓰기 모드(wb)로 열기
            pickle.dump(self, file)

    def init_records(self):
        del self.memory_for_record
        self.memory_for_record = np.array([[]])
        self.cumulative_rewards = 0.0