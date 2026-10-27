

# ---------------------------------------------------------------------------
# Compatibility shim - nombres que faltaban en este constants.py
# Anadido para reparar la perdida del fichero original. Si recuperas tu
# constants.py bueno, borra este bloque entero.
# ---------------------------------------------------------------------------
import os as _os
from ipywidgets import Image as _Image

# Ancho en px de las figuras de ahpCalculator.
# VALOR RECONSTRUIDO: no he podido recuperar el original. Todas las figuras del
# proyecto usan 700 o 1000; ajustalo si tu grafico sale con otro tamano.
plot_width = 1000

# Barra de carga: ipywidgets.Image con templates/images/loader.gif, igual que
# utilities.get_loading_bar(). Se resuelve la ruta relativa como hace utilities.
_imgpath = 'templates/images/'
if not _os.path.isdir(_imgpath):
    _imgpath = '../templates/images/'

try:
    with open(_os.path.join(_imgpath, 'loader.gif'), 'rb') as _f:
        loading_bar = _Image(value=_f.read())
except OSError:
    loading_bar = _Image()


def make_default_tree(key):
    """Delegado a utilities.make_default_tree.

    El import es diferido a proposito: utilities importa de constants, asi que
    un import a nivel de modulo daria una dependencia circular.
    """
    from .utilities import make_default_tree as _make_default_tree
    return _make_default_tree(key)
