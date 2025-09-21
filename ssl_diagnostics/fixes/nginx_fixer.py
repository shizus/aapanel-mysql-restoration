#!/usr/bin/env python3
"""
Nginx Fixer - Correcciones automáticas de configuraciones nginx
"""

import os
from typing import List, Dict, Any
from ..core.ssh_manager import SSHManager
from ..core.nginx_manager import NginxManager
from ..core.user_interaction import UserInteraction
from ..analyzers.nginx_analyzer import NginxAnalyzer

class NginxFixer:
    def __init__(self, ssh_manager: SSHManager):
        self.ssh = ssh_manager
        self.nginx = NginxManager(ssh_manager)
        self.ui = UserInteraction()
        self.analyzer = NginxAnalyzer(ssh_manager)
    
    def fix_domain_issues(self, target_domain: str) -> Dict[str, Any]:
        """Corregir todos los problemas nginx para un dominio específico"""
        step_id = f"fix_nginx_domain_{target_domain.replace('.', '_')}"
        
        if not self.ui.should_continue(step_id, f"Corregir problemas nginx para {target_domain}"):
            return {'skipped': True, 'reason': 'Usuario canceló o paso ya completado'}
        
        print(f"\n🔍 Analizando problemas nginx para {target_domain}...")
        analysis = self.analyzer.analyze_domain_issues(target_domain)
        
        if not analysis['issues']:
            print(f"✅ No se encontraron problemas nginx para {target_domain}")
            self.ui.mark_step_completed(step_id)
            return {'success': True, 'issues_found': 0, 'fixes_applied': 0}
        
        print(f"\n⚠️  Encontrados {len(analysis['issues'])} problemas:")
        for i, issue in enumerate(analysis['issues'], 1):
            print(f"  {i}. {issue['description']}")
        
        # Obtener sugerencias de corrección
        fixes = self.analyzer.suggest_fixes(analysis)
        
        if not fixes:
            print("ℹ️  No hay correcciones automáticas disponibles")
            return {'success': True, 'issues_found': len(analysis['issues']), 'fixes_applied': 0}
        
        print(f"\n🔧 Correcciones sugeridas:")
        for i, fix in enumerate(fixes, 1):
            risk_indicator = "🔴" if fix['risk_level'] == 'ALTO' else "🟡" if fix['risk_level'] == 'MEDIO' else "🟢"
            print(f"  {i}. {risk_indicator} {fix['fix']}")
        
        if not self.ui.confirm(f"\n¿Aplicar estas {len(fixes)} correcciones?"):
            return {'cancelled': True, 'reason': 'Usuario canceló las correcciones'}
        
        results = {
            'success': False,
            'issues_found': len(analysis['issues']),
            'fixes_applied': 0,
            'fixes_details': []
        }
        
        # Aplicar correcciones una por una
        for fix in fixes:
            fix_result = self._apply_fix(fix, target_domain)
            if fix_result['success']:
                results['fixes_applied'] += 1
                results['fixes_details'].append(fix_result['description'])
                print(f"✅ {fix_result['description']}")
            else:
                print(f"❌ {fix_result['description']}")
        
        # Verificar nginx después de las correcciones
        if results['fixes_applied'] > 0:
            if self._test_nginx_config():
                print(f"\n✅ Configuraciones nginx corregidas exitosamente")
                results['success'] = True
                self.ui.mark_step_completed(step_id)
            else:
                print(f"\n❌ Errores en configuración nginx después de las correcciones")
        
        return results
    
    def _apply_fix(self, fix: Dict[str, str], target_domain: str) -> Dict[str, Any]:
        """Aplicar una corrección específica"""
        step_id = fix['step_id']
        
        if step_id.startswith('disable_'):
            return self._disable_config_file(fix, step_id)
        elif step_id.startswith('fix_priority_'):
            return self._fix_priority_conflict(fix, step_id)
        elif step_id.startswith('create_config_'):
            return self._create_domain_config(fix, target_domain)
        elif step_id == 'fix_nginx_syntax':
            return self._fix_nginx_syntax()
        else:
            return {
                'success': False,
                'description': f"Tipo de corrección no implementada: {step_id}"
            }
    
    def _disable_config_file(self, fix: Dict[str, str], step_id: str) -> Dict[str, Any]:
        """Deshabilitar archivo de configuración agregando .disabled"""
        # Extraer nombre del archivo del step_id
        config_name = step_id.replace('disable_', '').replace('_', '.')
        
        if not config_name.endswith('.conf'):
            config_name += '.conf'
        
        config_path = f"/www/server/panel/vhost/nginx/{config_name}"
        disabled_path = f"{config_path}.disabled"
        
        try:
            # Verificar que el archivo existe
            stdout, stderr, exit_code = self.ssh.execute_command(f"test -f {config_path}")
            exists = exit_code == 0
            if not exists:
                return {
                    'success': False,
                    'description': f"Archivo {config_name} no encontrado"
                }
            
            # Renombrar para deshabilitar
            stdout, stderr, exit_code = self.ssh.execute_command(f"mv {config_path} {disabled_path}")
            success = exit_code == 0
            
            if success:
                return {
                    'success': True,
                    'description': f"Configuración {config_name} deshabilitada"
                }
            else:
                return {
                    'success': False,
                    'description': f"Error deshabilitando {config_name}: {stderr}"
                }
        
        except Exception as e:
            return {
                'success': False,
                'description': f"Error deshabilitando configuración: {e}"
            }
    
    def _fix_priority_conflict(self, fix: Dict[str, str], step_id: str) -> Dict[str, Any]:
        """Corregir conflicto de prioridad alfabética"""
        config_name = step_id.replace('fix_priority_', '').replace('_', '.')
        
        # Por ahora, la estrategia es deshabilitar la configuración problemática
        return self._disable_config_file(fix, f"disable_{config_name.replace('.', '_')}")
    
    def _create_domain_config(self, fix: Dict[str, str], target_domain: str) -> Dict[str, Any]:
        """Crear configuración nginx optimizada para el dominio"""
        config_content = self._generate_domain_config(target_domain)
        config_path = f"/www/server/panel/vhost/nginx/{target_domain}.conf"
        
        try:
            # Verificar si ya existe
            stdout, stderr, exit_code = self.ssh.execute_command(f"test -f {config_path}")
            exists = exit_code == 0
            if exists:
                return {
                    'success': False,
                    'description': f"Ya existe configuración para {target_domain}"
                }
            
            # Escribir configuración
            success = self.ssh.write_file(config_path, config_content)
            
            if success:
                return {
                    'success': True,
                    'description': f"Configuración nginx creada para {target_domain}"
                }
            else:
                return {
                    'success': False,
                    'description': f"Error escribiendo configuración para {target_domain}"
                }
        
        except Exception as e:
            return {
                'success': False,
                'description': f"Error creando configuración: {e}"
            }
    
    def _generate_domain_config(self, domain: str) -> str:
        """Generar contenido de configuración nginx optimizada"""
        return f"""server {{
    listen 80;
    listen 443 ssl http2;
    server_name {domain} www.{domain};
    
    index index.php index.html index.htm default.php default.htm default.html;
    root /www/wwwroot/{domain};
    
    # SSL Configuration
    ssl_certificate /www/server/panel/vhost/cert/{domain}/fullchain.pem;
    ssl_certificate_key /www/server/panel/vhost/cert/{domain}/privkey.pem;
    ssl_protocols TLSv1.1 TLSv1.2 TLSv1.3;
    ssl_ciphers EECDH+CHACHA20:EECDH+CHACHA20-draft:EECDH+AES128:RSA+AES128:EECDH+AES256:RSA+AES256:EECDH+3DES:RSA+3DES:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    add_header Strict-Transport-Security "max-age=31536000";
    
    # Force HTTPS
    if ($server_port !~ 443) {{
        rewrite ^(.*)$ https://$host$1 permanent;
    }}
    
    # Error and Access logs
    error_log  /www/wwwlogs/{domain}.error.log;
    access_log  /www/wwwlogs/{domain}.access.log;
    
    # PHP Configuration
    location ~ \\.php$ {{
        try_files $uri =404;
        fastcgi_pass unix:/tmp/php-cgi-74.sock;
        fastcgi_index index.php;
        include fastcgi.conf;
    }}
    
    # WordPress specific rules
    location / {{
        try_files $uri $uri/ /index.php?$args;
    }}
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Deny access to sensitive files
    location ~ /\\. {{
        deny all;
    }}
    
    location ~* \\.(log|conf)$ {{
        deny all;
    }}
}}
"""
    
    def _fix_nginx_syntax(self) -> Dict[str, Any]:
        """Intentar corregir errores de sintaxis nginx"""
        test_passed, test_output = self.nginx.test_config()
        
        if test_passed:
            return {
                'success': True,
                'description': "Configuración nginx ya es válida"
            }
        
        # Para errores de sintaxis, es mejor mostrar el error y que se corrija manualmente
        return {
            'success': False,
            'description': f"Errores de sintaxis nginx requieren corrección manual: {test_output}"
        }
    
    def _test_nginx_config(self) -> bool:
        """Verificar que la configuración nginx sea válida"""
        test_passed, _ = self.nginx.test_config()
        return test_passed
    
    def disable_interceptors(self, target_domain: str) -> Dict[str, Any]:
        """Deshabilitar todas las configuraciones que interceptan requests para un dominio"""
        step_id = f"disable_interceptors_{target_domain.replace('.', '_')}"
        
        if not self.ui.should_continue(step_id, f"Deshabilitar interceptores para {target_domain}"):
            return {'skipped': True, 'reason': 'Usuario canceló o paso ya completado'}
        
        print(f"\n🔍 Buscando interceptores para {target_domain}...")
        interceptors = self.nginx.find_interceptors(target_domain)
        
        if not interceptors:
            print(f"✅ No se encontraron interceptores para {target_domain}")
            self.ui.mark_step_completed(step_id)
            return {'success': True, 'interceptors_found': 0, 'interceptors_disabled': 0}
        
        print(f"\n📋 Encontrados {len(interceptors)} interceptores:")
        for i, interceptor in enumerate(interceptors, 1):
            config_name = os.path.basename(interceptor['config_file'])
            print(f"  {i}. {config_name} - {interceptor['description']}")
        
        if not self.ui.confirm(f"\n¿Deshabilitar estos {len(interceptors)} interceptores?"):
            return {'cancelled': True, 'reason': 'Usuario canceló'}
        
        results = {
            'success': True,
            'interceptors_found': len(interceptors),
            'interceptors_disabled': 0,
            'errors': []
        }
        
        for interceptor in interceptors:
            config_file = interceptor['config_file']
            config_name = os.path.basename(config_file)
            disabled_file = f"{config_file}.disabled"
            
            try:
                stdout, stderr, exit_code = self.ssh.execute_command(f"mv {config_file} {disabled_file}")
                success = exit_code == 0
                if success:
                    results['interceptors_disabled'] += 1
                    print(f"✅ {config_name} deshabilitado")
                else:
                    results['errors'].append(f"Error deshabilitando {config_name}: {stderr}")
                    print(f"❌ Error deshabilitando {config_name}")
            except Exception as e:
                results['errors'].append(f"Excepción deshabilitando {config_name}: {e}")
                print(f"❌ Excepción deshabilitando {config_name}")
        
        if results['interceptors_disabled'] > 0:
            # Verificar configuración nginx después de los cambios
            if self._test_nginx_config():
                print(f"\n✅ {results['interceptors_disabled']} interceptores deshabilitados exitosamente")
                self.ui.mark_step_completed(step_id)
            else:
                print(f"\n⚠️  Interceptores deshabilitados pero hay errores de configuración")
                results['success'] = False
        
        return results