#!/usr/bin/env python3
"""
Nginx Manager - Manejo centralizado de configuraciones nginx
"""

import os
import re
from typing import List, Dict, Tuple, Optional, Any
from .ssh_manager import SSHManager

class NginxManager:
    def __init__(self, ssh_manager: SSHManager):
        self.ssh = ssh_manager
        self.vhost_dir = "/www/server/panel/vhost/nginx"
        self.nginx_conf = "/www/server/nginx/conf/nginx.conf"
    
    def get_active_configs(self) -> List[str]:
        """Obtener lista de archivos de configuración activos"""
        stdout, _, _ = self.ssh.execute_command(
            f"ls {self.vhost_dir}/*.conf 2>/dev/null",
            "Obteniendo configuraciones nginx activas"
        )
        return [line.strip() for line in stdout.split('\n') if line.strip()]
    
    def get_disabled_configs(self) -> List[str]:
        """Obtener lista de archivos de configuración deshabilitados"""
        stdout, _, _ = self.ssh.execute_command(
            f"ls {self.vhost_dir}/*.disabled {self.vhost_dir}/*.backup {self.vhost_dir}/*.old 2>/dev/null",
            "Obteniendo configuraciones nginx deshabilitadas"
        )
        return [line.strip() for line in stdout.split('\n') if line.strip()]
    
    def get_server_names(self, config_file: str) -> List[str]:
        """Extraer server_name de un archivo de configuración"""
        stdout, _, _ = self.ssh.execute_command(
            f"grep -E '^\\s*server_name' {config_file}",
            f"Extrayendo server_name de {config_file}"
        )
        
        server_names = []
        for line in stdout.split('\n'):
            if 'server_name' in line:
                # Extraer nombres después de server_name
                match = re.search(r'server_name\s+([^;]+);', line)
                if match:
                    names = match.group(1).strip().split()
                    server_names.extend(names)
        
        return server_names
    
    def get_listen_ports(self, config_file: str) -> List[str]:
        """Extraer puertos de escucha de un archivo de configuración"""
        stdout, _, _ = self.ssh.execute_command(
            f"grep -E '^\\s*listen' {config_file}",
            f"Extrayendo puertos de {config_file}"
        )
        return [line.strip() for line in stdout.split('\n') if line.strip()]
    
    def disable_config(self, config_file: str) -> str:
        """Deshabilitar una configuración agregando .disabled"""
        disabled_file = f"{config_file}.disabled"
        self.ssh.execute_command(
            f"mv {config_file} {disabled_file}",
            f"Deshabilitando {config_file} → {disabled_file}"
        )
        return disabled_file
    
    def enable_config(self, disabled_file: str) -> str:
        """Habilitar una configuración removiendo .disabled"""
        if disabled_file.endswith('.disabled'):
            active_file = disabled_file[:-9]  # Remover .disabled
            self.ssh.execute_command(
                f"mv {disabled_file} {active_file}",
                f"Habilitando {disabled_file} → {active_file}"
            )
            return active_file
        return disabled_file
    
    def create_config(self, filename: str, content: str) -> bool:
        """Crear nueva configuración nginx"""
        full_path = f"{self.vhost_dir}/{filename}"
        
        # Escapar content para heredoc
        escaped_content = content.replace("'", "'\"'\"'")
        
        self.ssh.execute_command(
            f"cat > {full_path} << 'EOF'\n{escaped_content}\nEOF",
            f"Creando configuración {full_path}"
        )
        return True
    
    def test_config(self) -> Tuple[bool, str]:
        """Probar configuración nginx"""
        stdout, stderr, exit_code = self.ssh.execute_command(
            "nginx -t",
            "Probando configuración nginx"
        )
        return exit_code == 0, stdout + stderr
    
    def reload_nginx(self) -> bool:
        """Recargar nginx"""
        _, _, exit_code = self.ssh.execute_command(
            "systemctl reload nginx",
            "Recargando nginx"
        )
        return exit_code == 0
    
    def get_nginx_status(self) -> str:
        """Obtener estado de nginx"""
        stdout, _, _ = self.ssh.execute_command(
            "systemctl status nginx --no-pager -l",
            "Verificando estado nginx"
        )
        return stdout
    
    def find_interceptors(self, target_domain: str) -> List[Dict[str, Any]]:
        """
        Encontrar configuraciones que podrían estar interceptando requests
        para un dominio específico
        """
        interceptors = []
        active_configs = self.get_active_configs()
        
        for config in active_configs:
            # Obtener server_names y puertos
            server_names = self.get_server_names(config)
            listen_ports = self.get_listen_ports(config)
            
            # Verificar si podría interceptar
            could_intercept = False
            reason = ""
            
            # Si no tiene server_name específico
            if not server_names or any('_' in name for name in server_names):
                could_intercept = True
                reason = "Configuración catch-all (server_name _)"
            
            # Si viene antes alfabéticamente que el target
            config_basename = os.path.basename(config)
            if config_basename < f"{target_domain}.conf":
                could_intercept = True
                reason += " + Orden alfabético anterior"
            
            if could_intercept:
                interceptors.append({
                    'config_file': config,
                    'server_names': server_names,
                    'listen_ports': listen_ports,
                    'reason': reason.strip()
                })
        
        return interceptors
    
    def analyze_domain_conflicts(self, target_domain: str) -> Dict[str, Any]:
        """Análisis completo de conflictos para un dominio"""
        analysis = {
            'target_domain': target_domain,
            'active_configs': [],
            'interceptors': [],
            'conflicts': []
        }
        
        active_configs = self.get_active_configs()
        
        for config in active_configs:
            server_names = self.get_server_names(config)
            listen_ports = self.get_listen_ports(config)
            
            config_info = {
                'file': config,
                'server_names': server_names,
                'listen_ports': listen_ports
            }
            analysis['active_configs'].append(config_info)
            
            # Verificar conflictos directos
            if target_domain in server_names:
                analysis['conflicts'].append({
                    'type': 'direct_conflict',
                    'config': config,
                    'description': f"Configuración define explícitamente {target_domain}"
                })
        
        # Encontrar interceptores
        analysis['interceptors'] = self.find_interceptors(target_domain)
        
        return analysis