#!/usr/bin/env python3
"""
State Manager - Persistencia de estado para evitar repetir pasos completados
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, Set

class StateManager:
    def __init__(self, domain: str, state_dir: Optional[str] = None):
        self.domain = domain
        self.state_dir = state_dir or os.path.join(os.path.dirname(__file__), '..', 'state')
        self.state_file = os.path.join(self.state_dir, f"{domain.replace('.', '_')}_state.json")
        
        # Crear directorio state si no existe
        os.makedirs(self.state_dir, exist_ok=True)
        
        self.state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Cargar estado desde archivo"""
        default_state = {
            'domain': self.domain,
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'completed_steps': [],
            'session_data': {},
            'analysis_results': {},
            'version': '1.0'
        }
        
        if not os.path.exists(self.state_file):
            return default_state
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                
            # Verificar que es para el dominio correcto
            if state.get('domain') != self.domain:
                print(f"⚠️  Estado existente es para {state.get('domain')}, creando nuevo estado para {self.domain}")
                return default_state
            
            # Actualizar campos que podrían faltar
            for key, value in default_state.items():
                if key not in state:
                    state[key] = value
            
            return state
        
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Error cargando estado, creando nuevo: {e}")
            return default_state
    
    def _save_state(self):
        """Guardar estado actual al archivo"""
        try:
            self.state['last_updated'] = datetime.now().isoformat()
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        
        except IOError as e:
            print(f"⚠️  Error guardando estado: {e}")
    
    def is_step_completed(self, step_id: str) -> bool:
        """Verificar si un paso ya fue completado"""
        return step_id in self.state['completed_steps']
    
    def mark_step_completed(self, step_id: str, details: Optional[Dict[str, Any]] = None):
        """Marcar un paso como completado"""
        if step_id not in self.state['completed_steps']:
            self.state['completed_steps'].append(step_id)
        
        # Guardar detalles del paso si se proporcionan
        if details:
            if 'step_details' not in self.state:
                self.state['step_details'] = {}
            self.state['step_details'][step_id] = {
                'completed_at': datetime.now().isoformat(),
                'details': details
            }
        
        self._save_state()
    
    def get_completed_steps(self) -> Set[str]:
        """Obtener conjunto de pasos completados"""
        return set(self.state['completed_steps'])
    
    def clear_step(self, step_id: str):
        """Limpiar un paso específico (forzar que se ejecute de nuevo)"""
        if step_id in self.state['completed_steps']:
            self.state['completed_steps'].remove(step_id)
        
        if 'step_details' in self.state and step_id in self.state['step_details']:
            del self.state['step_details'][step_id]
        
        self._save_state()
        print(f"🔄 Paso {step_id} marcado para re-ejecutar")
    
    def clear_all_steps(self):
        """Limpiar todos los pasos (empezar desde cero)"""
        self.state['completed_steps'] = []
        self.state['step_details'] = {}
        self._save_state()
        print("🔄 Todos los pasos marcados para re-ejecutar")
    
    def save_analysis_result(self, analysis_type: str, result: Dict[str, Any]):
        """Guardar resultado de análisis para referencia futura"""
        self.state['analysis_results'][analysis_type] = {
            'timestamp': datetime.now().isoformat(),
            'result': result
        }
        self._save_state()
    
    def get_analysis_result(self, analysis_type: str) -> Optional[Dict[str, Any]]:
        """Obtener resultado de análisis previo"""
        if analysis_type in self.state['analysis_results']:
            return self.state['analysis_results'][analysis_type]['result']
        return None
    
    def save_session_data(self, key: str, value: Any):
        """Guardar datos de sesión"""
        self.state['session_data'][key] = value
        self._save_state()
    
    def get_session_data(self, key: str, default: Any = None) -> Any:
        """Obtener datos de sesión"""
        return self.state['session_data'].get(key, default)
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Obtener resumen del estado actual"""
        return {
            'domain': self.state['domain'],
            'created_at': self.state['created_at'],
            'last_updated': self.state['last_updated'],
            'total_completed_steps': len(self.state['completed_steps']),
            'completed_steps': self.state['completed_steps'],
            'has_analysis_results': len(self.state.get('analysis_results', {})) > 0,
            'state_file': self.state_file
        }
    
    def print_state_summary(self):
        """Imprimir resumen del estado"""
        summary = self.get_state_summary()
        
        print(f"\n📊 Estado actual para {summary['domain']}:")
        print(f"   Archivo: {summary['state_file']}")
        print(f"   Creado: {summary['created_at']}")
        print(f"   Actualizado: {summary['last_updated']}")
        print(f"   Pasos completados: {summary['total_completed_steps']}")
        
        if summary['completed_steps']:
            print(f"   Pasos: {', '.join(summary['completed_steps'])}")
        
        if summary['has_analysis_results']:
            analysis_types = list(self.state.get('analysis_results', {}).keys())
            print(f"   Análisis guardados: {', '.join(analysis_types)}")
    
    def reset_state(self):
        """Resetear completamente el estado"""
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
            print(f"🗑️  Estado eliminado: {self.state_file}")
        
        self.state = self._load_state()
        print(f"🔄 Estado reseteado para {self.domain}")

# Función de utilidad para limpiar estados antiguos
def cleanup_old_states(state_dir: Optional[str] = None, days: int = 30):
    """Limpiar archivos de estado más antiguos que X días"""
    if not state_dir:
        state_dir = os.path.join(os.path.dirname(__file__), '..', 'state')
    
    if not os.path.exists(state_dir):
        return
    
    from datetime import datetime, timedelta
    cutoff_date = datetime.now() - timedelta(days=days)
    
    cleaned_count = 0
    for filename in os.listdir(state_dir):
        if filename.endswith('_state.json'):
            filepath = os.path.join(state_dir, filename)
            try:
                # Verificar fecha de modificación del archivo
                mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                if mod_time < cutoff_date:
                    os.remove(filepath)
                    cleaned_count += 1
                    print(f"🗑️  Estado antiguo eliminado: {filename}")
            except OSError:
                continue
    
    if cleaned_count > 0:
        print(f"✅ {cleaned_count} estados antiguos eliminados")
    else:
        print("ℹ️  No hay estados antiguos para limpiar")