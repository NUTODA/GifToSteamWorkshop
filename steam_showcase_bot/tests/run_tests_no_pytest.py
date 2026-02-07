import importlib, traceback, sys

mod = importlib.import_module('steam_showcase_bot.tests.test_startup_shutdown')
failures = []
for name in dir(mod):
    if name.startswith('test_'):
        fn = getattr(mod, name)
        try:
            fn()
            print(f'OK: {name}')
        except Exception:
            print(f'FAIL: {name}')
            traceback.print_exc()
            failures.append(name)

if failures:
    print('\nFAILED tests:', failures)
    sys.exit(1)
print('\nAll tests passed')
