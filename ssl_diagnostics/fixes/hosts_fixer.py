#!/usr/bin/env python3
"""
Hosts Fixer - Correcciones automáticas de archivo /etc/hosts
"""

import re
from typing import List, Dict, Tuple, Any
from ..core.ssh_manager import SSHManager
from ..core.user_interaction import UserInteraction
from ..analyzers.hosts_analyzer import HostsAnalyzer

class HostsFixer:
    def __init__(self, ssh_manager: SSHManager):
        self.ssh = ssh_manager
        self.ui = UserInteraction()
        self.analyzer = HostsAnalyzer(ssh_manager)
    
    def fix_all_issues(self) -> Dict[str, Any]:
        """Corregir todos los problemas detectados en /etc/hosts"""
        step_id = "fix_hosts_file_issues"
        
        if not self.ui.should_continue(step_id, "Analizar y corregir problemas en /etc/hosts"):
            return {'skipped': True, 'reason': 'Usuario canceló o paso ya completado'}
        
        print("\n🔍 Analizando archivo /etc/hosts...")
        analysis = self.analyzer.analyze_hosts_file()
        
        if not analysis['issues']:
            print("✅ No se encontraron problemas en /etc/hosts")
            self.ui.mark_step_completed(step_id)
            return {'success': True, 'issues_found': 0, 'fixes_applied': 0}
        
        print(f"\n⚠️  Encontrados {len(analysis['issues'])} problemas:")
        for i, issue in enumerate(analysis['issues'], 1):
            print(f"  {i}. {issue['description']}")
        
        # Confirmar si proceder con las correcciones
        if not self.ui.confirm("\n¿Proceder con las correcciones automáticas?"):
            return {'cancelled': True, 'reason': 'Usuario canceló las correcciones'}
        
        results = {
            'success': False,
            'issues_found': len(analysis['issues']),
            'fixes_applied': 0,
            'backup_created': False,
            'fixes_details': []
        }
        
        # Crear backup del archivo original
        backup_result = self._create_hosts_backup()
        results['backup_created'] = backup_result
        
        if not backup_result:
            print("❌ Error creando backup. Abortando correcciones por seguridad.")
            return results
        
        # Aplicar correcciones
        current_content = analysis['content']
        fixed_content = current_content
        
        for issue in analysis['issues']:
            fix_result = self._apply_issue_fix(issue, fixed_content)
            if fix_result['success']:
                fixed_content = fix_result['new_content']
                results['fixes_applied'] += 1
                results['fixes_details'].append(fix_result['description'])
                print(f"✅ {fix_result['description']}")
            else:
                print(f"❌ {fix_result['description']}")
        
        # Escribir archivo corregido si hubo cambios
        if results['fixes_applied'] > 0:
            write_success = self._write_hosts_file(fixed_content)
            if write_success:
                print(f"\n✅ Archivo /etc/hosts corregido exitosamente")
                print(f"   - {results['fixes_applied']} problemas corregidos")
                print(f"   - Backup guardado en /etc/hosts.backup")
                results['success'] = True
                self.ui.mark_step_completed(step_id)
            else:
                print(f"\n❌ Error escribiendo archivo corregido")
                self._restore_from_backup()
        else:
            print(f"\n⚠️  No se pudieron aplicar correcciones")
        
        return results
    
    def _create_hosts_backup(self) -> bool:
        """Crear backup del archivo /etc/hosts"""
        try:
            stdout, stderr, exit_code = self.ssh.execute_command("cp /etc/hosts /etc/hosts.backup")
            return exit_code == 0
        except Exception as e:
            print(f"Error creando backup: {e}")
            return False
    
    def _restore_from_backup(self) -> bool:
        """Restaurar archivo desde backup"""
        try:
            stdout, stderr, exit_code = self.ssh.execute_command("cp /etc/hosts.backup /etc/hosts")
            success = exit_code == 0
            if success:
                print("📋 Archivo restaurado desde backup")
            return success
        except Exception as e:
            print(f"Error restaurando backup: {e}")
            return False
    
    def _apply_issue_fix(self, issue: Dict[str, Any], content: str) -> Dict[str, Any]:
        """Aplicar corrección para un problema específico"""
        issue_type = issue['type']
        
        if issue_type == 'malformed_line':
            return self._fix_malformed_line(issue, content)
        elif issue_type == 'problematic_domain':
            return self._fix_problematic_domain(issue, content)
        elif issue_type == 'duplicate_entry':
            return self._fix_duplicate_entry(issue, content)
        else:
            return {
                'success': False,
                'description': f"Tipo de problema no reconocido: {issue_type}",
                'new_content': content
            }
    
    def _fix_malformed_line(self, issue: Dict[str, Any], content: str) -> Dict[str, Any]:
        """Corregir línea malformada"""
        malformed_line = issue['line']
        line_number = issue.get('line_number', 0)
        
        # Detectar el patrón problemático: IP sin espacio + dominio + IP + dominio
        pattern = r'(\d+\.\d+\.\d+\.\d+)([a-zA-Z0-9.-]+)(\d+\.\d+\.\d+\.\d+)\s+([a-zA-Z0-9.-]+)'
        match = re.search(pattern, malformed_line)
        
        if match:
            ip1, domain1, ip2, domain2 = match.groups()
            
            # Crear líneas separadas y correctamente formateadas
            fixed_line1 = f"{ip1} {domain1}"
            fixed_line2 = f"{ip2} {domain2}"
            
            # Reemplazar la línea malformada
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip() == malformed_line.strip():
                    lines[i] = f"{fixed_line1}\n{fixed_line2}"
                    break
            
            new_content = '\n'.join(lines)
            
            return {
                'success': True,
                'description': f"Línea malformada corregida: {domain1} y {domain2} separados",
                'new_content': new_content
            }
        
        return {
            'success': False,
            'description': f"No se pudo corregir línea malformada en línea {line_number}",
            'new_content': content
        }
    
    def _fix_problematic_domain(self, issue: Dict[str, Any], content: str) -> Dict[str, Any]:
        """Corregir dominio problemático"""
        domain = issue['domain']
        current_ip = issue.get('current_ip', '')
        
        # Si el dominio está apuntando a localhost, comentar la línea
        if current_ip in ['127.0.0.1', '::1']:
            pattern = rf'^(\s*)(\d+\.\d+\.\d+\.\d+|\:\:1)\s+.*{re.escape(domain)}.*$'
            
            def comment_line(match):
                indent = match.group(1)
                line = match.group(0)
                return f"{indent}# {line.strip()} # Comentado automáticamente"
            
            new_content = re.sub(pattern, comment_line, content, flags=re.MULTILINE)
            
            if new_content != content:
                return {
                    'success': True,
                    'description': f"Entrada problemática para {domain} comentada",
                    'new_content': new_content
                }
        
        return {
            'success': False,
            'description': f"No se pudo corregir dominio problemático: {domain}",
            'new_content': content
        }
    
    def _fix_duplicate_entry(self, issue: Dict[str, Any], content: str) -> Dict[str, Any]:
        """Corregir entrada duplicada"""
        domain = issue['domain']
        ips = issue.get('ips', [])
        
        if len(ips) < 2:
            return {
                'success': False,
                'description': f"No hay suficientes IPs duplicadas para {domain}",
                'new_content': content
            }
        
        # Comentar todas las entradas del dominio excepto la primera
        lines = content.split('\n')
        domain_entries_found = 0
        
        for i, line in enumerate(lines):
            if domain in line and not line.strip().startswith('#'):
                # Si es la primera entrada, la dejamos
                if domain_entries_found == 0:
                    domain_entries_found += 1
                    continue
                
                # Comentar entradas adicionales
                lines[i] = f"# {line.strip()} # Duplicado comentado automáticamente"
                domain_entries_found += 1
        
        if domain_entries_found > 1:
            new_content = '\n'.join(lines)
            return {
                'success': True,
                'description': f"Eliminadas {domain_entries_found - 1} entradas duplicadas para {domain}",
                'new_content': new_content
            }
        
        return {
            'success': False,
            'description': f"No se encontraron duplicados para eliminar: {domain}",
            'new_content': content
        }
    
    def _write_hosts_file(self, content: str) -> bool:
        """Escribir contenido corregido al archivo /etc/hosts"""
        try:
            # Usar el método write_file del SSHManager
            success = self.ssh.write_file("/etc/hosts", content)
            
            if not success:
                print(f"Error escribiendo archivo")
            
            return success
        except Exception as e:
            print(f"Error escribiendo archivo /etc/hosts: {e}")
            return False
    
    def clean_specific_domain(self, domain: str) -> Dict[str, Any]:
        """Limpiar entradas específicas de un dominio del archivo hosts"""
        step_id = f"clean_hosts_domain_{domain.replace('.', '_')}"
        
        if not self.ui.should_continue(step_id, f"Limpiar entradas de {domain} de /etc/hosts"):
            return {'skipped': True, 'reason': 'Usuario canceló o paso ya completado'}
        
        print(f"\n🔍 Buscando entradas de {domain} en /etc/hosts...")
        
        try:
            success, content = self.ssh.read_file("/etc/hosts")
            if not success:
                return {'success': False, 'error': 'No se pudo leer /etc/hosts'}
            
            lines = content.split('\n')
            domain_lines = []
            
            for i, line in enumerate(lines, 1):
                if domain in line and not line.strip().startswith('#'):
                    domain_lines.append({'line_number': i, 'content': line.strip()})
            
            if not domain_lines:
                print(f"✅ No se encontraron entradas activas para {domain}")
                self.ui.mark_step_completed(step_id)
                return {'success': True, 'entries_found': 0, 'entries_cleaned': 0}
            
            print(f"\n📋 Encontradas {len(domain_lines)} entradas para {domain}:")
            for entry in domain_lines:
                print(f"  Línea {entry['line_number']}: {entry['content']}")
            
            if not self.ui.confirm(f"\n¿Comentar estas {len(domain_lines)} entradas?"):
                return {'cancelled': True, 'reason': 'Usuario canceló'}
            
            # Crear backup
            if not self._create_hosts_backup():
                return {'success': False, 'error': 'No se pudo crear backup'}
            
            # Comentar las líneas
            new_lines = []
            entries_cleaned = 0
            
            for line in lines:
                if domain in line and not line.strip().startswith('#'):
                    new_lines.append(f"# {line.strip()} # Limpiado automáticamente")
                    entries_cleaned += 1
                else:
                    new_lines.append(line)
            
            new_content = '\n'.join(new_lines)
            
            if self._write_hosts_file(new_content):
                print(f"✅ {entries_cleaned} entradas de {domain} comentadas exitosamente")
                self.ui.mark_step_completed(step_id)
                return {
                    'success': True,
                    'entries_found': len(domain_lines),
                    'entries_cleaned': entries_cleaned
                }
            else:
                self._restore_from_backup()
                return {'success': False, 'error': 'Error escribiendo archivo corregido'}
                
        except Exception as e:
            return {'success': False, 'error': f'Error procesando /etc/hosts: {e}'}