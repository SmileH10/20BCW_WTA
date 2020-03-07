from env import Env
from agent import RL, Greedy
from entity import Asset, Flight, Battery
from animation import GraphicDisplay
from dataIO import write_data
from time import time
import random
from datetime import datetime
import pickle
import os, sys


class MainApp(object):
    def __init__(self, agent_name='rl', task='Test', map_width=200.0, map_height=300.0, battery_num=3, flight_num=20, flight_time_interval=30,
                 termination=('Iteration number', 5), autosave_iter=2, animation=True):
        self.gui_framework = None
        self.env = None
        self.agent_name = agent_name
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
        self.env = Env(self.map_width, self.map_height)
        # self.log_dir = "./logs/{}-{}/".format(self.agent_name.lower(), datetime.now().strftime("%m-%d_%H-%M-%S"))
        if self.agent_name.lower() == 'greedy':
            self.env.agent = Greedy()
            self.log_dir = "./logs/greedy-{}/".format(datetime.now().strftime("%m-%d_%H-%M-%S"))
        elif self.agent_name.lower() in ('rl', 'reinforcement learning'):
            self.env.agent = RL()
            self.log_dir = "./logs/rl-{}/".format(datetime.now().strftime("%m-%d_%H-%M-%S"))
        else:  # agent file loaded
            with open(self.agent_name, 'rb') as file:  # james.p 파일을 바이너리 읽기 모드(rb)로 열기
                self.env.agent = pickle.load(file)
            loaded_filename = self.agent_name.split('/')[-2] + '_' + self.agent_name.split('/')[-1].split('.')[0]
            self.log_dir = "./logs/{}-{}/".format(loaded_filename, datetime.now().strftime("%m-%d_%H-%M-%S"))

        if self.animation:
            self.env.animation = GraphicDisplay(self.map_height, self.map_width, unit_pixel=min(int(1230.0 / self.map_height), int(910.0 / self.map_width)))

        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        if self.gui_framework:
            self.gui_framework.write_console("log directory: " + self.log_dir, box='textBrowser_setting')
            self.gui_framework.write_console("log directory: " + self.log_dir)

        self.iter = 0
        self.start_time = time()
        self.init_env()
        self.init_env_iter()

    def run_main(self):
        self.initialize()
        while True:
            # 초기화
            self.init_env_iter()
            # Run 시뮬레이션
            self.env.run_simulation(self.iter, self.task)
            # 결과 저장 및 출력
            self.save_and_print()
            if self.stop_signal():
                break
            # iter 숫자 증가
            self.iter += 1
        if self.gui_framework:
            self.gui_framework.stop_program()
            self.gui_framework.write_console("Ends running.")
        if self.env.animation:
            self.env.animation.mainloop()
        print("[main.py] Ends")

    def save_and_print(self):
        # Auto-save
        if self.iter % self.autosave_iter == 0:
            if self.env.animation:
                self.env.animation.save_file(self.log_dir)
            if self.env.agent.name == 'rl':
                # 에이전트 파일 저장
                self.env.agent.save_file(self.log_dir, self.iter)

        # 결과 출력 코드
        # # Program에 출력
        temp_time_h = (self.termination[1] - time() + self.start_time) / (60.0 * 60)
        temp_time_m = (self.termination[1] - time() + self.start_time) % (60.0 * 60) / 60.0
        temp_time_s = (self.termination[1] - time() + self.start_time) % 60.0
        if self.termination[0][:4].lower() == 'time':
            if self.env.agent.name == 'rl':
                txt = "simulation iter %d ends. %dh:%dm:%.0fs left. num_f_survived: %d, cum_rewards: %.2f"\
                      % (self.iter, temp_time_h, temp_time_m, temp_time_s, self.env.num_f_survived, self.env.agent.cumulative_rewards)
            else:
                txt = "simulation iter %d ends. %dh:%dm:%.0fs left. num_f_survived: %d" \
                      % (self.iter, temp_time_h, temp_time_m, temp_time_s, self.env.num_f_survived)
        elif self.termination[0][:4].lower() == 'iter':
            if self.env.agent.name == 'rl':
                txt = "simulation iter %d of %d ends. num_f_survived: %d, cum_rewards: %.2f"\
                      % (self.iter, self.termination[1] - 1, self.env.num_f_survived, self.env.agent.cumulative_rewards)
            else:
                txt = "simulation iter %d of %d ends. num_f_survived: %d" % (self.iter, self.termination[1] - 1, self.env.num_f_survived)
        print(txt)
        if self.gui_framework:
            self.gui_framework.write_console(txt)
        # # 파일로 저장
        filename = "results"
        extension = ".csv"
        if self.env.agent.name == 'rl':
            if not os.path.isfile(self.log_dir + filename + extension):
                headstr = 'Iteration, num_f_survived, total rewards'
            else:
                headstr = False
            tempdic_rawdata = {"%d" % self.iter: "%d, %.2f" % (self.env.num_f_survived, self.env.agent.cumulative_rewards)}
        else:
            if not os.path.isfile(self.log_dir + filename + extension):
                headstr = 'Iteration, num_f_survived'
            else:
                headstr = False
            tempdic_rawdata = {"%d" % self.iter: "%d" % self.env.num_f_survived}
        write_data(self.log_dir, data=tempdic_rawdata, filename=filename, head=headstr, extension=extension)
        # # lm 데이터를 파일로 저장
        if self.env.agent.name == 'rl':
            filename = "LinearModel_data"
            if not os.path.isfile(self.log_dir + filename + extension):
                headstr = ', '.join('feature%d' % i for i in range(self.env.agent.num_features)) + ', Y(=Q)'
            else:
                headstr = False
            write_data(self.log_dir, data=self.env.agent.memory_for_record, filename=filename, head=headstr, list_type='2D')
            self.env.agent.initialize()

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

    def init_env(self):
        # battery 생성
        self.battery = {}
        temp_x = self.map_width / 2 / self.b_num
        for b in range(self.b_num):
            # 일단 위치는 균등하게 퍼트려놓음.
            self.battery[b] = Battery(b_id=b, x=temp_x, y=100)
            temp_x += self.map_width / self.b_num

    def init_env_iter(self):
        """
        매 iteration 마다 sim_t 초기화 / battery 초기화 / asset 새로 생성 / flight 새로 생성
        """
        self.env.sim_t = 0
        self.env.num_f_survived = 0
        if self.task.lower() == 'test':
            random.seed(self.iter + 910814)
        # elif self.task.lower() == 'train':  # 로딩한 agent 이어서 학습할 때 예전 꺼 그대로 반복하지 않도록...
        #     random.seed(self.iter)

        """
        flight 출발좌표: (x, map_height - 10)
        battery 위치좌표: (x, 사거리 * 2.5)
        asset 위치좌표: (x, 5)
        """

        for b in range(self.b_num):
            self.battery[b].initialize()

        # asset 생성
        asset_num = self.f_num
        temp_x = [random.random() for _ in range(asset_num)]
        temp_x.sort()
        for a in range(asset_num):
            self.asset[a] = Asset(a_id=a, x=temp_x[a] * self.map_width, y=5, value=1)

        # flight 생성
        temp_x = [random.random() for _ in range(self.f_num)]
        temp_x.sort()
        for f in range(self.f_num):
            # 일단 출발위치는 uniform 분포, 목표자산 아무거나 설정
            self.flight[f] = Flight(f_id=f, init_x=temp_x[f] * self.map_width, init_y=self.map_height - 10, target_asset=self.asset[f],
                                    start_t=random.randint(0, self.f_interval))

        # env 에 반영
        del self.env.flight, self.env.battery, self.env.asset
        self.env.flight = self.flight
        self.env.asset = self.asset
        self.env.battery = self.battery


if __name__ == '__main__':
    my_main = MainApp()
    my_main.run_main()

    # # # Load animation
    # # ani = GraphicDisplay(map_height, map_width, unit_pixel=5, load_file=True)
    # # ani.mainloop()
