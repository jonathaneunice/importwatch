import sys
import os
import re
import logging
from atexit import register as register_exit_handler
import __builtin__
import distutils.sysconfig as sysconfig

__version__ = '0.21'

log = logging.getLogger(__name__)

orig_import = __builtin__.__import__

def identify_standard_modules():
    """
    Find the standard / system modules, so we don't over-report.
    """
    # Based on Adam Spiers answer to this Stack Overflow question:
    # http://stackoverflow.com/questions/6463918/how-can-i-get-a-list-of-all-the-python-standard-library-modules
    
    sys_mods = set()
    
    std_lib = sysconfig.get_python_lib(standard_lib=True)
    
    for top, dirs, files in os.walk(std_lib):
        for nm in files:
            prefix = top[len(std_lib)+1:]
            if prefix[:13] == 'site-packages':
                continue
            if nm == '__init__.py':
                sys_mods.add(top[len(std_lib)+1:].replace(os.path.sep,'.'))
            elif nm[-3:] == '.py':
                sys_mods.add(os.path.join(prefix, nm)[:-3].replace(os.path.sep,'.'))
            elif nm[-3:] == '.so' and top[-11:] == 'lib-dynload':
                sys_mods.add(nm[0:-3])
    
    for builtin in sys.builtin_module_names:
        sys_mods.add(builtin)
        
    sys_mods.add('os.path') # a common (but dynamically generated) import
    sys_mods.add('org.python.core')
    
    return sys_mods

sys_modules = identify_standard_modules()
unique_imports = set()

def emit_unique():

    modules = sorted([ m for m in unique_imports if m not in sys_modules ])
    print "Unique modules imported:", ' '.join(modules)
    
    packages = sorted(set([ m.split('.')[0] for m in modules ]))
    print "Unique packages:", ' '.join(packages)

def make_with_regex(regex=None):
    if regex:
        matcher = re.compile(regex)
    else:
        matcher = None
    def new_import(name, *args, **kwargs):
        # exporatory printing code follows - looking at args that get passed
        if False:
            print "NAME:", name
            
            print "ARGS:",
            for a in args:
                if isinstance(a, dict):
                    print "dict with keys", sorted(a.keys())
                    for k in '__name__ __package__ __file__'.split():
                        if k in a:
                            print "  ", k, a[k]
                else:
                    print a,
            print
            print "KWARGS:", kwargs
            print "--"
        if name not in sys_modules:
            if (not matcher) or matcher.match(name):
                log.info("'%s' imported.", name)
                unique_imports.add(name)
        return orig_import(name, *args, **kwargs)
    return new_import
                

def start(regex=None, echo=False, atexit=True):
    __builtin__.__import__ = make_with_regex(regex)
    if echo:
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console.setFormatter(formatter)
        log.setLevel(logging.DEBUG)
        log.addHandler(console)
    if atexit:
        register_exit_handler(emit_unique)

# Intersting tool to see what modules were imported. Echo is too verbose and real-time,
# IMO. Should have option to log to specific file. The naming of standard modules is
# hard. Not sure we have it licked, even with Stack Overflow help. Based on the way
# that modules are reported to import, have some probably unnecessary duplication.
# For purposes of establishing correct setup.py files, enough to know that say, stuf,
# or tornado loaded--do not need their sub modules. If args[0].__name__ == 'pkgutil'
# then name is a standard library name. Otherwise the __file__ attribute eg
# __file__ /Library/Python/2.7/site-packages/tornado/autoreload.pyc
# can give some real help. Eg, if under site-packages, going to be an installed
# package.  But in some cases, it's going to be a dynamic load, with very little
# information provided to the import engine, and the names of
# modules or packages printed are going to be disconnected from the modules/packages
# in which they're housed, or from which they're called. C'est la guerre!
# The package list remains a good starting point.

# NB Doesn't handle py3 as yet.
