import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Optional
from models import DNSProfile, DNSType
from nambancore.toolbox import BaseToolBox, toolbox
from nambancore.action_history import ActionHistory
from nambancore.dns_actions import ApplyDNSProfile, BackupDNSConfig


class DNSManager:
    """DNS Manager using action-based system for safe, reversible changes.
    
    ActionHistory is lazily loaded on first use to avoid privileged operations
    during application startup.
    """
    
    def __init__(self, history_dir: str = "/var/lib/namban"):
        self.dropin_path = Path("/etc/systemd/resolved.conf.d/namban.conf")
        self.base_config_path = Path("/etc/systemd/resolved.conf")
        self.config_path = self.dropin_path
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
        """Read current DNS servers directly without requiring root privileges."""
        try:
            target_path = self.dropin_path if self.dropin_path.exists() else self.base_config_path
            if not target_path.exists():
                return []
            
            with open(target_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            dns_servers = []
            for line in content.splitlines():
                line = line.strip()
                if line.startswith('DNS='):
                    servers_str = line.split('=', 1)[1]
                    for s in servers_str.split():
                        # Strip DoT SNI suffix (#hostname) for user-friendly display
                        dns_servers.append(s.split('#')[0])
            
            return dns_servers
        except Exception as e:
            print(f"Error reading DNS config: {e}")
            return []
    
    def clear_history(self) -> None:
        """Clear action history (for testing/cleanup)."""
        self.history.clear_history()