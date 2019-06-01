#!/usr/bin/env python
import configparser
import json
import os
import sys

from appdirs import user_config_dir
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSlot, QStringListModel
from PyQt5.QtGui import QKeySequence
from subprocess import check_output, CalledProcessError, STDOUT


class Configuration(object):
    CONFIG_FILE_NAME = 'pyscreen.ini'
    DEFAULT_CATEGORY = 'DEFAULT'
    SAVE_DIRECTORY_KEY = 'save_dir'
    SCREENSHOT_COMMAND_KEY = 'command'
    EXIT_ON_SAVE_KEY = 'close_on_save'
    HISTORY_KEY = 'history'
    HISTORY_LEN_KEY = 'history_len'

    DEFAULT_EXIT_ON_SAVE = False
    DEFAULT_SAVE_DIR = ''
    DEFAULT_HISTORY = []
    DEFAULT_HISTORY_LEN = 30
    DEFAULT_COMMAND = 'import -quality 60 {}.png'

    def __init__(self, config_file=None):
        self.config = configparser.ConfigParser()
        self.config_path = config_file or user_config_dir(self.CONFIG_FILE_NAME)
        self.load()

    def _set_simple_value(self, label, value):
        self.config[self.DEFAULT_CATEGORY][label] = json.dumps(value)

    def _get_simple_value(self, label, default_return=''):
        if label not in self.config[self.DEFAULT_CATEGORY]:
            self._set_simple_value(label, default_return)
            return default_return
        return json.loads(self.config[self.DEFAULT_CATEGORY][label])

    def _set_list_value(self, key, label, values):
        if not isinstance(values, list):
            raise TypeError("Values must be a list object")
        self.config[key][label] = json.dumps(values)

    def _get_list_value(self, key, label):
        if label not in self.config[key]:
            return []
        return json.loads(self.config[key][label])

    def save(self):
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)

    def load(self):
        self.config.read(self.config_path)
        for key in Configuration.sections():
            if key not in self.config:
                self.config[key] = {}

    @staticmethod
    def sections():
        return [Configuration.DEFAULT_CATEGORY]

    @property
    def exit_on_save(self):
        return self._get_simple_value(self.EXIT_ON_SAVE_KEY,
                                      self.DEFAULT_EXIT_ON_SAVE)

    @exit_on_save.setter
    def exit_on_save(self, value):
        self._set_simple_value(self.EXIT_ON_SAVE_KEY, value)

    @property
    def save_directory(self):
        return self._get_simple_value(self.SAVE_DIRECTORY_KEY,
                                      self.DEFAULT_SAVE_DIR)

    @save_directory.setter
    def save_directory(self, value):
        if not isinstance(value, str):
            raise TypeError('Alert file must be a string')
        self._set_simple_value(self.SAVE_DIRECTORY_KEY, value)

    @property
    def history(self):
        return self._get_list_value(self.DEFAULT_CATEGORY,
                                    self.HISTORY_KEY)

    @history.setter
    def history(self, values):
        if len(values) > self.history_size:
            values = values[len(values) - self.history_size:]
        return self._set_list_value(self.DEFAULT_CATEGORY,
                                    self.HISTORY_KEY,
                                    values)

    @property
    def history_size(self):
        return self._get_simple_value(self.HISTORY_LEN_KEY,
                                      self.DEFAULT_HISTORY_LEN)

    @property
    def command(self):
        return self._get_simple_value(self.SCREENSHOT_COMMAND_KEY,
                                      self.DEFAULT_COMMAND)


class PyScreen(QWidget):

    def __init__(self):
        super(PyScreen, self).__init__()
        self.config = Configuration()
        self.config.load()
        self.layout = QGridLayout()
        self.current_row = 0
        self.screenshot_format = "Screenshot_%Y%m%d_%H%M%S"
        self.initUI()

    def initUI(self):
        self.setGeometry(400, 400, 400, 220)
        self.setWindowTitle('PyScreen')
        self.setLayout(self.layout)
        self._add_select_dir()
        self._add_define_name()
        self._add_simple_options()
        self._add_take_screen()
        self._init_shortcuts()
        self.screen_name.setFocus()

    def pick_dir(self):
        dialog = QFileDialog()
        folder_path = dialog.getExistingDirectory(None, "Select Folder")
        self.folder_path.setText(folder_path)

    def _add_select_dir(self):
        self.folder_path = QLineEdit(self.config.save_directory, self)
        self.dirBtn = QPushButton('Dir', self)
        self.dirBtn.clicked.connect(self.pick_dir)
        self.dirBtn.adjustSize()
        self.layout.addWidget(self.folder_path, self.current_row, 0)
        self.layout.addWidget(self.dirBtn, self.current_row, 1)
        self.current_row += 1

    def _add_define_name(self):
        self.screen_name = QLineEdit(self)
        self.history_model = QStringListModel(self.config.history, self)
        self.completer = QCompleter(self.history_model, self)
        self.screen_name.setCompleter(self.completer)
        self.screen_name.setPlaceholderText("File name")
        self.layout.addWidget(self.screen_name, self.current_row, 0)
        self.current_row += 1

    def _add_simple_options(self):
        self.exitonscreen = QRadioButton("Exit after screen")
        self.exitonscreen.setChecked(self.config.exit_on_save)
        self.layout.addWidget(self.exitonscreen, self.current_row, 0)
        self.current_row += 1

    def _add_take_screen(self):
        self.screenBtn = QPushButton('Take Screenshot', self)
        self.screenBtn.clicked.connect(self.take_screenshot)
        self.exitBtn = QPushButton('Exit', self)
        self.exitBtn.clicked.connect(self._exit)
        self.layout.addWidget(self.screenBtn, self.current_row, 0)
        self.layout.addWidget(self.exitBtn, self.current_row, 1)
        self.current_row += 1

    def _init_shortcuts(self):
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut.activated.connect(self.take_screenshot)
        shortcut = QShortcut(QKeySequence("Ctrl+q"), self)
        shortcut.activated.connect(self._exit)
        shortcut = QShortcut(QKeySequence("Ctrl+s"), self)
        shortcut.activated.connect(self._save_config)
        QShortcut(QKeySequence('Return'),
                  self.screen_name,
                  self.take_screenshot)

    def take_screenshot(self):
        self.hide()
        try:
            command = self.config.command
            full_path, name = self._make_filename()
            self._update_history(name)
            check_output(command.format(full_path), stderr=STDOUT, shell=True)
            if self.exitonscreen.isChecked():
                self._exit()
        except CalledProcessError as e:
            p = PopUp(self)
            p.setText(e.output)
            p.setWindowTitle("Import Error!")
            p.show()
        self.show()

    def _update_history(self, element):
        history = self.config.history
        if element not in history:
            history.append(element)
        self.config.history = history
        self.history_model.setStringList(self.config.history)

    def _make_filename(self):
        full_path = self.folder_path.text()
        name = self.screen_name.text().strip()
        if len(name) == 0:
            now = datetime.now()
            name = now.strftime(self.screenshot_format)
        name = name.replace(' ', '_')
        full_path = os.path.join(full_path, name)
        return full_path, name

    def _exit(self):
        self._save_config()
        self.close()
        sys.exit(0)

    def _save_config(self):
        self.config.exit_on_save = self.exitonscreen.isChecked()
        self.config.save_directory = str(self.folder_path.text())
        self.config.save()


class PopUp(QDialog):
    def __init__(self, *args, **kwargs):
        QDialog.__init__(self, *args, **kwargs)
        self.setLayout(QVBoxLayout())
        self.label = QLabel(self)
        self.layout().addWidget(self.label)

    @pyqtSlot(str)
    def setText(self, text):
        self.label.setText(text)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PyScreen()
    window.show()
    sys.exit(app.exec_())
