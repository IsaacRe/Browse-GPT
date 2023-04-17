import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import time
from typing import Tuple
import concurrent.futures
from selenium.webdriver.support.ui import WebDriverWait
from undetected_chromedriver import Chrome
from datetime import datetime
import json
import multiprocessing as mp
from typing import List

from browse_gpt.db import DBClient
from browse_gpt.browser.chromedriver import start_driver
from browse_gpt.config import ParsePageConfig

logger = logging.getLogger(__name__)


def wait_for_request(port: int, q: mp.Queue):
    httpd = HTTPServer(("localhost", port), RequestHandler)
    logger.info(f"Waiting for next browser request {httpd.server_port}")
    httpd.handle_request()
    logger.info(RequestHandler.browser_response_stack)
    q.put_nowait(RequestHandler.browser_response_stack[0])


def wait_for_page_load(driver: Chrome, poll_interval: float = 0.1) -> Tuple[float, str]:
    source = None
    t = 0
    while source != driver.page_source:
        source = driver.page_source
        t += poll_interval
        time.sleep(poll_interval)
    return t, source


def wait_for_page_ready(driver: Chrome):
    t = datetime.utcnow()
    WebDriverWait(driver, 10).until(is_ready)
    return (datetime.utcnow() - t).total_seconds(), driver.page_source


def is_ready(driver: Chrome) -> bool:
    return driver.execute_script('return document.readyState') == 'complete'


def main(config: ParsePageConfig):
    driver.get("https://fandango.com")  # dont block until page load so that we can get user
    
    # httpd = HTTPServer(("localhost", 8012), RequestHandler)
    # httpd2 = HTTPServer(("localhost", 8013), RequestHandler)
    port = 8012
    # wait_c = asyncio.create_task(wait_for_request(httpd))
    # wait_c2 = asyncio.create_task(wait_for_request(httpd2))
    # process_c = asyncio.create_task(process_page('hi'))
    # process_c2 = asyncio.create_task(process_page('hello'))


    futures = [pool.submit(wait_for_request, port, q), pool.submit(process_page, 200)]
    done, running = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)
    #as_completed = concurrent.futures.as_completed(futures)
    #first = next(as_completed)  # wait for first completed job

    logger.info(q.get_nowait())

    return 0


def process_page(t: int):
        wait_for_page_ready(driver)
        time.sleep(t)
        return 1


class RequestHandler(BaseHTTPRequestHandler):
    browser_response_stack = []

    def do_GET(self):
        self.send_response(200)

    def do_POST(self):
        data_string = self.rfile.read(int(self.headers['Content-Length']))

        data = json.loads(data_string)
        logger.info(data)
        self.send_response(200)

        self.browser_response_stack.append(data)


if __name__ == "__main__":
    driver = start_driver()
    
    pool = concurrent.futures.ProcessPoolExecutor(max_workers=2)
    mngr = mp.Manager()
    q = mngr.Queue()
    sys.exit(main(ParsePageConfig.parse_args()))
