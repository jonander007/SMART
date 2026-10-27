#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/main.py
import ipywidgets as widgets
import os
# from ipyfilechooser import FileChooser
from base64 import b64encode
import json, os, base64
import json
import threading
import uuid
import time
import pandas as pd
from IPython.display import display, HTML, clear_output, Javascript
from IPython.display import FileLink
from jinja2 import Environment, FileSystemLoader
import webbrowser
from .alternativeEditor import AlternativeEditor
from .criteriaEditor import CriteriaEditor
from .caseInformation import CaseInformation
from .criteriaComparator import CriteriaComparator
from .alternativeRator import AlternativeRator
from .alternativeComparator import AlternativeComparator
from .alternativeRating import AlternativeRating
from .ahpCalculator import AhpCalculator
from .criteriaHierarchy import CriteriaHierarchy
from .constants import tab_titles, default_alternatives, tmp_dir, __VERSION__, sleep_time
from .loggerWidget import LoggerWidget
import subprocess
from .smtQuestionnaire import generate_questionnaire_html
from .utilities import clean_up, decode_tuples, encode_tuples, make_default_tree, get_loading_bar, read_file, get_logo, assign_colors_and_hatches

__CREATION_DATE__ = 'Monday Aug 05, 2024 17:14:09 CEST'
__LAST_MODIFIED__ = 'Wednesday Jul 16, 2025 12:30:44 CEST'

#    TODO: 

loading_bar = get_loading_bar()

# Check for tmp_dir
if not os.path.isdir(tmp_dir):
    os.mkdir(tmp_dir)

class Smart():
    def __init__(self, file_only=False, default=None):
        #clean_up()
        self.logger = LoggerWidget(file_only=file_only)
        self.logger.log('debug', 'LoggerWidget initialized')
        self.logger.log('info', 'Initializing Smart')
        self.criteria_colors = None
        if default:
            tree = make_default_tree(default)
            alternatives = default_alternatives[default]
        self.downLabel = widgets.Label(
                value = 'IDOM-SMART version {}'.format(__VERSION__),
                #  style = section_label_style,
                layout=widgets.Layout(width='95%'),
                )
        
        # Define the tabs
        self.tabs = widgets.Tab()

        if default:
            self.tabsDict = {
                    tab_titles[0]: CaseInformation(logger=self.logger),
                    tab_titles[1]: AlternativeEditor(logger=self.logger, alternative_list=alternatives, nalternatives=len(alternatives)),
                    tab_titles[2]: CriteriaEditor(logger=self.logger, default=default),
                    tab_titles[3]: CriteriaComparator(logger=self.logger),
                    tab_titles[4]: AlternativeRator(logger=self.logger),
                    tab_titles[5]: CriteriaHierarchy(logger=self.logger),
                    tab_titles[6]: AhpCalculator(logger=self.logger),
                    }
        else:
            self.tabsDict = {
                    tab_titles[0]: CaseInformation(logger=self.logger),
                    tab_titles[1]: AlternativeEditor(logger=self.logger),
                    tab_titles[2]: CriteriaEditor(logger=self.logger),
                    tab_titles[3]: CriteriaComparator(logger=self.logger),
                    tab_titles[4]: AlternativeRator(logger=self.logger),
                    tab_titles[5]: CriteriaHierarchy(logger=self.logger),
                    tab_titles[6]: AhpCalculator(logger=self.logger),
                    }
        self.tabs.children = [t.allWidgets for t in self.tabsDict.values()]
        self.tabs.titles = list(self.tabsDict.keys())
        self.tabs.observe(self.tab_change, names='selected_index')

        # Export Questionnaire button
        self.questionnaireOut = widgets.Output()
        self.exportQuestionnaireButton = widgets.Button(
            description='Export Questionnaire',
            button_style='info',
            tooltip='Export a standalone HTML questionnaire for external filling',
            icon='file-export',
            style={'description_width': 'initial'},
        )
        self.exportQuestionnaireButton.on_click(self._export_questionnaire)

        # allWidgets to display
        self.allWidgets = widgets.VBox([
            self.tabs,
            widgets.HBox([self.exportQuestionnaireButton, self.questionnaireOut]),
            self.logger.all_widgets,
            self.downLabel,
            ])
        
        # Handle file saving — must be initialised before save_widget_state
        self._cached_data = None  # in-memory cache updated by save_widget_state
        self._loaded_data = None  # full decoded .smt for deferred tab loading
        self._pending_tabs = set()  # heavy tabs not yet populated
        self.pid = self._get_file_uuid()
        self.temp_file = os.path.join(tmp_dir, f'tmp{self.pid}.smt')
        # Unique id for THIS kernel. Voila can spawn more than one kernel for the
        # same notebook (e.g. a phantom kernel from a health-check GET). Only the
        # kernel the browser is actually attached to should autosave, otherwise a
        # stale kernel overwrites the user's edits. We claim a lock and the most
        # recently started kernel wins (the browser attaches to the last one).
        self._kernel_id = str(uuid.uuid4())
        self._claim_autosave_lock()

        # Handle input file reading        
        self.filename = self._get_file_input()
        if self.filename:
            # Load synchronously: display() calls inside Output widgets only
            # propagate correctly from the main kernel thread, not from a
            # background thread (Voila/nbclient limitation).
            self._write_progress(20, 'Reading case file...')
            self.load_widget_state()
            self._write_progress(90, 'Finalising...')

        self._start_background_update()
        # Signal completion — wait_for_voila reads this to know the kernel is done
        self._write_progress(100, 'Ready')


    def _write_progress(self, pct, msg=''):
        try:
            progress_file = os.path.join(tmp_dir, 'loading_progress.json')
            with open(progress_file, 'w') as f:
                json.dump({'pct': pct, 'msg': msg}, f)
        except Exception:
            pass

    def _get_file_input(self, filename='smart.input'):
        with open(os.path.join(tmp_dir, filename), 'r') as f:
            file_input = str(f.read())
            file_input = None if file_input == 'None' else file_input
        return file_input

    def _get_file_uuid(self, filename='smart.uuid'):
        with open(os.path.join(tmp_dir, filename), 'r') as f:
            file_uuid = str(f.read()).strip()
        return file_uuid
        
    def _claim_autosave_lock(self):
        """Register this kernel as the active autosaver."""
        try:
            with open(os.path.join(tmp_dir, 'active_kernel.lock'), 'w') as f:
                f.write(self._kernel_id)
        except Exception:
            pass

    def _is_autosave_owner(self):
        """True if this kernel currently owns the autosave lock."""
        try:
            with open(os.path.join(tmp_dir, 'active_kernel.lock'), 'r') as f:
                return f.read().strip() == self._kernel_id
        except Exception:
            # If the lock file is missing, fall back to allowing the save.
            return True

    def _start_background_update(self, sleeptime=sleep_time):
        def update():
            count = 0
            file_uuid = self._get_file_uuid()
            self.logger.log('info', f'Autosave thread START - pid={self.pid!r} '
                                    f'disk_uuid={file_uuid!r} temp_file={self.temp_file!r}')
            while file_uuid == self.pid:
                thread_id = threading.get_ident()
                # Only the kernel the browser is attached to writes the file.
                if self._is_autosave_owner():
                    self.save_widget_state(count, thread_id)
                    count += 1
                time.sleep(sleeptime)
                file_uuid = self._get_file_uuid()
            self.logger.log('info', f'Autosave thread STOP - pid={self.pid!r} '
                                    f'disk_uuid now {file_uuid!r} (mismatch, stopped after {count} saves)')
        self.thread = threading.Thread(target=update, daemon=True)
        self.thread.start()
        
    def tab_change(self, change):
        self.logger.log('debug', f'Tab change: {change}')
        # A tab change is a real user interaction, so this kernel is the live
        # one — make sure it owns the autosave lock.
        self._claim_autosave_lock()
        # If navigating to a heavy tab whose data was deferred, apply it now.
        new_key = tab_titles.get(change['new'])
        just_loaded = False
        if new_key in self._pending_tabs:
            just_loaded = self._load_pending_tab(new_key)
        # Build `data` from the CURRENT widget state, not a possibly-stale cache.
        # Reading get_all_outputs() live ensures edits made in one tab are seen
        # when another tab is rebuilt on navigation (and prevents the rebuild
        # from overwriting fresh edits with old cached values).
        data = {}
        for key, item in self.tabsDict.items():
            if key in [tab_titles[5], tab_titles[6]]:
                continue  # Hierarchy/Results are derived, never stored
            # Deferred heavy tabs still hold the originally-loaded values.
            if key in self._pending_tabs and self._loaded_data is not None \
                    and key in self._loaded_data:
                data[key] = self._loaded_data[key]
            else:
                try:
                    data[key] = item.get_all_outputs()
                except Exception:
                    # Fall back to loaded/cached data if a tab can't report yet
                    if self._loaded_data is not None and key in self._loaded_data:
                        data[key] = self._loaded_data[key]
                    elif self._cached_data is not None and key in self._cached_data:
                        data[key] = self._cached_data[key]
        #  print(change)
        # Update comparison dicts in old tab (if needed)
        if tab_titles[change['old']] == tab_titles[3]: # Criteria Comparison
            criteria = self.tabsDict[tab_titles[3]].criteriaSelector.value
            self.tabsDict[tab_titles[3]].allQuestionaires[criteria] = self.tabsDict[tab_titles[3]].selectedQuestionaire.comparisons_to_dict()
        elif tab_titles[change['old']] == tab_titles[4]: # Alternative Rating
            if not self.tabsDict[tab_titles[4]].invalid:
                if isinstance(self.tabsDict[tab_titles[4]].rator, AlternativeComparator):
                    criteria = self.tabsDict[tab_titles[4]].rator.criteriaSelector.value
                    self.tabsDict[tab_titles[4]].rator.allQuestionaires[criteria] = self.tabsDict[tab_titles[4]].rator.selectedQuestionaire.comparisons_to_dict()
                elif isinstance(self.tabsDict[tab_titles[4]].rator, AlternativeRating):
                    criteria = self.tabsDict[tab_titles[4]].rator.ratingScaleComparator.criteriaSelector.value
                    self.tabsDict[tab_titles[4]].rator.ratingScaleComparator.allQuestionaires[criteria] = self.tabsDict[tab_titles[4]].rator.ratingScaleComparator.selectedQuestionaire.comparisons_to_dict()
        # Generate colors
        if tab_titles[change['old']] == tab_titles[2] or not isinstance(self.criteria_colors, pd.DataFrame):
            self.criteria_colors = assign_colors_and_hatches(data[tab_titles[2]][tab_titles[2]])
        # Update current tab (skip if we just loaded it via deferred loading)
        if tab_titles[change['new']] == tab_titles[3]: # Criteria Comparison
            if not just_loaded:
                self.tabsDict[tab_titles[3]].update(data[tab_titles[2]][tab_titles[2]],
                        self.criteria_colors)
        elif tab_titles[change['new']] == tab_titles[4]: # Alternative Rating
            if not just_loaded:
                self.tabsDict[tab_titles[4]].update(data[tab_titles[1]][tab_titles[1]][-1], data[tab_titles[2]][tab_titles[2]], data[tab_titles[1]][tab_titles[1]][:-1]
                        )
        elif tab_titles[change['new']] == tab_titles[5]: # Hierarchy
            self.tabsDict[tab_titles[5]].update(
                    data[tab_titles[2]][tab_titles[2]],
                    data.get(tab_titles[4])
                    )
        elif tab_titles[change['new']] == tab_titles[6]: # Results
            self.tabsDict[tab_titles[6]].update(
                    data[tab_titles[2]][tab_titles[2]],
                    data[tab_titles[3]][tab_titles[3]],
                    data[tab_titles[1]][tab_titles[1]],
                    data[tab_titles[4]],
                    self.criteria_colors
                    )
        # Refresh the cache with the live state we just gathered.
        self._cached_data = data

    def _load_pending_tab(self, key):
        """Apply saved values to a heavy tab the first time it is opened."""
        data = self._loaded_data
        if data is None or key not in self._pending_tabs:
            return False
        try:
            if key == tab_titles[3]:  # Criteria Comparison
                # Build internal state without rendering, fill saved values,
                # then render once. set_all_values triggers the single render.
                self.tabsDict[key].update(
                    data[tab_titles[2]][tab_titles[2]], render=False
                )
                self.tabsDict[key].set_all_values(data[tab_titles[3]])
                # Render the now-populated selected questionaire.
                self.tabsDict[key].render_selected()
            elif key == tab_titles[4]:  # Alternative Rating
                self.tabsDict[key].set_all_values(data)
                # set_all_values builds the rator with silent=True (no render);
                # render() now performs the single final render so the user sees
                # the populated rating table / comparison immediately.
                self.tabsDict[key].render()
        except Exception as e:
            # Loading failed — keep the tab in _pending_tabs so autosave keeps
            # using the original loaded data instead of empty widgets.
            # Never fail silently: a blank tab with no explanation is impossible
            # to diagnose. Log the full traceback and say so in the tab itself.
            import traceback
            tb = traceback.format_exc()
            self.logger.log('error', f'_load_pending_tab failed for {key}: {e}')
            for line in tb.rstrip().splitlines():
                self.logger.log('error', f'    {line}')
            try:
                out = getattr(self.tabsDict[key], 'out', None)
                if out is not None:
                    with out:
                        clear_output()
                        display(HTML(
                            '<div style="border:1px solid #e74c3c;background:#fdf2f2;'
                            'border-radius:6px;padding:12px 14px;font-size:13px;'
                            'color:#922;">'
                            f'<b>This tab could not be loaded.</b><br>'
                            f'<code>{type(e).__name__}: {e}</code><br>'
                            '<span style="color:#666">The full traceback is in the '
                            'log panel below (set Log Level to ERROR or lower).</span>'
                            '</div>'
                        ))
            except Exception:
                pass
            return False
        # Only mark as loaded (out of pending) if it succeeded.
        self._pending_tabs.discard(key)
        return True

    def save_widget_state(self, count, thread_id):
        data = {}
        for key, item in self.tabsDict.items():
            if key in [tab_titles[5], tab_titles[6]]:
                continue
            # A heavy tab whose data is still deferred has empty widgets.
            # Use the originally-loaded values instead of overwriting with blanks.
            if key in self._pending_tabs and self._loaded_data is not None \
                    and key in self._loaded_data:
                data[key] = self._loaded_data[key]
            else:
                # Never let one tab's failure abort the whole save. Fall back to
                # the last known good value (loaded data or previous cache) so
                # edits to other tabs are still persisted.
                try:
                    data[key] = item.get_all_outputs()
                except Exception as e:
                    self.logger.log('error', f'get_all_outputs failed for {key}: {e}')
                    if self._loaded_data is not None and key in self._loaded_data:
                        data[key] = self._loaded_data[key]
                    elif self._cached_data is not None and key in self._cached_data:
                        data[key] = self._cached_data[key]
                    else:
                        continue
        self._cached_data = data  # cache for tab_change to avoid re-reading disk
        try:
            with open(self.temp_file, 'w') as f:
                json.dump(encode_tuples(data), f, indent=4)
                f.flush()
            # Log what got saved for the Alternatives tab so we can verify edits persist
            alts = data.get(tab_titles[1], {})
            # Also read the widget live to compare against what was saved
            try:
                live = self.tabsDict[tab_titles[1]].get_all_outputs().get(tab_titles[1])
            except Exception as ex:
                live = f'<err {ex}>'
            pend = tab_titles[1] in self._pending_tabs
            self.logger.log('info', f'Autosave #{count} -> {self.temp_file} | '
                                    f'pending={pend} saved={alts.get(tab_titles[1], alts)} '
                                    f'live_widget={live}')
        except Exception as e:
            self.logger.log('error', f'save_widget_state write failed: {e}')

    def load_widget_state(self):
        self.logger.log('info', f'Reading case from file: {self.filename}')
        with open(self.filename, 'r', encoding='utf-8') as f:
            encoded_data = json.load(f)
        data = decode_tuples(encoded_data)

        # Keep the full decoded data so deferred (heavy) tabs can load on demand.
        self._loaded_data = data
        # Track which heavy tabs still need their values applied.
        self._pending_tabs = set()

        # Set values for each Tab
        for key, item in data.items():
            self.logger.log('debug', f'Tab: {key}')
            # Lightweight tabs — load immediately (cheap, few widgets)
            if key in [tab_titles[0], tab_titles[1], tab_titles[2]]:
                self.tabsDict[key].set_all_values(item)
            # Heavy tabs (Criteria Comparison, Alternative Rating) — defer until
            # the user navigates to them. Building hundreds of ToggleButtons /
            # Comboboxes here blocks Voila's initial render and can exceed the
            # IOPub timeout on large cases (e.g. EPM2). _load_pending_tab()
            # applies the saved values the first time the tab is opened.
            elif key in [tab_titles[3], tab_titles[4]]:
                self._pending_tabs.add(key)
            # Results tab
            #  elif key == tab_titles[5]:
                #  self.tabsDict[key].update(
                    #  self.tabsDict[tab_titles[2]].tree.to_dict(), 
                    #  self.tabsDict[tab_titles[3]].get_compare_objects(), 
                    #  self.tabsDict[tab_titles[1]].get_selected_alternatives(),
                    #  self.tabsDict[tab_titles[4]].get_compare_objects(),
                    #  )

    def _export_questionnaire(self, b):
        """Export a standalone HTML questionnaire from the current case state."""
        from IPython.display import clear_output
        with self.questionnaireOut:
            clear_output()
        try:
            self.save_widget_state(-1, -1)
            with open(self.temp_file, 'r') as f:
                encoded_data = json.load(f)
            data = decode_tuples(encoded_data)
            general = data.get('General', {})
            title = (general.get('Description', '') or
                     (os.path.splitext(os.path.basename(self.filename))[0]
                      if self.filename else 'AHP Case'))
            out_path = os.path.join(tmp_dir, 'Questionnaire.html')
            generate_questionnaire_html(data, out_path)
            with self.questionnaireOut:
                display(HTML(
                    f'<span style="color:green;font-weight:600;">✓ Exported:</span> '
                    f'<a href="{out_path}" target="_blank">{os.path.basename(out_path)}</a>'
                ))
            self.logger.log('info', f'Questionnaire exported to {out_path}')
        except Exception as e:
            with self.questionnaireOut:
                display(HTML(f'<span style="color:red;font-weight:600;">✗ Export failed:</span> {e}'))
            self.logger.log('error', f'Questionnaire export failed: {e}')
            raise

