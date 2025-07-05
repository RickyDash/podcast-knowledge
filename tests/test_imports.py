import importlib

packages = ["ingest", "search", "analytics", "infra"]

def test_packages_importable():
    for pkg in packages:
        assert importlib.import_module(pkg)
