class TypedList(list):
    def append(self, item):
        if item in self:
            raise TypeError('item already included')
        return super().append(item)
