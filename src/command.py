from queue import Queue
import queue
import logging, threading, os, shutil, time
import utils
from pathlib import Path
from concurrent.futures import Future, ThreadPoolExecutor
from ftplib import FTP
from urllib.parse import ParseResult, urlparse

class Command:
    def execute(self) -> None: 
        raise NotImplementedError("Missing method execute()")

class Producer():
    def __init__(self) -> None:
        super().__init__()
        self.queue : Queue[Command] = Queue()
        self._lock = threading.Lock()
        self._command_set : set[Command] = set()

    def add(self, command: Command) -> None:
        with self._lock:
            if command in self._command_set:
                logging.debug(f"[Producer] Skipping duplicate command: {command}")
                return
            self.queue.put(command)
            self._command_set.add(command)
    
    def get(self,timeout: int = 1) -> Command:
        command : Command = self.queue.get(timeout=timeout)
        with self._lock:
            self._command_set.discard(command)
        return command
        

class Consumer(threading.Thread):
    def __init__(self, producer: Producer) -> None:
        super().__init__()
        self.producer: Producer = producer
        self.stop_requested: bool = False

    def run(self) -> None:
        
        while not self.stop_requested:
            try:
                cmd = self.producer.get(timeout=1)
                logging.debug(f"[Consumer] Executing command {cmd}")
                try:
                    cmd.execute()
                except Exception as e:
                    logging.error(f"[Consumer] Error executing commmand {cmd}: {e}")
            except queue.Empty:
                continue
        logging.debug("[Consumer] 'None' received, will exit")

    def stop(self) -> None:
        self.stop_requested = True


## CREATE CUSTOM COMMAND HERE
class CopyCommand(Command):
    def __init__(self, base_path: str, out_paths: list[str], event_path: str, remove_in: bool = False) -> None:
        self.base_path: str = base_path
        self.out_paths: tuple[str, ...] = tuple(out_paths)
        self.event_path: str = event_path
        self.remove_in: bool = remove_in

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CopyCommand):
            return False
        return (
            self.base_path == other.base_path and
            self.out_paths == other.out_paths and
            self.event_path == other.event_path and
            self.remove_in == other.remove_in
        )

    def __hash__(self) -> int:
        return hash((self.base_path, tuple(self.out_paths), self.event_path, self.remove_in))

    def __repr__(self) -> str:
        return (f"CopyCommand(base_path={self.base_path}, "
                f"out_paths={self.out_paths}, "
                f"event_path={self.event_path}, "
                f"remove_in={self.remove_in})")

    def execute(self) -> None:
        logging.info(f"[CopyCommand] from {self.base_path} to {self.out_paths} for {self.event_path}")
        diff: str = utils.split(self.base_path, self.event_path)
        logging.debug(f"Split Path: {diff}")
        futures: list[Future[None]] = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            for out_path in self.out_paths:
                future = executor.submit(self.copy, self.event_path, out_path, diff)
                futures.append(future)
        all_success: bool = True
        for f in futures:
            try:
                f.result() #Wait for end of all copys
            except Exception as e:
                all_success = False
                logging.error(f"[CopyCommand] Error in copy: {e}")
        if self.remove_in and all_success:
            self.delete(self.event_path)
        elif self.remove_in and not all_success:
            logging.warning(f"[CopyCommand] Errors found in copy. Not deleting {self.base_path}")
        logging.info(f"[CopyCommand] from {self.base_path} to {self.out_paths} for {self.event_path} finished")


    def copy(self,origin: str,base_out_path: str,diff_path: str) -> None:
        if utils.is_ftp_path(base_out_path):
            self.ftp_copy(origin,base_out_path,diff_path)
        elif utils.is_standard_path(base_out_path):
            self.base_copy(origin,base_out_path,diff_path)
        else: raise ValueError(f"Unsupported dest path {base_out_path}")

    def delete(self,origin: str) -> None:
        if os.path.exists(origin):
            os.remove(origin)
    
    def base_copy(self,origin: str,base_out_path: str,diff_path: str) -> None:
        dest_path: Path = Path(base_out_path) / diff_path.lstrip(r"\/")
        logging.debug(f"[CopyCommand] Full out Path: {dest_path}")

        origin_path: Path = Path(origin)
        max_retries: int = 15 #TODO make max_retries equal to path difference, for network folder creation
        wait_seconds: int = 3

        parent_folder: Path = dest_path.parent
        for attempt in range(max_retries):
            try:
                parent_folder.mkdir(parents=True, exist_ok=True) #In SMB/UNC this command will create only one folder, because of network latency
            except Exception as e:
                logging.warning(f"[CopyCommand] Attempt {attempt+1}: mkdir failed: {e}")
            if parent_folder.exists():
                break
            logging.info(f"[CopyCommand] Waiting for folder to appear: {parent_folder}")
            time.sleep(wait_seconds)
        else:
            logging.error(f"[CopyCommand] Folder {parent_folder} was not created after {max_retries} attempts.")
            return
        time.sleep(wait_seconds)
        utils.wait_for_file_ready(origin)
        logging.debug(f"Origin: {origin_path}, Dest: {dest_path}")
        if dest_path.exists():
            origin_size: int = origin_path.stat().st_size
            dest_size: int = dest_path.stat().st_size
            if origin_size == dest_size:
                logging.info(f"[CopyCommand] File existing. Skipping {origin_path}")
                return
            else:
                logging.debug(f"[CopyCommand] File exists but size differs (origin: {origin_size}, dest: {dest_size}), overwriting")

        shutil.copy(origin_path, dest_path)
        logging.info(f"[CopyCommand] Copied: {origin_path} to {dest_path}")

    def ftp_copy(self,origin: str,base_out_path: str,diff_path: str) -> None:
        parsed: ParseResult = urlparse(base_out_path)
        host: str | None = parsed.hostname
        port: int = parsed.port or 21
        user: str = parsed.username or 'anonymous'
        password: str = parsed.password or ''

        if host is None:
            raise ValueError(f"Invalid hostname in ftp input {base_out_path}")

        full_path: str = utils.join_url_path(base_out_path,diff_path)

        remote_dirs: list[str] = utils.get_dir_list(diff_path)
        remote_file: str = full_path.strip("/").split("/")[-1]

        with FTP() as ftp:
            logging.debug(f"[CopyCommand] Connecting to FTP: {host}:{port}")
            ftp.connect(host, port)
            ftp.login(user, password)
            logging.debug(f"[CopyCommand] Connected")
            base_dir: str = parsed.path
            if base_dir and base_dir != "/":
                ftp.cwd(base_dir)
            for directory in remote_dirs:
                if directory not in ftp.nlst():
                    try:
                        ftp.mkd(directory)
                    except Exception:
                        pass
                ftp.cwd(directory)
            logging.debug(f"[CopyCommand] Check if input file is available...")
            utils.wait_for_file_ready(origin)
            try:
                ftp.voidcmd("TYPE I")
                remote_size: int | None = ftp.size(remote_file)
            except Exception:
                remote_size = -1  # File not exist in server

            local_size: int = os.path.getsize(origin)

            if remote_size == local_size:
                logging.info(f"[CopyCommand] File existing. Skipping: {full_path}")
                return

            logging.debug(f"[CopyCommand] Start upload")
            with open(origin, "rb") as f:
                ftp.storbinary(f"STOR {remote_file}", f)
            logging.info(f"[CopyCommand] Uploaded: {full_path}")

