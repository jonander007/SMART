# Changelog

## [2026-07-20] Fix recurrente: "widget model not found" (regresión)

Tres arreglos previos se habían perdido en los archivos desplegados. Los tres
producen el mismo síntoma (`VBoxModel._deserialize_state` -> widget model not found):

- **idom-smart.ipynb**: eliminado `metadata.widgets` (243 KB de estado obsoleto),
  limpiados outputs/execution_count, corregido `IPython.core.display` ->
  `IPython.display` en la celda 0.
- **run-idom-smart.py**:
  - Añadido `_strip_widget_state()`, invocado en cada `find_port_and_start_voila`,
    para que `metadata.widgets` no resucite al guardar (limpieza permanente en arranque).
  - `wait_for_voila` vuelve a usar comprobación por socket TCP en vez de
    `requests.get` (elimina el kernel fantasma que competía por el temp file
    y generaba model_ids que el navegador nunca registraba).
- **voila.json**: repuestos `iopub_msg_rate_limit=100000`,
  `iopub_data_rate_limit=100000000`, `rate_limit_window=10` e `iopub_timeout=300`,
  para no perder mensajes `comm_open` en la ráfaga de creación de widgets.
