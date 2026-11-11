
[app]

title = Only Roblox Visualizer
package.name = visualizer
package.domain = org.onlyroblox

source.dir = .
source.include_exts = py,kv,png,jpg,atlas,xml,java

version = 1.0

requirements = python3,kivy,pillow,pyjnius

orientation = portrait
fullscreen = 0

android.api = 35
android.minapi = 23
android.archs = arm64-v8a, armeabi-v7a

android.permissions = POST_NOTIFICATIONS

android.add_src = ScreenCaptureService.java

android.extra_manifest_xml = extra_manifest.xml
android.extra_manifest_application_arguments = extra_manifest_application_arguments.xml

[buildozer]

log_level = 2
warn_on_root = 0
