ONLY ROBLOX VISUALIZER — PAQUETE PARA GITHUB

Este ZIP contiene el proyecto fuente y una configuracion de GitHub Actions.
No es el APK: GitHub intentara compilar el APK cuando subas estos archivos.

COMO USARLO
1. Extrae este ZIP en tu telefono o computadora.
2. En GitHub crea un repositorio nuevo (puede ser Public o Private).
3. Dentro del repositorio, usa "Add file" > "Upload files".
4. Sube TODO el contenido que extrajiste, incluyendo la carpeta oculta
   .github. Es importante que .github/workflows/android.yml quede en la raiz
   del repositorio, y que buildozer.spec y main.py tambien queden en la raiz.
5. Confirma con "Commit changes".
6. Abre la pestaña Actions del repositorio. Selecciona
   "Build Only Roblox Visualizer APK" y pulsa "Run workflow" si no inicio
   automaticamente al subir los archivos.
7. Cuando la ejecucion termine con marca verde, abre esa ejecucion y baja a
   "Artifacts". Descarga "Only-Roblox-Visualizer-APK".
8. Extrae el ZIP del artefacto: dentro estara el archivo .apk.

SI NO APARECE ACTIONS
Comprueba que subiste la carpeta .github/workflows/android.yml exactamente
con ese nombre y en la raiz del repositorio. GitHub no ejecuta workflows que
quedan dentro de una carpeta adicional.

SI LA COMPILACION FALLA
Abre la ejecucion roja de Actions y consulta el primer paso que fallo. La
configuracion automatiza Buildozer, pero no puede garantizar que este proyecto
compile sin ajustes. El proyecto aun no ha sido compilado ni probado en un
Motorola fisico.

LIMITACIONES CONOCIDAS DEL CODIGO ORIGINAL
- pytesseract por si solo no incorpora el motor Tesseract ni sus datos de
  idioma. El OCR necesita integracion adicional para funcionar plenamente.
- No incluye un modelo de deteccion de objetos entrenado para Roblox.
- El contenido visual no permite confirmar con certeza si un avatar es un
  jugador real, NPC o bot.
- No es executor, inyector ni lector de memoria de Roblox.
- Usa el permiso oficial Android MediaProjection: Android muestra un dialogo
  de consentimiento y una notificacion mientras la captura esta activa.
- Segun el codigo fuente, los frames se mantienen temporalmente en memoria.

IMPORTANTE SOBRE LA CARPETA .github
En algunos administradores de archivos las carpetas que empiezan con punto
se ocultan. Activa "mostrar archivos ocultos" antes de seleccionar el contenido
para subirlo a GitHub.
