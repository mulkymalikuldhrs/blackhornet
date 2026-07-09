"""Stub for missing agent_sandbox package."""

class Sandbox:
    def __init__(self, *args, **kwargs):
        pass

    async def create(self, *args, **kwargs):
        return self

    async def upload_file(self, *args, **kwargs):
        pass

    async def run_command(self, *args, **kwargs):
        return {"stdout": "", "stderr": ""}

    async def destroy(self):
        pass