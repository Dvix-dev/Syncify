# Sincronizador Spotify → YouTube Music

App de escritorio (Python + CustomTkinter) que copia tus **playlists** y tus canciones con
**"me gusta"** de Spotify a tu biblioteca de **YouTube Music**, con interfaz gráfica.

## Características

- Lista tus playlists propias y colaborativas de Spotify y elige cuáles sincronizar.
- Sincroniza los "me gusta" a una playlist dedicada en YT Music (nombre configurable).
- Opcional: dar "me gusta" 👍 en YT Music a cada canción sincronizada.
- Búsqueda inteligente con coincidencia difusa (ignora acentos, paréntesis, etc.).
- Detecta duplicados: solo añade las canciones que faltan.
- Barra de progreso, registro en vivo y lista de canciones no encontradas.
- Detención en cualquier momento.

## Instalación

Requisitos: Python 3.10 o superior.

```bash
pip install -r requirements.txt
python main.py
```

## Configuración inicial (una sola vez)

### 1. Credenciales de Spotify

1. Ve a https://developer.spotify.com/dashboard e inicia sesión.
2. Crea una app ("Create app") con cualquier nombre.
3. En la configuración de la app añade este **Redirect URI**:
   ```
   http://127.0.0.1:8888/callback
   ```
   y marca las APIs **Web API**.
4. Copia el **Client ID** y el **Client Secret** y pégualos en la app.
5. Pulsa "Conectar con Spotify": se abrirá el navegador para autorizar.

> Nota: desde abril 2025 las apps nuevas de Spotify necesitan estar en "Development mode"
> y tener tu cuenta añadida como usuario de prueba en *User Management* (añádete a ti mismo).

### 2. Conectar YouTube Music

1. Abre https://music.youtube.com en tu navegador e inicia sesión con la cuenta correcta.
2. Pulsa **F12** → pestaña **Red / Network**.
3. Recarga la página y haz clic en cualquier petición dirigida a `music.youtube.com`.
4. Copia todo el bloque de **cabeceras de la petición** (request headers).
5. Pega ese bloque en la ventana "Conectar YouTube Music" de la app y pulsa **Conectar**.

La autenticación se guarda localmente en `~/.spotify_yt_sync/yt_headers_auth.json`
y solo tendrás que repetirlo si caduca.

## Uso

1. Conecta Spotify y YouTube Music.
2. Marca las playlists que quieras copiar (y activa "Incluir me gusta" si quieres).
3. Elige la privacidad de las playlists que se creen.
4. Pulsa **Sincronizar seleccionadas** y observa el registro.

Las playlists se crean en YT Music con el mismo nombre; si ya existen, solo se
añaden las canciones que falten (nunca se borra nada).

## Estructura del proyecto

```
main.py                  # punto de entrada
syncer/
  config.py              # configuración persistente (~/.spotify_yt_sync)
  spotify_client.py      # API de Spotify (spotipy)
  ytmusic_client.py      # API de YouTube Music (ytmusicapi)
  engine.py              # motor de sincronización + coincidencia difusa
  gui.py                 # interfaz gráfica (CustomTkinter)
```

## Limitaciones

- YouTube Music es una API no oficial (`ytmusicapi`); si Google cambia algo puede fallar
  hasta actualizar la librería (`pip install -U ytmusicapi`).
- Algunas canciones no existen en YT Music o tienen títulos distintos: quedarán listadas
  como "sin encontrar".
- La sincronización es incremental (añade lo que falta). No elimina canciones que hayas
  quitado en Spotify ni borra nada de tu biblioteca de YT Music.
