from .actions import BaseAction, action_pool
from .toolbox import BaseToolBox
from typing import TypedDict, Any, List
from pathlib import Path
import json

class FSManagerDataChanges(TypedDict):
    index: int
    action: str
    data: Any

class FSManagerData(TypedDict):
    changes: List[FSManagerDataChanges]

class FSManager:
    def __init__(self, data_dir: str, tool_box: BaseToolBox):
        self.data_dir = Path(data_dir)
        self.tool_box = tool_box


    def do_action(self, action: BaseAction):
        changes = action.do(self.tool_box)
        current_state = self._read_data()
        current_state['changes'].append(
            FSManagerDataChanges(
                action=action.__class__.__name__,
                data=changes,
                index=len(current_state['changes'])
            )
        )
        self._write_data(current_state)

    def undo_everything(self):
        history = self._read_data()
        for change in sorted(history['changes'], key=lambda x: x['index'], reverse=True):
            action_name = change['action']
            action_data = change['data']
            Action = action_pool.get(action_name)
            if Action:
                Action.undo(action_data, self.tool_box)
        self._write_data(self._base_data)


    @property
    def _data_file_path(self):
        return self.data_dir / 'changes'

    @property
    def _base_data(self):
        return FSManagerData(
                changes=[]
            )

    def _read_data(self) -> FSManagerData:
        file_path = self._data_file_path
        if not self.tool_box.exists(str(file_path)):
            return self._base_data
        
        raw = self.tool_box.read(str(file_path))
        return json.loads(raw)
    
    def _write_data(self, data: FSManagerData):
        file_path = self._data_file_path
        self.tool_box.write(str(file_path), json.dumps(data))