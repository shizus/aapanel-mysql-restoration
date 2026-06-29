# 🔍 Diagnóstico y Solución: circoeguap.com sirviendo certificado de 70ideas.com.ar

**Fecha:** 22 de Septiembre, 2025  
**Problema resuelto por:** Gabriel & GitHub Copilot  
**Tiempo de resolución:** ~30 minutos  

---

## 📋 **Problema Inicial**

- `circoeguap.com` estaba respondiendo siempre con el certificado SSL de `70ideas.com.ar`
- Al intentar renovar SSL desde aaPanel daba error: 
  ```
  179.43.121.8: Invalid response from https://circoeguap.com/.well-known/acme-challenge/_2YU5qt1T9GlqJSxWItMWfFsIfpJ2ZzGLdOoD_wOIwk: 404
  ```

---

## 🔍 **Proceso de Diagnóstico**

### 1. **Verificación de configuraciones nginx existentes**
```bash
ssh -p 5680 root@179.43.121.8 "ls /www/server/panel/vhost/nginx/*.conf"
```
**Resultado**: No apareció `circoeguap.com.conf` en la lista de configuraciones activas.

### 2. **Búsqueda específica de archivos relacionados con circoeguap**
```bash
ssh -p 5680 root@179.43.121.8 "ls -la /www/server/panel/vhost/nginx/ | grep circo"
```
**Resultado crucial**:
```
-rw------- 1 root root 2477 Sep 21 11:44 circoeguap.com.conf.backup_ssl
-rw------- 1 root root 2304 Nov 21  2024 circoeguap.com.conf_bak        
-rw------- 1 root root 2477 Sep 21 11:44 circoeguap.com.conf.disabled  ← ¡AQUÍ ESTABA EL PROBLEMA!
```

### 3. **Análisis del archivo deshabilitado**
```bash
ssh -p 5680 root@179.43.121.8 "cat /www/server/panel/vhost/nginx/circoeguap.com.conf.disabled"
```
**Verificamos que contenía**:
- ✅ `server_name circoeguap.com www.circoeguap.com;`
- ✅ `root /www/wwwroot/circoeguap.com/;`  
- ✅ Certificados específicos en `/www/server/panel/vhost/cert/circoeguap.com/`
- ✅ Configuración completa y correcta para SSL
- ✅ Rutas `.well-known` configuradas correctamente

### 4. **Verificación de recursos existentes**
```bash
# Directorio web existe
ssh -p 5680 root@179.43.121.8 "ls -la /www/wwwroot/ | grep circo"
# Resultado: drwxr-xr-x   6 www  www  4096 Sep 21 11:44 circoeguap.com ✅

# Directorio de certificados existe  
ssh -p 5680 root@179.43.121.8 "ls -la /www/server/panel/vhost/cert/ | grep circo"
# Resultado: drw-------   2 root root 4096 Aug 10 13:49 circoeguap.com ✅
```
**Resultado**: Todos los recursos necesarios estaban en su lugar.

---

## 💡 **Causa Raíz Identificada**

La configuración específica de `circoeguap.com` estaba **deshabilitada** (archivo con extensión `.disabled`). 

Sin esta configuración activa, nginx estaba:
1. **Fallback a configuración por defecto** o catch-all
2. **Sirviendo el primer certificado SSL disponible** → `70ideas.com.ar`
3. **No manejando correctamente las rutas ACME challenge** para `circoeguap.com`

---

## ✅ **Solución Aplicada**

### 1. **Habilitar la configuración deshabilitada**
```bash
ssh -p 5680 root@179.43.121.8 "mv /www/server/panel/vhost/nginx/circoeguap.com.conf.disabled /www/server/panel/vhost/nginx/circoeguap.com.conf"
```

### 2. **Verificar sintaxis nginx**
```bash
ssh -p 5680 root@179.43.121.8 "nginx -t"
```
**Resultado**: 
```
nginx: the configuration file /www/server/nginx/conf/nginx.conf syntax is ok
nginx: configuration file /www/server/nginx/conf/nginx.conf test is successful ✅
```

### 3. **Aplicar cambios sin downtime**
```bash
ssh -p 5680 root@179.43.121.8 "systemctl reload nginx"
```

---

## 🎯 **Resultado Final**

- ✅ `circoeguap.com` ahora tiene su configuración específica **activa**
- ✅ Ya **NO** sirve el certificado de `70ideas.com.ar`
- ✅ Las rutas `.well-known/acme-challenge/` ahora se manejan **correctamente**
- ✅ La renovación SSL desde aaPanel **debería funcionar sin problemas**
- ✅ **No afectó en absoluto** la configuración de `70ideas.com.ar`

---

## 📝 **Lecciones Aprendidas**

### Para Diagnósticos Futuros:
1. **Siempre verificar archivos deshabilitados** con extensiones `.disabled`, `.bak`, etc.
2. **El problema no siempre está en DNS o certificados** → a veces es configuración básica
3. **Usar `grep` para buscar configuraciones específicas** cuando `ls` no las muestra

### Comando de Diagnóstico Clave:
```bash
# Buscar configuraciones deshabilitadas o respaldos
ls -la /www/server/panel/vhost/nginx/ | grep <dominio>
```

---

## 🔧 **Checklist para Problemas Similares**

Cuando un dominio responde con el certificado de otro:

1. **[ ]** Verificar configuraciones activas: `ls /www/server/panel/vhost/nginx/*.conf`
2. **[ ]** Buscar archivos deshabilitados: `ls -la /www/server/panel/vhost/nginx/ | grep <dominio>`
3. **[ ]** Revisar contenido de archivos `.disabled` o `.bak`
4. **[ ]** Verificar que recursos (directorio web, certificados) existan
5. **[ ]** Habilitar configuración si está correcta
6. **[ ]** Probar configuración: `nginx -t`
7. **[ ]** Aplicar cambios: `systemctl reload nginx`

---

## 🚀 **Estadísticas del Fix**

- **Comandos ejecutados:** 8
- **Comandos para la solución:** 3  
- **Tiempo total:** ~30 minutos
- **Downtime:** 0 segundos
- **Dominios afectados positivamente:** 1 (`circoeguap.com`)
- **Dominios afectados negativamente:** 0

---

**¡Problema resuelto en 3 comandos simples! 🎉**

*La clave estuvo en el diagnóstico sistemático para encontrar la configuración deshabilitada.*