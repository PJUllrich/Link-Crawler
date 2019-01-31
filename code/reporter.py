import logging.config

logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
logger = logging.getLogger(__name__)


class Reporter:
    """
    Utility class for the link crawler for logging.
    """

    @staticmethod
    def status(scanned, total):
        if total > 0:
            print(f'\r{scanned} of {total} '
                  f'({(scanned / total):.2f}%) '
                  f'links scanned. ',
                  end='')

    @staticmethod
    def broken(parent, url, status):
        logger.info(f'Broken: {parent} - {url} - {status}')

    @staticmethod
    def scan(parent, url):
        logger.debug(f'Now scanning: {parent} - {url}')

    @staticmethod
    def info(msg):
        logger.info(msg)

    @staticmethod
    def debug(msg):
        logger.debug(msg)

    @staticmethod
    def error(parent, url, error):
        logger.error(f'{parent} - {url} - {error}')
