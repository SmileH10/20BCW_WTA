from env import Env
from agent import RL, Greedy
from animation import GraphicDisplay
from dataIO import write_data
from time import time
from datetime import datetime
import pickle
import os, sys


class MainApp(object):
    def __init__(self, agent_name='rl', task='Train', map_width=200.0, map_height=300.0, battery_num=3, flight_num=20, flight_time_interval=50,
                 termination=('Iteration number', 10000), autosave_iter=50, animation=True):
        self.gui_framework = None
        self.env = None
        self.agent_name = agent_name
        self.agent = None
        self.task = task
        assert self.task.lower() in ('train', 'test')
        self.termination = termination
        assert termination[0].lower() in ('time', 'time(sec)', 'iter', 'iteration number')
        self.autosave_iter = autosave_iter
        self.animation = animation
        self.map_width, self.map_height = map_width, map_height

        self.battery, self.asset, self.flight = {}, {}, {}
        self.b_num = battery_num
        self.f_num = flight_num
        self.f_interval = flight_time_interval  # 첫 출발 flight ~ 마지막 출발 flight 의 시간 간격 (unit_time)

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
        if self.animation:
            self.animation = GraphicDisplay(self.map_height, self.map_width,
                                            unit_pixel=min(int(1230.0 / self.map_height), int(910.0 / self.map_width)))
        # 기타 설정 초기화하기
        self.iter = 0
        self.start_time = time()
        self.iter_start_time = time()
        self.env.init_env()

    def run_main(self):
        self.initialize()
        while True:
            # 초기화
            self.env.init_env_iter(self.task, self.iter)
            if self.agent.name == 'rl':
                self.agent.init_records()
            # Run 시뮬레이션 (1 scenario)
            while not self.env.check_termination():
                # # 1) Agent 가 가장 좋은 액션 선택해서 알려줌
                actions_taken, _ = self.agent.select_action(self.env, self.task)
                # # 2-1) Action (action_taken) 수행 직후 (시간 경과 x) 상태 변화 반영
                self.env.transit_afteraction_state(actions_taken)
                # 애니메이션 사용 시, 데이터 저장
                if self.animation:
                    self.animation.save_stepdata(self, self.env)
                # 2-2) action_taken 수행 후 다음 시점 다음 상태로 이동하기
                self.env.transit_next_state()
            if self.animation:
                self.animation.event_cnt = 0
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
        if self.animation:
            self.animation.mainloop()
        print("[main.py] Ends")

    def save_and_print(self):
        # Auto-save
        if self.iter % self.autosave_iter == 0:
            if self.animation:
                self.animation.save_file(self.log_dir)
            if self.agent.name == 'rl':
                # 에이전트 파일 저장
                self.agent.save_file(self.log_dir, self.iter)

        # 결과 출력 코드
        # # 파일로 저장
        filename = "results"
        extension = ".csv"
        if self.agent.name == 'rl':
            if not os.path.isfile(self.log_dir + filename + extension):
                headstr = 'Iteration, num_f_survived, total rewards'
            else:
                headstr = False
            tempdic_rawdata = {"%d" % self.iter: "%d, %.2f" % (self.env.num_f_survived, self.agent.cumulative_rewards)}
        else:
            if not os.path.isfile(self.log_dir + filename + extension):
                headstr = 'Iteration, num_f_survived'
            else:
                headstr = False
            tempdic_rawdata = {"%d" % self.iter: "%d" % self.env.num_f_survived}
        write_data(self.log_dir, data=tempdic_rawdata, filename=filename, head=headstr, extension=extension)
        # # lm 데이터를 파일로 저장
        if self.agent.name == 'rl':
            filename = "LinearModel_data"
            data_features_qhat, rsquared = self.agent.update_weight(print_memory=True)
            if not os.path.isfile(self.log_dir + filename + extension):
                headstr = ', '.join('feature%d' % i for i in range(self.agent.num_features)) + ', Y(=Q)'
            else:
                headstr = False
            write_data(self.log_dir, data=data_features_qhat, filename=filename, head=headstr, list_type='2D')
        # # Program에 출력
        temp_time_h = (self.termination[1] - time() + self.start_time) / (60.0 * 60)
        temp_time_m = (self.termination[1] - time() + self.start_time) % (60.0 * 60) / 60.0
        temp_time_s = (self.termination[1] - time() + self.start_time) % 60.0
        if self.termination[0][:4].lower() == 'time':
            if self.agent.name == 'rl':
                txt = "simulation iter %d ends. %dh:%dm:%.0fs left. num_f_survived: %d, cum_rewards: %.2f, Rsquared: %.2f, sec/iter: %.1f" \
                      % (self.iter, temp_time_h, temp_time_m, temp_time_s, self.env.num_f_survived, self.agent.cumulative_rewards, rsquared, time()-self.iter_start_time)
            else:
                txt = "simulation iter %d ends. %dh:%dm:%.0fs left. num_f_survived: %d, sec/iter: %.1f" \
                      % (self.iter, temp_time_h, temp_time_m, temp_time_s, self.env.num_f_survived, time()-self.iter_start_time)
        elif self.termination[0][:4].lower() == 'iter':
            if self.agent.name == 'rl':
                txt = "simulation iter %d of %d ends. num_f_survived: %d, cum_rewards: %.2f, Rsquared: %.2f, sec/iter: %.1f" \
                      % (self.iter, self.termination[1] - 1, self.env.num_f_survived, self.agent.cumulative_rewards, rsquared, time()-self.iter_start_time)
            else:
                txt = "simulation iter %d of %d ends. num_f_survived: %d, sec/iter: %.1f" \
                      % (self.iter, self.termination[1] - 1, self.env.num_f_survived, time()-self.iter_start_time)
        print(txt)
        if self.gui_framework:
            self.gui_framework.write_console(txt)
        self.iter_start_time = time()

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

    # # # Load animation
    # # ani = GraphicDisplay(map_height, map_width, unit_pixel=5, load_file=True)
    # # ani.mainloop()
