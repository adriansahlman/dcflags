# dcflags

Python package for initializing a dataclass with values from the command line and from environmental variables.

## Install

dcflags is available through pip
```shell
pip install dcflags
```

## Usage
```python
# main.py

import dataclasses
import dcflags


@dataclasses.dataclass
class Config:
    output: str
    workers: int = 1
    verbose: bool = False


if __name__ == "__main__":
    cfg = dcflags.parse(Config)
    print(cfg)
```
```
# help message
$ python main.py --help
usage: main.py [-h] [--output OUTPUT] [--workers WORKERS] [--verbose [VERBOSE]]

options:
  -h, --help           show this help message and exit
  --output OUTPUT      type: str, env: $OUTPUT
  --workers WORKERS    type: int, env: $WORKERS, default: 1
  --verbose [VERBOSE]  type: bool, env: $VERBOSE, default: False

# missing required argument
$ python main.py
usage: main.py [-h] [--output OUTPUT] [--workers WORKERS] [--verbose [VERBOSE]]
main.py: error: the following arguments are required: --output/$OUTPUT

# command line arguments
$ python main.py --output=file.txt
Config(output='file.txt', workers=1, verbose=False)

# env vars
$ OUTPUT=test.txt python main.py
Config(output='test.txt', workers=1, verbose=False)

# a bit of everything
$ OUTPUT=new.txt python main.py --verbose --workers=3
Config(output='new.txt', workers=3, verbose=True)
```
