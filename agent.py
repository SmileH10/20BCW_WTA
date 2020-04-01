from util import calc_object_dist, calc_bf_kill_prob
from rl_cores import Memory, get_actionset, get_afteraction_state

# from sklearn import linear_model
import numpy as np
import pandas as pd
import random
import os
import pickle
from time import time
from keras.layers import Input, Dense
from keras.models import Sequential
from matplotlib import pyplot as plt
from collections import defaultdict


class Greedy(object):
    def __init__(self):
        self.name = 'greedy'
        self.loss_history = None

    @staticmethod
    def get_action(state, use_delay):
        # 가능한 모든 actions 불러오기
        actionset = get_actionset(state, use_delay=use_delay)
        # 가장 좋은 행동 선택하기
        best_surv_probs = float("inf")
        if len(actionset) == use_delay:
            action_done = False
            action_taken = ["DoNothing"]
        else:
            action_done = True
            action_taken = ["DoNothing"]
            for actions in actionset:  # e.g.) actions: [(b1, f1), (b2, f3), (b3, f1)]
                # 전투기를 향해 날아가고 있는 미사일이 있다면, 그 전투기에게 또 쏘지 않음.
                valid_action = True
                for fid in state.flight.keys():
                    if sum([1 for m in state.missile.values() if m.flight.id == fid]) \
                            + sum([1 for a in actions if a[1] == fid]) >= 2:
                        valid_action = False
                if not valid_action:
                    continue
                # 생존확률을 가장 낮게하는 행동을 고름
                surv_probs = {f.id: f.surv_prob for f in state.flight.values()}
                for a in actions:  # e.g.) a: (b1, f1)
                    if a != "DoNothing":
                        bid, fid = a[0], a[1]
                        surv_probs[fid] *= (1 - calc_bf_kill_prob(state.battery[bid], state.flight[fid]))
                temp_surv_probs = sum(surv_probs[f.id] for f in state.flight.values())
                if temp_surv_probs < best_surv_probs:
                    best_surv_probs = temp_surv_probs
                    action_taken = actions
        return action_taken, action_done, None


class RL(object):
    def __init__(self):
        self.name = "rl"
        self.epsilon = 1
        self.gamma = 0.999
        self.num_features = 5
        self.initialize_model()
        self.batch_size = 4
        self.loss_history = []

        # 메모리
        self.memory_capa = 10000
        self.memory = Memory(max_size=self.memory_capa)

        # 결과 출력할 때 사용
        self.time_check = defaultdict(lambda: 0.)  # {'get_action-calc_qval': 0., 'update_weight-calc_qval': 0.}
        self.num_visit = defaultdict(lambda: 0.)

    def initialize_model(self):
        self.model = Sequential()
        self.model.add(Dense(1, input_dim=self.num_features, activation='sigmoid'))
        self.model.compile(loss='mse', optimizer='adam')

    def get_action(self, state, use_delay):
        self.num_visit['[get_action]'] += 1
        # 가능한 모든 actions 불러오기
        actionset = get_actionset(state, use_delay=use_delay)
        # 가능한 행동이 1개일 때 [("DoNothing", "DoNothing", ..., "DoNothing")]
        if len(actionset) == use_delay:
            action_taken = ["DoNothing"]
            action_done = False
            feature = None
        # 가능한 행동이 여러 개일 때
        else:
            self.num_visit['[get_action] action_done'] += 1
            action_done = True
            # print('actionset: ', len(actionset))
            # epsilon 확률로 임의의 action 선택
            if random.random() < self.epsilon or len(self.memory) < self.batch_size:
                # print("random!")
                action_taken = random.choice(actionset)
                afteraction_state = get_afteraction_state(state, action_taken)  # 행동 후 상태
                feature = self.get_features(afteraction_state)
            else:
                self.num_visit['[get_action] action_based_on_qval'] += 1
                start_t = time()
                _, action_taken, feature = self.max_qval(state, actionset)
                self.time_check['[get_action] max_qval'] += time() - start_t
            # print('action_taken: ', action_taken)
        return action_taken, action_done, feature

    def max_qval(self, state, actionset):
        self.num_visit['[max_qval]'] += 1
        start_t = time()
        max_list = []
        best_q = float("-inf")
        self.num_visit['[get_feature/max_qval] avg'] = (self.num_visit['[get_feature/max_qval] avg'] * (self.num_visit['[max_qval]'] - 1) + len(actionset)) \
                                                       / self.num_visit['[max_qval]']
        for action in actionset:
            self.num_visit['[max_qval] action'] += 1
            start_t2 = time()
            afteraction_state = get_afteraction_state(state, action)  # 행동 후 상태
            self.time_check['[max_qval] get_afteraction_state'] += time() - start_t2
            start_t3 = time()
            feature = self.get_features(afteraction_state)
            self.time_check['[max_qval] get_features'] += time() - start_t3
            start_t4 = time()
            temp_q = self.get_qvalue(feature)  # 행동 후 상태에 대한 q-value 계산
            self.time_check['[max_qval] get_qvalue'] += time() - start_t4
            if temp_q > best_q:
                best_q = temp_q
                max_list.clear()
                max_list.append([action, feature])
            elif temp_q == best_q:
                max_list.append([action, feature])
        choosen = random.choice(max_list)
        best_a = choosen[0]
        best_feature = choosen[1]
        self.time_check['[max_qval] total'] += time() - start_t
        return best_q, best_a, best_feature

    def get_qvalue(self, feature):
        return self.model.predict(np.array([feature]))[0][0]

    def update_weight(self, use_delay):
        """
        features: (S[t], a[t])
        reward: r[t]
        best_q: max_a[t+1]( Q(S[t+1], a[t+1]) )
        Q(S[t], a[t]) = r[t] + max_a[t+1]( Q(S[t+1], a[t+1]) ) 가 되도록 가중치 업데이트.
        Q(S[t], a[t]) = linear model (S[t], a[t]) = lm.predict(self.previous_features)
        """
        xdata, ydata = [], []
        batch_data = self.memory.sample(batch_size=self.batch_size)
        for experience in batch_data:  # experience: [features, reward, t, next_state, next_t]
            self.num_visit['[update_weight] exp'] += 1
            feature = experience[0]
            reward = experience[1]
            t = experience[2]
            next_state = experience[3]
            next_t = experience[4]
            actionset = get_actionset(next_state, use_delay)
            start_t = time()
            max_qval, _, _ = self.max_qval(next_state, actionset)
            self.time_check['[update_weight] max_qval'] += time() - start_t
            y = reward + self.gamma ** (next_t - t) * max_qval
            xdata.append(feature)
            ydata.append(y)
        # 메모리에 있는 데이터들로 가중치 업데이트
        history = self.model.fit(np.array(xdata), np.array(ydata), verbose=0, batch_size=self.batch_size)
        self.loss_history.append(history.history['loss'][0])
        # self.model.train_on_batch(np.array(xdata), np.array(ydata))

    def get_features(self, state):
        """
        :INPUT: 현재 전투기/레이더/포대/미사일 등 상태 정보 (env에 정보가 있음.)
        :return: list of features' values (계산된 feature 값들의 리스트)
        """
        self.num_visit['[get_features]'] += 1
        start_t = time()
        features = [-1. for _ in range(self.num_features)]
        # features[0] = sum(f.surv_prob for f in env.flight.values())  # 예시) 모든 비행기 생존확률의 합
        # 여기서부터 찬우형이 한 거 수정본.
        fs = state.flight.values()
        bs = state.battery.values()
        ms = state.missile.values()
        fb_dist = {(f, b): calc_object_dist(f, b) for f in fs for b in bs}
        b_business = {}
        for b in bs:
            b_business[b.id] = sum(f.surv_prob / fb_dist[(f, b)] for f in fs
                                   if fb_dist[(f, b)] == min(fb_dist[(f, b2)] for b2 in bs))
        features[0] = sum((b_business[b.id] + 1) ** 2 for b in bs)
        self.time_check['[get_featue] f0'] += time() - start_t
        start_t1 = time()
        b_urgency = {}
        for b in bs:
            b_urgency[b.id] = sum(f.surv_prob / fb_dist[(f, b)] for f in fs
                                  if fb_dist[(f, b)] == min(fb_dist[(f, b2)] for b2 in bs)
                                  and fb_dist[(f, b)] <= b.radius)
        features[1] = sum(max(b_urgency[b.id], 0) for b in bs)

        self.time_check['[get_featue] f1'] += time() - start_t1
        start_t2 = time()

        b_future_business = {}
        before = sum(calc_bf_kill_prob(b, f) for f in fs for b in bs)

        param_future = 1
        for f in fs:
            for moving_number in range(param_future):
                if state.sim_t >= f.start_t:  # 출발시간이 지났으면 움직임 반영하기.
                    f.x += f.v_x
                    f.y += f.v_y
                    if f.x >= state.map_width:
                        f.x = state.map_width
                        f.v_x = 0
                        f.v_y = -0.272
                    elif f.x <= 0:
                        f.x = 0
                        f.v_x = 0
                        f.v_y = -0.272
        for b in bs:
            b_future_business[b.id] = sum(f.surv_prob / fb_dist[(f, b)] for f in fs
                                          if fb_dist[(f, b)] == min(fb_dist[(f, b2)] for b2 in bs))
        features[2] = sum((b_future_business[b.id] + 1) ** 2 for b in bs)
        self.time_check['[get_featue] f2'] += time() - start_t2
        start_t3 = time()

        after = sum(calc_bf_kill_prob(b, f) for f in fs for b in bs)
        features[3] = after - before
        self.time_check['[get_featue] f3'] += time() - start_t3
        start_t4 = time()

        remain_time = {}
        for b in bs:
            if b.radar_capa > 0:
                remain_time[b.id] = b.reload
            else:
                remain_time[b.id] = min(m.expc_arrt for m in ms if m.battery.id == b.id)
        features[4] = sum(remain_time[b.id] for b in bs)
        self.time_check['[get_featue] f4'] += time() - start_t4
        self.time_check['[get_featue] total'] += time() - start_t

        assert self.num_features == len(features)
        return features

    def save_file(self, log_dir, iteration):
        save_dir = log_dir
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        for old_file in os.scandir(save_dir):  # 파일 삭제하기.
            if os.path.splitext(old_file)[1] == '.h5':  # [0]: 파일경로+이름까지, [1]: 확장자
                os.remove(old_file)
        # with open(save_dir + 'rl_iter%d.pkl' % iteration, 'wb') as file:  # james.p 파일을 바이너리 쓰기 모드(wb)로 열기
        #     pickle.dump(self, file)
        self.model.save(save_dir + 'trained_iter%d.h5' % iteration)

    def init_records(self):
        for key in self.time_check.keys():
            self.time_check[key] = 0.
        self.epsilon *= 0.8
        self.epsilon = max(self.epsilon, 0.05)
        print("set epsilon: %.2f" % self.epsilon)
        self.loss_history = []
        self.time_check = defaultdict(lambda: 0.)
        self.num_visit = defaultdict(lambda: 0.)