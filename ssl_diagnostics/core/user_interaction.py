#!/usr/bin/env python3
"""
User Interaction - Sistema de confirmaciones interactivas con persistencia
"""

import os
from typing import Set, Optional
from .state_manager import StateManager

class UserInteraction:
    def __init__(self, domain: Optional[str] = None):
        self.domain = domain
        self.state_manager: Optional[StateManager] = None
        self.completed_steps: Set[str] = set()
        
        # Si se proporciona dominio, usar state manager
        if domain:
            self.state_manager = StateManager(domain)
            self.completed_steps = self.state_manager.get_completed_steps()
    
    def confirm(self, message: str) -> bool:
        """Mostrar prompt Y/N y obtener confirmación del usuario"""
        while True:
            response = input(f"{message} (Y/n): ").strip().lower()
            
            if response in ['y', 'yes', 'sí', 'si', '']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                print("Por favor responde Y (sí) o N (no)")
    
    def should_continue(self, step_id: str, description: str) -> bool:
        """Verificar si debe continuar con un paso (considerando si ya fue completado)"""
        # Verificar en state manager primero si está disponible
        if self.state_manager and self.state_manager.is_step_completed(step_id):
            print(f"⏭️  Paso ya completado: {description}")
            return False
        
        # Verificar en memoria local
        if step_id in self.completed_steps:
            print(f"⏭️  Paso ya completado: {description}")
            return False
        
        return self.confirm(f"🔧 {description} ¿Continuar?")
    
    def mark_step_completed(self, step_id: str, details: Optional[dict] = None):
        """Marcar un paso como completado"""
        self.completed_steps.add(step_id)
        
        # Guardar en state manager si está disponible
        if self.state_manager:
            self.state_manager.mark_step_completed(step_id, details)
        
        print(f"✅ Paso completado: {step_id}")
    
    def reset_completed_steps(self):
        """Resetear todos los pasos completados"""
        self.completed_steps.clear()
        
        if self.state_manager:
            self.state_manager.clear_all_steps()
        
        print("🔄 Pasos completados reseteados")
    
    def reset_specific_step(self, step_id: str):
        """Resetear un paso específico"""
        self.completed_steps.discard(step_id)
        
        if self.state_manager:
            self.state_manager.clear_step(step_id)
        
        print(f"🔄 Paso {step_id} reseteado")
    
    def list_completed_steps(self):
        """Listar pasos completados"""
        if self.completed_steps:
            print("📋 Pasos completados:")
            for step in sorted(self.completed_steps):
                print(f"   ✅ {step}")
        else:
            print("📋 No hay pasos completados")
    
    def show_state_summary(self):
        """Mostrar resumen del estado si hay state manager"""
        if self.state_manager:
            self.state_manager.print_state_summary()
        else:
            self.list_completed_steps()
    
    def confirm_action(self, 
                      problem_description: str, 
                      proposed_solution: str,
                      step_id: Optional[str] = None,
                      risk_level: str = "MEDIO") -> bool:
        """
        Solicitar confirmación del usuario para realizar una acción
        
        Args:
            problem_description: Descripción del problema detectado
            proposed_solution: Descripción de la solución propuesta  
            step_id: ID único del paso (para skip de pasos completados)
            risk_level: BAJO/MEDIO/ALTO
        
        Returns:
            True si el usuario acepta, False si rechaza
        """
        
        # Verificar si el paso ya fue completado
        if step_id and (
            (self.state_manager and self.state_manager.is_step_completed(step_id)) or
            step_id in self.completed_steps
        ):
            print(f"⏭️  Paso '{step_id}' ya fue completado anteriormente. Saltando...")
            return False
        
        # Mostrar información del problema y solución
        print("\n" + "="*60)
        print("🚨 PROBLEMA DETECTADO")
        print("="*60)
        print(f"📋 Descripción: {problem_description}")
        print(f"🔧 Solución propuesta: {proposed_solution}")
        print(f"⚠️  Nivel de riesgo: {risk_level}")
        print("="*60)
        
        # Solicitar confirmación
        while True:
            response = input("¿Proceder con esta corrección? (Y/N/S para Skip): ").upper().strip()
            
            if response in ['Y', 'YES', 'SI', 'S', '1']:
                if step_id:
                    self.mark_step_completed(step_id, {'solution': proposed_solution})
                return True
            elif response in ['N', 'NO', '0']:
                print("❌ Acción cancelada por el usuario")
                return False
            elif response in ['SKIP']:
                if step_id:
                    self.mark_step_completed(step_id, {'skipped': True, 'reason': 'Saltado por el usuario'})
                print("⏭️  Paso saltado por el usuario")
                return False
            else:
                print("❓ Por favor responde Y (Si), N (No), o SKIP (Saltar)")
    
    def info(self, message: str):
        """Mostrar mensaje informativo"""
        print(f"ℹ️  {message}")
    
    def warning(self, message: str):
        """Mostrar mensaje de advertencia"""
        print(f"⚠️  {message}")
    
    def error(self, message: str):
        """Mostrar mensaje de error"""
        print(f"❌ {message}")
    
    def success(self, message: str):
        """Mostrar mensaje de éxito"""
        print(f"✅ {message}")