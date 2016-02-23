import pkgutil
import inspect

senders = {}

for loader, module_name, is_pkg in pkgutil.walk_packages(__path__):
    module = loader.find_module(module_name).load_module(module_name)
    senders[module_name] = {}
    for name, value in inspect.getmembers(module):
        if name.startswith('__'):
            continue
        if name in ['sender', 'listner']:
            senders[module_name][name] = value

del module
del is_pkg
del name
del pkgutil
del inspect
del loader
del value
del module_name