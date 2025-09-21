# Server Health Check Tool

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/yourusername/server-health-check/graphs/commit-activity)

A Python tool to automatically monitor and fix common issues with aaPanel and MySQL binary logs on remote servers.

## Problem Statement

When managing servers with aaPanel and MySQL, several common issues can occur:

1. aaPanel services might stop unexpectedly
2. MySQL binary logs can become inconsistent, particularly when the `mysql-bin.index` file references non-existent binary log files
3. These issues often require manual intervention and knowledge of specific commands

This tool automates the detection and resolution of these problems, reducing downtime and simplifying server maintenance.

## Features

- Remote server connection via SSH
- Automatic aaPanel service status check and restart
- MySQL binary log verification and repair
- Automatic backup before any critical changes
- Interactive prompts for potentially dangerous operations

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/server-health-check.git
cd server-health-check

# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate the virtual environment
poetry shell
```

## Usage

### Interactive Mode
```bash
poetry run server-health-check
```

The tool will prompt you for:
- Server IP address
- SSH port (default: 22)
- Username (default: root)
- Password

### Command Line Mode
```bash
poetry run server-health-check -H hostname -p port -u username [-y]
```

Options:
- `-H, --host`: Server IP address or hostname
- `-p, --port`: SSH port (default: 22)
- `-u, --user`: SSH username (default: root)
- `-P, --password`: SSH password (not recommended, use interactive mode instead)
- `-y, --yes`: Automatically answer yes to all prompts

Example:
```bash
poetry run server-health-check -H example.com -p 22 -u root -y
```

## How it Works

1. **SSH Connection**: Establishes a secure connection to your server
2. **aaPanel Check**: 
   - Verifies if aaPanel services are running
   - Automatically starts them if they're down
3. **MySQL Binary Log Verification**:
   - Scans existing binary log files
   - Checks for inconsistencies in mysql-bin.index
   - Creates a backup of the index file
   - Removes invalid references
   - Restarts MySQL if necessary

## Prevention

The MySQL binary log inconsistency issue typically occurs due to:

1. **Unexpected Server Shutdowns**:
   - Power failures
   - System crashes
   - Force-stopping MySQL without proper shutdown
   
2. **Disk Space Issues**:
   - When the disk gets full, MySQL might fail to write new binary logs
   - Automatic cleanup scripts might delete binary logs but fail to update the index
   
3. **Manual File Management**:
   - Manually deleting binary log files without using `PURGE BINARY LOGS`
   - Direct manipulation of the binary log directory

To prevent these issues:

1. **Proper MySQL Shutdown**:
   - Always use proper shutdown commands (`systemctl stop mysqld` or `service mysql stop`)
   - Implement UPS for power failure protection
   
2. **Binary Log Management**:
   - Use MySQL's built-in commands for log rotation:
     ```sql
     PURGE BINARY LOGS TO 'mysql-bin.000XXX';
     -- or
     PURGE BINARY LOGS BEFORE DATE(NOW() - INTERVAL 7 DAY);
     ```
   - Configure automatic log rotation in my.cnf:
     ```ini
     expire_logs_days = 7
     ```
   
3. **Disk Space Monitoring**:
   - Set up disk space monitoring
   - Configure alerts when disk usage exceeds 80%
   - Regularly archive old binary logs

4. **Regular Backups**:
   - Maintain regular backups of your databases
   - Test backup restoration procedures
   - Keep backups on separate storage

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
