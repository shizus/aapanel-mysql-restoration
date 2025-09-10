#!/usr/bin/env python3
import paramiko
import re
import time
import getpass
import sys
from typing import Tuple, List, Optional

class ServerHealthCheck:
    def __init__(self, hostname: str, username: str, port: int = 22):
        self.hostname = hostname
        self.username = username
        self.port = port
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self, password: str) -> bool:
        """Establece la conexión SSH con el servidor."""
        try:
            self.ssh.connect(self.hostname, self.port, self.username, password)
            return True
        except Exception as e:
            print(f"Error de conexión: {str(e)}")
            return False

    def execute_command(self, command: str) -> Tuple[str, str, int]:
        """Ejecuta un comando y devuelve stdout, stderr y el código de salida."""
        stdin, stdout, stderr = self.ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        return stdout.read().decode(), stderr.read().decode(), exit_status

    def check_aapanel(self) -> bool:
        """Verifica el estado de aaPanel y lo inicia si está caído."""
        print("\nVerificando estado de aaPanel...")
        stdout, _, _ = self.execute_command("bt status")
        
        if "not running" in stdout.lower():
            print("aaPanel no está ejecutándose. Intentando iniciar...")
            _, _, exit_status = self.execute_command("bt start")
            if exit_status == 0:
                print("aaPanel iniciado correctamente.")
                return True
            else:
                print("Error al iniciar aaPanel.")
                return False
        else:
            print("aaPanel está ejecutándose correctamente.")
            return True

    def check_mysql_binlogs(self) -> Optional[str]:
        """
        Verifica los archivos binlog de MySQL y detecta inconsistencias.
        Retorna el último número de archivo válido o None si no hay problemas.
        """
        print("\nVerificando logs binarios de MySQL...")
        
        # Obtener lista de archivos binlog
        stdout, _, _ = self.execute_command("ls -1 /www/server/data/mysql-bin.* | grep -v index")
        files = stdout.strip().split('\n')
        
        # Extraer números de archivo
        numbers = []
        for f in files:
            match = re.search(r'mysql-bin\.(\d+)$', f)
            if match:
                numbers.append(int(match.group(1)))
        
        if not numbers:
            return None
            
        # Verificar secuencia
        numbers.sort()
        last_valid = numbers[-1]
        
        # Leer el index
        stdout, _, _ = self.execute_command("cat /www/server/data/mysql-bin.index")
        index_content = stdout.strip().split('\n')
        
        # Buscar referencias a archivos que no existen
        invalid_files = []
        for line in index_content:
            match = re.search(r'mysql-bin\.(\d+)$', line)
            if match:
                num = int(match.group(1))
                if num > last_valid:
                    invalid_files.append(num)
        
        if invalid_files:
            print(f"Se encontraron referencias a archivos inexistentes en mysql-bin.index: {invalid_files}")
            return str(last_valid)
        
        return None

    def fix_mysql_binlogs(self, last_valid: str) -> bool:
        """Corrige el archivo index de MySQL eliminando referencias inválidas."""
        print("\nCorrigiendo archivo mysql-bin.index...")
        
        # Hacer backup
        _, _, status = self.execute_command(f"cp /www/server/data/mysql-bin.index /www/server/data/mysql-bin.index.backup")
        if status != 0:
            print("Error al crear backup del archivo index.")
            return False

        # Crear archivo temporal sin las referencias inválidas
        command = f"""grep -v -E 'mysql-bin\\.[0-9]{{3,}}$' /www/server/data/mysql-bin.index | grep -v 'mysql-bin\\.{int(last_valid)+1}' > /www/server/data/mysql-bin.index.tmp"""
        _, _, status = self.execute_command(command)
        if status != 0:
            print("Error al crear archivo temporal.")
            return False

        # Reemplazar archivo original
        _, _, status = self.execute_command("mv /www/server/data/mysql-bin.index.tmp /www/server/data/mysql-bin.index")
        if status != 0:
            print("Error al reemplazar archivo index.")
            return False

        # Corregir permisos
        _, _, status = self.execute_command("chown mysql:mysql /www/server/data/mysql-bin.index && chmod 644 /www/server/data/mysql-bin.index")
        if status != 0:
            print("Error al corregir permisos.")
            return False

        print("Archivo index corregido correctamente.")
        return True

    def restart_mysql(self) -> bool:
        """Reinicia el servicio MySQL."""
        print("\nReiniciando MySQL...")
        _, _, status = self.execute_command("systemctl restart mysqld")
        if status == 0:
            print("MySQL reiniciado correctamente.")
            return True
        else:
            print("Error al reiniciar MySQL.")
            return False

    def check_mysql_status(self) -> bool:
        """Verifica el estado de MySQL."""
        stdout, _, _ = self.execute_command("systemctl status mysqld")
        return "active (running)" in stdout

    def close(self):
        """Cierra la conexión SSH."""
        self.ssh.close()

def main():
    # Solicitar datos de conexión
    hostname = input("Ingrese la dirección IP del servidor: ")
    port = int(input("Ingrese el puerto SSH (default 22): ") or "22")
    username = input("Ingrese el usuario (default: root): ") or "root"
    password = getpass.getpass("Ingrese la contraseña: ")

    # Crear instancia y conectar
    checker = ServerHealthCheck(hostname, username, port)
    if not checker.connect(password):
        print("No se pudo establecer conexión. Saliendo...")
        return

    try:
        # Verificar aaPanel
        checker.check_aapanel()

        # Verificar MySQL binlogs
        last_valid = checker.check_mysql_binlogs()
        if last_valid:
            response = input("\n¿Desea corregir el archivo index? (s/N): ").lower()
            if response == 's':
                if checker.fix_mysql_binlogs(last_valid):
                    checker.restart_mysql()
                    if checker.check_mysql_status():
                        print("\nTodo el proceso se completó correctamente.")
                    else:
                        print("\nMySQL no pudo iniciarse correctamente.")
            else:
                print("\nOperación cancelada por el usuario.")
        else:
            print("\nNo se encontraron problemas con los logs binarios.")

    finally:
        checker.close()

if __name__ == "__main__":
    main()
