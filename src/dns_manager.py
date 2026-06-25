import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Optional
from models import DNSProfile, DNSType
from core.toolbox import BaseToolBox, toolbox
from core.action_history import ActionHistory
from core.dns_actions import ApplyDNSProfile, BackupDNSConfig


class DNSManager:
    """DNS Manager using action-based system for safe, reversible changes.
    
    ActionHistory is lazily loaded on first use to avoid privileged operations
    during application startup.
    """
    
    def __init__(self, history_dir: str = "/var/lib/namban"):
        self.config_path = Path("/etc/systemd/resolved.conf")
        self.toolbox = toolbox
        self._history: Optional[ActionHistory] = None
        self.history_dir = history_dir
        self.current_profile: Optional[DNSProfile] = None
    
    @property
    def history(self) -> ActionHistory:
        """Lazily load ActionHistory on first access."""
        if self._history is None:
            self._history = ActionHistory(self.history_dir)
        return self._history

    def apply_profile(self, profile: DNSProfile) -> bool:
        """Apply DNS profile with automatic rollback capability.
        
        Records action in history for potential recovery if system crashes.
        """
        try:
            # Backup current config before applying
            backup_action = BackupDNSConfig(
                source=str(self.config_path),
                backup_path=str(Path(self.history_dir) / "resolved.conf.backup")
            )
            backup_data = backup_action.do(self.toolbox)
            self.history.record_action(backup_action, backup_data, profile.name)
            
            # Apply the DNS profile
            apply_action = ApplyDNSProfile(profile, str(self.config_path))
            action_data = apply_action.do(self.toolbox)
            self.history.record_action(apply_action, action_data, profile.name)
            
            self.current_profile = profile
            return True
        except Exception as e:
            print(f"Error applying profile: {e}")
            return False
    
    def restore_previous_config(self) -> bool:
        """Restore to previous DNS configuration from history."""
        return self.history.rollback_all_actions(self.toolbox)
    
    def restore_to_action(self, action_index: int) -> bool:
        """Restore to a specific point in action history."""
        return self.history.rollback_to_action(action_index, self.toolbox)
    
    def get_history(self) -> List[dict]:
        """Get full action history."""
        return self.history.get_history()
    
    def get_recent_actions(self, count: int = 10) -> List[dict]:
        """Get recent actions."""
        return self.history.get_recent_actions(count)
    
    def get_current_dns(self) -> List[str]:
        """Read current DNS servers from resolved.conf."""
        try:
            if not self.toolbox.exists(str(self.config_path)):
                return []
            
            content = self.toolbox.read(str(self.config_path))
            dns_servers = []
            
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('DNS='):
                    servers_str = line.replace('DNS=', '')
                    dns_servers.extend(servers_str.split())
            
            return dns_servers
        except Exception as e:
            print(f"Error reading DNS config: {e}")
            return []
    
    def clear_history(self) -> None:
        """Clear action history (for testing/cleanup)."""
        self.history.clear_history()

        return []