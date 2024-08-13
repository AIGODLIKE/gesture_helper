import json
import os.path

__translate__ = {}


def __all_translate__() -> dict:
    res = dict()
    for i in __translate__.values():
        res.update(i)
    return res


def register():
    global __translate__
    folder = os.path.dirname(__file__)

    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith('.json'):
                try:
                    language = os.path.basename(root)
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data:
                            key = language, file[:-5]
                            __translate__[key] = data
                except Exception as e:
                    print("加载语言文件失败", e.args)


def unregister():
    global __translate__
    __translate__.clear()
