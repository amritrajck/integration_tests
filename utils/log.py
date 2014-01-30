"""
utils.log
---------

This module creates the cfme logger, for use throughout the project. This logger only captures log
messages explicitly sent to it, not logs emitted by other components (such as selenium). To capture
those, consider using the pytest-capturelog plugin.

Example Usage
^^^^^^^^^^^^^

.. code-block:: python

    from utils.log import logger

    logger.debug('debug log message')
    logger.info('info log message')
    logger.warning('warning log message')
    logger.error('error log message')
    logger.critical('critical log message')

The above will result in the following output in ``cfme_tests/logs/cfme.log``::

    1970-01-01 00:00:00,000 [D] debug log message (filename.py:3)
    1970-01-01 00:00:00,000 [I] info log message (filename.py:4)
    1970-01-01 00:00:00,000 [W] warning log message (filename.py:5)
    1970-01-01 00:00:00,000 [E] error log message (filename.py:6)
    1970-01-01 00:00:00,000 [C] fatal log message (filename.py:7)

Additionally, if ``log_error_to_console`` is True (see below), the following will be
written to stderr::

    [E] error (filename.py:6)
    [C] fatal (filename.py:7)


Configuration
^^^^^^^^^^^^^

.. code-block:: yaml

    # in env.yaml
    logging:
        # Can be one of DEBUG, INFO, WARNING, ERROR, CRITICAL
        level: INFO
        # Maximum logfile size, in bytes, before starting a new logfile
        # Set to 0 to disable log rotation
        max_logfile_size: 0
        # Maximimum backup copies to make of rotated log files (e.g. cfme.log.1, cfme.log.2, ...)
        # Set to 0 to keep no backups
        max_logfile_backups: 0
        # If True, messages of level ERROR and CRITICAL are also written to stderr
        errors_to_console: False
        # Default file format
        file_format: "%(asctime)-15s [%(levelname).1s] %(message)s (%(relpath)s:%(lineno)d)"
        # Default format to console if errors_to_console is True
        stream_format: "[%(levelname)s] %(message)s (%(relpath)s:%(lineno)d)"

Additionally, individual logger configurations can be overridden by defining nested configuration
values using the logger name as the configuration key.

.. code-block:: yaml

    # in env.yaml
    logging:
        cfme:
            # set the cfme log level to debug
            level: DEBUG
        perflog:
            # make the perflog a little more "to the point"
            file_format: "%(message)s"

.. warning::

    Creating a logger with the same name as one of the default configuration keys,
    e.g. ``create_logger('level')`` will cause a rift in space-time (or a ValueError).
    Do not attempt.

Message Format
^^^^^^^^^^^^^^

    ``year-month-day hour:minute:second,millisecond [Level] message text (file:linenumber)``

``[Level]``:

    One letter in square brackets, where ``[I]`` corresponds to INFO, ``[D]`` corresponds to
    DEBUG, and so on.

``(file:linenumber)``:

    The relative location from which this log message was emitted. Paths outside

Members
^^^^^^^

"""
import logging
from logging.handlers import RotatingFileHandler
from time import time

from utils import conf
from utils.path import get_rel_path, log_path

# set logging defaults
_default_conf = {
    'level': 'INFO',
    'max_file_size': 0,
    'max_file_backups': 0,
    'errors_to_console': False,
    'file_format': '%(asctime)-15s [%(levelname).1s] %(message)s (%(relpath)s:%(lineno)d)',
    'stream_format': '[%(levelname)s] %(message)s (%(relpath)s:%(lineno)d)'
}


def _load_conf(logger_name=None):
    # Reload logging conf from env, then update the logging_conf
    try:
        del(conf['env'])
    except KeyError:
        # env not loaded yet
        pass

    logging_conf = _default_conf.copy()

    yaml_conf = conf.env.get('logging', {})
    # Update the defaults with values from env yaml
    logging_conf.update(yaml_conf)
    # Additionally, look in the logging conf for file-specific loggers
    if logger_name in logging_conf:
        logging_conf.update(logging_conf[logger_name])

    return logging_conf


class _RelpathFilter(logging.Filter):
    """Adds the relpath attr to records

    Not actually a filter, this was the least ridiculous way to add custom dynamic
    record attributes.

    """
    def filter(self, record):
        record.relpath = get_rel_path(record.pathname)
        return True


class Perflog(object):
    """Performance logger, useful for timing arbitrary events by name

    Logged events will be written to ``log/perf.log`` by default, unless
    a different log file name is passed to the Perflog initializer.

    Usage:

        from utils.log import perflog
        perflog.start('event_name')
        # do stuff
        seconds_taken = perflog.stop('event_name')
        # seconds_taken is also written to perf.log for later analysis

    """
    tracking_events = {}

    def __init__(self, perflog_name='perf'):
        self.logger = create_logger(perflog_name)

    def start(self, event_name):
        """Start tracking the named event

        Will reset the start time if the event is already being tracked

        """
        if event_name in self.tracking_events:
            self.logger.warning('"%s" event already started, resetting start time', event_name)
        else:
            self.logger.debug('"%s" event tracking started', event_name)
        self.tracking_events[event_name] = time()

    def stop(self, event_name):
        """Stop tracking the named event

        Returns:
            A float value of the time passed since ``start`` was last called, in seconds,
            *or* ``None`` if ``start`` was never called.

        """
        if event_name in self.tracking_events:
            seconds_taken = time() - self.tracking_events.pop(event_name)
            self.logger.info('"%s" event took %f seconds', event_name, seconds_taken)
            return seconds_taken
        else:
            self.logger.error('"%s" not being tracked, call .start first', event_name)
            return None


def create_logger(logger_name):
    """Creates and returns the named logger

    If the logger already exists, it will be destroyed and recreated
    with the current config in env.yaml

    """
    # If the logger already exists, destroy it
    if logger_name in logging.root.manager.loggerDict:
        del(logging.root.manager.loggerDict[logger_name])

    # Grab the logging conf
    conf = _load_conf(logger_name)

    log_path.ensure(dir=True)
    log_file = str(log_path.join('%s.log' % logger_name))

    relpath_filter = _RelpathFilter()

    # log_file is dynamic, so we can't used logging.config.dictConfig here without creating
    # a custom RotatingFileHandler class. At some point, we should do that, and move the
    # entire logging config into env.yaml

    file_formatter = logging.Formatter(conf['file_format'])
    file_handler = RotatingFileHandler(log_file, maxBytes=conf['max_file_size'],
        backupCount=conf['max_file_backups'], encoding='utf8')
    file_handler.setFormatter(file_formatter)

    logger = logging.getLogger(logger_name)
    logger.addHandler(file_handler)
    logger.setLevel(conf['level'])
    if conf['errors_to_console']:
        stream_formatter = logging.Formatter(conf['stream_format'])
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.ERROR)
        stream_handler.setFormatter(stream_formatter)

        logger.addHandler(stream_handler)

    logger.addFilter(relpath_filter)
    return logger

logger = create_logger('cfme')
perflog = Perflog()
