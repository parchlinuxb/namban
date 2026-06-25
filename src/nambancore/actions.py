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
    def __init__(self, *actions:type[BaseAction]):
        self.actions = actions
    
    def get(self, name:str) -> type[BaseAction]:
        for action in self.actions:
            if action.__name__ == name:
                return action
        return None

# Import DNS actions to register them
from .dns_actions import ApplyDNSProfile, BackupDNSConfig

action_pool = ActionPool(WriteToFile, ApplyDNSProfile, BackupDNSConfig)