"""
Server Health Check Tool
-----------------------
A tool to monitor and fix common issues with aaPanel and MySQL binary logs.
"""
import paramiko
import re
import getpass
from typing import Tuple, Optional

class ServerHealthCheck:
    def __init__(self, hostname: str, username: str, port: int = 22):
        self.hostname = hostname
        self.username = username
        self.port = port
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self, password: str) -> bool:
        """Establishes SSH connection to the server."""
        try:
            self.ssh.connect(self.hostname, self.port, self.username, password)
            return True
        except Exception as e:
            print(f"Connection error: {str(e)}")
            return False

    def execute_command(self, command: str) -> Tuple[str, str, int]:
        """Executes a command and returns stdout, stderr and exit code."""
        stdin, stdout, stderr = self.ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        return stdout.read().decode(), stderr.read().decode(), exit_status

    def check_aapanel(self) -> bool:
        """Verifies aaPanel status and starts it if it's down."""
        print("\nChecking aaPanel status...")
        stdout, _, _ = self.execute_command("bt status")
        
        if "not running" in stdout.lower():
            print("aaPanel is not running. Attempting to start...")
            _, _, exit_status = self.execute_command("bt start")
            if exit_status == 0:
                print("aaPanel started successfully.")
                return True
            else:
                print("Error starting aaPanel.")
                return False
        else:
            print("aaPanel is running correctly.")
            return True

    def check_mysql_binlogs(self) -> Optional[str]:
        """
        Verifies MySQL binlog files and detects inconsistencies.
        Returns the last valid file number or None if no problems found.
        """
        print("\nChecking MySQL binary logs...")
        
        stdout, _, _ = self.execute_command("ls -1 /www/server/data/mysql-bin.* | grep -v index")
        files = stdout.strip().split('\n')
        
        numbers = []
        for f in files:
            match = re.search(r'mysql-bin\.(\d+)$', f)
            if match:
                numbers.append(int(match.group(1)))
        
        if not numbers:
            return None
            
        numbers.sort()
        last_valid = numbers[-1]
        
        stdout, _, _ = self.execute_command("cat /www/server/data/mysql-bin.index")
        index_content = stdout.strip().split('\n')
        
        invalid_files = []
        for line in index_content:
            match = re.search(r'mysql-bin\.(\d+)$', line)
            if match:
                num = int(match.group(1))
                if num > last_valid:
                    invalid_files.append(num)
        
        if invalid_files:
            print(f"Found references to non-existent files in mysql-bin.index: {invalid_files}")
            return str(last_valid)
        
        return None

    def fix_mysql_binlogs(self, last_valid: str) -> bool:
        """Fixes MySQL index file by removing invalid references."""
        print("\nFixing mysql-bin.index file...")
        
        _, _, status = self.execute_command(f"cp /www/server/data/mysql-bin.index /www/server/data/mysql-bin.index.backup")
        if status != 0:
            print("Error creating index file backup.")
            return False

        # Ensure last_valid is zero-padded to 6 digits (e.g., 000797)
        next_valid_padded = f"{int(last_valid) + 1:06d}"
        command = (
            f"grep -v -E 'mysql-bin\\.[0-9]{{6,}}$' /www/server/data/mysql-bin.index | "
            f"grep -v 'mysql-bin.{next_valid_padded}' > /www/server/data/mysql-bin.index.tmp"
        )
        _, _, status = self.execute_command(command)
        if status != 0:
            print("Error creating temporary file.")
            return False

        _, _, status = self.execute_command("mv /www/server/data/mysql-bin.index.tmp /www/server/data/mysql-bin.index")
        if status != 0:
            print("Error replacing index file.")
            return False

        _, _, status = self.execute_command("chown mysql:mysql /www/server/data/mysql-bin.index && chmod 644 /www/server/data/mysql-bin.index")
        if status != 0:
            print("Error fixing permissions.")
            return False

        print("Index file fixed successfully.")
        return True

    def restart_mysql(self) -> bool:
        """Restarts MySQL service."""
        print("\nRestarting MySQL...")
        _, _, status = self.execute_command("systemctl restart mysqld")
        if status == 0:
            print("MySQL restarted successfully.")
            return True
        else:
            print("Error restarting MySQL.")
            return False

    def check_mysql_status(self) -> bool:
        """Verifies MySQL status."""
        stdout, _, _ = self.execute_command("systemctl status mysqld")
        return "active (running)" in stdout

    def close(self):
        """Closes SSH connection."""
        self.ssh.close()
