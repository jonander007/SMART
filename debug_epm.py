#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Diagnóstico de carga de un .smt fuera de Voila.
Uso (con el venv activado, desde C:\\Users\\jgoit\\Desktop\\smart_v2):
    python debug_epm.py "C:\\ruta\\a\\EPM.smt"
Imprime el traceback completo si la carga falla.
"""
import sys, os, traceback

if len(sys.argv) < 2:
    print("Uso: python debug_epm.py <ruta_al_.smt>")
    sys.exit(1)

smt_path = sys.argv[1]
if not os.path.isfile(smt_path):
    print(f"No existe el archivo: {smt_path}")
    sys.exit(1)

os.makedirs('tmp', exist_ok=True)
with open('tmp/smart.uuid', 'w') as f:
    f.write('debuguuid')
with open('tmp/smart.input', 'w') as f:
    f.write(smt_path)

print(f"=== Cargando {smt_path} ===\n")
try:
    import scripts.main as main
    smart = main.Smart()
    print("\n>>> load_widget_state TERMINO SIN ERROR")
    # Probar el guardado que corre en background
    try:
        smart.save_widget_state(0, 0)
        print(">>> save_widget_state OK")
    except Exception:
        print(">>> save_widget_state FALLO:")
        traceback.print_exc()
    # Probar navegar a cada tab
    for idx in range(1, 9):
        try:
            smart.tab_change({'old': 0, 'new': idx})
            print(f">>> tab_change -> {idx} OK")
        except Exception:
            print(f">>> tab_change -> {idx} FALLO:")
            traceback.print_exc()
except Exception:
    print("\n>>> CARGA FALLO con este traceback:\n")
    traceback.print_exc()
