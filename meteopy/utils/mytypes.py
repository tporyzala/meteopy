class TypedList(list):
    def append(self, item):
        if item in self:
            raise TypeError('item already included')
        return super().append(item)


def run_all(obj):
    obj._run_all = True
    return obj
