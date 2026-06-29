#!/usr/bin/env python3
"""
AApanel Analyzer - Diagnostico de acceso al panel por host/puerto/ruta.

Este modulo es de solo lectura: no modifica archivos remotos.
"""

from typing import Dict, Any, List, Optional
from ..core.ssh_manager import SSHManager


class AAPanelAnalyzer:
    def __init__(self, ssh_manager: SSHManager):
        self.ssh = ssh_manager
        self.vhost_dir = "/www/server/panel/vhost/nginx"

    def _run(self, command: str):
        return self.ssh.execute_command(command)

    def _read_single_line_file(self, filepath: str) -> str:
        stdout, _, exit_code = self._run(f"test -f {filepath} && head -n 1 {filepath}")
        if exit_code != 0:
            return ""
        return stdout.strip()

    def start_aapanel_if_needed(self) -> Dict[str, Any]:
        """Levanta aaPanel si esta caido y devuelve resultado de la operacion."""
        result: Dict[str, Any] = {
            "attempted": False,
            "started": False,
            "already_running": False,
            "status_output": "",
            "start_output": "",
            "error": "",
        }

        status_stdout, status_stderr, status_code = self._run("bt status")
        status_text = f"{status_stdout}\n{status_stderr}".strip()
        result["status_output"] = status_text

        status_l = status_stdout.lower()
        is_running = "running" in status_l and "not running" not in status_l
        if status_code == 0 and is_running:
            result["already_running"] = True
            return result

        result["attempted"] = True
        start_stdout, start_stderr, start_code = self._run("bt start")
        result["start_output"] = f"{start_stdout}\n{start_stderr}".strip()

        # Verificar nuevamente el estado
        verify_stdout, verify_stderr, _ = self._run("bt status")
        verify_l = verify_stdout.lower()
        result["status_output"] = f"{verify_stdout}\n{verify_stderr}".strip()
        result["started"] = start_code == 0 and ("running" in verify_l and "not running" not in verify_l)

        if not result["started"] and not result["already_running"]:
            result["error"] = "No se pudo levantar aaPanel con bt start"

        return result

    def analyze_panel_endpoint(
        self,
        public_host: str,
        expected_port: Optional[int] = None,
        expected_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        expected_path = (expected_path or "").strip("/")

        result: Dict[str, Any] = {
            "public_host": public_host,
            "expected_port": expected_port,
            "expected_path": expected_path,
            "detected_port": None,
            "detected_path": "",
            "detected_bound_domain": "",
            "aapanel_running": False,
            "port_listening": False,
            "host_vhost_matches": [],
            "path_matches": [],
            "probe_https_host_only": "",
            "probe_https_host_port_path": "",
            "issues": [],
            "recommendations": [],
        }

        # 1) Servicio aaPanel
        stdout, _, _ = self._run("bt status")
        status_l = stdout.lower()
        result["aapanel_running"] = "running" in status_l and "not running" not in status_l
        if not result["aapanel_running"]:
            result["issues"].append("aaPanel no parece estar en ejecucion (bt status).")
            result["recommendations"].append("Levantar aaPanel con 'bt start' y volver a diagnosticar.")

        # 2) Configuracion base aaPanel
        detected_port = self._read_single_line_file("/www/server/panel/data/port.pl")
        detected_path = self._read_single_line_file("/www/server/panel/data/admin_path.pl")
        detected_domain = self._read_single_line_file("/www/server/panel/data/domain.conf")

        if detected_port.isdigit():
            result["detected_port"] = int(detected_port)
        result["detected_path"] = detected_path.strip("/")
        result["detected_bound_domain"] = detected_domain

        if expected_port is not None and result["detected_port"] is not None and result["detected_port"] != expected_port:
            result["issues"].append(
                f"Puerto esperado {expected_port}, pero aaPanel tiene {result['detected_port']}."
            )
            result["recommendations"].append(
                f"Alinear el puerto esperado con aaPanel o ajustar aaPanel al puerto {expected_port}."
            )

        if expected_path and result["detected_path"] and result["detected_path"] != expected_path:
            result["issues"].append(
                f"Ruta esperada '{expected_path}', pero aaPanel tiene '{result['detected_path']}'."
            )
            result["recommendations"].append(
                "Usar la ruta real de aaPanel o actualizar la ruta de entrada en aaPanel."
            )

        # 3) Verificar socket escuchando
        listen_port = result["detected_port"] or expected_port
        if listen_port:
            _, _, exit_code = self._run(
                f"ss -lntp 2>/dev/null | grep -E ':{listen_port}([[:space:]]|$)' >/dev/null"
            )
            result["port_listening"] = exit_code == 0
            if not result["port_listening"]:
                result["issues"].append(f"No se detecta proceso escuchando en el puerto {listen_port}.")
                result["recommendations"].append(
                    f"Revisar firewall/servicio y confirmar que aaPanel escuche en {listen_port}."
                )

        # 4) Revisar nginx para host y ruta esperados
        escaped_host = public_host.replace(".", "\\.")
        host_cmd = (
            "grep -R --line-number -E "
            f"'server_name[^;]*\\b{escaped_host}\\b' {self.vhost_dir}/*.conf 2>/dev/null"
        )
        host_stdout, _, _ = self._run(host_cmd)
        host_matches = [line.strip() for line in host_stdout.splitlines() if line.strip()]
        result["host_vhost_matches"] = host_matches

        if not host_matches:
            result["issues"].append(
                "No hay vhost nginx activo con server_name para el host publico indicado."
            )
            result["recommendations"].append(
                "Crear un vhost dedicado para ese host o definir el comportamiento por default_server."
            )

        if expected_path:
            path_cmd = (
                "grep -R --line-number -E "
                f"'location\\s+/?{expected_path}(/|\\s|\\{{)' {self.vhost_dir}/*.conf 2>/dev/null"
            )
            path_stdout, _, _ = self._run(path_cmd)
            path_matches = [line.strip() for line in path_stdout.splitlines() if line.strip()]
            result["path_matches"] = path_matches

            if not path_matches:
                result["issues"].append(
                    f"No se encontro una location para '/{expected_path}' en vhosts activos."
                )
                result["recommendations"].append(
                    f"Agregar location /{expected_path}/ (o ajustar la ruta) en el vhost correcto."
                )

        # 5) Probes HTTPS para ver comportamiento real
        host_only_cmd = (
            f"curl -k -s -o /dev/null -w '%{{http_code}}|%{{redirect_url}}' https://{public_host}/"
        )
        host_only_stdout, _, _ = self._run(host_only_cmd)
        result["probe_https_host_only"] = host_only_stdout.strip()

        if listen_port:
            probe_path = expected_path or result["detected_path"]
            path_suffix = f"/{probe_path}/" if probe_path else "/"
            host_port_path_cmd = (
                f"curl -k -s -o /dev/null -w '%{{http_code}}|%{{redirect_url}}' "
                f"https://{public_host}:{listen_port}{path_suffix}"
            )
            host_port_path_stdout, _, _ = self._run(host_port_path_cmd)
            result["probe_https_host_port_path"] = host_port_path_stdout.strip()

        return result

    def format_summary(self, analysis: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("\n=== Diagnostico aaPanel endpoint (solo lectura) ===")
        lines.append(f"Host publico: {analysis['public_host']}")
        lines.append(f"Puerto esperado: {analysis['expected_port']}")
        lines.append(f"Ruta esperada: /{analysis['expected_path']}/" if analysis['expected_path'] else "Ruta esperada: (no definida)")
        lines.append(f"aaPanel running: {'SI' if analysis['aapanel_running'] else 'NO'}")
        lines.append(f"Puerto detectado (aaPanel): {analysis['detected_port']}")
        lines.append(f"Ruta detectada (aaPanel): /{analysis['detected_path']}/" if analysis['detected_path'] else "Ruta detectada (aaPanel): (vacia)")
        lines.append(f"Dominio vinculado en aaPanel: {analysis['detected_bound_domain'] or '(vacio)'}")
        lines.append(f"Puerto escuchando: {'SI' if analysis['port_listening'] else 'NO'}")
        lines.append(f"Probe https://host/: {analysis['probe_https_host_only'] or '(sin respuesta)'}")
        lines.append(f"Probe https://host:puerto/ruta/: {analysis['probe_https_host_port_path'] or '(sin respuesta)'}")

        if analysis['host_vhost_matches']:
            lines.append("\nVhosts con server_name del host publico:")
            lines.extend([f"- {line}" for line in analysis['host_vhost_matches']])

        if analysis['path_matches']:
            lines.append("\nLocations que matchean la ruta esperada:")
            lines.extend([f"- {line}" for line in analysis['path_matches']])

        if analysis['issues']:
            lines.append("\nProblemas detectados:")
            lines.extend([f"- {issue}" for issue in analysis['issues']])
        else:
            lines.append("\nProblemas detectados: ninguno")

        if analysis['recommendations']:
            lines.append("\nRecomendaciones:")
            lines.extend([f"- {rec}" for rec in analysis['recommendations']])

        lines.append("\nNota: este comando puede ejecutar bt start si aaPanel esta caido.")
        return "\n".join(lines)
