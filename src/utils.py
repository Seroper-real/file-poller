import os
import re
import threading
import time
from urllib.parse import ParseResult, urlparse, urlunparse
import posixpath
from pathlib import Path, PurePath

def split(father_path: str, child_path: str) -> str:
    return child_path[len(os.path.commonprefix([father_path, child_path])):]

def is_ftp_path(path: str) -> bool:
    parsed: ParseResult = urlparse(path)
    return parsed.scheme.lower() == "ftp"

def is_smb_path(path: str) -> bool:
    parsed: ParseResult = urlparse(path)
    return parsed.scheme.lower() == "smb"

def is_standard_path(path: str) -> bool:
    return not is_smb_path(path) and not is_ftp_path(path)

def join_url_path(base_url: str, sub_path: str) -> str:
    parsed: ParseResult = urlparse(base_url)
    safe_sub_path: str = PurePath(sub_path).as_posix()
    joined_path: str = posixpath.join(parsed.path, safe_sub_path.lstrip("/"))
    full_url: str = urlunparse(parsed._replace(path=joined_path)) #TODO check type
    return full_url

def get_dir_list(path: str) -> list[str]:
    safe_path: str = PurePath(path).as_posix()
    parts: list[str] = [p for p in safe_path.strip("/").split("/") if p]  # remove empty elements
    # Heuristic: if last part has '.' (ex: 'file.txt') then we will consider it as a file
    if parts and '.' in parts[-1]:
        return parts[:-1]
    else:
        return parts

def wait_for_file_ready(path: str, timeout: int = 120, stable_time: int =2) -> bool:
    start: float = time.time()
    last_size: int = -1
    stable_since: float | None = None

    while time.time() - start < timeout:
        try:
            current_size: int = os.path.getsize(path)
            with open(path, 'rb'):
                pass  # try to read file

            if current_size == last_size:
                if stable_since is None:
                    stable_since = time.time()
                elif time.time() - stable_since >= stable_time:
                    return True  # File is readable without permission error
            else:
                stable_since = None
                last_size = current_size

        except (PermissionError, OSError):
            stable_since = None  # Not yet ready

        time.sleep(0.5)

    raise TimeoutError(f"Cannot access {path} after {timeout} seconds")

def path_is_matching(path: str, include: tuple[str, ...], exclude: tuple[str, ...]) -> bool:
    match_inc: bool = any(re.match(pattern, path) for pattern in include)
    match_exc: bool = any(re.match(pattern, path) for pattern in exclude)
    return match_inc and not match_exc

def find_files(directory: str, include: tuple[str, ...], exclude: tuple[str, ...]) -> list[str]:
    return [
        str(p)
        for p in Path(directory).rglob('*')
        if p.is_file() and path_is_matching(str(p),include, exclude)
    ]

def ask_bool(prompt: str, timeout: int =15) -> bool:
    result: dict[str, str | None]  = {"answer": None}
    def user_input() -> None:
        answer: str = input(prompt).strip().lower()
        if answer in ("y", "n"):
            result["answer"] = answer
    thread = threading.Thread(target=user_input)
    thread.daemon = True
    thread.start()
    thread.join(timeout)

    if result["answer"] == "y":
        return True
    elif result["answer"] == "n":
        return False
    else:
        print(f"No answer received in {timeout} seconds. Default: n")
        return False

def event_to_str(path: str | bytes | bytearray | memoryview) -> str:
    if isinstance(path, str):
        return path
    if isinstance(path,memoryview):
        return path.tobytes().decode('utf-8') #TODO CHECK ENCODING WINDOWS AND UNIX
    else:
        return path.decode('utf-8') #TODO CHECK ENCODING WINDOWS AND UNIX # at this point can only be bytes or bytearray
