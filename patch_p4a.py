#!/usr/bin/env python3
"""Patch P4A's build.py to fix Android dist creation on GitHub runners:
  1. Skip 'pip install -U pip' (CDN truncation corrupts the venv pip -> ImportError BuildDependencyInstallError)
  2. Skip 'pip install Cython' (not needed for our pure-Python modules; partial download corrupts venv pip)
Usage: python3 patch_p4a.py <path-to-python-for-android>
"""
import sys, py_compile

path = sys.argv[1] + "/pythonforandroid/build.py"
s = open(path).read()
changed = False

old1 = """        info('Upgrade pip to latest version')
        shprint(sh.bash, '-c', (
            "source venv/bin/activate && pip install -U pip"
        ), _env=copy.copy(base_env))"""
new1 = """        info('SKIP pip self-upgrade (CDN truncation corrupts it); using ensurepip pip')"""
if old1 in s:
    s = s.replace(old1, new1)
    changed = True
    print("patched: skip pip self-upgrade")
elif "SKIP pip self-upgrade" in s:
    print("already patched: pip self-upgrade skipped")

old2 = """        info('Install Cython in case one of the modules needs it to build')
        shprint(sh.bash, '-c', (
            "venv/bin/pip install Cython"
        ), _env=copy.copy(base_env))"""
new2 = """        info('SKIP Cython install (not needed for pure-Python modules)')"""
if old2 in s:
    s = s.replace(old2, new2)
    changed = True
    print("patched: skip Cython install")
elif "SKIP Cython install" in s:
    print("already patched: Cython skipped")

if changed:
    open(path, "w").write(s)
py_compile.compile(path, doraise=True)
print("build.py OK ->", path)
