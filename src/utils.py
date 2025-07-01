import os
import re
import threading
import time
from urllib.parse import urlparse, urlunparse
import posixpath
from pathlib import Path, PurePath

def split(father_path, child_path):
    return child_path[len(os.path.commonprefix([father_path, child_path])):]

def is_ftp_path(path):
    parsed = urlparse(path)
    return parsed.scheme.lower() == "ftp"

def is_smb_path(path):
    parsed = urlparse(path)
    return parsed.scheme.lower() == "smb"

def is_standard_path(path):
    return not is_smb_path(path) and not is_ftp_path(path)

def join_url_path(base_url, sub_path):
    parsed = urlparse(base_url)
    safe_sub_path = PurePath(sub_path).as_posix()
    joined_path = posixpath.join(parsed.path, safe_sub_path.lstrip("/"))
    full_url = urlunparse(parsed._replace(path=joined_path))
    return full_url

def get_dir_list(path):
    safe_path = PurePath(path).as_posix()
    parts = [p for p in safe_path.strip("/").split("/") if p]  # rimuove elementi vuoti
    # Heuristic: se l'ultima parte ha un '.' (es: 'file.txt'), è un file
    if parts and '.' in parts[-1]:
        return parts[:-1]
    else:
        return parts

def wait_for_file_ready(path, timeout=120, stable_time=2):
    start = time.time()
    last_size = -1
    stable_since = None

    while time.time() - start < timeout:
        try:
            current_size = os.path.getsize(path)
            with open(path, 'rb'):
                pass  # Prova a leggerlo

            if current_size == last_size:
                if stable_since is None:
                    stable_since = time.time()
                elif time.time() - stable_since >= stable_time:
                    return True  # File stabile e leggibile
            else:
                stable_since = None
                last_size = current_size

        except (PermissionError, OSError):
            stable_since = None  # Non ancora pronto

        time.sleep(0.5)

    raise TimeoutError(f"Cannot access {path} after {timeout} seconds")

def path_is_matching(path, include, exclude):
    match_inc = any(re.match(pattern, path) for pattern in include)
    match_exc = any(re.match(pattern, path) for pattern in exclude)
    return match_inc and not match_exc

def find_files(directory, include, exclude):
    return [
        str(p)
        for p in Path(directory).rglob('*')
        if p.is_file and path_is_matching(str(p),include, exclude)
    ]

def ask_bool(prompt, timeout=15):
    result = {"answer": None}
    def user_input():
        answer = input(prompt).strip().lower()
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
