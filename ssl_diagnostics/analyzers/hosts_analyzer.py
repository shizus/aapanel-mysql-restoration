#!/usr/bin/env python3
"""
Hosts Analyzer - Análisis del archivo /etc/hosts
"""

import re
from typing import Dict, List, Tuple, Any
from ..core.ssh_manager import SSHManager

class HostsAnalyzer:
    def __init__(self, ssh_manager: SSHManager):
        self.ssh = ssh_manager
        self.hosts_file = "/etc/hosts"
    
    def analyze_hosts_file(self) -> Dict[str, Any]:
        """Análisis completo del archivo /etc/hosts"""
        analysis = {
            'file_exists': False,
            'total_lines': 0,
            'localhost_entries': [],
            'domain_entries': [],
            'malformed_entries': [],
            'problematic_domains': [],
            'has_problems': False
        }
        
        if not self.ssh.file_exists(self.hosts_file):
            return analysis
        
        analysis['file_exists'] = True
        
        # Leer contenido del archivo
        stdout, _, _ = self.ssh.execute_command(
            f"cat {self.hosts_file}",
            "Leyendo archivo /etc/hosts"
        )
        
        lines = stdout.split('\n')
        analysis['total_lines'] = len([l for l in lines if l.strip()])
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            entry_analysis = self._analyze_hosts_entry(line, line_num)
            
            if entry_analysis['type'] == 'localhost':
                analysis['localhost_entries'].append(entry_analysis)
            elif entry_analysis['type'] == 'domain':
                analysis['domain_entries'].append(entry_analysis)
            elif entry_analysis['type'] == 'malformed':
                analysis['malformed_entries'].append(entry_analysis)
                analysis['has_problems'] = True
        
        # Identificar dominios problemáticos
        analysis['problematic_domains'] = self._identify_problematic_domains(
            analysis['domain_entries']
        )
        
        if analysis['problematic_domains']:
            analysis['has_problems'] = True
        
        return analysis
    
    def _analyze_hosts_entry(self, line: str, line_num: int) -> Dict[str, Any]:
        """Analizar una entrada específica del hosts"""
        entry = {
            'line_number': line_num,
            'original_line': line,
            'type': 'unknown',
            'ip': '',
            'hostnames': [],
            'is_malformed': False,
            'problems': []
        }
        
        # Verificar si la línea está malformada (texto concatenado sin espacios)
        if self._is_malformed_line(line):
            entry['type'] = 'malformed'
            entry['is_malformed'] = True
            entry['problems'].append("Línea malformada - dominios concatenados sin espacios")
            return entry
        
        # Parsear línea normal
        parts = line.split()
        if len(parts) < 2:
            entry['type'] = 'malformed'
            entry['is_malformed'] = True
            entry['problems'].append("Formato inválido - menos de 2 elementos")
            return entry
        
        entry['ip'] = parts[0]
        entry['hostnames'] = parts[1:]
        
        # Clasificar tipo de entrada
        if entry['ip'] in ['127.0.0.1', '::1']:
            if any(host in ['localhost', 'localhost.localdomain'] for host in entry['hostnames']):
                entry['type'] = 'localhost'
            else:
                entry['type'] = 'domain'
        else:
            entry['type'] = 'external'
        
        return entry
    
    def _is_malformed_line(self, line: str) -> bool:
        """Detectar líneas malformadas como '127.0.0.1 domain1127.0.0.1 domain2'"""
        # Buscar patrones como IP+texto+IP
        pattern = r'127\.0\.0\.1\s*\w+127\.0\.0\.1'
        return bool(re.search(pattern, line))
    
    def _identify_problematic_domains(self, domain_entries: List[Dict[str, Any]]) -> List[str]:
        """Identificar dominios que podrían causar problemas"""
        problematic = []
        
        # Dominios conocidos que causan problemas específicos
        problem_domains = ['eydeck.com', 'circoeguap.com']
        
        for entry in domain_entries:
            for hostname in entry['hostnames']:
                if hostname in problem_domains:
                    problematic.append(hostname)
        
        return list(set(problematic))
    
    def suggest_fixes(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Sugerir correcciones basadas en el análisis"""
        fixes = []
        
        if analysis['malformed_entries']:
            fixes.append({
                'issue': 'Entradas malformadas detectadas',
                'fix': 'Reescribir archivo /etc/hosts con formato correcto',
                'risk_level': 'ALTO',
                'step_id': 'fix_malformed_hosts'
            })
        
        if analysis['problematic_domains']:
            domains = ', '.join(analysis['problematic_domains'])
            fixes.append({
                'issue': f'Dominios problemáticos en hosts: {domains}',
                'fix': 'Eliminar entradas de dominios problemáticos',
                'risk_level': 'MEDIO',
                'step_id': 'remove_problematic_domains'
            })
        
        if len(analysis['domain_entries']) > 0:
            fixes.append({
                'issue': 'Entradas de dominios en /etc/hosts pueden causar problemas',
                'fix': 'Limpiar /etc/hosts dejando solo entradas localhost estándar',
                'risk_level': 'BAJO',
                'step_id': 'clean_domain_entries'
            })
        
        return fixes
    
    def generate_clean_hosts_content(self) -> str:
        """Generar contenido limpio para /etc/hosts"""
        return """127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
::1         localhost localhost.localdomain localhost6 localhost6.localdomain6

# Archivo limpiado - eliminadas todas las entradas de dominios que causaban conflictos"""