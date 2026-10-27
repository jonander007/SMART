#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/titleAndHelp.py
import ipywidgets as widgets
from IPython.display import display, HTML, Javascript
import webview
from .constants import section_label_style, __VERSION__

__CREATION_DATE__ = 'Monday Aug 05, 2024 16:21:47 CEST'
__LAST_MODIFIED__ = 'Monday Nov 25, 2024 15:57:26 CET'

#    TODO: 
#           Add things to do here

class TitleAndHelp():
    def __init__(self, title, helpdoc):
        self.title = title
        self.helpdoc = helpdoc

        self.label = widgets.Label(
                value = title,
                style = section_label_style,
                layout=widgets.Layout(width='95%'),
                )
        self.helpButton = widgets.Button(
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Help',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='5%'),
            icon='question' # (FontAwesome names without the `fa-` prefix)
                )
        self.out = widgets.Output()
        self.helpButton.on_click(self.show_help)
        self.allWidgets = widgets.VBox([
                widgets.HBox([self.label, self.helpButton]),
                self.out
            ])

    def show_help(self, button):
        with self.out:
            # with open(self.helpdoc, 'r') as f:
            with open (self.helpdoc, 'r') as f:
                html = f.read().format(version=__VERSION__)
            webview.create_window('Help', html=html, on_top=True, text_select=True)
            webview.start()
                # md_content = f.read()
                # html = markdown.markdown(md_content.format(version=__VERSION__))
                #  html = html.replace('\n', '\\n').replace("'", "\\'")
                # html = html.replace('\n', '\\n')
                # s = f'var win = window.open("", "Title", "toolbar=no, location=no, directories=no, status=no, menubar=no, scrollbars=yes, resizable=yes, width=780, height=200, top="+(screen.height-400)+", left="+(screen.width-840));'
                # s += f'win.document.body.innerHTML = \'' + html + '\';'
                # display(Javascript(s))
