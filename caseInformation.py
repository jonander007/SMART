#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/caseInformation.py
import ipywidgets as widgets
from datetime import datetime
from .titleAndHelp import TitleAndHelp
from .constants import tab_titles

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Tuesday Aug 06, 2024 09:38:49 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Thursday Dec 19, 2024 16:26:58 CET'

#    TODO: 
#           Add things to do here

TAB = 0
TAB_TITLE = tab_titles[TAB]

class CaseInformation():
    def __init__(self, logger, date=None, analyst=None, description=None, filepath=None):
        self.logger = logger
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Initializing')
        self.title = TitleAndHelp('General Information', 'docs/help_caseInformation.html')
        #  self.fileChooser = FileChooser(layout=widgets.Layout(width='95%'))
        #  if filepath:
            #  self.fileChooser.selected = filepath
        if date:
            date = datetime.strptime(date, '%d-%m-%Y')
        else:
            date = datetime.today()
        self.datePicker = widgets.DatePicker(
                description = 'Date',
                disabled = False,
                value = date
                )
        self.text = widgets.Text(
                value = analyst,
                placeholder = 'Enter name of the anayst',
                description = 'Analyst',
                disabled = False
                )
        self.description = widgets.Textarea(
                value = description,
                placeholder = 'Enter a description',
                description = 'Description',
                disabled = False,
                layout=widgets.Layout(width='95%')
                )
        self.allWidgets = widgets.VBox([
            self.title.allWidgets,
            #  self.fileChooser,
            widgets.HBox([
                self.datePicker,
                self.text
                ]),
            self.description
            ])

    def get_all_outputs(self):
        data = {
                'Date': self.datePicker.value.strftime('%d-%m-%Y'),
                'Analyst': self.text.value,
                'Description': self.description.value,
                #  'File': self.fileChooser.selected
                }
        self.logger.log('debug', f'caseInformation.get_all_outputs.data={data}')
        return data

    def set_all_values(self, data):
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Setting all values')
        self.logger.log('debug', f'caseInformation.set_all_values.data={data}')
        self.datePicker.value = datetime.strptime(data['Date'], '%d-%m-%Y')
        self.text.value = data['Analyst']
        self.description.value = data['Description']
