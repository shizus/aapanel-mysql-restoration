"""Main entry point for the Server Health Check Tool."""
from .checker import ServerHealthCheck
import getpass
import argparse

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Server Health Check Tool for aaPanel and MySQL')
    parser.add_argument('-H', '--host', help='Server IP address or hostname')
    parser.add_argument('-p', '--port', type=int, default=22, help='SSH port (default: 22)')
    parser.add_argument('-u', '--user', default='root', help='SSH username (default: root)')
    parser.add_argument('-P', '--password', help='SSH password (not recommended, use interactive mode instead)')
    parser.add_argument('-y', '--yes', action='store_true', help='Automatically answer yes to all prompts')
    return parser.parse_args()

def main():
    """Main function that runs the server health check."""
    args = parse_args()
    
    # If any required parameter is missing, switch to interactive mode
    if not all([args.host, args.user]):
        print("Running in interactive mode...")
        hostname = args.host or input("Enter server IP address: ")
        port = args.port or int(input("Enter SSH port (default 22): ") or "22")
        username = args.user or input("Enter username (default: root): ") or "root"
        password = args.password or getpass.getpass("Enter password: ")
    else:
        hostname = args.host
        port = args.port
        username = args.user
        password = args.password or getpass.getpass("Enter password: ")

    # Create instance and connect
    checker = ServerHealthCheck(hostname, username, port)
    if not checker.connect(password):
        print("Could not establish connection. Exiting...")
        return

    try:
        # Check aaPanel
        checker.check_aapanel()

        # Check MySQL binlogs
        last_valid = checker.check_mysql_binlogs()
        if last_valid:
            if args.yes:
                response = 'y'
            else:
                response = input("\nDo you want to fix the index file? (y/N): ").lower()
            if response == 'y':
                if checker.fix_mysql_binlogs(last_valid):
                    checker.restart_mysql()
                    if checker.check_mysql_status():
                        print("\nProcess completed successfully.")
                    else:
                        print("\nMySQL could not start properly.")
            else:
                print("\nOperation cancelled by user.")
        else:
            print("\nNo issues found with binary logs.")

    finally:
        checker.close()

if __name__ == "__main__":
    main()
