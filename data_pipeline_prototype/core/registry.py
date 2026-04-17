import importlib
import pkgutil
import plugins

class PluginRegistry:
    def __init__(self):
        self.providers = {}

    def load_plugins(self):
        for _, module_name, _ in pkgutil.iter_modules(plugins.__path__):
            module = importlib.import_module(f"plugins.{module_name}")
            if hasattr(module, "register"):
                module.register(self)

    def register_provider(self, name, provider):
        self.providers[name] = provider