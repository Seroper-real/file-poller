from command import CopyCommand
from watchdog.events import FileSystemEventHandler
import logging
import utils

class PollerHandler(FileSystemEventHandler):
    
    def __init__(self, producer, base_path, out_paths, matches, excludes, move=False):
        super().__init__()
        self.producer = producer
        self.base_path = base_path
        self.out_paths = tuple(out_paths)
        self.exts = tuple(matches)
        self.excludes = tuple(excludes)
        self.move = move

    def handle_event(self, is_directory, path):
        if not is_directory:
            diff = utils.split(self.base_path, path)
            if utils.path_is_matching(diff,self.exts,self.excludes):
                logging.info(f"Found file: {path}")
                self.producer.add(CopyCommand(base_path=self.base_path,out_paths=self.out_paths,event_path=path,remove_in=self.move))
            else:
                logging.info(f"Skip file: {path}")

    def on_created(self, event):
        self.handle_event(event.is_directory, event.src_path)

    def on_moved(self, event):
        self.handle_event(event.is_directory, event.dest_path)

    def manage_existing(self):
        path_list = utils.find_files(self.base_path,self.exts,self.excludes)
        for p in path_list:
            self.producer.add(CopyCommand(base_path=self.base_path,out_paths=self.out_paths,event_path=p,remove_in=self.move))
