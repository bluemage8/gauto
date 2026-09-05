"""android.webkit.WebView wrapper as a Kivy widget for buildozer APK.

Bidirectional JS bridge WITHOUT needing pyjnius Java-interface binding:
  - Python -> JS + result : evaluateJavascript(code, cb)  (API 19+, returns result)
  - JS -> Python          : JS calls location.href = "kivybridge://post/<base64>"
                            which we intercept in shouldOverrideUrlLoading and hop
                            back to the Kivy main thread.

This is the most robust pattern for Kivy-on-Android because it avoids the
fragile @java_interface binding for addJavascriptInterface.

On desktop the widget is a stub so the app still imports/runs for dev.
"""

from __future__ import annotations

import base64
import json
import sys

from kivy.uix.widget import Widget
from kivy.event import EventDispatcher
from kivy.clock import Clock
from kivy.utils import platform as kplatform

try:
    __ANDROID__
    IS_ANDROID = True
except NameError:
    IS_ANDROID = (kplatform == "android")


class WebView(Widget, EventDispatcher):
    """Kivy widget hosting an Android WebView (or a desktop stub)."""

    on_loaded = EventDispatcher.create("on_loaded")
    on_page_error = EventDispatcher.create("on_page_error")
    on_js_message = EventDispatcher.create("on_js_message")

    def __init__(self, url: str = "about:blank", **kwargs):
        super().__init__(**kwargs)
        self.url = url
        self._wv = None          # java WebView
        self._ctx = None
        self._ready = False
        self._req_id = 0
        self._pending = {}       # mid -> cb
        self.init_backend()

    # ------------------------------------------------------------------
    def init_backend(self):
        if IS_ANDROID:
            from android import activity, run_on_ui_thread
            self._ctx = activity
            run_on_ui_thread(self._create_native)
        else:
            self._ready = True
            Clock.schedule_once(lambda dt: self.dispatch("on_loaded"), 0.1)

    # ------------------------------------------------------------------
    def _create_native(self):
        from android import run_on_ui_thread
        from android.view import ViewGroup, View
        from android.webkit import (
            WebView as JWebView,
            WebChromeClient,
            WebSettings,
            WebViewClient,
        )

        def _make():
            wv = JWebView(self._ctx)
            s = wv.getSettings()
            s.setJavaScriptEnabled(True)
            s.setDomStorageEnabled(True)
            s.setAllowFileAccess(True)
            s.setAllowUniversalAccessFromFileURLs(True)
            s.setMediaPlaybackRequiresUserGesture(False)
            try:
                s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW)
            except Exception:
                pass
            try:
                s.setUserAgentString(
                    s.getUserAgentString() + " GameAuto/1.0")
            except Exception:
                pass

            def client():
                class _Client(WebViewClient):
                    def shouldOverrideUrlLoading(self, view, item):
                        url = item.getUrl()
                        if url and url.startswith("kivybridge://"):
                            # extract base64 payload
                            rest = url[len("kivybridge://"):]
                            try:
                                path = rest.split("/post/")[-1] if "/post/" in rest else rest
                                payload = base64.b64decode(path).decode("utf-8")
                            except Exception:
                                payload = rest
                            run_on_ui_thread(
                                lambda: self._on_bridge_payload(payload))
                            return True
                        return False
                    def onReceivedError(self, view, request, err):
                        run_on_ui_thread(lambda: self.dispatch(
                            "on_page_error",
                            f"error {getattr(err, 'getErrorCode', lambda: -1)()}:\n"
                            f"{request.getUrl() if request else '?'}:\n"
                            f"{err.getDescription() if err else '?'}"))
                    def onPageFinished(self, view, url):
                        if getattr(view, "getUrl", None) and view.getUrl() == self.url:
                            self._ready = True
                            run_on_ui_thread(
                                lambda: self.dispatch("on_loaded"))
                return _Client()
            wv.setWebViewClient(client())
            wv.setWebChromeClient(WebChromeClient())

            root = self._ctx.getWindow().getDecorView()
            root.addView(wv)
            wv.setLayoutParams(ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT))
            wv.loadUrl(self.url)
            self._wv = wv
        run_on_ui_thread(_make)

    # ------------------------------------------------------------------
    def _on_bridge_payload(self, payload: str):
        if payload.startswith("@@RESULT@@"):
            try:
                d = json.loads(payload[len("@@RESULT@@"):])
            except Exception:
                return
            mid = d.get("id")
            cb = self._pending.pop(mid, None)
            if cb:
                result = d.get("data")
                Clock.schedule_once(lambda dt: cb(result), 0)
            elif d.get("error"):
                self.dispatch("on_page_error", f"eval{mid}: {d['error']}")
        else:
            self.dispatch("on_js_message", payload)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def load_url(self, url: str):
        self.url = url
        if IS_ANDROID and self._wv:
            from android import run_on_ui_thread
            run_on_ui_thread(lambda: self._wv.loadUrl(url))
        else:
            Clock.schedule_once(lambda dt: self.dispatch("on_loaded"), 0.05)

    def reload(self):
        if IS_ANDROID and self._wv:
            from android import run_on_ui_thread
            run_on_ui_thread(lambda: self._wv.reload())
        else:
            self.load_url(self.url)

    def go_back(self):
        if IS_ANDROID and self._wv:
            from android import run_on_ui_thread
            def _b():
                try:
                    if self._wv.canGoBack():
                        self._wv.goBack()
                    else:
                        Clock.schedule_once(lambda dt: self.dispatch("on_loaded"),0)
                except Exception:
                    pass
            run_on_ui_thread(_b)

    def can_go_back(self) -> bool:
        if IS_ANDROID and self._wv:
            from java.lang import Thread
            result = {"v": False}
            ev = threading.Event()
            from android import run_on_ui_thread
            def _g():
                try:
                    result["v"] = bool(self._wv.canGoBack())
                except Exception:
                    result["v"] = False
                ev.set()
            run_on_ui_thread(_g)
            ev.wait(2)
            return result["v"]
        return False

    def evaluate_js(self, code: str, result_cb=None):
        """Run JS. result_cb(js_result_str_or_None) is async, called on main thread.
        Wrap code to return a JSON string for structured data."""
        if not (IS_ANDROID and self._wv):
            if result_cb:
                Clock.schedule_once(lambda dt: result_cb(None), 0)
            return
        self._req_id += 1
        mid = self._req_id
        if result_cb:
            self._pending[mid] = result_cb
        # JS: run code; encode result as base64 of JSON {id, data}; post via bridge
        js = (
            "(function(){"
            "var r=(" + code + ");"
            "var s=(typeof r==='string')?r:JSON.stringify(r);"
            "var o={id:" + str(mid) + ",data:s};"
            "var b=unescape(encodeURIComponent(JSON.stringify(o)));"
            "void(location.href='kivybridge://post/' + b);"
            "})()"
        )
        from android import run_on_ui_thread
        from java.lang import Runnable
        def _run():
            try:
                self._wv.evaluateJavascript(js, None)
            except Exception as e:
                self._pending.pop(mid, None)
                self.dispatch("on_page_error", f"evaljs fail: {e}")
        run_on_ui_thread(_run)


# thread helpers (import here so can_go_back works)
import threading  # noqa: E402
