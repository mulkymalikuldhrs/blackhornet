"""Stub for missing agent package."""

class MemoryProvider:
    def __init__(self, *args, **kwargs):
        pass

    async def store(self, *args, **kwargs):
        return True

    async def retrieve(self, *args, **kwargs):
        return None

    async def search(self, *args, **kwargs):
        return []