import math
import os

import yaml
from ament_index_python.packages import get_package_share_directory


def construct_angle_radians(loader, node):
    value = loader.construct_scalar(node)
    return float(value)


def construct_angle_degrees(loader, node):
    return math.radians(construct_angle_radians(loader, node))


def _register_constructors():
    yaml.SafeLoader.add_constructor("!radians", construct_angle_radians)
    yaml.SafeLoader.add_constructor("!degrees", construct_angle_degrees)


def load_yaml(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    return load_yaml_abs(os.path.join(package_path, file_path))


def load_yaml_abs(absolute_file_path):
    _register_constructors()
    try:
        with open(absolute_file_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except OSError:
        return None
