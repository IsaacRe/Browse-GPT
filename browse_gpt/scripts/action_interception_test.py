from selenium.webdriver.support.events import EventFiringWebDriver, AbstractEventListener
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome
import time
import sys
import os
import logging

from browse_gpt.config import BrowingSessionConfig
from browse_gpt.browser.chromedriver import start_driver

logger = logging.getLogger(__name__)

config = BrowingSessionConfig.parse_args()

class TestListener(AbstractEventListener):
    def on_click(self, element, webdriver):
        print("Click")
        logger.info("Click intercepted:", element)


#def main(config: BrowingSessionConfig):
driver = Chrome(executable_path=os.getenv("CHROMEDRIVER_PATH"))
driver = EventFiringWebDriver(driver=driver, event_listener=TestListener())
driver.get(config.url)
a = driver.find_element(by=By.XPATH, value="//button")
a.click()
time.sleep(10000)

# return 0



# if __name__ == "__main__":
#     sys.exit(main(BrowingSessionConfig.parse_args()))
