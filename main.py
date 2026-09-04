"""Simple Game Automation Android app (KivyMD 2.0.0 minimal).

Tabs:
  - 游戏 : WebView showing the game URL
  - 设置 : URL input + 加载/刷新/返回/测试JS buttons + status
"""

from __future__ import annotations

from kivy.lang import Builder
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDButton
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.screen import MDScreen
from kivymd.uix.tab import (
    MDTabsPrimary, MDTabsItem, MDTabsItemText, MDTabsCarousel)

from webview_widget import WebView

GAME_URL = "https://gt010.xdcq.shlehe.cn"


class GameApp(MDApp):
    title = "Game Auto"

    def build(self):
        self.theme_cls.primary_palette = "Olive"
        self.theme_cls.theme_style = "Light"

        self.webview = WebView(url=GAME_URL)
        self.webview.on_loaded = self.on_web_loaded
        self.webview.on_page_error = self.on_web_error
        self.webview.on_js_message = self.on_js_message

        self.status = MDLabel(
            text=f"正在加载: {self.webview.url}",
            size_hint_y=None,
            halign="left",
        )

        # ---- game tab (webview) ----
        game_screen = MDScreen(name="game")
        game_screen.add_widget(self.webview)

        # ---- settings tab ----
        url_field = MDTextField(
            text=self.webview.url,
            hint_text="https://...",
            size_hint_y=None,
            height=64,
        )

        def do_load(*_):
            u = (url_field.text or "").strip()
            if not u:
                return
            if not u.startswith("http"):
                u = "https://" + u
            self.webview.load_url(u)

        def do_reload(*_):
            self.webview.reload()

        def do_back(*_):
            if self.webview.can_go_back():
                self.webview.goBack()
            else:
                self.status.text = "没有上一页"

        def do_test_js(*_):
            def _cb(res):
                self.status.text = str(res)[:200]
            self.webview.evaluate_js(
                "JSON.stringify({href: location.href, title: document.title})",
                _cb)

        url_box = MDBoxLayout(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(10),
        )
        url_box.add_widget(MDLabel(text="游戏地址", size_hint_y=None,
                                   halign="left"))
        url_box.add_widget(url_field)
        url_box.add_widget(MDLabel(text="状态", size_hint_y=None,
                                   halign="left"))
        sc = MDLabel(self.status.text, size_hint_y=None, halign="left")
        self._status_widget = sc
        url_box.add_widget(sc)
        url_box.add_widget(MDButton(text="加载", height=64,
                                    size_hint_y=None, on_release=do_load))
        url_box.add_widget(MDButton(text="刷新", height=64,
                                    size_hint_y=None, on_release=do_reload))
        url_box.add_widget(MDButton(text="返回上一页", height=64,
                                    size_hint_y=None, on_release=do_back))
        url_box.add_widget(MDButton(text="测试JS", height=64,
                                    size_hint_y=None, on_release=do_test_js))
        url_screen = MDScreen(name="url")
        url_screen.add_widget(url_box)

        # ---- tabs bar ----
        tabs = MDTabsPrimary(
            MDTabsCarousel(id="slides", size_hint_y=None, height=dp(980)),
            id="tabs",
            allow_stretch=True,
        )
        tabs.add_widget(MDTabsItem(MDTabsItemText(text="游戏")))
        tabs.add_widget(MDTabsItem(MDTabsItemText(text="设置")))
        tabs.ids.slides.add_widget(game_screen)
        tabs.ids.slides.add_widget(url_screen)
        return tabs

    # keep status label updated
    def _sync_status(self, text):
        try:
            self._status_widget.text = text
        except Exception:
            pass

    def on_web_loaded(self):
        t = f"已加载: {self.webview.url}"
        self._sync_status(t)
        print("[WebView] loaded:", self.webview.url)

    def on_web_error(self, info):
        self._sync_status(f"错误: {info}")
        print("[WebView] error:", info)

    def on_js_message(self, msg):
        print("[JS->PY]", msg)
        self._sync_status(str(msg)[:300])


if __name__ == "__main__":
    GameApp().run()
