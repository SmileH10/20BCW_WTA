import tkinter as tk
import tkinter.messagebox
import tkinter.ttk
from PIL import ImageTk, Image
from collections import defaultdict
from time import sleep
import math  # pi 사용
import pickle
import os


class GraphicDisplay(tk.Tk):
    def __init__(self, width, height, unit_pixel=4, load_file=False):
        super(GraphicDisplay, self).__init__()
        self.title('WTA Simulation')
        self.width = int(width)  # 캔버스 가로 크기
        self.height = int(height)  # 캔버스 세로 크기
        self.unit = unit_pixel  # 단위픽셀 수
        self.geometry('{0}x{1}'.format(self.width * self.unit + 50, self.height * self.unit + 50))

        self.f_imgfile, self.b_imgfile, self.m_imgfile, self.a_imgfile = self.load_images()  # canvas에 image로 그린 객체들 딕셔너리
        self.f_img, self.b_img, self.m_img, self.a_img = {}, {}, {}, {}  # canvas에 image로 그린 객체들 딕셔너리

        self.canvas = self._build_canvas()
        self.time_text = self.canvas.create_text(10, 10, text="time = 0.00", font=('Helvetica', '10', 'normal'), anchor="nw")
        self.iter = 0
        self.sim_speed = 1/1000.0  # sec:sim_t
        self.event_cnt = 0
        self.is_moving = 0  # pause 기능을 위한 변수.
        # self.data = [[]]  # data[iter][event_cnt] = [sim_t, flight(object dic), battery, missile] 형태로 저장.

        if load_file:
            self.data = self.load_file()
        else:
            self.data = defaultdict(dict)

    def _build_canvas(self):
        canvas = tk.Canvas(self, bg='white',
                           height=self.height * self.unit,
                           width=self.width * self.unit)
        # canvas.create_image(self.width * UNIT / 2, self.height * UNIT / 2, image=self.backgroundimg)

        run_entire_button = tk.Button(self, text="Run(entire)", command=self.run_entire)
        run_entire_button.configure(width=10, activebackground="#33B5E5")
        canvas.create_window(self.width * self.unit * 0.08, self.height * self.unit + 10, window=run_entire_button)  # 왼쪽상단이 (0, 0) 인듯
        run_onestep_forward_button = tk.Button(self, text="Run(1step forward)", command=self.run_onestep_forward)
        run_onestep_forward_button.configure(width=17, activebackground="#33B5E5")
        canvas.create_window(self.width * self.unit * 0.22, self.height * self.unit + 10, window=run_onestep_forward_button)
        run_onestep_backward_button = tk.Button(self, text="Run(1step backward)", command=self.run_onestep_backward)
        run_onestep_backward_button.configure(width=17, activebackground="#33B5E5")
        canvas.create_window(self.width * self.unit * 0.385, self.height * self.unit + 10, window=run_onestep_backward_button)
        run_reset_button = tk.Button(self, text="reset", command=self.run_reset)
        run_reset_button.configure(width=8, activebackground="#33B5E5")
        canvas.create_window(self.width * self.unit * 0.525, self.height * self.unit + 10, window=run_reset_button)
        run_pause_button = tk.Button(self, text="pause", command=self.run_pause)
        run_pause_button.configure(width=8, activebackground="#33B5E5")
        canvas.create_window(self.width * self.unit * 0.61, self.height * self.unit + 10, window=run_pause_button)

        iter_minus_button = tk.Button(self, text="iter-", command=self.iter_minus)
        iter_minus_button.configure(width=8, activebackground="#33B5E5")
        canvas.create_window(self.width * self.unit * 0.74, self.height * self.unit + 10, window=iter_minus_button)
        iter_plus_button = tk.Button(self, text="iter+", command=self.iter_plus)
        iter_plus_button.configure(width=8, activebackground="#33B5E5")
        canvas.create_window(self.width * self.unit * 0.825, self.height * self.unit + 10, window=iter_plus_button)

        change_speed_button = tk.Button(self, text="speed", command=self.change_speed)
        change_speed_button.configure(width=8, activebackground="#33B5E5")
        canvas.create_window(self.width * self.unit * 0.945, self.height * self.unit + 10, window=change_speed_button)

        canvas.pack()

        return canvas

    # def save_status(self, simiter, time, status):
    #     pass
    #     if self.event_cnt == 0 or self.previous_status != status:
    #         self.data[simiter][self.event_cnt] = (time, status)
    #         self.event_cnt += 1
    #         self.previous_status = status

    def printing_time(self, sim_t, font='Helvetica', size=12, style='bold', anchor="nw"):
        hour = sim_t / (60.0 * 60)
        minute = sim_t % (60.0 * 60) / 60.0
        second = sim_t % 60.0
        time_str = "time = %.1f secs (%d : %d : %.1f)" % (sim_t, hour, minute, second)
        font = (font, str(size), style)
        self.canvas.delete(self.time_text)
        self.time_text = self.canvas.create_text(10, 10, fill="black", text=time_str, font=font, anchor=anchor)

    # def printing_iter(self, font='Helvetica', size=12, style='bold', anchor="ne"):
    #     pass
    #     iter_str = "iteration: %d / %d (Total %d)" % (self.iter, len(self.data.keys()) - 1, len(self.data.keys()))
    #     font = (font, str(size), style)
    #     if hasattr(self, 'iter_text'):
    #         self.canvas.delete(self.iter_text)
    #     self.iter_text = self.canvas.create_text(self.width * self.unit - 10, 10, fill="black", text=iter_str, font=font, anchor=anchor)

    @staticmethod
    def load_images():
        # background = ImageTk.PhotoImage(Image.open("./img/background2.png").resize((WIDTH * UNIT, HEIGHT * UNIT)))
        f_imgfile, b_imgfile, m_imgfile, a_imgfile = {}, {}, {}, {}
        for i in range(12):
            f_imgfile[i] = ImageTk.PhotoImage(Image.open("./img/triangle%d.png" % i).resize((15, 15)))
            m_imgfile[i] = ImageTk.PhotoImage(Image.open("./img/circle%d.png" % i).resize((15, 15)))
            b_imgfile[i] = ImageTk.PhotoImage(Image.open("./img/rectangle.png").resize((15, 15)))
            a_imgfile[i] = ImageTk.PhotoImage(Image.open("./img/rectangle.png").resize((15, 15)))
        return f_imgfile, b_imgfile, m_imgfile, a_imgfile

    def draw_status(self, status):
        # status = (sim_t, f_dic, m_dic, b_dic)
        # object를 담은 딕셔너리
        flight = status[1]  # f_id, x, y, direction
        missile = status[2]  # m_id, x, y
        if len(status) >= 4:
            battery = status[3]  # b_id, x, y
            for b_id in battery.keys():
                y = battery[b_id].x * self.unit
                x = self.width * self.unit - battery[b_id].y * self.unit
                self.b_imgfile[b_id] = ImageTk.PhotoImage(Image.open('./img/rectangle.png').resize((15, 15)))
                self.b_img[b_id] = {'image': self.canvas.create_image(x, y, image=self.b_imgfile[b_id % 12]),
                                    'text': self.canvas.create_text(x, y, text=str(b_id))}
            # asset = status[4]
            # for a_id in asset.keys():
            #     y = asset[a_id].x * self.unit
            #     x = self.width * self.unit - asset[a_id].y * self.unit
            #     a_imgfile = ImageTk.PhotoImage(Image.open("./img/rectangle.png").resize((30, 30)))
            #     self.a_img[a_id] = {'image': self.canvas.create_image(x, y, image=a_imgfile),
            #                         'text': self.canvas.create_text(x, y, text=str(a_id))}

        for f_id in self.f_img.keys():
            self.canvas.delete(self.f_img[f_id]['image'])
            self.canvas.delete(self.f_img[f_id]['text'])

        # for a_id in self.a_img.keys():
        #     self.canvas.delete(self.a_img[a_id]['image'])
        #     self.canvas.delete(self.a_img[a_id]['text'])

        for m_id in self.m_img.keys():
            self.canvas.delete(self.m_img[m_id]['image'])
            self.canvas.delete(self.m_img[m_id]['text'])

        for f_id in flight.keys():
            y = flight[f_id].x * self.unit
            x = self.width * self.unit - flight[f_id].y * self.unit
            rotate_degree = -90
            rotate_degree += (flight[f_id].direction + 0.5 * math.pi) * 180.0 / math.pi
            self.f_imgfile[f_id % 12] = ImageTk.PhotoImage(Image.open("./img/triangle%d.png" % (f_id % 12)).rotate(rotate_degree).resize((15, 15)))
            self.f_img[f_id] = {'image': self.canvas.create_image(x, y, image=self.f_imgfile[f_id % 12]),
                                'text': self.canvas.create_text(x, y, text=str(f_id))}

        for m_id in missile.keys():
            y = missile[m_id].x * self.unit
            x = self.width * self.unit - missile[m_id].y * self.unit
            self.m_img[m_id] = {'image': self.canvas.create_image(x, y, image=self.m_imgfile[m_id[0] % 12]),
                                'text': self.canvas.create_text(x, y, text=str(m_id[1])+", "+str(m_id[2]))}

    def run_entire(self):
        self.is_moving = 1
        while self.event_cnt <= len(self.data[self.iter]) - 2:
            current_time = self.data[self.iter][self.event_cnt][0]
            next_time = self.data[self.iter][self.event_cnt + 1][0]
            sleep(self.sim_speed * (next_time - current_time))
            self.run_onestep_forward()
            # self.after(int(self.sim_speed * (next_time - current_time)), self.run_onestep_forward())
            self.update()  # 화면 업데이트하기(?) 과거의 나는 이거 왜 넣었던거지?ㅋㅋㅋ
            if self.is_moving == 0:  # pause 버튼 누르면 멈추기
                break
        self.is_moving = 0

    def run_onestep_forward(self):
        if 0 <= self.event_cnt <= len(self.data[self.iter]) - 2:
            time = self.data[self.iter][self.event_cnt][0]
            self.printing_time(time)
            self.draw_status(self.data[self.iter][self.event_cnt])
            self.event_cnt += 1
        else:
            tk.messagebox.showwarning("Error", "simulation ends")

    def run_onestep_backward(self):
        if 1 <= self.event_cnt <= len(self.data[self.iter]):
            self.event_cnt -= 1
            time = self.data[self.iter][self.event_cnt][0]
            self.printing_time(time)
            self.draw_status(self.data[self.iter][self.event_cnt])
        else:
            tk.messagebox.showwarning("Error", "you're at the simulation starting point")

    def run_reset(self):
        self.is_moving = 0
        sleep(0.01)
        self.event_cnt = 0
        time = self.data[self.iter][self.event_cnt][0]
        self.printing_time(time)
        # self.printing_iter()
        self.draw_status(self.data[self.iter][self.event_cnt])

    def run_pause(self):
        self.is_moving = 0

    def iter_plus(self):
        pass
        if -1 <= self.iter < len(self.data.keys()) - 1:
            self.iter += 1
            self.run_reset()
        else:
            tk.messagebox.showwarning("Error", "iteration ends")

    def iter_minus(self):
        pass
        if 1 <= self.iter < len(self.data.keys()) + 1:
            self.iter -= 1
            self.run_reset()
        else:
            tk.messagebox.showwarning("Error", "you're at the first iteration")

    def change_speed(self):
        win_entry = tk.Toplevel(self)
        win_entry.title("enter simulation speed")
        win_entry.geometry('300x130+550+450')

        def check_ok(event=None):
            tk.messagebox.showinfo("simulation speed info", "simulation speed changes to %s" % input_num.get())
            # self.sim_speed = int(input_num.get()) / 10000.0
            self.sim_speed = 1/float(input_num.get())
            win_entry.destroy()
        input_num = tk.StringVar()

        label = tk.Label(win_entry)
        label.config(text="enter simulation speed \n (sec / 1 simulation time. the larger the faster) "
                          "\n default: 1000 (1000 times faster)")
        label.pack(ipadx=5, ipady=5)
        textbox = tk.ttk.Entry(win_entry, width=10, textvariable=input_num)
        textbox.pack(ipadx=5, ipady=5)
        action = tk.ttk.Button(win_entry, text="OK", command=check_ok)
        action.pack(ipadx=5, ipady=5)
        win_entry.bind("<Return>", check_ok)
        win_entry.mainloop()

    def save_file(self):
        save_dir = "./gui_pkl/"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        with open(save_dir + 'simGUI_data.pkl', 'wb') as file:  # james.p 파일을 바이너리 쓰기 모드(wb)로 열기
            pickle.dump(self.data, file)

    @staticmethod
    def load_file():
        with open('simGUI_data.pkl', 'rb') as file:  # james.p 파일을 바이너리 읽기 모드(rb)로 열기
            return pickle.load(file)


if __name__ == '__main__':
    pass
