#!/usr/bin/env python3
"""
SSL Manager - Manejo centralizado de certificados SSL
"""

import os
import re
from typing import Dict, List, Optional, Tuple, Any
from .ssh_manager import SSHManager

class SSLManager:
    def __init__(self, ssh_manager: SSHManager):
        self.ssh = ssh_manager
        self.cert_dir = "/www/server/panel/vhost/cert"
    
    def get_certificate_info(self, domain: str) -> Dict[str, Any]:
        """Obtener información de certificado para un dominio"""
        cert_path = f"{self.cert_dir}/{domain}"
        
        info = {
            'domain': domain,
            'cert_dir_exists': False,
            'fullchain_exists': False,
            'privkey_exists': False,
            'certificate_details': {}
        }
        
        # Verificar si existe el directorio
        if self.ssh.file_exists(cert_path):
            info['cert_dir_exists'] = True
            
            # Verificar archivos de certificado
            fullchain_path = f"{cert_path}/fullchain.pem"
            privkey_path = f"{cert_path}/privkey.pem"
            
            info['fullchain_exists'] = self.ssh.file_exists(fullchain_path)
            info['privkey_exists'] = self.ssh.file_exists(privkey_path)
            
            # Obtener detalles del certificado si existe
            if info['fullchain_exists']:
                info['certificate_details'] = self._get_cert_details(fullchain_path)
        
        return info
    
    def _get_cert_details(self, cert_file: str) -> Dict[str, str]:
        """Extraer detalles del certificado"""
        details = {}
        
        # Obtener subject
        stdout, _, _ = self.ssh.execute_command(
            f"openssl x509 -in {cert_file} -noout -subject",
            f"Obteniendo subject de {cert_file}"
        )
        if stdout:
            subject_match = re.search(r'CN\s*=\s*([^,\n]+)', stdout)
            if subject_match:
                details['common_name'] = subject_match.group(1).strip()
        
        # Obtener fechas de validez
        stdout, _, _ = self.ssh.execute_command(
            f"openssl x509 -in {cert_file} -noout -dates",
            f"Obteniendo fechas de {cert_file}"
        )
        if stdout:
            for line in stdout.split('\n'):
                if 'notBefore=' in line:
                    details['not_before'] = line.split('=', 1)[1].strip()
                elif 'notAfter=' in line:
                    details['not_after'] = line.split('=', 1)[1].strip()
        
        # Obtener issuer
        stdout, _, _ = self.ssh.execute_command(
            f"openssl x509 -in {cert_file} -noout -issuer",
            f"Obteniendo issuer de {cert_file}"
        )
        if stdout:
            issuer_match = re.search(r'CN\s*=\s*([^,\n]+)', stdout)
            if issuer_match:
                details['issuer'] = issuer_match.group(1).strip()
        
        return details
    
    def verify_certificate_chain(self, domain: str) -> Tuple[bool, str]:
        """Verificar cadena de certificados"""
        cert_file = f"{self.cert_dir}/{domain}/fullchain.pem"
        
        if not self.ssh.file_exists(cert_file):
            return False, f"Archivo de certificado no encontrado: {cert_file}"
        
        stdout, stderr, exit_code = self.ssh.execute_command(
            f"openssl verify {cert_file}",
            f"Verificando cadena de certificados para {domain}"
        )
        
        return exit_code == 0, stdout + stderr
    
    def test_ssl_connection(self, domain: str, port: int = 443) -> Dict[str, Any]:
        """Probar conexión SSL a un dominio"""
        result = {
            'success': False,
            'certificate_subject': '',
            'certificate_issuer': '',
            'connection_info': ''
        }
        
        stdout, stderr, exit_code = self.ssh.execute_command(
            f"echo | openssl s_client -connect localhost:{port} -servername {domain} -showcerts 2>/dev/null | grep 'subject\\|issuer' | head -2",
            f"Probando conexión SSL a {domain}:{port}"
        )
        
        if stdout:
            for line in stdout.split('\n'):
                if 'subject=' in line:
                    result['certificate_subject'] = line.strip()
                elif 'issuer=' in line:
                    result['certificate_issuer'] = line.strip()
            
            result['success'] = bool(result['certificate_subject'])
            result['connection_info'] = stdout
        
        return result
    
    def list_all_certificates(self) -> List[Dict[str, Any]]:
        """Listar todos los certificados disponibles"""
        stdout, _, _ = self.ssh.execute_command(
            f"ls -la {self.cert_dir}/",
            "Listando todos los certificados"
        )
        
        certificates = []
        for line in stdout.split('\n'):
            if line.strip() and ' -> ' not in line and line.startswith('d'):
                # Es un directorio
                parts = line.split()
                if len(parts) >= 9:
                    domain = parts[8]
                    if domain not in ['.', '..']:
                        cert_info = self.get_certificate_info(domain)
                        certificates.append(cert_info)
        
        return certificates
    
    def extract_certificate_from_server(self, domain: str, port: int = 443) -> str:
        """Extraer certificado desde el servidor en vivo"""
        stdout, _, _ = self.ssh.execute_command(
            f"echo | openssl s_client -connect {domain}:{port} -showcerts 2>/dev/null | openssl x509 -outform PEM",
            f"Extrayendo certificado de {domain}:{port}"
        )
        return stdout