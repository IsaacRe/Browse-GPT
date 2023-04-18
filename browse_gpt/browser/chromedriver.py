import os
import os.path
import undetected_chromedriver as uc
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

EXTENSION_DIR = "chrome-extension"


def start_driver(extension_name: str = None) -> uc.Chrome:
    chrome_options = uc.ChromeOptions()
    dc = DesiredCapabilities().CHROME
    dc["pageLoadStrategy"] = "none"
    if extension_name:
        ext_path = os.path.join(os.getcwd(), EXTENSION_DIR, extension_name)
        chrome_options.add_argument(f"--load-extension={ext_path}")
        chrome_options.add_argument(f"--disable-web-security")  # allow cross-origin request to our server
    return uc.Chrome(
        options=chrome_options,
        driver_executable_path=os.getenv("CHROMEDRIVER_PATH"),
        browser_executable_path=os.getenv("CHROME_PATH"),
        desired_capabilities=dc,
    )


def get_annotator(driver: uc.Chrome) -> "PageAnnotator":
    return PageAnnotator(driver=driver)


class PageAnnotator:
    def __init__(self, driver: uc.Chrome):
        self.driver = driver
        self.modified_elem_style = {}
        
    def set_style(self, element, style):
        self.driver.execute_script("arguments[0].setAttribute('style', arguments[1]);",
                          element, style)

    def highlight(self, element, color: str):
        self.modified_elem_style[element] = element.get_attribute('style')
        self.set_style(element, f"border: 10px solid {color};")
        
    def clear(self):
        for e, s in self.modified_elem_style.items():
            self.set_style(e, s)
        self.modified_elem_style = {}
