"""A simplified logging interface for SuttaCentral.

For simplicity, all logs are combined and sent to log/app.log. We do this by
bypassing the default cherrypy logger (which splits logs into an access and
error log) and instead use our own custom logger.

To create a log message, use the standard Python logging pattern:

    >>> import logging
    >>> logger = logging.getLogger(__name__)
    >>> # ...
    >>> logger.info('my message')
"""

import cherrypy
import regex
import logging
from logging.handlers import RotatingFileHandler
from colorama import Fore
from copy import copy

from sc import config


class SCLogFormatter(logging.Formatter):

    def __init__(self, colorize=False):
        self.colorize = colorize
        super().__init__(fmt='[{asctime}] {levelname} {name} {message}',
                         datefmt='%Y-%m-%d %H:%M:%S', style='{')

    def format(self, record):
        record = copy(record)
        self._remove_cherrypy_app_suffix(record)
        self._remove_cherrypy_error_time_and_context(record)
        self._remove_cherrypy_access_time(record)
        self._indent_msg(record)
        if self.colorize:
            self._colorize(record)
        return super().format(record)

    _cherrypy_app_re = regex.compile(r'^(cherrypy\.(?:error|access))\.[0-9]+$')

    def _remove_cherrypy_app_suffix(self, record):
        match = self._cherrypy_app_re.match(record.name)
        if match:
            record.name = match[1]

    def _remove_cherrypy_error_time_and_context(self, record):
        if record.name == 'cherrypy.error':
            record.msg = record.msg.split(' ', 2)[2]

    def _remove_cherrypy_access_time(self, record):
        if record.name == 'cherrypy.access':
            parts = record.msg.split(' ', 4)
            del(parts[3])
            record.msg = ' '.join(parts)

    def _indent_msg(self, record):
        lines = record.msg.strip().splitlines()
        if len(lines) > 1:
            record.msg = '\n' + '\n'.join(['    ' + line for line in lines])

    _levelno_to_color = {
        logging.DEBUG: Fore.BLUE,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED,
    }

    def _colorize(self, record):
        levelname_color = self._levelno_to_color[record.levelno]
        record.name = levelname_color + record.name + Fore.RESET
        record.levelname = levelname_color + record.levelname + Fore.RESET


def setup():
    """Setup and attach the logger."""
    config['global']['log.access_file'] = ''
    config['global']['log.error_file'] = ''
    config['global']['log.screen'] = False
    log_level = getattr(logging, config.log_level)
    logging.root.setLevel(logging.NOTSET)
    file_log.setLevel(log_level)
    logging.root.addHandler(file_log)
    if config.log_screen:
        console_log.setLevel(log_level)
        logging.root.addHandler(console_log)

file_log = RotatingFileHandler(str(config.log_path), 
                maxBytes=4*1024*1024, backupCount=1)
file_log.setFormatter(SCLogFormatter())

console_log = logging.StreamHandler()
console_log.setFormatter(SCLogFormatter(colorize=True))
