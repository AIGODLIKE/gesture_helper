import logging
import os


def log_path():
    folder = os.path.join(os.environ["TMP"], r"blender")
    if not os.path.isdir(folder):
        os.makedirs(folder)

    log_file_path = os.path.join(folder, "gesture_helper.log")
    return log_file_path


log = logging.getLogger("gesture_helper")  # 设置logger可输出日志级别范围

_console_handler = logging.StreamHandler()  # 添加日志文件handler，用于输出日志到文件中
log.setLevel(logging.DEBUG)  # 添加控制台handler，用于输出日志到控制台
log.addHandler(_console_handler)  # 将handler添加到日志器中

_formatter = logging.Formatter('%(asctime)s - %(name)s %(levelname)s-0 %(message)s')  # 设置格式并赋予handler
_console_handler.setFormatter(_formatter)

_file_handler = logging.FileHandler(filename=log_path(), encoding='UTF-8')  # 设置日志输出路径
log.addHandler(_file_handler)
_file_handler.setFormatter(_formatter)
