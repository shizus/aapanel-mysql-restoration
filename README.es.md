# Herramienta de Verificación de Servidor

[![Versión de Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Licencia](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Mantenimiento](https://img.shields.io/badge/Mantenido%3F-sí-green.svg)](https://github.com/yourusername/server-health-check/graphs/commit-activity)

Una herramienta Python para monitorear y corregir automáticamente problemas comunes con aaPanel y los logs binarios de MySQL en servidores remotos.

## Problema

Al administrar servidores con aaPanel y MySQL, pueden ocurrir varios problemas comunes:

1. Los servicios de aaPanel pueden detenerse inesperadamente
2. Los logs binarios de MySQL pueden volverse inconsistentes, particularmente cuando el archivo `mysql-bin.index` hace referencia a archivos de log binarios que no existen
3. Estos problemas a menudo requieren intervención manual y conocimiento de comandos específicos

Esta herramienta automatiza la detección y resolución de estos problemas, reduciendo el tiempo de inactividad y simplificando el mantenimiento del servidor.

## Características

- Conexión a servidor remoto vía SSH
- Verificación automática del estado del servicio aaPanel y reinicio
- Verificación y reparación de logs binarios de MySQL
- Backup automático antes de cualquier cambio crítico
- Solicitudes interactivas para operaciones potencialmente peligrosas

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/yourusername/server-health-check.git
cd server-health-check

# Instalar Poetry si aún no lo tienes
curl -sSL https://install.python-poetry.org | python3 -

# Instalar dependencias
poetry install

# Activar el entorno virtual
poetry shell
```

## Uso

### Modo Interactivo
```bash
poetry run server-health-check
```

La herramienta te solicitará:
- Dirección IP del servidor
- Puerto SSH (por defecto: 22)
- Nombre de usuario (por defecto: root)
- Contraseña

### Modo Línea de Comandos
```bash
poetry run server-health-check -H hostname -p puerto -u usuario [-y]
```

Opciones:
- `-H, --host`: Dirección IP o nombre del servidor
- `-p, --port`: Puerto SSH (por defecto: 22)
- `-u, --user`: Nombre de usuario SSH (por defecto: root)
- `-P, --password`: Contraseña SSH (no recomendado, mejor usar modo interactivo)
- `-y, --yes`: Responder automáticamente sí a todas las preguntas

Ejemplo:
```bash
poetry run server-health-check -H example.com -p 22 -u root -y
```

## Cómo Funciona

1. **Conexión SSH**: Establece una conexión segura con tu servidor
2. **Verificación de aaPanel**: 
   - Verifica si los servicios de aaPanel están ejecutándose
   - Los inicia automáticamente si están caídos
3. **Verificación de Logs Binarios de MySQL**:
   - Escanea los archivos de log binarios existentes
   - Busca inconsistencias en mysql-bin.index
   - Crea un backup del archivo index
   - Elimina referencias inválidas
   - Reinicia MySQL si es necesario

## Contribuciones

¡Las contribuciones son bienvenidas! No dudes en enviar un Pull Request.

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.
