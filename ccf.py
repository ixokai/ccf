"""
Cascading Configuration Files


This is a very simple system for reading vaguely INI-like configuration files. Now, the first question any sane
person should ask is: why the hell did I write this, even if its only like 90 lines?

There's ConfigParser in the stdlib, and endless other options on PyPi. Most are better written, many more
featureful, but by the time I got halfway through the list I was frustrated with none quite doing what I wanted,
so gave up.

So we have this.

The design goals are twofold:
    1) Python 3 only
    2) INI-ish, for ease of use by the non-technicals
    3) 'Cascading' configuration files, thus the name; so if file 1 has [database] username=foo, but file 2 has
       [database] username=bar, then reading cfg.database.username would return 'bar'. The system is designed for
       situations where you read multiple files and where later ones override defaults in earlier ones.
    4) To use Python 3-style 'str.format()' interpolation, because I use it elsewhere in my app and I want users to
       need to learn only one interpolation language.

This is a VERY SIMPLE LIBRARY that I threw together, and may be of no interest to anyone else, ever. I intend on
expanding its functionality over time, but if anyone else (shock) has a use for it, keep the design goals above in
mind. I don't have any intention of changing it against those goals.

Example usage:

myapp.conf
```ini
[database]
connection = mongodb+srv://{database[username]}:{database[password}@myservice.mongodb.net/test
```

secrets.conf
```
[database]
username = foo
password = bar
```

db.py
```python
from ccf import ConfigReader
cfg = ConfigReader(["myapp.conf", "secrets.conf"])
print("Connect to: {cfg.database.connection}".format(cfg=cfg)
"""

from typing import Union, List
from collections import OrderedDict


__VERSION__ = "0.0.1"


class _OptionWrapper:
    def __init__(self, current, context):
        self.current = current
        self.context = context

    def __getattr__(self, key):
        value = self.current[key]
        if isinstance(value, OrderedDict):
            return _OptionWrapper(value, self.context)
        else:
            return value.format(**self.context)


class ConfigReader:
    def __init__(self, cfg_files: Union[str, List[str]]):
        context = OrderedDict()

        if isinstance(cfg_files, list):
            ...
        elif isinstance(cfg_files, str):
            cfg_files = [cfg_files]
        else:
            raise TypeError("For argument cfg_files, got {!r} and expected a string or list of strings.".format(cfg_files))

        for cfg_file in cfg_files:
            with open(cfg_file, "rU") as cp:
                context = self._parse(context, cp)

        self.context = context

    @staticmethod
    def _build_section(context: OrderedDict, section: str):
        sections = section.split(".")
        current = context

        for section in sections:
            section = section.strip().lower()
            if section not in current:
                current[section] = OrderedDict()

            current = current[section]

        return current

    def _parse(self, config: OrderedDict, cp: file):
        section = ""
        context = config

        for line in cp:
            line = line.strip()

            if line.startswith("#"):
                continue

            if line.startswith("["):
                section = line[line.find("[")+1:line.rfind("]")]

                context = self._build_section(context, section)
                continue

            if not section:
                continue

            if line.strip():
                name, value = (x.strip() for x in line.split("=", 1))

                if value.isnumeric():
                    value = int(value)
                elif value in ("True", "False", "None"):
                    value = eval(value)
                elif "." in value and value.replace(".", "").isnumeric():
                    value = float(value)

                context[name] = value

        return config

    def __getattr__(self, key):
        return _OptionWrapper(self.context[key], self.context)
