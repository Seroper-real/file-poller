from command import CopyCommand, Producer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
import logging
import utils

class PollerHandler(FileSystemEventHandler):
    
    def __init__(self, producer: Producer, base_path: str, out_paths: list[str], matches: list[str], excludes: list[str], move: bool = False) -> None:
        super().__init__()
        self.producer: Producer = producer
        self.base_path: str = base_path
        self.out_paths: list[str] = out_paths
        self.exts: tuple[str, ...] = tuple(matches)
        self.excludes: tuple[str, ...] = tuple(excludes)
        self.move: bool = move

    def handle_event(self, is_directory: bool, path: bytes | str) -> None:
        if not is_directory:
            path_str: str = utils.event_to_str(path)
            diff: str = utils.split(self.base_path, path_str)
            if utils.path_is_matching(diff,self.exts,self.excludes):
                logging.info(f"Found file: {path_str}")
                self.producer.add(CopyCommand(base_path=self.base_path,out_paths=self.out_paths,event_path=path_str,remove_in=self.move))
            else:
                logging.info(f"Skip file: {path_str}")

    def on_created(self, event: FileSystemEvent) -> None:
        self.handle_event(event.is_directory, event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        self.handle_event(event.is_directory, event.dest_path)

    def manage_existing(self) -> None:
        path_list: list[str] = utils.find_files(self.base_path,self.exts,self.excludes)
        for p in path_list:
            self.producer.add(CopyCommand(base_path=self.base_path,out_paths=self.out_paths,event_path=p,remove_in=self.move))
