import ctypes
import json
import logging
import sys
import threading
import time
from pathlib import Path

import PyQt5
import pynput
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QGridLayout, QPushButton, QFileDialog, \
    QMessageBox, QMainWindow, QRadioButton, QButtonGroup

from papergames_manager import PapergamesManager
from piskvork_manager import PiskvorkManager


class QTextEditLogger(logging.Handler, QtCore.QObject):
    appendPlainText = QtCore.pyqtSignal(str)

    def __init__(self, parent):
        super().__init__()
        QtCore.QObject.__init__(self)
        self.widget = QtWidgets.QPlainTextEdit(parent)
        self.widget.setReadOnly(True)
        self.appendPlainText.connect(self.widget.appendPlainText)

    def emit(self, record):
        msg = self.format(record)
        self.appendPlainText.emit(msg)


class DebugWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowIcon(QtGui.QIcon('icon.svg'))
        self.setWindowTitle("Debug")
        self.resize(400, 400)

        self.label = QLabel()

        layout = QGridLayout()
        layout.addWidget(self.label, 0, 0)
        self.setLayout(layout)

        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.config = dict()
        self.scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100.0
        self.screen = QApplication.primaryScreen()
        self.chess_thread_running = False

        self.debug_window = DebugWindow()

        self.log_level_button = QButtonGroup()

        self.log_level_info_radia_button = QRadioButton('Info')
        self.log_level_info_radia_button.setChecked(True)
        self.log_level_button.addButton(self.log_level_info_radia_button, 0)
        self.log_level_debug_radia_button = QRadioButton('Debug')
        self.log_level_debug_radia_button.setChecked(False)
        self.log_level_button.addButton(self.log_level_debug_radia_button, 1)

        self.pbrain_path_edit = QLineEdit()
        self.pbrain_path_edit.setText('pbrain.exe')

        self.pbrain_path_select_button = QPushButton('Select')
        # noinspection PyUnresolvedReferences
        self.pbrain_path_select_button.clicked.connect(self.select_pbrain_path)

        self.left_top_corner_mouse_x_edit = QLineEdit()
        self.left_top_corner_mouse_x_edit.setText('0')
        self.left_top_corner_mouse_x_edit.setValidator(QIntValidator(0, self.screen.size().width() - 1))

        self.left_top_corner_mouse_y_edit = QLineEdit()
        self.left_top_corner_mouse_y_edit.setText('0')
        self.left_top_corner_mouse_y_edit.setValidator(QIntValidator(0, self.screen.size().height() - 1))

        self.right_bottom_corner_mouse_x_edit = QLineEdit()
        self.right_bottom_corner_mouse_x_edit.setText(str(self.screen.size().width() - 1))
        self.right_bottom_corner_mouse_x_edit.setValidator(QIntValidator(0, self.screen.size().width() - 1))

        self.right_bottom_corner_mouse_y_edit = QLineEdit()
        self.right_bottom_corner_mouse_y_edit.setText(str(self.screen.size().height() - 1))
        self.right_bottom_corner_mouse_y_edit.setValidator(QIntValidator(0, self.screen.size().height() - 1))

        self.set_mouse_button = QPushButton('Set Mouse Range')
        # noinspection PyUnresolvedReferences
        self.set_mouse_button.clicked.connect(self.set_mouse)

        self.timeout_turn_edit = QLineEdit()
        self.timeout_turn_edit.setText('4.000')
        self.timeout_turn_edit.setValidator(QDoubleValidator(0.0, 40.0, 3))

        self.turn_wait_time_edit = QLineEdit()
        self.turn_wait_time_edit.setText('4.000')
        self.turn_wait_time_edit.setValidator(QDoubleValidator(0.0, 40.0, 1))

        self.first_move_button = QButtonGroup()

        self.is_first_move_radia_button = QRadioButton('Yes')
        self.is_first_move_radia_button.setChecked(True)
        self.first_move_button.addButton(self.is_first_move_radia_button, 0)
        self.not_first_move_radia_button = QRadioButton('No')
        self.not_first_move_radia_button.setChecked(False)
        self.first_move_button.addButton(self.not_first_move_radia_button, 1)

        self.start_or_stop_button = QPushButton('Start')
        # noinspection PyUnresolvedReferences
        self.start_or_stop_button.clicked.connect(self.start_or_stop)

        self.text_logger = QTextEditLogger(self)

        self.debug_window_button = QPushButton('Debug')
        # noinspection PyUnresolvedReferences
        self.debug_window_button.clicked.connect(lambda: self.debug_window.show())

        self.about_button = QPushButton('About')
        # noinspection PyUnresolvedReferences
        self.about_button.clicked.connect(
            lambda: QMessageBox.about(
                self, 'About', 'PaperGames Gomoku AI v0.1\n\n' +
                               'Repository: https://github.com/Mythologyli/papergames-gomoku-ai\n' +
                               'Author: Myth (https://github.com/Mythologyli)\n\n' +
                               'MIT License\n' +
                               'For study only, not for commercial use.'
            )
        )

        self.grid = QGridLayout()
        self.grid.setSpacing(10)

        self.grid.addWidget(QLabel('Log Level:'), 1, 0)
        self.grid.addWidget(self.log_level_info_radia_button, 1, 1)
        self.grid.addWidget(self.log_level_debug_radia_button, 1, 2)

        self.grid.addWidget(QLabel('Pbrain'), 2, 0)
        self.grid.addWidget(self.pbrain_path_edit, 2, 1)
        self.grid.addWidget(self.pbrain_path_select_button, 2, 2)

        self.grid.addWidget(QLabel('Left Top'), 3, 0)
        self.grid.addWidget(self.left_top_corner_mouse_x_edit, 3, 1)
        self.grid.addWidget(self.left_top_corner_mouse_y_edit, 3, 2)

        self.grid.addWidget(QLabel('Right Bottom'), 4, 0)
        self.grid.addWidget(self.right_bottom_corner_mouse_x_edit, 4, 1)
        self.grid.addWidget(self.right_bottom_corner_mouse_y_edit, 4, 2)

        self.grid.addWidget(self.set_mouse_button, 5, 0, 1, 3)

        self.grid.addWidget(QLabel('Turn Timeout'), 6, 0)
        self.grid.addWidget(self.timeout_turn_edit, 6, 1)

        self.grid.addWidget(QLabel('Turn Wait Time'), 7, 0)
        self.grid.addWidget(self.turn_wait_time_edit, 7, 1)

        self.grid.addWidget(QLabel('Is First Move'), 8, 0)
        self.grid.addWidget(self.is_first_move_radia_button, 8, 1)
        self.grid.addWidget(self.not_first_move_radia_button, 8, 2)

        self.grid.addWidget(self.start_or_stop_button, 9, 0, 1, 3)

        self.grid.addWidget(QLabel('Log'), 10, 0, 1, 3)
        self.grid.addWidget(self.text_logger.widget, 11, 0, 3, 3)

        self.grid.addWidget(self.debug_window_button, 14, 0)

        self.grid.addWidget(self.about_button, 14, 2)

        self.widget = QWidget()
        self.widget.setLayout(self.grid)
        self.setCentralWidget(self.widget)

        self.setWindowIcon(QtGui.QIcon('icon.svg'))

        self.setWindowTitle('PaperGames Gomoku AI v0.1')
        self.closeEvent = self.close_event

        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)

        self.load_config()

    def close_event(self, event):
        reply = QMessageBox.question(
            self,
            'Save',
            'Do you want to save the config?',
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

        if reply == QMessageBox.Yes:
            self.save_config()
        else:
            if reply == QMessageBox.Cancel:
                event.ignore()
                return

        event.accept()

    def load_config(self):
        if Path('config.json').is_file():
            with open('config.json', 'r') as f:
                self.config = json.load(f)

                self.pbrain_path_edit.setText(self.config['pbrain']['path'])
                self.timeout_turn_edit.setText(str(self.config['pbrain']['timeout_turn']))
                self.left_top_corner_mouse_x_edit.setText(str(self.config['mouse']['left_top']['x']))
                self.left_top_corner_mouse_y_edit.setText(str(self.config['mouse']['left_top']['y']))
                self.right_bottom_corner_mouse_x_edit.setText(str(self.config['mouse']['right_bottom']['x']))
                self.right_bottom_corner_mouse_y_edit.setText(str(self.config['mouse']['right_bottom']['y']))
                self.turn_wait_time_edit.setText(str(self.config['turn_wait_time']))

    def save_config(self):
        self.config = {
            'pbrain': {
                'path': self.pbrain_path_edit.text(),
                'timeout_turn': float(self.timeout_turn_edit.text())
            },
            'mouse': {
                'left_top': {
                    'x': int(self.left_top_corner_mouse_x_edit.text()),
                    'y': int(self.left_top_corner_mouse_y_edit.text())
                },
                'right_bottom': {
                    'x': int(self.right_bottom_corner_mouse_x_edit.text()),
                    'y': int(self.right_bottom_corner_mouse_y_edit.text())
                }
            },
            'turn_wait_time': float(self.turn_wait_time_edit.text())
        }

        with open('config.json', 'w') as f:
            json.dump(self.config, f, indent=4)

    def select_pbrain_path(self):
        pbrain_path_str = QFileDialog.getOpenFileName(self, 'Select pbrain', str(Path.cwd()), 'pbrain (*.exe)')[0]

        if pbrain_path_str:
            self.pbrain_path_edit.setText(pbrain_path_str)

    def set_mouse(self):
        QMessageBox.information(
            self,
            'Set Left Top Position',
            'After click OK, please click the left top corner of the chessboard!',
            QMessageBox.Ok
        )

        with pynput.mouse.Events() as events:
            for event in events:
                if isinstance(event, pynput.mouse.Events.Click):
                    self.left_top_corner_mouse_x_edit.setText(str(event.x))
                    self.left_top_corner_mouse_y_edit.setText(str(event.y))
                    break

        QMessageBox.information(
            self,
            'Set Right Bottom Position',
            'After click OK, please click the right bottom corner of the chessboard!',
            QMessageBox.Ok
        )

        with pynput.mouse.Events() as events:
            for event in events:
                if isinstance(event, pynput.mouse.Events.Click):
                    self.right_bottom_corner_mouse_x_edit.setText(str(event.x))
                    self.right_bottom_corner_mouse_y_edit.setText(str(event.y))
                    break

        QMessageBox.information(self, 'Set Mouse Position', 'Set mouse position successfully!', QMessageBox.Ok)

    def start_or_stop(self):
        if self.chess_thread_running:
            self.chess_thread_running = False
        else:
            if self.start_or_stop_button.text() == 'Start':
                self.chess_thread_running = True
                threading.Thread(target=self._start).start()
                self.start_or_stop_button.setText('Stop')

    def _sleep_and_is_running(self, secs):
        if not self.chess_thread_running:
            return False

        for i in range(int(secs * 10)):
            if not self.chess_thread_running:
                return False

            time.sleep(0.1)

        return True

    def _start(self):
        is_end = False

        logger = logging.getLogger()

        logger.addHandler(self.text_logger)

        if self.log_level_info_radia_button.isChecked():
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.DEBUG)

        self.text_logger.widget.clear()

        piskvork_manager = PiskvorkManager(
            logger,
            Path(self.pbrain_path_edit.text()),
            float(self.timeout_turn_edit.text()),
        )

        if piskvork_manager.proc is None:
            self.chess_thread_running = False
            self.start_or_stop_button.setText('Start')
            return

        papergames_manager = PapergamesManager(
            logger,
            (int(self.left_top_corner_mouse_x_edit.text()), int(self.left_top_corner_mouse_y_edit.text())),
            (int(self.right_bottom_corner_mouse_x_edit.text()), int(self.right_bottom_corner_mouse_y_edit.text())),
        )

        move_list = [(-1, -1)]

        if self.is_first_move_radia_button.isChecked():
            x, y = piskvork_manager.begin()

            papergames_manager.move(x, y)
            logger.info(f"My move: {(x, y)}")
            move_list.append((x, y))
            papergames_manager.mouse_to_original_position()

        while not is_end:
            while True:
                if not self._sleep_and_is_running(0):
                    is_end = True
                    break

                last_move = papergames_manager.get_last_move(self.debug_window.label)

                if last_move not in move_list:
                    logger.info(f"Opponent move: {last_move}")
                    move_list.append(last_move)

                    start_time = time.time()

                    # Get my move from piskvork brain
                    x, y = piskvork_manager.get_move(last_move[0], last_move[1])

                    # Wait for clicking the mouse
                    if time.time() - start_time < float(self.turn_wait_time_edit.text()):
                        if not self._sleep_and_is_running(
                                float(self.turn_wait_time_edit.text()) - (time.time() - start_time)
                        ):
                            is_end = True
                            break

                    papergames_manager.move(x, y)
                    logger.info(f"My move: {(x, y)}")
                    move_list.append((x, y))
                    papergames_manager.mouse_to_original_position()

                    # Make sure the clicking was successful
                    retry_time = 0
                    while True:
                        if not self._sleep_and_is_running(1 + retry_time * 2):
                            is_end = True
                            break

                        last_move = papergames_manager.get_last_move(self.debug_window.label)
                        if last_move == (x, y) or last_move not in move_list:
                            break

                        retry_time += 1
                        if retry_time > 3:
                            logger.error("Failed to click. Maybe game is over.")
                            self.chess_thread_running = False
                            is_end = True
                            break

                        logger.warning('Clicking failed, retrying...')
                        papergames_manager.move(x, y)
                        papergames_manager.mouse_to_original_position()

                    break

        piskvork_manager.kill()
        self.start_or_stop_button.setText('Start')
        logger.info('Stop!')


def main():
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
