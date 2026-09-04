[app]
title = Game Auto
package.name = gameauto
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,html,js,css
version = 0.1.0
requirements = python3,kivy==2.3.1,pyjnius==1.7.0,kivymd==2.0.0,materialyoucolor==3.0.4,materialshapes==0.3,asynckivy==0.6.4,pillow
android.release = False
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK
android.api = 34
android.minapi = 24
android.ndk = 28c
android.accept_sdk_license = True
android.archs = arm64-v8a,armeabi-v7a
p4a.branch = master

[buildozer]
log_level = 1
