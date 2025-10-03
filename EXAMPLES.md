# 📖 Ejemplos de Uso - Nueva Versión

## 🎨 Modo GUI (Interfaz Gráfica)

### Inicio Básico
```powershell
python main_new.py --gui
```

**Pasos en la GUI:**
1. Selecciona tu dispositivo de audio del dropdown
2. Configura idioma origen (From) y destino (To)
3. Selecciona el traductor (google o deepl)
4. Presiona "▶ Start"
5. ¡Habla o reproduce audio!
6. Ve las transcripciones y traducciones en tiempo real

### Ventajas de la GUI
- ✅ No necesitas recordar comandos
- ✅ Visualización clara de transcripciones y traducciones
- ✅ Fácil cambio de configuración
- ✅ Estadísticas en tiempo real

---

## 💻 Modo CLI (Línea de Comandos)

### Ejemplo 1: Transcripción Básica
Inglés a Español usando Google Translate:

```powershell
python main_new.py --device airpods --src en --tgt es
```

### Ejemplo 2: Usando DeepL (Mejor Calidad)
Asegúrate de tener `DEEPL_API_KEY` en tu `.env`:

```powershell
python main_new.py --device discord --src en --tgt es --translator deepl
```

### Ejemplo 3: Solo Transcripción (Sin Traducción)
```powershell
python main_new.py --device speakers --src en --translator none
```

### Ejemplo 4: Diferentes Idiomas

**Francés a Inglés:**
```powershell
python main_new.py --device chrome --src fr --tgt en
```

**Japonés a Español:**
```powershell
python main_new.py --device zoom --src ja --tgt es
```

**Alemán a Inglés:**
```powershell
python main_new.py --device teams --src de --tgt en
```

### Ejemplo 5: Sin Resultados Intermedios
Para menor verbosidad:

```powershell
python main_new.py --device airpods --src en --tgt es --no-interim
```

### Ejemplo 6: Modelo Diferente de Deepgram
Modelos disponibles: nova-2 (mejor), nova, base (más rápido)

```powershell
python main_new.py --device airpods --src en --tgt es --model base
```

### Ejemplo 7: Ajustar Sensibilidad de Pausas
Cambiar cuántos milisegundos de silencio finalizan una frase:

```powershell
# Más sensible (pausas cortas = nueva frase)
python main_new.py --device airpods --src en --tgt es --endpointing 200

# Menos sensible (permite pausas más largas)
python main_new.py --device airpods --src en --tgt es --endpointing 500
```

---

## 🔍 Comandos de Utilidad

### Listar Dispositivos Disponibles
```powershell
python main_new.py --list-devices
```

**Salida esperada:**
```
Available loopback devices:

  [ 8] Speakers (Loopback)
  [12] AirPods (Loopback)
  [15] Discord (Loopback)
```

### Probar Captura de Audio
Graba 10 segundos para verificar que el dispositivo funciona:

```powershell
python main_new.py --test-capture airpods
```

Esto creará un archivo `test_capture_YYYYMMDD_HHMMSS.wav` que puedes reproducir.

---

## 🎯 Casos de Uso Reales

### Caso 1: Traducir Reuniones de Zoom
```powershell
# Primero, encuentra el dispositivo de Zoom
python main_new.py --list-devices

# Luego úsalo
python main_new.py --device zoom --src en --tgt es
```

### Caso 2: Subtítulos de YouTube en Tiempo Real
```powershell
python main_new.py --device chrome --src en --tgt es
```

### Caso 3: Traducir Podcasts
```powershell
python main_new.py --device spotify --src en --tgt es --translator deepl
```

### Caso 4: Aprender Idiomas (Solo Transcripción)
```powershell
# Solo transcribe para practicar comprensión
python main_new.py --device netflix --src es --translator none
```

### Caso 5: Reuniones Multilingües
```powershell
# Alemán a Español con alta calidad
python main_new.py --device teams --src de --tgt es --translator deepl --model nova-2
```

---

## ⚙️ Configuración Avanzada

### Archivo .env Completo
```env
# Requerido
DEEPGRAM_API_KEY=tu_clave_deepgram_aqui

# Opcional (para mejor traducción)
DEEPL_API_KEY=tu_clave_deepl_aqui
```

### Script de Inicio Rápido
Crea un archivo `start.ps1`:

```powershell
# start.ps1
$env:DEEPGRAM_API_KEY="tu_clave"
python main_new.py --device airpods --src en --tgt es --translator deepl
```

Luego ejecuta:
```powershell
.\start.ps1
```

---

## 🚀 Optimizaciones Automáticas

La nueva versión incluye optimizaciones que funcionan automáticamente:

### 1. Caché de Traducciones
```
Primera vez:  "Hello" -> "Hola" (500ms)
Segunda vez:  "Hello" -> "Hola" (1ms)  ⚡ Desde caché!
```

### 2. Traducción Asíncrona
```
Antes:  Transcribir ⏸️ → Traducir ⏸️ → Mostrar
Ahora:  Transcribir → Mostrar | Traducir en paralelo ⚡
```

### 3. Sin Bloqueos
La transcripción nunca se detiene esperando traducciones.

---

## 📊 Comparación de Comandos

| Acción | Versión Anterior | Nueva Versión |
|--------|------------------|---------------|
| Inicio GUI | ❌ No disponible | `python main_new.py --gui` |
| CLI básico | `python main.py --device x` | `python main_new.py --device x` |
| Listar devices | `python main.py --list-devices` | `python main_new.py --list-devices` |
| Test capture | `python main.py --test-capture x` | `python main_new.py --test-capture x` |

---

## 💡 Tips y Trucos

### Tip 1: Encuentra el Nombre del Dispositivo
Los dispositivos de loopback usan el nombre de la app. Busca por:
- `chrome` para Google Chrome
- `discord` para Discord
- `zoom` para Zoom
- `airpods` para AirPods
- `speakers` para altavoces del sistema

### Tip 2: El Caché Mejora con el Tiempo
Cuanto más uses el sistema con el mismo contenido (ej: reuniones recurrentes), más rápido será.

### Tip 3: Google vs DeepL
- **Google Translate**: Gratis, bueno para la mayoría de casos
- **DeepL**: Requiere API key, mejor calidad para textos profesionales

### Tip 4: Ajusta Endpointing Según Tu Caso
- **Conversaciones rápidas**: `--endpointing 200`
- **Presentaciones/monólogos**: `--endpointing 500`
- **Default (balanceado)**: `--endpointing 300`

### Tip 5: Usa la GUI para Explorar
La GUI es perfecta para:
- Encontrar el dispositivo correcto
- Probar diferentes configuraciones
- Ver qué funciona mejor

---

## 🐛 Troubleshooting Rápido

**Problema:** No veo mi dispositivo
```powershell
# Solución: Reproduce audio primero
python main_new.py --list-devices
# Los dispositivos solo aparecen cuando hay audio activo
```

**Problema:** Traducción lenta
```powershell
# Solución: Usa Google en vez de DeepL
python main_new.py --device x --src en --tgt es --translator google
```

**Problema:** Muchos mensajes intermedios
```powershell
# Solución: Desactiva interim results
python main_new.py --device x --src en --tgt es --no-interim
```

---

¿Más preguntas? Consulta:
- `README_NEW.md` - Documentación completa
- `MIGRATION.md` - Guía de migración
- El código en `src/` - Ahora está bien organizado y comentado!
