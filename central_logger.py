import multiprocessing
import logging

class CentralLogger(multiprocessing.Process):
    def __init__(self, queue):
        multiprocessing.Process.__init__(self)
        self.queue = queue
        self.log = ""

    def run(self):
        logging.basicConfig(filename="day_trading_assistant.log", level=logging.DEBUG)
        self.log = logging.getLogger(__name__)
        self.log.info("  Started Central Logging process")

        while True:
            log_level, message = self.queue.get()
            if log_level == "stop":
                self.log.info("  Shutting down Central Logging process")
                break
            elif log_level == "DEBUG":
                self.log.debug(message)
            elif log_level == "INFO":
                self.log.info(message)
            elif log_level == "WARNING":
                self.log.warning(message)
            else:
                self.log.warning("  Central Logging: Received wrong logging level")
