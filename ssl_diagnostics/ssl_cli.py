#!/usr/bin/env python3
"""
SSL Diagnostics CLI - Herramientas de línea de comandos para diagnóstico SSL
"""

import sys
import os
import argparse
from datetime import datetime

# Agregar el directorio padre al path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ssl_diagnostics.ssl_diagnostics_main import SSLDiagnosticsMain
from ssl_diagnostics.core.state_manager import StateManager, cleanup_old_states

def cmd_diagnose(args):
    """Comando principal de diagnóstico"""
    print(f"🔍 Iniciando diagnóstico SSL para {args.domain}")
    
    if args.reset:
        state_manager = StateManager(args.domain)
        state_manager.reset_state()
        print("🔄 Estado reseteado")
    
    diagnostics = SSLDiagnosticsMain(args.domain)
    results = diagnostics.run_complete_diagnosis()
    
    if results['success']:
        print(f"\n🎉 Diagnóstico completado exitosamente")
        return 0
    else:
        print(f"\n❌ Diagnóstico completado con errores")
        return 1

def cmd_state(args):
    """Comandos de manejo de estado"""
    if not args.domain:
        print("❌ Dominio requerido para comandos de estado")
        return 1
    
    state_manager = StateManager(args.domain)
    
    if args.show:
        state_manager.print_state_summary()
    elif args.reset:
        state_manager.reset_state()
    elif args.clear_step:
        state_manager.clear_step(args.clear_step)
    elif args.clear_all:
        state_manager.clear_all_steps()
    else:
        state_manager.print_state_summary()
    
    return 0

def cmd_cleanup(args):
    """Limpiar estados antiguos"""
    days = args.days or 30
    cleanup_old_states(days=days)
    return 0

def cmd_list_states(args):
    """Listar todos los archivos de estado"""
    state_dir = os.path.join(os.path.dirname(__file__), '..', 'state')
    
    if not os.path.exists(state_dir):
        print("📋 No hay archivos de estado")
        return 0
    
    state_files = [f for f in os.listdir(state_dir) if f.endswith('_state.json')]
    
    if not state_files:
        print("📋 No hay archivos de estado")
        return 0
    
    print(f"📋 Estados encontrados ({len(state_files)}):")
    for state_file in sorted(state_files):
        domain = state_file.replace('_state.json', '').replace('_', '.')
        filepath = os.path.join(state_dir, state_file)
        
        try:
            mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            print(f"   {domain} - {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        except OSError:
            print(f"   {domain} - Error leyendo fecha")
    
    return 0

def main():
    """Función principal de CLI"""
    parser = argparse.ArgumentParser(
        description="SSL Diagnostics - Herramientas para diagnóstico y corrección SSL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s diagnose 70ideas.com.ar              # Diagnóstico completo
  %(prog)s diagnose 70ideas.com.ar --reset      # Diagnóstico desde cero
  %(prog)s state 70ideas.com.ar --show          # Mostrar estado
  %(prog)s state 70ideas.com.ar --reset         # Resetear estado
  %(prog)s cleanup --days 7                     # Limpiar estados > 7 días
  %(prog)s list-states                          # Listar todos los estados
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')
    
    # Comando diagnose
    diagnose_parser = subparsers.add_parser('diagnose', help='Ejecutar diagnóstico SSL completo')
    diagnose_parser.add_argument('domain', help='Dominio a diagnosticar')
    diagnose_parser.add_argument('--reset', action='store_true', 
                                help='Resetear estado antes de empezar')
    diagnose_parser.set_defaults(func=cmd_diagnose)
    
    # Comando state
    state_parser = subparsers.add_parser('state', help='Manejo de estado')
    state_parser.add_argument('domain', help='Dominio del estado')
    state_parser.add_argument('--show', action='store_true', help='Mostrar estado actual')
    state_parser.add_argument('--reset', action='store_true', help='Resetear estado completamente')
    state_parser.add_argument('--clear-step', help='Limpiar un paso específico')
    state_parser.add_argument('--clear-all', action='store_true', help='Limpiar todos los pasos')
    state_parser.set_defaults(func=cmd_state)
    
    # Comando cleanup
    cleanup_parser = subparsers.add_parser('cleanup', help='Limpiar estados antiguos')
    cleanup_parser.add_argument('--days', type=int, default=30,
                                help='Días de antigüedad para limpiar (default: 30)')
    cleanup_parser.set_defaults(func=cmd_cleanup)
    
    # Comando list-states
    list_parser = subparsers.add_parser('list-states', help='Listar todos los archivos de estado')
    list_parser.set_defaults(func=cmd_list_states)
    
    # Parse argumentos
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print(f"\n❌ Interrumpido por el usuario")
        return 130
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())