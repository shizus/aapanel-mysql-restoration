#!/usr/bin/env python3
"""
Nginx Analyzer - Análisis de configuraciones nginx
"""

import os
from typing import Dict, List, Any
from ..core.ssh_manager import SSHManager
from ..core.nginx_manager import NginxManager

class NginxAnalyzer:
    def __init__(self, ssh_manager: SSHManager):
        self.ssh = ssh_manager
        self.nginx = NginxManager(ssh_manager)
    
    def analyze_domain_issues(self, target_domain: str) -> Dict[str, Any]:
        """Análisis completo de problemas nginx para un dominio"""
        analysis = {
            'target_domain': target_domain,
            'has_active_config': False,
            'active_config_file': '',
            'interceptors': [],
            'conflicts': [],
            'issues': [],
            'nginx_test_passed': False
        }
        
        # Verificar si nginx funciona
        test_passed, test_output = self.nginx.test_config()
        analysis['nginx_test_passed'] = test_passed
        
        if not test_passed:
            analysis['issues'].append({
                'type': 'nginx_config_error',
                'description': 'Nginx tiene errores de configuración',
                'details': test_output
            })
        
        # Buscar configuración activa del dominio
        active_configs = self.nginx.get_active_configs()
        for config in active_configs:
            config_basename = os.path.basename(config)
            if target_domain in config_basename:
                analysis['has_active_config'] = True
                analysis['active_config_file'] = config
                break
        
        # Analizar interceptores
        interceptors = self.nginx.find_interceptors(target_domain)
        analysis['interceptors'] = interceptors
        
        if interceptors:
            analysis['issues'].append({
                'type': 'request_interceptors',
                'description': f'Encontradas {len(interceptors)} configuraciones que pueden interceptar requests',
                'details': interceptors
            })
        
        # Buscar conflictos de configuración
        conflicts = self._find_configuration_conflicts(target_domain, active_configs)
        analysis['conflicts'] = conflicts
        
        if conflicts:
            analysis['issues'].append({
                'type': 'configuration_conflicts',
                'description': f'Encontrados {len(conflicts)} conflictos de configuración',
                'details': conflicts
            })
        
        return analysis
    
    def _find_configuration_conflicts(self, target_domain: str, active_configs: List[str]) -> List[Dict[str, Any]]:
        """Encontrar conflictos de configuración específicos"""
        conflicts = []
        
        # Configuraciones que podrían interceptar por orden alfabético
        target_config_name = f"{target_domain}.conf"
        
        for config in active_configs:
            config_basename = os.path.basename(config)
            
            # Si viene antes alfabéticamente
            if config_basename < target_config_name:
                server_names = self.nginx.get_server_names(config)
                listen_ports = self.nginx.get_listen_ports(config)
                
                # Si no tiene server_name específico (catch-all)
                if not server_names or any('_' in name for name in server_names):
                    conflicts.append({
                        'config_file': config,
                        'type': 'alphabetical_priority_catchall',
                        'description': f'{config_basename} viene antes alfabéticamente y es catch-all',
                        'server_names': server_names,
                        'listen_ports': listen_ports
                    })
                
                # Si escucha en los mismos puertos que necesitamos
                if any('80' in port or '443' in port for port in listen_ports):
                    conflicts.append({
                        'config_file': config,
                        'type': 'port_conflict',
                        'description': f'{config_basename} escucha en puertos 80/443',
                        'server_names': server_names,
                        'listen_ports': listen_ports
                    })
        
        return conflicts
    
    def suggest_fixes(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Sugerir correcciones basadas en el análisis"""
        fixes = []
        target_domain = analysis['target_domain']
        
        # Si nginx tiene errores de configuración
        if not analysis['nginx_test_passed']:
            fixes.append({
                'issue': 'Nginx tiene errores de configuración sintáctica',
                'fix': 'Corregir errores de sintaxis nginx antes de continuar',
                'risk_level': 'ALTO',
                'step_id': 'fix_nginx_syntax'
            })
        
        # Deshabilitar interceptores
        for interceptor in analysis['interceptors']:
            config_file = interceptor['config_file']
            config_name = os.path.basename(config_file)
            
            fixes.append({
                'issue': f'Configuración {config_name} intercepta requests para {target_domain}',
                'fix': f'Deshabilitar {config_name} agregando .disabled',
                'risk_level': 'MEDIO',
                'step_id': f'disable_{config_name.replace(".", "_")}'
            })
        
        # Resolver conflictos de configuración
        for conflict in analysis['conflicts']:
            config_file = conflict['config_file']
            config_name = os.path.basename(config_file)
            
            if conflict['type'] == 'alphabetical_priority_catchall':
                fixes.append({
                    'issue': f'{config_name} es catch-all y tiene prioridad alfabética',
                    'fix': f'Deshabilitar {config_name} o crear configuración con mayor prioridad',
                    'risk_level': 'MEDIO',
                    'step_id': f'fix_priority_{config_name.replace(".", "_")}'
                })
        
        # Si no hay configuración activa para el dominio
        if not analysis['has_active_config']:
            fixes.append({
                'issue': f'No existe configuración activa para {target_domain}',
                'fix': f'Crear configuración nginx optimizada para {target_domain}',
                'risk_level': 'MEDIO',
                'step_id': f'create_config_{target_domain.replace(".", "_")}'
            })
        
        return fixes
    
    def analyze_all_configurations(self) -> Dict[str, Any]:
        """Análisis general de todas las configuraciones nginx"""
        analysis = {
            'total_active_configs': 0,
            'total_disabled_configs': 0,
            'active_configs': [],
            'disabled_configs': [],
            'catch_all_configs': [],
            'duplicate_server_names': []
        }
        
        # Obtener configuraciones activas
        active_configs = self.nginx.get_active_configs()
        analysis['total_active_configs'] = len(active_configs)
        analysis['active_configs'] = active_configs
        
        # Obtener configuraciones deshabilitadas
        disabled_configs = self.nginx.get_disabled_configs()
        analysis['total_disabled_configs'] = len(disabled_configs)
        analysis['disabled_configs'] = disabled_configs
        
        # Identificar configuraciones catch-all
        for config in active_configs:
            server_names = self.nginx.get_server_names(config)
            if not server_names or any('_' in name for name in server_names):
                analysis['catch_all_configs'].append({
                    'config_file': config,
                    'server_names': server_names
                })
        
        # Buscar server_names duplicados
        server_name_map = {}
        for config in active_configs:
            server_names = self.nginx.get_server_names(config)
            for server_name in server_names:
                if server_name not in server_name_map:
                    server_name_map[server_name] = []
                server_name_map[server_name].append(config)
        
        for server_name, configs in server_name_map.items():
            if len(configs) > 1:
                analysis['duplicate_server_names'].append({
                    'server_name': server_name,
                    'configs': configs
                })
        
        return analysis