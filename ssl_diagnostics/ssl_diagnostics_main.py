#!/usr/bin/env python3
"""
SSL Diagnostics Main - Orquestador principal para diagnóstico y corrección SSL
"""

import sys
import os
from typing import Dict, Any, Optional

# Agregar el directorio padre al path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ssl_diagnostics.core.ssh_manager import SSHManager
from ssl_diagnostics.core.user_interaction import UserInteraction
from ssl_diagnostics.core.nginx_manager import NginxManager
from ssl_diagnostics.core.ssl_manager import SSLManager
from ssl_diagnostics.analyzers.hosts_analyzer import HostsAnalyzer
from ssl_diagnostics.analyzers.nginx_analyzer import NginxAnalyzer
from ssl_diagnostics.fixes.hosts_fixer import HostsFixer
from ssl_diagnostics.fixes.nginx_fixer import NginxFixer

class SSLDiagnosticsMain:
    def __init__(self, target_domain: str):
        self.target_domain = target_domain
        self.ui = UserInteraction(target_domain)  # Pasar dominio para state management
        self.ssh: Optional[SSHManager] = None
        
        # Managers y analyzers se inicializan después de la conexión SSH
        self.nginx_manager: Optional[NginxManager] = None
        self.ssl_manager: Optional[SSLManager] = None
        self.hosts_analyzer: Optional[HostsAnalyzer] = None
        self.nginx_analyzer: Optional[NginxAnalyzer] = None
        self.hosts_fixer: Optional[HostsFixer] = None
        self.nginx_fixer: Optional[NginxFixer] = None
    
    def run_complete_diagnosis(self) -> Dict[str, Any]:
        """Ejecutar diagnóstico completo SSL con confirmaciones interactivas"""
        print(f"🔍 SSL Diagnostics - Análisis completo para {self.target_domain}")
        print("=" * 60)
        
        results = {
            'success': False,
            'target_domain': self.target_domain,
            'steps_completed': [],
            'steps_skipped': [],
            'errors': []
        }
        
        try:
            # Paso 1: Conectar SSH
            if not self._connect_ssh():
                results['errors'].append('Error conectando SSH')
                return results
            
            print("✅ Conexión SSH establecida")
            results['steps_completed'].append('ssh_connection')
            
            # Inicializar todos los componentes
            self._initialize_components()
            
            # Paso 2: Análisis inicial
            print(f"\n🔍 FASE 1: ANÁLISIS INICIAL")
            print("-" * 40)
            
            analysis_results = self._run_initial_analysis()
            if analysis_results.get('skipped'):
                results['steps_skipped'].append('initial_analysis')
            else:
                results['steps_completed'].append('initial_analysis')
            
            # Paso 3: Corrección de /etc/hosts
            print(f"\n🔧 FASE 2: CORRECCIÓN DE /etc/hosts")
            print("-" * 40)
            
            hosts_results = self._fix_hosts_issues()
            if hosts_results.get('skipped'):
                results['steps_skipped'].append('hosts_fixes')
            else:
                results['steps_completed'].append('hosts_fixes')
            
            # Paso 4: Corrección de nginx
            print(f"\n🔧 FASE 3: CORRECCIÓN DE NGINX")
            print("-" * 40)
            
            nginx_results = self._fix_nginx_issues()
            if nginx_results.get('skipped'):
                results['steps_skipped'].append('nginx_fixes')
            else:
                results['steps_completed'].append('nginx_fixes')
            
            # Paso 5: Verificación SSL
            print(f"\n🔒 FASE 4: VERIFICACIÓN SSL")
            print("-" * 40)
            
            ssl_results = self._verify_ssl_final()
            if ssl_results.get('skipped'):
                results['steps_skipped'].append('ssl_verification')
            else:
                results['steps_completed'].append('ssl_verification')
            
            # Paso 6: Reiniciar servicios
            print(f"\n🔄 FASE 5: REINICIO DE SERVICIOS")
            print("-" * 40)
            
            restart_results = self._restart_services()
            if restart_results.get('skipped'):
                results['steps_skipped'].append('service_restart')
            else:
                results['steps_completed'].append('service_restart')
            
            # Resumen final
            self._print_final_summary(results)
            results['success'] = True
            
        except KeyboardInterrupt:
            print(f"\n❌ Proceso interrumpido por el usuario")
            results['errors'].append('Proceso interrumpido por el usuario')
        except Exception as e:
            print(f"\n❌ Error inesperado: {e}")
            results['errors'].append(f'Error inesperado: {e}')
        finally:
            if self.ssh:
                self.ssh.close()
                print(f"\n🔌 Conexión SSH cerrada")
        
        return results
    
    def _connect_ssh(self) -> bool:
        """Conectar SSH al servidor"""
        step_id = "ssh_connection"
        
        if not self.ui.should_continue(step_id, "Conectar al servidor via SSH"):
            return False
        
        try:
            self.ssh = SSHManager()
            success = self.ssh.connect()
            
            if success:
                self.ui.mark_step_completed(step_id)
                return True
            else:
                print("❌ Error conectando SSH")
                return False
        except Exception as e:
            print(f"❌ Error conectando SSH: {e}")
            return False
    
    def _initialize_components(self):
        """Inicializar todos los componentes después de la conexión SSH"""
        if not self.ssh:
            raise ConnectionError("SSH connection not established")
            
        self.nginx_manager = NginxManager(self.ssh)
        self.ssl_manager = SSLManager(self.ssh)
        self.hosts_analyzer = HostsAnalyzer(self.ssh)
        self.nginx_analyzer = NginxAnalyzer(self.ssh)
        self.hosts_fixer = HostsFixer(self.ssh)
        self.nginx_fixer = NginxFixer(self.ssh)
    
    def _run_initial_analysis(self) -> Dict[str, Any]:
        """Ejecutar análisis inicial completo"""
        step_id = "initial_analysis"
        
        if not self.ui.should_continue(step_id, "Ejecutar análisis inicial completo"):
            return {'skipped': True}
        
        if not self.hosts_analyzer or not self.nginx_analyzer or not self.ssl_manager:
            raise RuntimeError("Components not initialized")
        
        print("🔍 Analizando archivo /etc/hosts...")
        hosts_analysis = self.hosts_analyzer.analyze_hosts_file()
        
        print("🔍 Analizando configuraciones nginx...")
        nginx_analysis = self.nginx_analyzer.analyze_domain_issues(self.target_domain)
        
        print("🔍 Verificando certificados SSL...")
        ssl_analysis = self.ssl_manager.analyze_ssl_status(self.target_domain)
        
        # Mostrar resumen del análisis
        print(f"\n📊 RESUMEN DEL ANÁLISIS:")
        print(f"   /etc/hosts: {len(hosts_analysis['issues'])} problemas detectados")
        print(f"   Nginx: {len(nginx_analysis['issues'])} problemas detectados")
        print(f"   SSL: {'✅ OK' if ssl_analysis.get('certificate_valid') else '❌ Problemas'}")
        
        if hosts_analysis['issues'] or nginx_analysis['issues']:
            print(f"\n⚠️  Se requieren correcciones para resolver los problemas SSL")
        
        self.ui.mark_step_completed(step_id)
        return {
            'hosts_analysis': hosts_analysis,
            'nginx_analysis': nginx_analysis,
            'ssl_analysis': ssl_analysis
        }
    
    def _fix_hosts_issues(self) -> Dict[str, Any]:
        """Corregir problemas en /etc/hosts"""
        if not self.hosts_fixer:
            raise RuntimeError("HostsFixer not initialized")
        return self.hosts_fixer.fix_all_issues()
    
    def _fix_nginx_issues(self) -> Dict[str, Any]:
        """Corregir problemas en nginx"""
        if not self.nginx_fixer:
            raise RuntimeError("NginxFixer not initialized")
            
        results = {}
        
        # Corregir problemas específicos del dominio
        domain_fixes = self.nginx_fixer.fix_domain_issues(self.target_domain)
        results['domain_fixes'] = domain_fixes
        
        # Deshabilitar interceptores específicamente
        interceptor_fixes = self.nginx_fixer.disable_interceptors(self.target_domain)
        results['interceptor_fixes'] = interceptor_fixes
        
        return results
    
    def _verify_ssl_final(self) -> Dict[str, Any]:
        """Verificación final de SSL"""
        step_id = "ssl_final_verification"
        
        if not self.ui.should_continue(step_id, f"Verificar SSL final para {self.target_domain}"):
            return {'skipped': True}
        
        if not self.ssl_manager or not self.nginx_manager:
            raise RuntimeError("Components not initialized")
        
        print(f"🔒 Verificando SSL para {self.target_domain}...")
        
        # Verificar certificado
        ssl_status = self.ssl_manager.analyze_ssl_status(self.target_domain)
        
        # Verificar que la configuración nginx es válida
        nginx_test_passed, nginx_output = self.nginx_manager.test_config()
        
        print(f"📋 Resultados de verificación SSL:")
        print(f"   Certificado válido: {'✅' if ssl_status.get('certificate_valid') else '❌'}")
        print(f"   Nginx configuración: {'✅' if nginx_test_passed else '❌'}")
        
        if ssl_status.get('certificate_valid') and nginx_test_passed:
            print(f"✅ SSL configurado correctamente para {self.target_domain}")
        else:
            print(f"⚠️  Aún hay problemas SSL que requieren atención manual")
        
        self.ui.mark_step_completed(step_id)
        return {
            'ssl_status': ssl_status,
            'nginx_test_passed': nginx_test_passed,
            'nginx_output': nginx_output
        }
    
    def _restart_services(self) -> Dict[str, Any]:
        """Reiniciar servicios nginx"""
        step_id = "restart_services"
        
        if not self.ui.should_continue(step_id, "Reiniciar servicios nginx"):
            return {'skipped': True}
        
        if not self.nginx_manager or not self.ssh:
            raise RuntimeError("Components not initialized")
        
        print("🔄 Reiniciando nginx...")
        
        # Verificar configuración antes de reiniciar
        test_passed, test_output = self.nginx_manager.test_config()
        
        if not test_passed:
            print(f"❌ No se puede reiniciar nginx: errores de configuración")
            print(f"   {test_output}")
            return {'success': False, 'error': 'Errores de configuración nginx'}
        
        # Reiniciar nginx
        stdout, stderr, exit_code = self.ssh.execute_command("systemctl restart nginx")
        restart_success = exit_code == 0
        
        if restart_success:
            print("✅ Nginx reiniciado exitosamente")
            self.ui.mark_step_completed(step_id)
            return {'success': True}
        else:
            print(f"❌ Error reiniciando nginx: {stderr}")
            return {'success': False, 'error': stderr}
    
    def _print_final_summary(self, results: Dict[str, Any]):
        """Imprimir resumen final del proceso"""
        print(f"\n" + "=" * 60)
        print(f"📋 RESUMEN FINAL - {self.target_domain}")
        print(f"=" * 60)
        
        print(f"✅ Pasos completados: {len(results['steps_completed'])}")
        for step in results['steps_completed']:
            print(f"   - {step}")
        
        if results['steps_skipped']:
            print(f"\n⏭️  Pasos omitidos: {len(results['steps_skipped'])}")
            for step in results['steps_skipped']:
                print(f"   - {step}")
        
        if results['errors']:
            print(f"\n❌ Errores: {len(results['errors'])}")
            for error in results['errors']:
                print(f"   - {error}")
        
        if results['success']:
            print(f"\n🎉 Proceso completado exitosamente")
            print(f"   Verificar https://{self.target_domain} en el navegador")
        else:
            print(f"\n⚠️  Proceso completado con errores")
            print(f"   Revisar logs y corregir problemas manualmente")

def main():
    """Función principal"""
    if len(sys.argv) != 2:
        print("Uso: python ssl_diagnostics_main.py <dominio>")
        print("Ejemplo: python ssl_diagnostics_main.py 70ideas.com.ar")
        sys.exit(1)
    
    target_domain = sys.argv[1]
    
    # Validar formato de dominio básico
    if '.' not in target_domain:
        print(f"❌ Formato de dominio inválido: {target_domain}")
        sys.exit(1)
    
    diagnostics = SSLDiagnosticsMain(target_domain)
    results = diagnostics.run_complete_diagnosis()
    
    # Código de salida basado en el resultado
    sys.exit(0 if results['success'] else 1)

if __name__ == "__main__":
    main()