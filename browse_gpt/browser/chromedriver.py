import os
import undetected_chromedriver as uc


def start_driver() -> uc.Chrome:
    chrome_options = uc.ChromeOptions()
    return uc.Chrome(
        options=chrome_options,
        driver_executable_path=os.getenv("CHROMEDRIVER_PATH"),
        browser_executable_path=os.getenv("CHROME_PATH"),
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
