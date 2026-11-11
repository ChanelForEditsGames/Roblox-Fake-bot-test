import base64
import re
from io import BytesIO
from datetime import datetime

from PIL import Image as PILImage

from kivy.app import App
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.clipboard import Clipboard
from kivy.uix.image import Image as KivyImage  # Registra el widget Image para KV.
from kivy.uix.gridlayout import GridLayout  # Registra GridLayout para KV.
from kivy.uix.popup import Popup
from kivy.uix.label import Label

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    from jnius import autoclass
    from android import activity, mActivity
    ANDROID_BRIDGE_AVAILABLE = True
except Exception:
    autoclass = None
    activity = None
    mActivity = None
    ANDROID_BRIDGE_AVAILABLE = False


REQUEST_CAPTURE = 7319
SERVICE_CLASS = "org.onlyroblox.visualizer.ScreenCaptureService"

KV = r"""
BoxLayout:
    orientation: "vertical"
    padding: dp(10)
    spacing: dp(7)
    canvas.before:
        Color:
            rgba: 0.035, 0.045, 0.075, 1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        size_hint_y: None
        height: dp(44)
        Label:
            text: "[b]ONLY ROBLOX VISUALIZER[/b]"
            markup: True
            font_size: "17sp"
            color: 0.4, 0.7, 1, 1
        Label:
            id: status
            text: "DETENIDO"
            font_size: "11sp"
            color: 0.75, 0.83, 0.95, 1

    BoxLayout:
        size_hint_y: None
        height: dp(44)
        spacing: dp(5)
        Button:
            text: "Visualizar"
            on_release: app.start_capture()
        Button:
            text: "Pausar"
            on_release: app.pause()
        Button:
            text: "Detener"
            on_release: app.stop()
        Button:
            text: "Eliminar frame"
            on_release: app.delete_frame()

    Label:
        text: "REGIÓN DE PANTALLA (porcentaje)"
        size_hint_y: None
        height: dp(22)
        color: 0.4, 0.7, 1, 1

    GridLayout:
        cols: 4
        size_hint_y: None
        height: dp(54)
        spacing: dp(4)
        Label:
            text: "X %"
        TextInput:
            id: crop_x
            text: "0"
            input_filter: "int"
            multiline: False
            hint_text: "0"
        Label:
            text: "Y %"
        TextInput:
            id: crop_y
            text: "0"
            input_filter: "int"
            multiline: False
            hint_text: "0"
        Label:
            text: "Ancho %"
        TextInput:
            id: crop_w
            text: "100"
            input_filter: "int"
            multiline: False
        Label:
            text: "Alto %"
        TextInput:
            id: crop_h
            text: "100"
            input_filter: "int"
            multiline: False

    Label:
        text: "X e Y indican dónde empieza la región; ancho y alto indican su tamaño."
        size_hint_y: None
        height: dp(26)
        font_size: "10sp"
        color: 0.7, 0.76, 0.86, 1

    Label:
        text: "FRAME ACTUAL (capturado en memoria)"
        size_hint_y: None
        height: dp(23)
        color: 0.4, 0.7, 1, 1

    Image:
        id: frame
        texture: None
        allow_stretch: True
        keep_ratio: True

    Label:
        text: "ANÁLISIS DEL FRAME"
        size_hint_y: None
        height: dp(23)
        color: 0.4, 0.7, 1, 1

    ScrollView:
        do_scroll_x: False
        Label:
            id: result
            text: "Pulsa Visualizar y acepta el permiso de captura de Android."
            size_hint_y: None
            height: self.texture_size[1] + dp(25)
            text_size: self.width, None
            halign: "left"
            valign: "top"
            color: 0.9, 0.93, 1, 1

    Button:
        text: "Copiar análisis"
        size_hint_y: None
        height: dp(42)
        on_release: app.copy_analysis()

    Label:
        id: history
        text: "Frames recibidos: 0"
        size_hint_y: None
        height: dp(22)
        color: 0.7, 0.8, 0.9, 1
"""


class RobloxVisualizer(App):
    def build(self):
        self.running = False
        self.paused = False
        self.frame_count = 0
        self.last_frame_counter = -1
        self.current_analysis = ""
        self.capture_timer = None
        self.service = None
        self.capture_activity_bound = False
        self.root_widget = Builder.load_string(KV)
        return self.root_widget

    def on_start(self):
        if ANDROID_BRIDGE_AVAILABLE:
            activity.bind(on_activity_result=self.on_activity_result)
            self.capture_activity_bound = True

    def on_pause(self):
        # El servicio Android puede seguir capturando mientras Roblox está delante.
        return True

    def on_stop(self):
        try:
            if self.capture_timer is not None:
                self.capture_timer.cancel()
                self.capture_timer = None
            if ANDROID_BRIDGE_AVAILABLE and self.running:
                self._service_class().stop(mActivity)
        except Exception:
            pass
        if self.capture_activity_bound:
            try:
                activity.unbind(on_activity_result=self.on_activity_result)
            except Exception:
                pass

    def _service_class(self):
        return autoclass(SERVICE_CLASS)

    def _region_values(self):
        ids = self.root.ids
        x = int(ids.crop_x.text or "0")
        y = int(ids.crop_y.text or "0")
        w = int(ids.crop_w.text or "100")
        h = int(ids.crop_h.text or "100")
        if not (0 <= x < 100 and 0 <= y < 100):
            raise ValueError("X e Y deben estar entre 0 y 99.")
        if not (1 <= w <= 100 and 1 <= h <= 100):
            raise ValueError("El ancho y el alto deben estar entre 1 y 100.")
        if x + w > 100 or y + h > 100:
            raise ValueError("La región debe caber dentro de la pantalla: X + ancho y Y + alto no pueden superar 100.")
        return x / 100.0, y / 100.0, w / 100.0, h / 100.0

    def start_capture(self):
        if not ANDROID_BRIDGE_AVAILABLE:
            self.show_error(
                "La captura real necesita un APK Android compilado con python-for-android y el puente Java. "
                "Este archivo no puede capturar la pantalla desde Pydroid 3 por sí solo."
            )
            return
        try:
            crop = self._region_values()
            manager_cls = autoclass("android.media.projection.MediaProjectionManager")
            manager = mActivity.getSystemService("media_projection")
            permission_intent = manager.createScreenCaptureIntent()
            self.pending_crop = crop
            mActivity.startActivityForResult(permission_intent, REQUEST_CAPTURE)
            self.root.ids.status.text = "ESPERANDO PERMISO"
        except Exception as exc:
            self.show_error("No se pudo solicitar la captura: " + str(exc))

    def on_activity_result(self, request_code, result_code, data):
        if request_code != REQUEST_CAPTURE:
            return
        if result_code != -1 or data is None:
            self.root.ids.status.text = "PERMISO CANCELADO"
            return
        try:
            x, y, w, h = self.pending_crop
            self.service = self._service_class()
            self.service.start(mActivity, int(result_code), data,
                               float(x), float(y), float(w), float(h))
            self.running = True
            self.paused = False
            self.last_frame_counter = -1
            self.root.ids.status.text = "CAPTURANDO"
            if self.capture_timer is not None:
                self.capture_timer.cancel()
            self.capture_timer = Clock.schedule_interval(self.pull_frame, 0.45)
        except Exception as exc:
            self.show_error("No se pudo iniciar el servicio de captura: " + str(exc))

    def pull_frame(self, _dt):
        if not self.running or self.paused or self.service is None:
            return
        try:
            counter = int(self.service.getFrameCounter())
            if counter <= self.last_frame_counter:
                return
            encoded = self.service.getLatestFrameBase64()
            if not encoded:
                return
            raw = base64.b64decode(str(encoded))
            image = PILImage.open(BytesIO(raw)).convert("RGB")

            self.last_frame_counter = counter
            self.frame_count += 1
            self.root.ids.history.text = f"Frames recibidos: {self.frame_count}"

            self.root.ids.frame.texture = CoreImage(BytesIO(raw), ext="jpg").texture
            self.analyze(image)
            self.root.ids.status.text = "CAPTURANDO"
        except Exception as exc:
            self.root.ids.status.text = "ERROR DE FRAME"
            self.root.ids.result.text = "Error al leer el frame: " + str(exc)

    def analyze(self, image):
        recognized_text = ""
        ocr_message = "OCR no disponible en este APK."
        if pytesseract is not None:
            try:
                recognized_text = pytesseract.image_to_string(image, config="--psm 11").strip()
                ocr_message = "OCR ejecutado."
            except Exception as exc:
                ocr_message = "OCR instalado, pero falta/configuración incorrecta del motor Tesseract: " + str(exc)

        lines = [line.strip() for line in recognized_text.splitlines() if line.strip()]
        known = [
            "resume", "reset", "leave", "players", "settings", "roblox",
            "reanudar", "salir", "reiniciar", "jugadores", "configuración",
            "menu", "report", "reportar"
        ]
        found = sorted({word for word in known if word in recognized_text.lower()})

        report = [
            "ONLY ROBLOX VISUALIZER",
            "=" * 28,
            "\nCAPTURA:",
            "Frame recibido directamente de la pantalla; no se guardó como archivo.",
            "\nINTERFAZ / PALABRAS VISIBLES:",
            ", ".join(found) if found else "No se reconocieron botones conocidos.",
            "\nTEXTO DETECTADO:",
        ]
        report.extend("- " + line for line in lines[:40])
        if not lines:
            report.append("No se detectó texto legible.")
        report.extend([
            "\nESTADO DEL OCR:",
            ocr_message,
            "\nAVATARES / PERSONAJES:",
            "El frame está disponible para inspección visual. Este proyecto base todavía no incluye un modelo de visión entrenado para detectar avatares.",
            "\nJUGADOR / NPC / BOT:",
            "No se puede confirmar por píxeles si un avatar lo controla una persona o el juego. El nombre o una etiqueta visible pueden dar pistas, no una prueba.",
            "\nOBJETOS:",
            "El OCR lee texto; no identifica de forma fiable la función de cada objeto 3D.",
            "\nHORA DEL FRAME:",
            datetime.now().strftime("%H:%M:%S"),
        ])
        self.current_analysis = "\n".join(report)
        self.root.ids.result.text = self.current_analysis

    def pause(self):
        if not self.running or self.service is None:
            self.root.ids.status.text = "SIN CAPTURA ACTIVA"
            return
        self.paused = not self.paused
        try:
            self.service.setPaused(bool(self.paused))
        except Exception:
            pass
        self.root.ids.status.text = "PAUSADO" if self.paused else "CAPTURANDO"

    def stop(self):
        self.running = False
        self.paused = False
        if self.capture_timer is not None:
            self.capture_timer.cancel()
            self.capture_timer = None
        try:
            if ANDROID_BRIDGE_AVAILABLE:
                self._service_class().stop(mActivity)
        except Exception as exc:
            self.root.ids.result.text = "La captura se detuvo en la interfaz, pero el servicio indicó: " + str(exc)
        self.root.ids.status.text = "DETENIDO"

    def delete_frame(self):
        self.root.ids.frame.texture = None
        self.current_analysis = ""
        self.root.ids.result.text = "Vista previa eliminada. No se guarda ningún frame en el almacenamiento."
        try:
            if self.service is not None:
                self.service.clearLatestFrame()
                self.last_frame_counter = int(self.service.getFrameCounter())
        except Exception:
            pass
        self.root.ids.status.text = "FRAME ELIMINADO"

    def copy_analysis(self):
        if self.current_analysis:
            Clipboard.copy(self.current_analysis)
            self.root.ids.status.text = "COPIADO"

    def show_error(self, message):
        Popup(
            title="Only Roblox Visualizer",
            content=Label(text=message),
            size_hint=(0.9, 0.45)
        ).open()


RobloxVisualizer().run()
