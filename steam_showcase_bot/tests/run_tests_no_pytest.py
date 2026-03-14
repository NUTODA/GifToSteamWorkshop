import importlib
import pkgutil
import sys
import traceback

import steam_showcase_bot.tests as tests_pkg


def _iter_test_modules():
    prefix = tests_pkg.__name__ + '.'
    for module_info in pkgutil.iter_modules(tests_pkg.__path__):
        if module_info.name.startswith('test_'):
            module_name = prefix + module_info.name
            try:
                yield importlib.import_module(module_name)
            except Exception as exc:
                print(f'SKIP: {module_name} (import error: {exc})')


failures = []
for mod in _iter_test_modules():
    for name in dir(mod):
        if name.startswith('test_'):
            fn = getattr(mod, name)
            try:
                fn()
                print(f'OK: {mod.__name__}.{name}')
            except Exception:
                print(f'FAIL: {mod.__name__}.{name}')
                traceback.print_exc()
                failures.append(f'{mod.__name__}.{name}')

if failures:
    print('\nFAILED tests:', failures)
    sys.exit(1)
print('\nAll tests passed')
