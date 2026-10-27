#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PATCH INSTRUCTIONS FOR main.py
================================
Three small changes are needed.  Each section is marked with the surrounding
context so you can find the exact location.

─────────────────────────────────────────────────────────────────────────────
CHANGE 1 — add import near the top of main.py (after the other .smtReport import)
─────────────────────────────────────────────────────────────────────────────

  # existing line (reference):
  from .utilities import clean_up, decode_tuples, encode_tuples, ...

  # ADD this line immediately after:
  from .smtQuestionnaire import smt_to_questionnaire

─────────────────────────────────────────────────────────────────────────────
CHANGE 2 — add the "Export Questionnaire" button in Smart.__init__
           (place it right after the existing Report/Save toolbar, or inside
            the VBox that already holds the main tabs).

  Look for the line that creates self.allWidgets (the VBox with self.tabs).
  Replace:

    self.allWidgets = widgets.VBox([
        self.tabs,
        self.logger.all_widgets,
        self.downLabel,
    ])

  With:

    self.questionnaireOut = widgets.Output()
    self.exportQuestionnaireButton = widgets.Button(
        description='Export Questionnaire',
        button_style='info',
        tooltip='Export a standalone HTML questionnaire for external filling',
        icon='file-export',
        style={'description_width': 'initial'},
    )
    self.exportQuestionnaireButton.on_click(self._export_questionnaire)

    self.allWidgets = widgets.VBox([
        self.tabs,
        widgets.HBox([self.exportQuestionnaireButton, self.questionnaireOut]),
        self.logger.all_widgets,
        self.downLabel,
    ])

─────────────────────────────────────────────────────────────────────────────
CHANGE 3 — add the handler method inside the Smart class
           (e.g. right before or after save_widget_state)
─────────────────────────────────────────────────────────────────────────────
"""

# ── Paste this method verbatim inside the Smart class ────────────────────

def _export_questionnaire(self, b):
    """Handler for the Export Questionnaire button."""
    import os, json
    from IPython.display import clear_output, display, HTML
    from .utilities import decode_tuples
    from .smtQuestionnaire import smt_to_questionnaire

    with self.questionnaireOut:
        clear_output()

    # Flush the current questionnaire state (same as tab_change does)
    tab3_title = self.tabs.titles[3]   # Criteria Comparison
    tab4_title = self.tabs.titles[4]   # Alternative Rating
    current_idx = self.tabs.selected_index

    try:
        # Sync active tab state to temp file first
        self.save_widget_state(-1, -1)

        with open(self.temp_file, 'r') as f:
            encoded_data = json.load(f)
        data = decode_tuples(encoded_data)

        # Derive the case title from General tab or filename
        general = data.get('General', {})
        title = general.get('Description', '') or \
                (os.path.splitext(os.path.basename(self.filename))[0]
                 if self.filename else 'AHP Case')

        output_path = smt_to_questionnaire(title, data)

        with self.questionnaireOut:
            display(HTML(
                f'<span style="color:green;font-weight:600;">✓ Questionnaire exported:</span> '
                f'<a href="{output_path}" target="_blank">{os.path.basename(output_path)}</a>'
            ))
        self.logger.log('info', f'Questionnaire exported to {output_path}')

    except Exception as e:
        with self.questionnaireOut:
            display(HTML(
                f'<span style="color:red;font-weight:600;">✗ Export failed:</span> {e}'
            ))
        self.logger.log('error', f'Questionnaire export failed: {e}')
        raise
