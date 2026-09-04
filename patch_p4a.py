#!/usr/bin/env python3
"""Patch P4A's build.py to fix Android dist creation on GitHub runners:
  1. Skip 'pip install -U pip' (CDN truncation corrupts the venv pip -> ImportError BuildDependencyInstallError)
  2. Skip 'pip install Cython' (not needed for our pure-Python modules; partial download corrupts venv pip)
  3. Raise recipe-download HTTP retry (GitHub egress proxy returns bursty 502/504)
Usage: python3 patch_p4a.py <path-to-python-for-android>
"""
import sys, py_compile

base = sys.argv[1]
build_py = base + "/pythonforandroid/build.py"
s = open(build_py).read()
changed = False

# 1) Skip pip self-upgrade
old1 = """        info('Upgrade pip to latest version')
        shprint(sh.bash, '-c', (
            "source venv/bin/activate && pip install -U pip"
        ), _env=copy.copy(base_env))"""
new1 = """        info('SKIP pip self-upgrade (CDN truncation corrupts it); using ensurepip pip')"""
if old1 in s:
    s = s.replace(old1, new1); changed = True; print("patched: skip pip self-upgrade")
elif "SKIP pip self-upgrade" in s:
    print("already: pip self-upgrade skipped")

# 2) Skip Cython install
old2 = """        info('Install Cython in case one of the modules needs it to build')
        shprint(sh.bash, '-c', (
            "venv/bin/pip install Cython"
        ), _env=copy.copy(base_env))"""
new2 = """        info('SKIP Cython install (not needed for pure-Python modules)')"""
if old2 in s:
    s = s.replace(old2, new2); changed = True; print("patched: skip Cython install")
elif "SKIP Cython install" in s:
    print("already: Cython skipped")

if changed:
    open(build_py, "w").write(s)
py_compile.compile(build_py, doraise=True)
print("build.py OK ->", build_py)

# 3) Raise recipe download retry in recipe.py (GitHub egress proxy -> bursty 502/504)
recipe_py = base + "/pythonforandroid/recipe.py"
r = open(recipe_py).read()
rc_changed = False
oldretry = "                    if attempts >= 5:\n                        raise"
newretry = "                    if attempts >= 18:\n                        raise"
if oldretry in r:
    r = r.replace(oldretry, newretry)
    rc_changed = True
    print("patched: download max attempts 5 -> 18")
# Also cap the backoff sleep so it doesn't exceed 30s (keep retries moving)
oldsleep = "                    time.sleep(seconds)\n                    seconds *= 2"
newsleep = "                    seconds = min(seconds * 2, 30)\n                    time.sleep(seconds)"
if oldsleep in r:
    r = r.replace(oldsleep, newsleep)
    rc_changed = True
    print("patched: download backoff capped at 30s")
if rc_changed:
    open(recipe_py, "w").write(r)
    py_compile.compile(recipe_py, doraise=True)
    print("recipe.py OK ->", recipe_py)
else:
    print("note: recipe.py retry pattern not found; buildozer-level retries still apply")
