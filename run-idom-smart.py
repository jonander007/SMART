import json
import webview
import webview.menu as wm
import subprocess
import time
import requests
import socket
import os, signal
import shutil
from functools import partial
from scripts.utilities import clean_up, decode_tuples, add_msg_to_template
from scripts.smtReport import smt_to_report
from scripts.smtQuestionnaire import generate_questionnaire_html
import uuid
import matplotlib

# Avoid matplotlib UserWarning: Starting a Matplotlib GUI outside of the main thread will likely fail
matplotlib.use('agg')

LOADING_TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'loading.html')


class AppAPI:
    """Exposed to JS via window.pywebview.api throughout the whole app."""
    def __init__(self, app):
        self._app = app

    # These actions reload the window. They MUST run in a background thread so
    # that the JS API call returns immediately and pywebview can resolve its
    # return-value callback BEFORE the page navigates away. Otherwise pywebview
    # tries to evaluate_js on a window that already changed → WebViewException.
    def new_case(self):
        import threading
        threading.Thread(target=self._app.new_file_dialog, daemon=True).start()

    def open_case(self):
        import threading
        threading.Thread(target=self._app.open_file_dialog, daemon=True).start()

    def compare_results(self):
        import threading
        threading.Thread(target=self._app.compare_results, daemon=True).start()

    def go_back(self):
        import threading
        threading.Thread(target=self._app.go_back, daemon=True).start()

    def get_loading_progress(self):
        import os, json
        from scripts.constants import tmp_dir
        try:
            path = os.path.join(tmp_dir, 'loading_progress.json')
            if os.path.isfile(path):
                with open(path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {'pct': 0, 'msg': ''}

    def rs_mode_chosen(self, val):
        """Called from the embedded RS-mode modal injected into the main window."""
        ev = getattr(self._app, '_rs_mode_event', None)
        if ev is not None:
            self._app._rs_mode_result = val
            ev.set()

class main():
    def __init__(self, uuid_file='tmp/smart.uuid', input_file='tmp/smart.input'):
        if not os.path.isdir('tmp'):
            os.mkdir('tmp')
        if not os.path.isfile(input_file):
            with open(input_file, 'w') as f:
                f.write('None')
        self.uuid_file = uuid_file
        self.input_file = input_file
        self.input_filename = None
        self.landing = True
        self.find_port_and_start_voila()
        self.voila_url = f"http://localhost:{self.port}"
        # Espera a que Voila esté activo
        if self.wait_for_voila():      
            # Permitir descargas
            webview.settings['ALLOW_DOWNLOADS'] = True
            # Abre la ventana web usando Webview    
            self.main_window = webview.create_window("SMART", 'landing.html', maximized=True, js_api=AppAPI(self))
            # Menu en webview para cargar/guardar
            menu_items = [
                wm.Menu(
                    'File',
                    [
                        wm.MenuAction('New', self.new_file_dialog),
                        wm.MenuAction('Open', self.open_file_dialog),
                        wm.MenuAction('Save', self.save_file_dialog),
                        wm.MenuSeparator(),
                        wm.MenuAction('Quit', self.quit_dialog),
                    ],
                ),
                wm.MenuAction('Report', self.generate_report),
                wm.MenuAction('Export Questionnaire', self.generate_questionnaire),
                wm.MenuAction('Compare Results', self.compare_results),
#                wm.Menu('About', [wm.MenuAction('This will do nothing', do_nothing)]),
            ]
            # Ejecuta la ventana Webview
            webview.start(menu=menu_items)
        else:
            print("Error: Voila no pudo arrancar correctamente.")
        clean_up()
        print(f'Terminating Voila process {self.voila_process.pid}')
        self.voila_process.terminate()
    
    def get_free_port(self, port):
        """Check if a port is free and return it; if not, increment until a free port is found."""
        while True:
            print(f'Checking if port {port} is free')
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) != 0:
                    print(f'Port {port} is free')
                    return port
                port += 1
    
    # Función para verificar si Voila está listo
    def _set_progress(self, pct, msg=''):
        """Write loading progress so loading.html can poll and display it."""
        import json as _json
        try:
            with open(os.path.join('tmp', 'loading_progress.json'), 'w') as f:
                _json.dump({'pct': pct, 'msg': msg}, f)
        except Exception:
            pass

    def wait_for_voila(self, timeout=120):
        """Wait until Voila HTTP server is up and notebook has finished executing.

        Drives the loading-screen progress bar across two phases:
          Phase 1 (0-18%): waiting for the Voila HTTP server to come up.
          Phase 2 (18-100%): notebook executing — main.py writes 20/90/100.
        """
        import json as _json
        progress_file = os.path.join('tmp', 'loading_progress.json')

        # Reset progress at the very start so the bar begins from 0.
        self._set_progress(2, 'Starting Voila server...')

        # ── Phase 1: wait for Voila HTTP server to respond ──────────────────
        server_up = False
        for i in range(timeout):
            try:
                response = requests.get(self.voila_url)
                if response.status_code == 200:
                    server_up = True
                    break
            except requests.ConnectionError:
                pass
            # Creep the bar from 2% up to ~18% while the server boots
            pct = min(18, 2 + i * 2)
            self._set_progress(pct, 'Starting Voila server...')
            time.sleep(1)

        if not server_up:
            return False

        self._set_progress(18, 'Loading case...')

        # ── Phase 2: wait for the notebook kernel to finish ─────────────────
        # main.py writes 20 → 90 → 100 as it loads. We poll until pct >= 100.
        # If the kernel never reports (e.g. new empty case), fall back on a
        # short grace period so we still navigate.
        last_pct = 18
        stale_ticks = 0
        for _ in range(timeout * 2):  # 0.5s steps
            try:
                with open(progress_file, 'r') as f:
                    prog = _json.load(f)
                pct = prog.get('pct', last_pct)
                if pct >= 100:
                    print("Voila está listo!")
                    time.sleep(0.5)  # buffer for JS callbacks
                    return True
                if pct == last_pct:
                    stale_ticks += 1
                else:
                    stale_ticks = 0
                    last_pct = pct
            except Exception:
                stale_ticks += 1
            # New/empty cases may never write progress past 18% — after ~6s
            # of no movement, assume ready and navigate.
            if stale_ticks > 12 and last_pct <= 18:
                print("Voila está listo!")
                self._set_progress(100, 'Ready')
                return True
            time.sleep(0.5)

        # Timeout — navigate anyway
        print("Voila está listo!")
        self._set_progress(100, 'Ready')
        return True
    
    def restart_voila(self):
        # Terminate voila process
        self.voila_process.terminate()
        self.find_port_and_start_voila()
    
    def new_file_dialog(self):
        # Reset progress before showing the loading screen so the bar starts at 0
        self._set_progress(0, 'Starting new case...')
        html = add_msg_to_template(LOADING_TEMPLATE, 'Starting new SMART case...')
        self.main_window.load_html(html)
        self.input_filename = None
        self.update_input()
        self.restart_voila()
        self.voila_url = f"http://localhost:{self.port}"
        self.load_voila_url()        
    
    def load_voila_url(self):
        """Navigate to Voila. Does NOT regenerate UUID."""
        self.landing = False
        if self.wait_for_voila():
            try:
                self.main_window.load_url(self.voila_url)
            except Exception as e:
                print(f"[SMART] load_voila_url error: {e}")

    def open_file_dialog(self):
        file_types = ('SMART Files (*.smart;*.smt)', 'All files (*.*)')
        active_window = webview.active_window()
        if active_window is None:
            return
        try:
            result = active_window.create_file_dialog(
                webview.OPEN_DIALOG, allow_multiple=True, file_types=file_types
            )
        except Exception as e:
            print(f'[SMART] open_file_dialog error: {e}')
            return
        if result:
            self.input_filename = result[0] if isinstance(result, (list, tuple)) else result
            # Reset progress before showing the loading screen so the bar starts at 0
            self._set_progress(0, 'Opening case...')
            html = add_msg_to_template(LOADING_TEMPLATE, 'Opening SMART case {}'.format(self.input_filename))
            self.main_window.load_html(html)
            self.update_input()
            self.restart_voila()
            self.voila_url = f"http://localhost:{self.port}/?token=smart"
            self.load_voila_url()
    
    def update_input(self):
        with open(self.input_file, 'w') as f:
            f.write(str(self.input_filename))
    
    def generate_report(self):
        if self.landing:
            webview.active_window().create_confirmation_dialog(
                'Impossible to download Report', 'Please load or create an AHP first.'
            )
            return
        tmp_file = self._current_tmp_file()
        if not os.path.isfile(tmp_file):
            webview.active_window().create_confirmation_dialog(
                'Report not available',
                'The case file is not ready yet — please wait a moment.'
            )
            return
        with open(tmp_file, 'rb') as f:
            data = decode_tuples(json.load(f))
        active_window = webview.active_window()
        result = active_window.create_file_dialog(webview.SAVE_DIALOG, directory='/', save_filename='Report.html')
        smt_to_report(self.input_filename or tmp_file, data)
        if result:
            dest = result[0] if isinstance(result, (list, tuple)) else result
            shutil.copy('tmp/Report.html', dest)
            print('Report saved as {}'.format(result))

    _RS_MODAL_JS = '(function() {\n  var old = document.getElementById(\'__smt_rs_modal\');\n  if (old) old.remove();\n\n  var overlay = document.createElement(\'div\');\n  overlay.id = \'__smt_rs_modal\';\n  overlay.style.cssText = [\n    \'position:fixed\',\'inset:0\',\'z-index:2147483647\',\n    \'background:rgba(15,24,41,.55)\',\'backdrop-filter:blur(3px)\',\n    \'display:flex\',\'align-items:center\',\'justify-content:center\',\n    \'font-family:Syne,Arial,sans-serif\'\n  ].join(\';\');\n\n  var css = document.createElement(\'style\');\n  css.textContent = `\n    #__smt_rs_modal .card{background:#fff;border:1px solid #d0d9ee;border-radius:16px;\n      padding:28px 32px;width:92%;max-width:520px;box-shadow:0 12px 40px rgba(15,24,41,.25);\n      font-family:Syne,Arial,sans-serif;}\n    #__smt_rs_modal .eyebrow{display:inline-flex;align-items:center;gap:6px;\n      font-family:\'DM Mono\',monospace;font-size:.68rem;letter-spacing:.1em;\n      color:#2563eb;background:#dbeafe;border:1px solid rgba(37,99,235,.2);\n      padding:3px 10px;border-radius:20px;margin-bottom:14px;text-transform:uppercase;}\n    #__smt_rs_modal .eyebrow::before{content:"";width:6px;height:6px;border-radius:50%;background:#2563eb;}\n    #__smt_rs_modal h2{font-size:1.3rem;font-weight:800;letter-spacing:-.02em;\n      margin:0 0 6px;color:#0f1829;}\n    #__smt_rs_modal .desc{font-size:.82rem;color:#4a5568;line-height:1.6;margin-bottom:20px;}\n    #__smt_rs_modal .options{display:flex;flex-direction:column;gap:9px;margin-bottom:20px;}\n    #__smt_rs_modal .opt{text-align:left;padding:13px 16px;border:1.5px solid #d0d9ee;\n      border-radius:11px;background:#fff;cursor:pointer;width:100%;\n      transition:border-color .15s,transform .1s,box-shadow .15s;\n      display:flex;flex-direction:column;gap:2px;font-family:inherit;}\n    #__smt_rs_modal .opt:hover{transform:translateY(-1px);box-shadow:0 6px 16px var(--shadow);\n      border-color:var(--c);}\n    #__smt_rs_modal .opt:active{transform:scale(.99);}\n    #__smt_rs_modal .opt-title{font-size:.92rem;font-weight:700;color:var(--c);}\n    #__smt_rs_modal .opt-desc{font-size:.74rem;color:#4a5568;line-height:1.5;}\n    #__smt_rs_modal .cancel-row{text-align:right;}\n    #__smt_rs_modal .cancel{font-family:\'DM Mono\',monospace;font-size:.7rem;color:#94a3b8;\n      background:none;border:none;cursor:pointer;padding:4px 8px;}\n    #__smt_rs_modal .cancel:hover{color:#4a5568;}\n  `;\n\n  function choose(val) {\n    document.getElementById(\'__smt_rs_modal\').remove();\n    window.pywebview.api.rs_mode_chosen(val);\n  }\n\n  overlay.innerHTML = `\n    <div class="card">\n      <div class="eyebrow">Export Questionnaire</div>\n      <h2>Rating Scales Comparison</h2>\n      <p class="desc">Choose how this section should appear in the exported questionnaire:</p>\n      <div class="options">\n        <button class="opt" style="--c:#1d4ed8;--shadow:rgba(37,99,235,.12)" onclick="window.__smtRsChoose(\'editable\')">\n          <div class="opt-title">✏️ &nbsp;Editable</div>\n          <div class="opt-desc">The expert can adjust the pairwise comparisons between scale options.</div>\n        </button>\n        <button class="opt" style="--c:#b45309;--shadow:rgba(217,119,6,.12)" onclick="window.__smtRsChoose(\'readonly\')">\n          <div class="opt-title">🔒 &nbsp;Read-only</div>\n          <div class="opt-desc">The analyst\'s values are shown for reference but cannot be changed.</div>\n        </button>\n        <button class="opt" style="--c:#374151;--shadow:rgba(55,65,81,.1)" onclick="window.__smtRsChoose(\'hidden\')">\n          <div class="opt-title">🚫 &nbsp;Omit section</div>\n          <div class="opt-desc">The Rating Scales Comparison tab is not included in the questionnaire.</div>\n        </button>\n      </div>\n      <div class="cancel-row">\n        <button class="cancel" onclick="window.__smtRsChoose(\'cancel\')">Cancel</button>\n      </div>\n    </div>`;\n\n  window.__smtRsChoose = choose;\n  document.head.appendChild(css);\n  document.body.appendChild(overlay);\n})();\n'

    def _pick_rs_mode(self):
        """Inject a modal overlay into the current main window (Voila or landing)
        and block until the user clicks one of its options.
        Returns 'editable', 'readonly', or 'hidden'.
        """
        import threading
        self._rs_mode_result = 'editable'
        self._rs_mode_event = threading.Event()

        win = webview.active_window()
        if win is None:
            return 'editable'
        try:
            win.evaluate_js(self._RS_MODAL_JS)
        except Exception as e:
            print(f'[SMART] _pick_rs_mode evaluate_js failed: {e}')
            return 'editable' 

        # Block this menu-action thread only — the webview UI thread stays responsive
        self._rs_mode_event.wait(timeout=120)

        result = self._rs_mode_result
        return result if result != 'cancel' else 'editable'

    def generate_questionnaire(self):
        if self.landing:
            webview.active_window().create_confirmation_dialog(
                'Impossible to export Questionnaire',
                'Please load or create an AHP case first.'
            )
            return
        tmp_file = self._current_tmp_file()
        if not os.path.isfile(tmp_file):
            webview.active_window().create_confirmation_dialog(
                'Questionnaire not available',
                'The case file is not ready yet — please wait a moment.'
            )
            return
        with open(tmp_file, 'rb') as f:
            data = decode_tuples(json.load(f))

        # Ask user which RS mode they want
        rs_mode = self._pick_rs_mode()

        active_window = webview.active_window()
        result = active_window.create_file_dialog(
            webview.SAVE_DIALOG, directory='/',
            save_filename='Questionnaire.html'
        )
        out_path = 'tmp/Questionnaire.html'
        generate_questionnaire_html(data, out_path, rs_mode=rs_mode)
        if result:
            dest = result[0] if isinstance(result, (list, tuple)) else result
            shutil.copy(out_path, dest)
            print(f'Questionnaire saved as {dest} (rs_mode={rs_mode})')


    def compare_results(self):
        """Carga el AHP Aggregator en la ventana principal (sin ventana secundaria)."""
        if not os.path.isfile('AHP_Aggregator.html'):
            webview.active_window().create_confirmation_dialog(
                'Compare Results',
                'AHP_Aggregator.html no encontrado en el directorio del proyecto.'
            )
            return
        aggregator_path = os.path.abspath('AHP_Aggregator.html').replace('\\', '/')
        self.main_window.load_url(f'file:///{aggregator_path}')

    def go_back(self):
        """Vuelve a la landing o al Voilà según el estado actual."""
        if self.landing:
            self.main_window.load_url('file:///' + os.path.abspath('landing.html').replace('\\', '/'))
        else:
            self.main_window.load_url(self.voila_url)

    def save_file_dialog(self):
        tmp_file = self._current_tmp_file()
        # Diagnostic: log which temp file we're about to copy and its alt count
        try:
            import json as _json
            with open(tmp_file, 'r') as _f:
                _d = _json.load(_f)
            _alts = _d.get('Alternatives', {}).get('Alternatives', '?')
            print(f'[SMART SAVE] tmp_file={tmp_file} exists={os.path.isfile(tmp_file)} alternatives={_alts}')
        except Exception as _e:
            print(f'[SMART SAVE] could not read {tmp_file}: {_e}')
        if not os.path.isfile(tmp_file):
            webview.active_window().create_confirmation_dialog(
                'Save not available',
                'The case is not ready yet — please wait a moment.'
            )
            return
        result = webview.active_window().create_file_dialog(
            webview.SAVE_DIALOG, directory='/', save_filename='ahp.smt'
        )
        if result:
            dest = result[0] if isinstance(result, (list, tuple)) else result
            shutil.copy(tmp_file, dest)
            print(f'[SMART SAVE] copied {tmp_file} -> {dest}')
        
    def quit_dialog(self):
        active_window = webview.active_window()
        result = active_window.create_confirmation_dialog('Quit?', 'Are you sure you want to quit?')
        if result:
            self.main_window.destroy()
    
    def update_uuid(self):
        self.uuid = f"{uuid.uuid4()}"
        with open(self.uuid_file, 'w') as f:
            f.write(self.uuid)

    def _current_tmp_file(self):
        """Return the temp .smt path using the UUID currently on disk.

        main.py (inside Voila) reads tmp/smart.uuid at startup and writes its
        autosave to tmp/tmp<that-uuid>.smt. Reading the UUID fresh here — rather
        than trusting self.uuid, which can drift if the file was reopened —
        guarantees Save/Report/Export read the file main.py is actually writing.
        """
        try:
            with open(self.uuid_file, 'r') as f:
                disk_uuid = f.read().strip()
            if disk_uuid:
                return f'tmp/tmp{disk_uuid}.smt'
        except Exception:
            pass
        return f'tmp/tmp{self.uuid}.smt'
    
    def find_port_and_start_voila(self):
        # Find a free port and open the notebook on voila in that port
        self.port = self.get_free_port(8866)
        self.update_uuid()
        self.voila_process = subprocess.Popen([
            'voila', 'idom-smart.ipynb',
            f'--port={self.port}',
            '--VoilaExecutor.iopub_timeout=120',
        ])


if __name__ == '__main__':
    main()

    
    
    
