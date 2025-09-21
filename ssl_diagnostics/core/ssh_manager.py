#!/usr/bin/env python3
"""
SSH Manager - Manejo centralizado de conexiones SSH
"""

import paramiko
import json
import os
from datetime import datetime
from typing import Optional, Tuple

class SSHManager:
    def __init__(self, config_file: str = "ssl_diagnostics/.env"):
        self.ssh: Optional[paramiko.SSHClient] = None
        self.config = self._load_config(config_file)
        
    def _load_config(self, config_file: str) -> dict:
        """Cargar configuración desde archivo"""
        config = {}
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        config[key] = value
        
        # Valores por defecto
        return {
            'hostname': '179.43.121.8',
            'port': 5680,
            'username': 'root',
            'password': config.get('SSH_PASS', ''),
            **config
        }
    
    def connect(self) -> bool:
        """Establecer conexión SSH"""
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.ssh.connect(
                hostname=self.config['hostname'],
                port=int(self.config['port']),
                username=self.config['username'],
                password=self.config['password']
            )
            print(f"✅ Conexión SSH establecida a {self.config['hostname']}:{self.config['port']}")
            return True
            
        except Exception as e:
            print(f"❌ Error conectando SSH: {e}")
            return False
    
    def execute_command(self, command: str, description: str = "") -> Tuple[str, str, int]:
        """
        Ejecutar comando SSH y retornar (stdout, stderr, exit_code)
        """
        if not self.ssh:
            raise ConnectionError("No hay conexión SSH activa")
        
        if description:
            print(f"\n🔧 {description}")
            print(f"Comando: {command}")
        
        stdin, stdout, stderr = self.ssh.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        
        stdout_text = stdout.read().decode('utf-8', errors='ignore')
        stderr_text = stderr.read().decode('utf-8', errors='ignore')
        
        # Filtrar warnings de npmrc
        if stderr_text and 'npmrc' not in stderr_text:
            print(f"⚠️  Error: {stderr_text}")
        
        if stdout_text:
            print(f"✅ Resultado:\n{stdout_text}")
        
        return stdout_text, stderr_text, exit_code
    
    def file_exists(self, filepath: str) -> bool:
        """Verificar si un archivo existe en el servidor"""
        _, _, exit_code = self.execute_command(f"test -f {filepath}")
        return exit_code == 0
    
    def read_file(self, filepath: str) -> Tuple[bool, str]:
        """Leer contenido de un archivo del servidor"""
        try:
            stdout, stderr, exit_code = self.execute_command(f"cat {filepath}")
            if exit_code == 0:
                return True, stdout
            else:
                return False, stderr
        except Exception as e:
            return False, str(e)
    
    def write_file(self, filepath: str, content: str) -> bool:
        """Escribir contenido a un archivo del servidor"""
        try:
            # Escapar contenido para echo
            escaped_content = content.replace("'", "'\"'\"'")
            stdout, stderr, exit_code = self.execute_command(f"echo '{escaped_content}' > {filepath}")
            return exit_code == 0
        except Exception as e:
            print(f"Error escribiendo archivo {filepath}: {e}")
            return False
    
    def backup_file(self, filepath: str, backup_suffix: Optional[str] = None) -> str:
        """Crear backup de un archivo"""
        if backup_suffix is None:
            backup_suffix = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        backup_path = f"{filepath}.backup.{backup_suffix}"
        self.execute_command(
            f"cp {filepath} {backup_path}",
            f"Creando backup: {filepath} → {backup_path}"
        )
        return backup_path
    
    def close(self):
        """Cerrar conexión SSH"""
        if self.ssh:
            self.ssh.close()
            print("🔒 Conexión SSH cerrada")
    
    def __enter__(self):
        """Context manager entry"""
        if self.connect():
            return self
        raise ConnectionError("No se pudo establecer conexión SSH")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()