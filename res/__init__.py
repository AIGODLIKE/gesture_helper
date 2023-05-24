import os
from os.path import dirname, realpath

SRC_PATH = dirname(realpath(__file__))


def get_path(path):
    return os.path.join(SRC_PATH, path)


def register():
    ...


def unregister():
    ...
