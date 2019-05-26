import configparser
import json
import os
import sys

from appdirs import user_config_dir
from PyQt5.QtWidgets import QApplication, QWidget


class Configuration(object):
    CONFIG_FILE_NAME = 'pyscreen.ini'
    DEFAULT_CATEGORY = 'DEFAULT'
    FILTER_SECTION = 'save_dir'
    DESC_FILTER_KEY = 'format'
    AUTO_SAVE_FILTERS = 'close_on_save'

    DEFAULT_CLOSE_ON_SAVE = False
    DEFAULT_SAVE_DIR = '/tmp/'

    def __init__(self, config_file=None):
        self.config = configparser.ConfigParser()
        self.config_path = config_file or user_config_dir(self.CONFIG_FILE_NAME)
        self.load()

    def _set_simple_value(self, label, value):
        self.config[self.DEFAULT_CATEGORY][label] = json.dumps(value)

    def _get_simple_value(self, label, default_return=''):
        if label not in self.config[self.DEFAULT_CATEGORY]:
            return default_return
        return json.loads(self.config[self.DEFAULT_CATEGORY][label])

    def _set_filters(self, label, filters):
        self._set_list_value(self.FILTER_SECTION, label, filters)

    def _get_filters(self, label):
        return self._get_list_value(self.FILTER_SECTION, label)

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


if __name__ == '__main__':
    app = QApplication(sys.argv)

    w = QWidget()
    w.resize(250, 150)
    w.move(300, 300)
    w.setWindowTitle('Simple')
    w.show()

    sys.exit(app.exec_())