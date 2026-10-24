from .toolbox import BaseToolBox


class BaseAction:
    def do(self, toolbox: BaseToolBox) -> dict:
        raise NotImplementedError

    @classmethod
    def undo(cls, state: dict, toolbox: BaseToolBox):
        raise NotImplementedError


class WriteToFile(BaseAction):
    def __init__(self, destination:str, body:str):
        self.destination = destination
        self.body = body
    
    def do(self, toolbox: BaseToolBox):
        dest_before = None
        if toolbox.exists(self.destination):
            dest_before = toolbox.read(self.destination)
        toolbox.write(self.destination, self.body)
        return {
            'dest_before': dest_before,
            'destination': self.destination
        }

    @classmethod
    def undo(cls, state:dict, toolbox: BaseToolBox):
        dest_before = state.get('dest_before')
        destination = state.get('destination')
        if dest_before is not None:
            toolbox.write(destination, dest_before)
        else:
            toolbox.remove(destination)

class ActionPool:
    def get(self, name:str) -> type[BaseAction]:
        # Imported here, not at module top: dns_actions imports this module
        from . import dns_actions  # noqa: F401  registers the DNS actions
        return next((a for a in BaseAction.__subclasses__() if a.__name__ == name), None)

action_pool = ActionPool()
