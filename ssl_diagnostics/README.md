# SSL Diagnostics

Sistema modular para diagnóstico y corrección automática de problemas SSL en servidores con aaPanel/nginx.

## Estructura del Proyecto

```
ssl_diagnostics/
├── core/                    # Módulos principales
│   ├── ssh_manager.py      # Gestión de conexiones SSH
│   ├── nginx_manager.py    # Gestión de nginx
│   ├── ssl_manager.py      # Gestión de certificados SSL
│   ├── user_interaction.py # Sistema de confirmaciones Y/N
│   └── state_manager.py    # Persistencia de estado
├── analyzers/              # Módulos de análisis
│   ├── hosts_analyzer.py   # Análisis de /etc/hosts
│   └── nginx_analyzer.py   # Análisis de configuraciones nginx
├── fixes/                  # Módulos de corrección
│   ├── hosts_fixer.py      # Correcciones de /etc/hosts
│   └── nginx_fixer.py      # Correcciones de nginx
├── reports/                # Informes y documentación
│   └── informe_70ideas_ssl_resolution.md
├── state/                  # Archivos de estado (auto-generado)
├── ssl_diagnostics_main.py # Script principal orquestador
├── ssl_cli.py             # Interfaz de línea de comandos
└── README.md              # Este archivo
```

## Características Principales

### 🔍 Diagnóstico Automático
- Análisis completo de configuraciones nginx
- Detección de problemas en /etc/hosts
- Verificación de certificados SSL
- Identificación de interceptores de requests

### 🔧 Correcciones Interactivas
- Confirmaciones Y/N para cada acción destructiva
- Backups automáticos antes de modificaciones
- Correcciones graduales con verificación

### 📊 Gestión de Estado
- Persistencia de pasos completados
- Omisión automática de pasos ya ejecutados
- Posibilidad de resetear estado o pasos específicos

### 🛡️ Seguridad
- Backups antes de modificaciones críticas
- Verificación de configuraciones antes de aplicar
- Niveles de riesgo para cada operación

## Uso Básico

### Diagnóstico Completo
```bash
python ssl_cli.py diagnose ejemplo.com
```

### Diagnóstico aaPanel (host/puerto/ruta)
```bash
python ssl_cli.py panel-diagnose vps-2191785-x.dattaweb.com --expected-port 9898 --expected-path puerta8
```

Por defecto, si aaPanel está caído el comando intenta levantarlo con `bt start` y luego re-ejecuta el diagnóstico.

Para desactivar ese comportamiento:
```bash
python ssl_cli.py panel-diagnose vps-2191785-x.dattaweb.com --expected-port 9898 --expected-path puerta8 --no-auto-start
```

### Ver Estado Actual
```bash
python ssl_cli.py state ejemplo.com --show
```

### Resetear Estado (empezar desde cero)
```bash
python ssl_cli.py diagnose ejemplo.com --reset
```

### Limpiar Estados Antiguos
```bash
python ssl_cli.py cleanup --days 7
```

## Configuración

Crear archivo `.environment` en el directorio del proyecto:
```
SSH_HOST=ip.del.servidor
SSH_PORT=puerto_ssh
SSH_USER=usuario
SSH_PASSWORD=contraseña
```

## Flujo de Trabajo

1. **Análisis Inicial**: Detecta problemas en hosts, nginx y SSL
2. **Corrección de /etc/hosts**: Limpia entradas malformadas
3. **Corrección de nginx**: Deshabilita interceptores y conflictos
4. **Verificación SSL**: Confirma funcionamiento correcto
5. **Reinicio de Servicios**: Aplica cambios finales

## Casos de Uso Resueltos

- ✅ Dominios mostrando certificado incorrecto
- ✅ Entradas malformadas en /etc/hosts (concatenación de dominios)
- ✅ Configuraciones nginx con prioridad alfabética incorrecta
- ✅ Interceptores catch-all bloqueando dominios específicos
- ✅ Certificados SSL válidos pero mal configurados

## Comandos CLI Disponibles

| Comando | Descripción |
|---------|-------------|
| `diagnose <dominio>` | Ejecuta diagnóstico completo |
| `diagnose <dominio> --reset` | Diagnóstico desde cero |
| `state <dominio> --show` | Muestra estado actual |
| `state <dominio> --reset` | Resetea estado |
| `state <dominio> --clear-step <id>` | Limpia paso específico |
| `cleanup --days <n>` | Limpia estados antiguos |
| `list-states` | Lista todos los estados |
| `panel-diagnose <host> [--expected-port N] [--expected-path ruta]` | Diagnostica acceso aaPanel y lo levanta si está caído |

## Seguridad Operativa

- `panel-diagnose` puede ejecutar `bt start` si aaPanel está caído, pero no toca configuraciones de nginx de sitios.
- Para mantener `70ideas.com.ar` estable, usar `panel-diagnose` antes de aplicar fixes de nginx.

## Desarrollo

### Agregar Nuevo Analizador
1. Crear módulo en `analyzers/`
2. Implementar método `analyze_*`
3. Integrar en `ssl_diagnostics_main.py`

### Agregar Nueva Corrección
1. Crear módulo en `fixes/`
2. Implementar método `fix_*` con confirmaciones
3. Usar `UserInteraction` para prompts Y/N
4. Integrar con `StateManager` para persistencia

### Estructura de Módulos
- Todos los módulos usan type hints
- Manejo de errores con try/catch
- Logs informativos con emojis
- Documentación en docstrings

## Resumen del Caso 70ideas.com.ar

Este sistema fue desarrollado para resolver un problema específico donde:
- `70ideas.com.ar` mostraba el certificado de `circoeguap.com`
- El archivo `/etc/hosts` tenía entradas malformadas concatenando dominios
- Configuraciones nginx con nombres alfabéticamente anteriores interceptaban requests
- El problema se manifestaba solo en el navegador, no en herramientas CLI

La solución involucró:
1. Limpieza completa de `/etc/hosts`
2. Deshabilitación de configuraciones nginx problemáticas
3. Creación de configuración nginx optimizada
4. Verificación de certificados y funcionamiento final

El resultado: SSL funcionando correctamente con certificado válido para el dominio correcto.