# file-poller

**filepoller** is a lightweight utility based on python library *watchdog*, that monitors configured directories for specific files and automatically copies or moves them to other destinations.

It's ideal for backups and automating file workflows between local folders and remote targets (with FTP)

## Features

- Monitor multiple input directories
- Match file paths using regular expressions
- Explicit ignore file paths with regular expression
- Recursive subfolder support, it will replicate folder structure on destination
- Won't copy if target file already exist and has the same dimension as source file
- FTP support
- Optional check ahd manage for already existing file

## Download

Download from [release page](https://github.com/Seroper-real/file-poller/releases)

## Configuration

### config.json

In execution directory must be present a configuration file called `config.json` with the following structure:

- `pollings[]`: list of active pollings
  - `path.in`: input folder to monitor, single value
  - `path.out[]`: list of output destinations (local folders or FTP URLs)
  - `matches[]`: regex patterns to include files (ex. `.*\\.mp4$` on windows, for grab only files with .mp4 extensions)
  - `ignores[]`: regex patterns to exclude files or directories, useful to exclude sub-folder (ex. `\\\\.*_tmp\\\\` on windows, will exclude any sub-folder named *_tmp)
  - `move`: `true` to move input files, `false` to copy (`move: true` will delete original file after all copies are done)
  - `recursive`: `true` to include subfolders, `false` to monitor only the base path
- `debug.level`: logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

You can use a `config-env-example.json` as a reference template.

### Ftp support

You can define a remote ftp path by using the connection string to configure all parameters

```
ftp://username:password@server.com:21/base/path
```

## Quick start for local run

Create your own config.json as mentioned above.

Install requirements specified in requirements.txt

```bash
pip install -r requirements.txt
```

Launch the script (you must have config.json in your working directory):

```bash
py src/main.py
```

### Requirements

- Python 3.13.3+

## Note

> ⚠️ **Never commit your actual `config.json` with sensitive data to a public repository**
