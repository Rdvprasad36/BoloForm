"""Tiny runner for environments without pytest: python tests/run_tests.py"""
import importlib, pkgutil, sys, traceback, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
failed = passed = 0
for m in sorted(pkgutil.iter_modules([str(pathlib.Path(__file__).parent)]), key=lambda m: m.name):
    if not m.name.startswith("test_"):
        continue
    mod = importlib.import_module(f"tests.{m.name}")
    for name in dir(mod):
        if name.startswith("test_") and callable(getattr(mod, name)):
            try:
                getattr(mod, name)(); passed += 1
            except Exception:
                failed += 1; print(f"FAIL {m.name}.{name}"); traceback.print_exc()
print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
