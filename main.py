from env import Env
from agent import RL, Greedy
from rl_cores import State
from animation import GraphicDisplay
from dataIO import write_data
from util import calc_mean
from time import time
from datetime import datetime
import pickle
import os, sys


class MainApp(object):
    def __init__(self, agent_name='greedy', task='Train', map_width=200.0, map_height=300.0, battery_num=3, flight_num=20, flight_time_interval=50,
                 termination=('Iteration number', 5), autosave_iter=2, use_animation=True):
        self.gui_framework = None
        self.env = None
        self.agent_name = agent_name
        self.agent = None
        self.task = task
        assert self.task.lower() in ('train', 'test')
        self.termination = termination
        assert termination[0].lower() in ('time', 'time(sec)', 'iter', 'iteration number')
        self.autosave_iter = autosave_iter
        self.use_animation = use_animation
        self.map_width, self.map_height = map_width, map_height

        self.battery, self.asset, self.flight = {}, {}, {}
        self.b_num = battery_num
        self.f_num = flight_num
        self.f_interval = flight_time_interval  # 첫 출발 flight ~ 마지막 출발 flight 의 시간 간격 (unit_time)

        self.use_delayaction = 0

    def initialize(self):
        # env 만들기
        self.env = Env(self.map_width, self.map_height, self.b_num, self.f_num, self.f_interval)
        # agent 만들기
        # # self.log_dir = "./logs/{}-{}/".format(self.agent_name.lower(), datetime.now().strftime("%m-%d_%H-%M-%S"))
        if self.agent_name.lower() == 'greedy':
            self.agent = Greedy()
            self.log_dir = "./logs/greedy-{}/".format(datetime.now().strftime("%m-%d_%H-%M-%S"))
        elif self.agent_name.lower() in ('rl', 'reinforcement learning'):
            self.agent = RL()
            self.log_dir = "./logs/rl-{}/".format(datetime.now().strftime("%m-%d_%H-%M-%S"))
        else:  # agent file loaded
            with open(self.agent_name, 'rb') as file:  # james.p 파일을 바이너리 읽기 모드(rb)로 열기
                self.agent = pickle.load(file)
            loaded_filename = self.agent_name.split('/')[-2] + '_' + self.agent_name.split('/')[-1].split('.')[0]
            self.log_dir = "./logs/{}-{}/".format(loaded_filename, datetime.now().strftime("%m-%d_%H-%M-%S"))
        # 저장경로 만들기
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        if self.gui_framework:
            self.gui_framework.write_console("log directory: " + self.log_dir, box='textBrowser_setting')
            self.gui_framework.write_console("log directory: " + self.log_dir)
        # 애니메이션 만들기
        if self.use_animation:
            self.animation = GraphicDisplay(self.map_height, self.map_width,
                                            unit_pixel=min(int(1230.0 / self.map_height), int(910.0 / self.map_width)) - 1)
        # 기타 설정 초기화하기
        self.iter = 0
        self.start_time = time()

    def initialize_iter(self):
        self.iter_start_time = time()
        self.episode_reward = 0.
        self.env.init_env(self.task, self.iter)
        if self.agent.name == 'rl':
            self.agent.init_records()
        if self.use_animation:
            self.animation.event_cnt = 0

    def run_main(self):
        self.initialize()
        while True:
            # 초기화
            self.initialize_iter()
            # Run 시뮬레이션 (1 scenario)
            state = State(self.env)
            first = True
            while not self.env.check_termination():
                # 1-1) agent 에 의해 action 선택, 1-2) action 직후 features=(s, a) 저장.
                action, action_done, feature = self.agent.get_action(state, use_delay=self.use_delayaction)
                # 2) action 후 다음 상태 & 보상 반환.
                next_state, reward = self.env.step(action)
                # RL 저장 및 업데이트 (가능한 행동이 있었을 경우만)
                if self.agent.name == 'rl' and self.task.lower() == 'train':
                    if action_done:
                        # print("reward: ", reward)
                        if first:
                            first = False
                        else:
                            self.agent.memory.push(prev_feature, prev_reward, prev_t, state, state.sim_t)
                        prev_feature = feature
                        prev_reward = reward
                        prev_t = state.sim_t
                        if len(self.agent.memory) >= self.agent.batch_size:
                            # print('time: ', self.env.sim_t)
                            self.agent.update_weight(use_delay=self.use_delayaction)

                state = next_state
                self.episode_reward += reward

                # 애니메이션 사용 시, 데이터 저장
                if self.use_animation and self.iter % self.autosave_iter == 0:
                    self.animation.save_stepdata(self.iter, self.env)

            # 결과 저장 및 출력
            self.save_and_print()
            # 전체 실험 종료조건 확인
            if self.stop_signal():
                break
            # iter 숫자 증가
            self.iter += 1

        if self.gui_framework:
            self.gui_framework.stop_program()
            self.gui_framework.write_console("Ends running.")
        if self.use_animation:
            self.animation.mainloop()
        print("[main.py] Ends")

    def save_and_print(self):
        # Auto-save
        if self.iter % self.autosave_iter == 0:
            if self.use_animation:
                self.animation.save_file(self.iter, self.log_dir)
            if self.agent.name == 'rl':
                self.agent.save_file(self.log_dir, self.iter)

        # 결과 출력 코드
        # # 파일로 저장
        filename = "results"
        extension = ".csv"
        if not os.path.isfile(self.log_dir + filename + extension):
            headstr = 'Iteration, num_f_survived, total rewards, loss'
        else:
            headstr = False
        tempdic_rawdata = {"%d" % self.iter: "%d, %.2f, %.4f" % (self.env.num_f_survived, self.episode_reward, calc_mean(self.agent.loss_history))}
        write_data(self.log_dir, data=tempdic_rawdata, filename=filename, head=headstr, extension=extension)

        # # Program에 출력
        if self.termination[0][:4].lower() == 'time':
            temp_time_h = (self.termination[1] - time() + self.start_time) / (60.0 * 60)
            temp_time_m = (self.termination[1] - time() + self.start_time) % (60.0 * 60) / 60.0
            temp_time_s = (self.termination[1] - time() + self.start_time) % 60.0
            txt = "simulation iter %d ends. %dh:%dm:%.0fs left. num_f_survived: %d, cum_rewards: %.2f, loss: %.3f, sec/iter: %.1f" \
                  % (self.iter, temp_time_h, temp_time_m, temp_time_s, self.env.num_f_survived, self.episode_reward, calc_mean(self.agent.loss_history), time()-self.iter_start_time)
        elif self.termination[0][:4].lower() == 'iter':
            txt = "simulation iter %d of %d ends. num_f_survived: %d, cum_rewards: %.2f, loss: %.3f, sec/iter: %.1f" \
                  % (self.iter, self.termination[1] - 1, self.env.num_f_survived, self.episode_reward, calc_mean(self.agent.loss_history), time()-self.iter_start_time)
        print(txt)

        if self.agent.name == 'rl':
            print("\n[time spent at]")
            for key in self.agent.time_check.keys():
                print(key, ": %.2f" % self.agent.time_check[key])
            print("\n[num_visit]")
            for key in self.agent.num_visit.keys():
                print(key, ": ", self.agent.num_visit[key])

        if self.gui_framework:
            self.gui_framework.write_console(txt)

    def stop_signal(self):
        # # 정지 signal 확인
        if self.gui_framework:
            if self.gui_framework._stopflag:
                if self.gui_framework._exitflag:
                    sys.exit()
                return True
        # 종료조건 확인
        if self.termination[0][:4].lower() == 'time':
            if time() - self.start_time >= self.termination[1]:
                return True
        elif self.termination[0][:4].lower() == 'iter':
            if self.iter >= self.termination[1] - 1:
                return True
        return False


if __name__ == '__main__':
    my_main = MainApp()
    my_main.run_main()

    # # Load animation
    # ani = GraphicDisplay(my_main.map_height, my_main.map_width,
    #                      unit_pixel=3,
    #                      load_file=(True, 'rl-03-27_13-58-52'))
    # ani.mainloop()
