ONLY ROBLOX VISUALIZER - SOURCE PROJECT

IMPORTANT
This is a source project for an Android APK, not a standalone Pydroid 3 script.
The original FileChooser/gallery flow has been removed. Frames are captured with
Android MediaProjection, cropped in memory, passed to Python as JPEG bytes and
not written to the phone's storage.

PROJECT FILES
- main.py: Kivy interface, Android permission request, frame polling, optional OCR.
- src/android/.../ScreenCaptureService.java: foreground service and MediaProjection.
- extra_manifest.xml: Android foreground-service permissions.
- extra_manifest_application_arguments.xml: service declaration.
- buildozer.spec: packaging configuration for Buildozer/python-for-android.

BUILD REQUIREMENT
Build the APK with Buildozer/python-for-android in a supported Linux build
environment. Pydroid 3 cannot compile this native Java service just by running
main.py. The Java source must be included in the APK and the XML declarations
must be merged into the Android manifest.

USE
1. Build and install the APK.
2. Open Only Roblox Visualizer and set X, Y, width and height as percentages.
   X/Y are the top-left position; width/height are the region size.
3. Tap Visualizar and accept Android's screen-capture permission.
4. Switch to Roblox. The foreground capture service continues collecting frames.
5. Return to the visualizer to see the latest captured frame and analysis.
6. Tap Detener to end the MediaProjection session.

PRIVACY
Frames are held temporarily in RAM and are not saved to gallery or storage by
this project. Android shows its screen-capture permission flow and an ongoing
foreground-service notification. Stop capture when finished.

LIMITATIONS
- The code's OCR is optional. pytesseract alone is not the Tesseract executable;
  the OCR engine and language data must also be bundled/configured in the APK.
- The project does not include an object-detection model trained for Roblox.
- Pixels/text cannot reliably prove whether an avatar is a real player, NPC, or
  bot. It can only report visible labels and uncertain visual clues.
- This project is not an exploit, executor, injector, or Roblox memory reader.

NOTE
The project is a starter implementation and has not been compiled/tested on the
user's Motorola device in this environment. Device-specific build fixes may be
needed depending on the Buildozer/python-for-android versions used.
