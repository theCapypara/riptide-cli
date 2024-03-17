import json
import os
import re
import time
from typing import Optional, Dict
from urllib import request

from importlib.metadata import distributions, distribution, Distribution
from packaging import version

from riptide.config.files import riptide_config_dir

REGEX_VERSION = re.compile(r"__version__\s*=\s*'(.*?)?'")


def check_for_update() -> Optional[Dict[str, str]]:
    # Check cache first
    cache_path = get_version_cache_path()
    try:
        with open(cache_path, 'r') as f:
            doc = json.load(f)
        if doc["time"] + 604_800 > time.time():  # 7 days
            cache_is_valid = True
            for pkg_name, cached_ver in doc["versions"].items():
                dist = distribution(pkg_name)
                if dist.version == cached_ver:
                    cache_is_valid = False
                    break
            if cache_is_valid:
                return doc["versions"]
        pass
    except Exception:
        pass

    versions = {}
    for pkg in distributions():
        if pkg.name.startswith("riptide-"):
            try:
                repo_url = _get_repo_url_for_egg(pkg)
                repo_url = repo_url.replace("github.com", "raw.githubusercontent.com")
                remote_setuppy = request.urlopen(f"{repo_url}release/setup.py").read().decode('utf-8')
                rematch = REGEX_VERSION.match(remote_setuppy.splitlines()[0])
                if rematch:
                    upstream_version = version.parse(rematch.group(1))
                    if upstream_version > version.parse(str(pkg.version)):
                        versions[pkg.name] = str(upstream_version)
            except Exception:
                pass
    try:
        with open(cache_path, 'w') as f:
            json.dump({'time': int(time.time()) , 'versions': versions}, f)
    except Exception:
        pass
    return versions


def _get_repo_url_for_egg(pkg: Distribution):
    return pkg.metadata['Home-page'].strip()


def get_version_cache_path():
    return os.path.join(riptide_config_dir(), 'versions.json')


if __name__ == '__main__':
    print(check_for_update())
