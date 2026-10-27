#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NotificationBar — unified toast notification system for SMART ipywidgets UI.

Usage in any tab:
    from .notificationBar import NotificationBar
    self.notif = NotificationBar()
    # then in allWidgets VBox, add self.notif.widget at the top

    self.notif.error('One or more alternatives are empty')
    self.notif.warning('CR > 0.10 — check your comparisons')
    self.notif.success('File saved successfully')
    self.notif.info('Loading case...')
    self.notif.clear()
"""

import ipywidgets as widgets
from IPython.display import display, HTML

__CREATION_DATE__ = 'Sunday Jun 01, 2026'
__LAST_MODIFIED__  = 'Sunday Jun 01, 2026'

# Colour palette aligned with custom_css design system
_STYLES = {
    'error':   {'bg': '#fef2f2', 'border': '#fca5a5', 'text': '#991b1b', 'icon': '✕'},
    'warning': {'bg': '#fffbeb', 'border': '#fcd34d', 'text': '#92400e', 'icon': '⚠'},
    'success': {'bg': '#f0fdf4', 'border': '#86efac', 'text': '#166534', 'icon': '✓'},
    'info':    {'bg': '#eff6ff', 'border': '#93c5fd', 'text': '#1e40af', 'icon': 'ℹ'},
}

_EMPTY_HTML = '<div style="height:0;overflow:hidden"></div>'


class NotificationBar:
    """
    A single ipywidgets.HTML widget that displays styled notification toasts.
    Place self.widget at the top of any tab's allWidgets VBox.
    """

    def __init__(self):
        self.widget = widgets.HTML(
            value=_EMPTY_HTML,
            layout=widgets.Layout(width='100%', margin='0 0 8px 0'),
        )

    def _render(self, level: str, message: str):
        s = _STYLES.get(level, _STYLES['info'])
        self.widget.value = (
            f'<div style="'
            f'display:flex;align-items:flex-start;gap:10px;'
            f'background:{s["bg"]};'
            f'border:1px solid {s["border"]};'
            f'border-left:4px solid {s["border"]};'
            f'border-radius:8px;'
            f'padding:10px 14px;'
            f'font-family:\'Syne\',sans-serif;'
            f'font-size:13px;'
            f'color:{s["text"]};'
            f'line-height:1.5;'
            f'margin-bottom:4px;'
            f'">'
            f'<span style="font-size:15px;flex-shrink:0;margin-top:1px">{s["icon"]}</span>'
            f'<span>{message}</span>'
            f'</div>'
        )

    def error(self, message: str):
        """Show a red error notification."""
        self._render('error', message)

    def warning(self, message: str):
        """Show an amber warning notification."""
        self._render('warning', message)

    def success(self, message: str):
        """Show a green success notification."""
        self._render('success', message)

    def info(self, message: str):
        """Show a blue info notification."""
        self._render('info', message)

    def clear(self):
        """Hide the notification bar."""
        self.widget.value = _EMPTY_HTML
