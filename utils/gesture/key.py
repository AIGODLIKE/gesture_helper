# 每一项手势的快捷键
# 不需要去记录每一个快捷键的位置
# 只需要记录快捷键用到的数据和空间
# 每次开启插件的时候从数据里面当场新建一些快捷键并填入缓存数据
# 使用临时快捷键来修改每一个快捷键的位置
import traceback


class GestureKey:
    @property
    def temp_key(self):
        return

    def draw_key(self, layout):
        ...

    def update_key(self):
        caller_name = traceback.extract_stack()[-2][2]
        print("update_key 被 {} 调用".format(caller_name))

    @staticmethod
    def load_key():
        ...

    @staticmethod
    def unload_key():
        ...
