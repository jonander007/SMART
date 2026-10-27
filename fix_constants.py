"""fix_constants.py - repara scripts/constants.py automaticamente.

NO hay que editar nada a mano. Copia este fichero a la raiz del proyecto
(la carpeta que contiene 'scripts'), y ejecuta:

    cd C:\\Users\\jgoit\\Desktop\\smart_v2
    python fix_constants.py

Que hace:
  1. Hace copia de seguridad de scripts/constants.py -> constants.py.bak
  2. Anade al final los nombres que faltan (plot_width, loading_bar,
     make_default_tree) si no estan ya
  3. Borra scripts/__pycache__
  4. Comprueba que ya no falta ningun nombre y lo dice

Es idempotente: ejecutarlo dos veces no duplica nada.
"""
import ast
import os
import re
import shutil
import sys

SENTINEL = '# === IDOM-SMART constants shim ==='

SHIM = '''

''' + SENTINEL + '''
# Nombres que faltaban en este constants.py, reconstruidos a partir de su uso
# en el resto del codigo. Si recuperas tu constants.py original, usalo y borra
# este bloque entero.
import os as _shim_os
from ipywidgets import Image as _ShimImage

# Ancho en px de las figuras de ahpCalculator.
# VALOR RECONSTRUIDO: no se pudo recuperar el original. El resto de figuras del
# proyecto usan 700 o 1000. Ajustalo si el grafico sale con otro tamano.
plot_width = 1000

# Barra de carga: mismo contenido que utilities.get_loading_bar(), con el mismo
# fallback de ruta que usa utilities.py.
_shim_imgpath = 'templates/images/'
if not _shim_os.path.isdir(_shim_imgpath):
    _shim_imgpath = '../templates/images/'

try:
    with open(_shim_os.path.join(_shim_imgpath, 'loader.gif'), 'rb') as _shim_f:
        loading_bar = _ShimImage(value=_shim_f.read())
except OSError:
    loading_bar = _ShimImage()


def make_default_tree(key):
    """Delegado a utilities.make_default_tree.

    Import diferido a proposito: utilities importa de constants, asi que un
    import a nivel de modulo crearia una dependencia circular.
    """
    from .utilities import make_default_tree as _make_default_tree
    return _make_default_tree(key)
'''

IMPORT_RE = re.compile(
    r'from\s+\.?constants\s+import\s+(\(([^)]*)\)|([^\n]*(?:\\\n[^\n]*)*))'
)


def defined_names(path):
    with open(path, encoding='utf-8') as f:
        tree = ast.parse(f.read(), filename=path)
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            names.add(elt.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split('.')[0])
        elif isinstance(node, (ast.If, ast.Try)):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assign):
                    for target in sub.targets:
                        if isinstance(target, ast.Name):
                            names.add(target.id)
    return names


def required_names(folder):
    needed = {}
    for filename in sorted(os.listdir(folder)):
        if not filename.endswith('.py') or filename == 'constants.py':
            continue
        try:
            with open(os.path.join(folder, filename), encoding='utf-8') as f:
                source = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        for match in IMPORT_RE.finditer(source):
            body = (match.group(2) or match.group(3) or '').replace('\\\n', ' ')
            for part in body.split(','):
                name = part.strip().split(' as ')[0].strip()
                if name and name != '*' and name.isidentifier():
                    needed.setdefault(name, []).append(filename)
    return needed


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else 'scripts'
    if not os.path.isdir(folder):
        print(f'ERROR: no encuentro la carpeta {folder!r}.')
        print('Ejecutalo desde la raiz del proyecto (la que contiene scripts/),')
        print('o pasale la ruta: python fix_constants.py C:\\\\ruta\\\\a\\\\scripts')
        return 2

    path = os.path.join(folder, 'constants.py')
    if not os.path.isfile(path):
        print(f'ERROR: no encuentro {path}')
        return 2

    print(f'constants.py : {os.path.abspath(path)}')

    with open(path, encoding='utf-8') as f:
        source = f.read()

    if SENTINEL in source:
        print('El shim YA estaba aplicado, no lo duplico.')
    else:
        backup = path + '.bak'
        shutil.copyfile(path, backup)
        print(f'copia de seguridad -> {os.path.abspath(backup)}')
        with open(path, 'a', encoding='utf-8') as f:
            f.write(SHIM)
        print('shim anadido al final de constants.py')

    # El fichero tiene que seguir siendo Python valido
    try:
        with open(path, encoding='utf-8') as f:
            ast.parse(f.read(), filename=path)
    except SyntaxError as exc:
        print(f'\nERROR: constants.py ha quedado con un error de sintaxis: {exc}')
        print('Restaura constants.py.bak y avisa.')
        return 2

    cache = os.path.join(folder, '__pycache__')
    if os.path.isdir(cache):
        shutil.rmtree(cache, ignore_errors=True)
        print('__pycache__ borrado')

    missing = {k: v for k, v in required_names(folder).items()
               if k not in defined_names(path)}
    print()
    if missing:
        print(f'TODAVIA FALTAN {len(missing)} nombre(s):')
        for name in sorted(missing):
            print(f'  {name:28s} <- lo importa: '
                  f'{", ".join(sorted(set(missing[name])))}')
        return 1

    print('OK - constants.py completo. Ya puedes arrancar la aplicacion.')
    print()
    print('Recuerda: plot_width = 1000 es un valor reconstruido, no el')
    print('original. Es cosmetico (ancho de las figuras de ahpCalculator).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
