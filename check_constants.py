"""check_constants.py - diagnostico de scripts/constants.py

Recorre todos los modulos de scripts/, recoge cada nombre que se importa con
'from .constants import ...' y lo compara con lo que constants.py define de
verdad. Lista lo que falta.

Uso (desde la raiz del proyecto, p.ej. C:\\Users\\jgoit\\Desktop\\smart_v2):

    python check_constants.py

o apuntando a otra carpeta:

    python check_constants.py C:\\ruta\\a\\scripts
"""
import ast
import os
import re
import sys


def defined_names(path):
    """Nombres que constants.py expone realmente."""
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
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split('.')[0])
        elif isinstance(node, (ast.If, ast.Try)):
            # Asignaciones dentro de if/try al nivel superior
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assign):
                    for target in sub.targets:
                        if isinstance(target, ast.Name):
                            names.add(target.id)
    return names


# Captura tambien los imports repartidos en varias lineas, con o sin parentesis
IMPORT_RE = re.compile(
    r'from\s+\.?constants\s+import\s+(\(([^)]*)\)|([^\n]*(?:\\\n[^\n]*)*))'
)


def required_names(folder):
    """Nombre -> lista de modulos que lo importan de constants."""
    needed = {}
    for filename in sorted(os.listdir(folder)):
        if not filename.endswith('.py') or filename == 'constants.py':
            continue
        path = os.path.join(folder, filename)
        try:
            with open(path, encoding='utf-8') as f:
                source = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        for match in IMPORT_RE.finditer(source):
            body = match.group(2) or match.group(3) or ''
            body = body.replace('\\\n', ' ')
            for part in body.split(','):
                name = part.strip().split(' as ')[0].strip()
                if name and name != '*' and name.isidentifier():
                    needed.setdefault(name, []).append(filename)
    return needed


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else 'scripts'
    if not os.path.isdir(folder):
        print(f'ERROR: no encuentro la carpeta {folder!r}.')
        print('Ejecutalo desde la raiz del proyecto, o pasale la ruta a scripts/.')
        return 2

    constants_path = os.path.join(folder, 'constants.py')
    if not os.path.isfile(constants_path):
        print(f'ERROR: no encuentro {constants_path}')
        return 2

    defined = defined_names(constants_path)
    needed = required_names(folder)
    missing = {k: v for k, v in needed.items() if k not in defined}

    print(f'constants.py analizado : {os.path.abspath(constants_path)}')
    print(f'nombres que define     : {len(defined)}')
    print(f'nombres que le piden   : {len(needed)}')
    print()

    if not missing:
        print('OK - no falta ningun nombre. El constants.py esta completo.')
        return 0

    print(f'FALTAN {len(missing)} nombre(s) en constants.py:')
    print()
    for name in sorted(missing):
        users = ', '.join(sorted(set(missing[name])))
        print(f'  {name:28s} <- lo importa: {users}')
    print()
    print('Restaura constants.py desde control de versiones o copia de')
    print('seguridad. Si anades los nombres a mano, vuelve a ejecutar esto')
    print('hasta que salga OK.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
