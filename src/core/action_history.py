"""Action history management with persistent storage for system safety."""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from .actions import BaseAction, action_pool
from .toolbox import BaseToolBox


class ActionRecord:
    """Record of a single action execution."""
    
    def __init__(self, action_name: str, action_data: dict, timestamp: str = None, 
                 profile_name: str = None, index: int = 0):
        self.action_name = action_name
        self.action_data = action_data
        self.timestamp = timestamp or datetime.now().isoformat()
        self.profile_name = profile_name
        self.index = index
    
    def to_dict(self) -> dict:
        return {
            'index': self.index,
            'action': self.action_name,
            'data': self.action_data,
            'timestamp': self.timestamp,
            'profile_name': self.profile_name
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'ActionRecord':
        return ActionRecord(
            action_name=data.get('action'),
            action_data=data.get('data', {}),
            timestamp=data.get('timestamp'),
            profile_name=data.get('profile_name'),
            index=data.get('index', 0)
        )

from .toolbox import toolbox

class ActionHistory:
    """Manages action history with persistent storage and rollback capability.
    
    Uses BaseToolBox for privileged file operations, allowing non-root users
    to interact with /var/lib/namban through pkexec elevation.
    Implements lazy loading - history is only loaded when first accessed.
    """
    
    def __init__(self, history_dir: str = "/var/lib/namban"):
        self.history_dir = Path(history_dir)
        self.history_file = self.history_dir / "action_history.json"
        self.actions_list: Optional[List[ActionRecord]] = None
        self._initialized = False
    
    
    def _ensure_initialized(self) -> None:
        """Lazily initialize history on first access."""
        if not self._initialized:
            self.ensure_history_dir()
            self.load_history()
            self._initialized = True
    
    def ensure_history_dir(self) -> None:
        """Create history directory if it doesn't exist using toolbox."""
        history_dir_str = str(self.history_dir)
        
        # Check if directory exists
        if not toolbox.exists(history_dir_str):
            # For directory creation, we need to use a privileged operation
            # Create a marker file in the directory to ensure it exists
            marker_file = self.history_dir / ".namban_initialized"
            try:
                toolbox.write(str(marker_file), "")
            except Exception as e:
                print(f"Warning: Could not ensure history directory: {e}")
    
    def load_history(self) -> None:
        """Load action history from disk using toolbox."""
        try:
            history_file_str = str(self.history_file)
            
            if toolbox.exists(history_file_str):
                content = toolbox.read(history_file_str)
                data = json.loads(content)
                self.actions_list = [ActionRecord.from_dict(record) for record in data]
            else:
                self.actions_list = []
        except (json.JSONDecodeError, IOError, Exception) as e:
            print(f"Warning: Could not load history: {e}")
            self.actions_list = []
    
    def save_history(self) -> None:
        """Save action history to disk using toolbox."""
        try:
            self._ensure_initialized()
            history_file_str = str(self.history_file)
            
            data = [record.to_dict() for record in self.actions_list]
            toolbox.write(history_file_str, json.dumps(data, indent=2))
        except IOError as e:
            print(f"Error: Could not save history: {e}")
    
    def record_action(self, action: BaseAction, action_data: dict, 
                     profile_name: Optional[str] = None) -> None:
        """Record a completed action."""
        self._ensure_initialized()
        
        record = ActionRecord(
            action_name=action.__class__.__name__,
            action_data=action_data,
            profile_name=profile_name,
            index=len(self.actions_list) if self.actions_list else 0
        )
        self.actions_list.append(record)
        self.save_history()
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get all action history records."""
        self._ensure_initialized()
        return [record.to_dict() for record in self.actions_list]
    
    def get_recent_actions(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent N actions."""
        self._ensure_initialized()
        return [record.to_dict() for record in self.actions_list[-count:]]
    
    def get_actions_by_profile(self, profile_name: str) -> List[Dict[str, Any]]:
        """Get all actions for a specific profile."""
        self._ensure_initialized()
        return [record.to_dict() for record in self.actions_list 
                if record.profile_name == profile_name]
    
    def clear_history(self) -> None:
        """Clear all action history."""
        self._ensure_initialized()
        self.actions_list = []
        self.save_history()

    
    def rollback_all_actions(self, toolbox: BaseToolBox) -> bool:
        """Rollback all recorded actions in reverse order."""
        try:
            self._ensure_initialized()
            
            # Process actions in reverse order
            for record in reversed(self.actions_list):
                action_name = record.action_name
                action_data = record.action_data
                
                Action = action_pool.get(action_name)
                if Action:
                    Action.undo(action_data, toolbox)
            
            # Clear history after successful rollback
            self.clear_history()
            return True
        except Exception as e:
            print(f"Error during rollback: {e}")
            return False
    
    def rollback_to_action(self, index: int, toolbox: BaseToolBox) -> bool:
        """Rollback to a specific action (undo everything after it)."""
        try:
            self._ensure_initialized()
            
            # Find the action with the given index
            target_index = -1
            for i, record in enumerate(self.actions_list):
                if record.index == index:
                    target_index = i
                    break
            
            if target_index == -1:
                print(f"Action with index {index} not found")
                return False
            
            # Rollback all actions after the target
            for record in reversed(self.actions_list[target_index + 1:]):
                action_name = record.action_name
                action_data = record.action_data
                
                Action = action_pool.get(action_name)
                if Action:
                    Action.undo(action_data, toolbox)
            
            # Remove the undone actions from history
            self.actions_list = self.actions_list[:target_index + 1]
            self.save_history()
            return True
        except Exception as e:
            print(f"Error during targeted rollback: {e}")
            return False
