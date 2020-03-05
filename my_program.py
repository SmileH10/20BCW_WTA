# import sys
# from PyQt5.QtWidgets import *  # QApplication, QWidget, QPushButton, QToolTip, QMainWindow, QAction, qApp
# from PyQt5.QtGui import QIcon, QFont
# from PyQt5.QtCore import QCoreApplication

import sys
from PyQt5.QtWidgets import QApplication, QDialog, QMainWindow, QDialogButtonBox, QMessageBox, QFileDialog
from PyQt5.QtCore import QProcess, QThreadPool, QRunnable, QObject, pyqtSignal, pyqtSlot, QThread
from PyQt5.uic import loadUi
from PyQt5 import QtGui
from main import MainApp
import pickle

from animation import GraphicDisplay  # TEMP


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn

    @pyqtSlot()
    def run(self):
        self.fn.run_main()


class SimconfigPage(QDialog):
    def __init__(self, homepage, mainapp):
        super(SimconfigPage, self).__init__()
        loadUi('./ui/ui_simconfigwindow.ui', self)
        self.mainapp = mainapp
        self.homepage = homepage

        self.load_current_setting()
        self.print_current_setting()

        # # 시그널/슬롯
        self.buttonBox.clicked.connect(self.handleButtonClick)

        # Agent: Greedy 는 Task: Test 못함
        self.check_task_feasibility()
        self.comboBox_agent.currentTextChanged.connect(self.check_task_feasibility)

    def handleButtonClick(self, button):
        sb = self.buttonBox.standardButton(button)
        if sb == QDialogButtonBox.Apply:
            self.ok_func()
            self.print_current_setting()
            self.homepage.print_setting()
        elif sb == QDialogButtonBox.Ok:
            self.ok_func()
            self.homepage.print_setting()
            self.destroy()
        elif sb == QDialogButtonBox.Cancel:
            self.destroy()

    def check_task_feasibility(self):
        if self.comboBox_agent.currentText().lower() == 'greedy':
            self.comboBox_task.setCurrentText('Test')
            # self.label_task.setText('Test')
            # self.label_task.setText('Test')
            self.comboBox_task.setEnabled(False)
        else:
            self.comboBox_task.setEnabled(True)

    def ok_func(self):
        self.mainapp.agent_name = self.comboBox_agent.currentText()
        self.mainapp.task = self.comboBox_task.currentText()
        self.mainapp.b_num = self.spinBox_numb.value()
        self.mainapp.f_num = self.spinBox_numf.value()
        self.mainapp.f_interval = self.doubleSpinBox_finterval.value()
        self.mainapp.map_width = self.doubleSpinBox_width.value()
        self.mainapp.termination = (self.comboBox_termtype.currentText(), self.spinBox_termcriteria.value())
        self.mainapp.autosave_iter = self.spinBox_autosave.value()

    def load_current_setting(self):
        self.comboBox_agent.setCurrentText(self.mainapp.agent_name)
        self.comboBox_task.setCurrentText(self.mainapp.task)
        self.spinBox_numb.setProperty("value", self.mainapp.b_num)
        self.spinBox_numf.setProperty("value", self.mainapp.f_num)
        self.doubleSpinBox_finterval.setProperty("value", self.mainapp.f_interval)
        self.doubleSpinBox_width.setProperty("value", self.mainapp.map_width)
        self.spinBox_termcriteria.setProperty("value", self.mainapp.termination[1])
        self.comboBox_termtype.setCurrentText(self.mainapp.termination[0])
        self.spinBox_autosave.setProperty("value", self.mainapp.autosave_iter)

    def print_current_setting(self):
        self.label_agent.setText(str(self.comboBox_agent.currentText()))
        self.label_task.setText(str(self.comboBox_task.currentText()))
        self.label_numb.setText(str(self.spinBox_numb.value()))
        self.label_numf.setText(str(self.spinBox_numf.value()))
        self.label_finterval.setText(str(self.doubleSpinBox_finterval.value()))
        self.label_width.setText(str(self.doubleSpinBox_width.value()))
        self.label_termtype.setText(str(self.comboBox_termtype.currentText()))
        self.label_termcriteria.setText(str(self.spinBox_termcriteria.value()))
        self.label_autosave.setText(str(self.spinBox_autosave.value()))


class MainPage(QMainWindow):
    def __init__(self):
        super(MainPage, self).__init__()
        loadUi('./ui/ui_mainwindow.ui', self)
        self.mainapp = MainApp()  # main.py 에서 연결
        self.mainapp.gui_framework = self
        self.threadpool = QThreadPool()
        self._stopflag = False  # main app 정지 신호
        self._exitflag = False  # main app 종료 신호

        # 초기 출력
        self.print_setting()  # mainwindow 의 textBrowser_setting 에 현재 설정 출력
        self.textBrowser.append("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        # 시그널/슬롯 생성
        self.actionSimulationSetting.triggered.connect(self.executeConfigPage)  # 페이지(윈도우) 연결
        self.actionRun.triggered.connect(self.run_program)  # Run mainapp
        self.actionStop.triggered.connect(self.stop_program)
        self.actionSaveAgent.triggered.connect(self.save_agent)
        self.actionLoadAni.triggered.connect(self.load_animation)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "Message",
            "Are you sure you want to quit? Any unsaved work will be lost.",
            QMessageBox.Close | QMessageBox.Cancel, QMessageBox.Cancel)

        if reply == QMessageBox.Close:
            self._stopflag = True
            self._exitflag = True
            event.accept()
        else:
            event.ignore()

    def run_program(self):
        worker = Worker(self.mainapp)
        # 정지설정 False / run & 설정버튼 비활성화
        self._stopflag = False
        self.actionRun.setEnabled(False)
        self.actionSimulationSetting.setEnabled(False)
        # Execute
        self.threadpool.start(worker)
        self.write_console("Multithreading with %d of %d threads" % (self.threadpool.activeThreadCount(), self.threadpool.maxThreadCount()))

        # Alternative: def run_program2(self):  # 외부에서 self.actionRun.triggered.connect(self.run_program2)        #
        #     self.thread = Thread(target=self.mainapp.run_main)
        #     self.thread.daemon = True
        #     self.thread.start()

    def stop_program(self):
        self._stopflag = True
        self.actionRun.setEnabled(True)
        self.actionSimulationSetting.setEnabled(True)

    def save_agent(self):
        if not self.mainapp.env:
            QMessageBox.warning(self, "Message", "Any agent/environment isn't loaded.")
        elif self.mainapp.env.agent.name == 'rl':
            self.mainapp.env.agent.save_file(self.mainapp.log_dir, self.mainapp.iter)
            QMessageBox.information(self, "Message", "RL agent file is saved")
        elif self.mainapp.env.agent.name == 'greedy':
            QMessageBox.warning(self, "Message", "Greedy agent file CANNOT be saved")

    def load_animation(self):
        options = QFileDialog.Options()
        # filter: "All Files (*)", "Python Files (*.py)", "PKL Files (*.pkl)"
        fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "PKL Files (*.pkl)", options=options)
        if fileName:
            QMessageBox.information(self, "Message", "animation file is loaded \n %s" % fileName)
            with open(fileName, 'rb') as file:  # james.p 파일을 바이너리 읽기 모드(rb)로 열기
                ani_data = pickle.load(file)
            temp_ani = GraphicDisplay(ani_data['width'], ani_data['height'], unit_pixel=ani_data['unit'])
            temp_ani.data = ani_data['data']
            temp_ani.mainloop()

    def print_setting(self):
        self.textBrowser_setting.setText("[ Current Setting ]\n")
        self.textBrowser_setting.append("Agent: %s" % self.mainapp.agent_name)
        self.textBrowser_setting.append("Task: %s" % self.mainapp.task)
        self.textBrowser_setting.append("Num Battery: %d" % self.mainapp.b_num)
        self.textBrowser_setting.append("Num Flight: %d" % self.mainapp.f_num)
        self.textBrowser_setting.append("Flight Time Interval: %.2f" % self.mainapp.f_interval)
        self.textBrowser_setting.append("Defense range (map width): %.2f" % self.mainapp.map_width)
        self.textBrowser_setting.append("Termination Type: %s" % str(self.mainapp.termination[0]))
        self.textBrowser_setting.append("Termination Criteria: %s" % str(self.mainapp.termination[1]))
        self.textBrowser_setting.append("Autosave cycle: %d iter" % self.mainapp.autosave_iter)

    def executeConfigPage(self):
        simconfig_page = SimconfigPage(self, self.mainapp)
        simconfig_page.exec_()

    def write_console(self, text, box='textBrowser'):
        if box == 'textBrowser_setting':
            self.textBrowser_setting.append(str(text))
            self.textBrowser_setting.moveCursor(QtGui.QTextCursor.End)
        else:
            self.textBrowser.append(str(text))
            self.textBrowser.moveCursor(QtGui.QTextCursor.End)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_widget = MainPage()
    main_widget.show()
    sys.exit(app.exec_())



