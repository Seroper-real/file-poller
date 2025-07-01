import logging
import json
import os
import time
from typing import Any, cast
from watchdog.observers import Observer
from poller_handler import PollerHandler
from command import Producer,Consumer
import utils

def load_config(path: str='config.json') -> dict[str, Any]:
    with open(path, 'r') as file:
        return cast(dict[str, Any], json.load(file))

def check_path(path: str) -> None:
    if utils.is_standard_path(path) and not os.path.exists(path):
        raise Exception(f"Path {path} does not exist. Check your configuration")

def setup_debugger(config: dict[str, Any]) -> None:
    conf_level: str = config['debug']['level']
    level: int = logging.ERROR
    if conf_level == "DEBUG":
        level = logging.DEBUG
    elif conf_level == "INFO":
        level = logging.INFO
    elif conf_level == "WARNING":
        level = logging.WARNING
    logging.basicConfig(level=level, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


if __name__ == "__main__":
    config: dict[str, Any] = load_config()
    setup_debugger(config)

    #Setup queue for async copy of files
    producer: Producer = Producer()
    consumer: Consumer = Consumer(producer)
    consumer.start()
    logging.debug(f"Consumer started")

    observers: list[Any] = []
    handlers: list[PollerHandler] = []
    for polling in config['pollings']:
        path: dict[str, Any] = polling['path']
        check_path(path['in'])
        for out_path in path['out']:
            check_path(out_path)
        event_handler = PollerHandler(producer=producer,base_path=path['in'],out_paths=path['out'],matches=polling['matches'],excludes=polling['ignores'], move=polling['move'])
        handlers.append(event_handler)
        observer = Observer()
        observer.schedule(event_handler, path['in'], recursive=polling['recursive'])
        observers.append(observer)
        logging.info(f"Monitoring configured on path: {path['in']}")
    
    for observer in observers:
        observer.start()
    logging.info(f"Monitorings started")
    

    ans: bool = utils.ask_bool("Do you want to search and process already existing file in polling paths? [y/n]")
    if ans:
        for handler in handlers:
            handler.manage_existing()

    try:
        logging.info(f"Waiting for files... Press CTRL+C to exit")
        while any(o.is_alive() for o in observers) or consumer.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info(f"Received CTRL+C, waiting for pending copies to be finished...")
        for observer in observers:
            observer.stop()
        consumer.stop()
    for observer in observers:
        observer.join()
    consumer.join()
