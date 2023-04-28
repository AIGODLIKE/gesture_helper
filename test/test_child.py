from collections.abc import Iterator

a = [[1, 2, 3, 4], [5, 6, 7, 8, [9, 10, 11]]]


class Test:
    def __init__(self, data):
        self.child = []
        if isinstance(data, Iterator):
            for i in data:
                if isinstance(i, Iterator):
                    self.child.append(Test(i))
                else:
                    self.child.append(i)

    def get_children(self):
        return [(i, *i.get_children()) for i in self.child]


t = Test(a)
print(t)
print(t.get_children())
