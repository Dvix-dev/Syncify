<div align="center">
  <img src="assets/syncify-logo.svg" alt="Syncify" width="800" />
  <p><strong>Sincroniza tus playlists y canciones favoritas entre Spotify y YouTube Music.</strong></p>
</div>

# Syncify

Aplicación de escritorio con interfaz gráfica que copia tus **playlists** y canciones con
**"me gusta"** de Spotify a tu biblioteca de **YouTube Music**.

> **Importante sobre Spotify:** Spotify exige actualmente una cuenta Premium para usar su
> Web API. No existe un método oficial para saltarse esa limitación. Syncify no intenta
> evadirla ni extraer credenciales: si tu cuenta no es Premium, la conexión puede ser
> rechazada. En ese caso puedes conservar la app instalada y usarla cuando tengas acceso
> Premium; no hay un sustituto oficial equivalente para leer playlists privadas y likes.

## Qué hace

- Lista tus playlists propias y colaborativas de Spotify para elegir cuáles copiar.
- Copia tus canciones con "me gusta" a una playlist configurable en YouTube Music.
- Opcionalmente marca esas canciones con 👍 en YouTube Music.
- Busca coincidencias aunque cambien los acentos, mayúsculas o textos como “Remastered”.
- Evita duplicados: las ejecuciones posteriores solo añaden canciones nuevas.
- No borra nada de YouTube Music.
- Muestra progreso, errores y canciones que no pudo encontrar.

## Instalación

Requisitos: Python 3.10 o superior.

```bash
pip install -r requirements.txt
python main.py
```

## Conectar Spotify

1. Necesitas una cuenta **Spotify Premium** para la Web API.
2. Entra en https://developer.spotify.com/dashboard e inicia sesión.
3. Crea una app y añade este Redirect URI exactamente:
   ```text
   http://127.0.0.1:8888/callback
   ```
4. Copia el **Client ID** y **Client Secret** en Syncify.
5. Pulsa **Conectar con Spotify** y autoriza el acceso en el navegador.

La app solo solicita lectura de playlists y canciones guardadas. Las credenciales se
almacenan localmente en `~/.spotify_yt_sync/config.json`.

## Conectar YouTube Music — guía sencilla

YouTube Music no ofrece una API oficial pública para administrar tu biblioteca personal.
Syncify usa `ytmusicapi`, una biblioteca no oficial que necesita una copia local de los
headers de una sesión ya iniciada en tu navegador.

### Obtener los headers en Chrome o Edge

1. Abre https://music.youtube.com.
2. Inicia sesión con la cuenta donde quieres crear las playlists.
3. Pulsa **F12** para abrir las herramientas de desarrollador.
4. Abre la pestaña **Network / Red**.
5. Recarga la página con **Ctrl+R**.
6. Escribe `browse` en el filtro de peticiones.
7. Haz clic en una petición que tenga método **POST**.
8. En el panel de detalles, pulsa botón derecho sobre la petición y elige:
   **Copy → Copy request headers**.
9. En Syncify pulsa **Conectar YouTube Music**, pega todo el texto y pulsa **Conectar**.

No copies los headers de respuesta ni solo una cookie: debe ser el bloque completo de
**request headers**. Syncify lo convierte automáticamente al archivo de autenticación.

### Seguridad y caducidad

- Los headers contienen una sesión autenticada: **no los compartas ni los publiques**.
- Syncify los guarda en tu equipo, en `~/.spotify_yt_sync/yt_headers_auth.json`.
- Si dejan de funcionar, repite el proceso y reemplaza la autenticación.
- Puedes seleccionar **Usar archivo existente…** si ya tienes un JSON generado por
  `ytmusicapi`.
- También hay un botón **Abrir guía online** que lleva a la documentación actualizada de
  `ytmusicapi`: https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html

## Uso

1. Conecta las dos cuentas.
2. Marca las playlists de Spotify que quieras sincronizar.
3. Activa **Incluir canciones con 'me gusta'** si también quieres copiarlas.
4. Elige si quieres dar "me gusta" en YT Music y la privacidad de las playlists nuevas.
5. Pulsa **Sincronizar seleccionadas**.

Syncify busca una playlist de YT Music con el mismo nombre. Si no existe, la crea. Si
existe, conserva su contenido y añade solo las canciones ausentes.

## Privacidad y limitaciones

- YouTube Music se maneja mediante una API no oficial; Google puede cambiarla.
- Algunas canciones pueden no estar disponibles o tener varias versiones. Se muestran
  como no encontradas para evitar añadir una coincidencia dudosa.
- El modo actual es seguro e incremental: **añade**, pero no elimina ni refleja bajas.
- Spotify Premium es un requisito impuesto por Spotify; no se puede bypassear de forma
  legítima mediante esta app.

## Estructura

```text
main.py                  # punto de entrada
assets/syncify-logo.svg   # logo de Syncify
syncer/
  config.py              # configuración local
  spotify_client.py      # lectura mediante Spotipy
  ytmusic_client.py      # escritura mediante ytmusicapi
  engine.py              # coincidencia y sincronización
  gui.py                 # interfaz gráfica
```
