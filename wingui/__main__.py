"""
WinGUI — Native Win32 GUI framework
Copyright (C) 2026 Divyanshu Sinha

Licensed under GNU LGPL v3.0
=============================

wingui/__main__.py
==================
Entry point for ``python -m wingui``.

Modes
-----
  python -m wingui              Interactive quick-start launcher (default)
  python -m wingui --demo       Run the built-in Hello World demo directly
  python -m wingui --examples   Launch the full 22-example gallery
  python -m wingui --check      Verify the DLL is present and loadable
  python -m wingui --help       Show this help text

All modes perform a DLL health-check first and print a clear build
command if wingui32.dll is missing.
"""

from __future__ import annotations

import ctypes
import os
import sys
import textwrap
import traceback

# ---------------------------------------------------------------------------
# Platform guard (mirrors wingui.py — give a clear error before importing)
# ---------------------------------------------------------------------------
if sys.platform != "win32":
    print(
        "wingui is a Windows-only package.\n"
        f"Current platform: {sys.platform!r}\n"
        "Exiting.",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Colour helpers (Windows 10+ VT100 via ENABLE_VIRTUAL_TERMINAL_PROCESSING)
# ---------------------------------------------------------------------------
def _enable_vt() -> bool:
    """Enable ANSI escape codes in the Windows console. Returns True on success."""
    try:
        import ctypes as _ct
        kernel32 = _ct.WinDLL("kernel32", use_last_error=True)
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        STDOUT_HANDLE = kernel32.GetStdHandle(-11)
        mode = _ct.c_ulong(0)
        kernel32.GetConsoleMode(STDOUT_HANDLE, _ct.byref(mode))
        kernel32.SetConsoleMode(STDOUT_HANDLE, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
        return True
    except Exception:
        return False


_VT = _enable_vt()

def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _VT else text

def green(t: str)  -> str: return _c(t, "32")
def yellow(t: str) -> str: return _c(t, "33")
def cyan(t: str)   -> str: return _c(t, "36")
def bold(t: str)   -> str: return _c(t, "1")
def red(t: str)    -> str: return _c(t, "31")
def dim(t: str)    -> str: return _c(t, "2")

# ---------------------------------------------------------------------------
# DLL discovery & health-check
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))

_BUILD_HINT = textwrap.dedent("""\
    Build it with MSYS2 / MinGW-w64:

        nasm -f win64 wingui32.asm -o wingui32.obj
        gcc  -shared -o wingui32.dll wingui32.obj \\
             -luser32 -lkernel32 -lgdi32 -lcomctl32

    Or with MSVC:

        nasm -f win64 wingui32.asm -o wingui32.obj
        link /DLL /OUT:wingui32.dll          \\
             /EXPORT:create_window           \\
             /EXPORT:show_window             \\
             /EXPORT:run_message_loop        \\
             /EXPORT:create_button           \\
             /EXPORT:create_label            \\
             /EXPORT:create_textbox          \\
             /EXPORT:set_window_title        \\
             /EXPORT:show_message_box        \\
             /EXPORT:close_window            \\
             /EXPORT:set_callback            \\
             wingui32.obj user32.lib kernel32.lib gdi32.lib comctl32.lib

    Place wingui32.dll in the same directory as wingui.py.
""")


def _find_dll() -> str | None:
    """Return the path to wingui32.dll / wingui2.dll, or None if not found."""
    for name in ("wingui32.dll", "wingui2.dll"):
        candidate = os.path.join(_HERE, name)
        if os.path.isfile(candidate):
            return candidate
    return None


def _check_dll(verbose: bool = True) -> bool:
    """
    Verify the DLL can be found and loaded.  Prints status to stdout.
    Returns True when everything is healthy.
    """
    dll_path = _find_dll()

    if dll_path is None:
        if verbose:
            print(red("✗  wingui32.dll not found"))
            print(dim(f"   Searched: {_HERE}"))
            print()
            print(yellow("   To build the DLL:"))
            print(textwrap.indent(_BUILD_HINT, "   "))
        return False

    try:
        ctypes.CDLL(dll_path)
    except OSError as exc:
        if verbose:
            print(red(f"✗  Found {os.path.basename(dll_path)} but could not load it"))
            print(dim(f"   Path   : {dll_path}"))
            print(dim(f"   Reason : {exc}"))
            print()
            print(yellow("   Common causes:"))
            print("   • DLL was compiled for x86 but Python is x64 (or vice-versa)")
            print("   • Missing -lgdi32 or -lcomctl32 in the link step")
            print("   • Rebuilt with MSVC but missing MSVC runtime — add /MT flag")
            print()
            print(yellow("   Rebuild hint:"))
            print(textwrap.indent(_BUILD_HINT, "   "))
        return False

    if verbose:
        print(green(f"✓  {os.path.basename(dll_path)} loaded successfully"))
        print(dim(f"   Path: {dll_path}"))
    return True


# ---------------------------------------------------------------------------
# Win32 read/write helpers (used in the built-in demo)
# ---------------------------------------------------------------------------
_user32 = ctypes.WinDLL("user32")


def _read(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(512)
    _user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value


def _write(hwnd: int, text: str) -> None:
    _user32.SetWindowTextW(hwnd, text)


# ---------------------------------------------------------------------------
# Built-in Hello World demo
# ---------------------------------------------------------------------------
def _run_demo() -> None:
    """
    A compact but feature-complete Hello World window that exercises:
      - create_window / create_label / create_textbox / create_button
      - on_command decorator (multiple handlers, multiple control IDs)
      - set_window_title (dynamic title bar)
      - show_message_box
      - close_window (Quit button)
      - context manager (__exit__ frees GDI handles)
    """
    from wingui import WinGUI

    print(bold("\nLaunching Hello World demo …"))
    print(dim("Close the window or click Quit to return to the menu.\n"))

    with WinGUI() as gui:
        hwnd = gui.create_window(540, 280, "wingui - Hello World")

        # ── Row 1: name input ─────────────────────────────────────────────
        gui.create_label  (hwnd,  20,  24, 160, 22, "Your name:")
        txt_name = gui.create_textbox(hwnd, 185,  22, 335, 28)

        # ── Row 2: message input ──────────────────────────────────────────
        gui.create_label  (hwnd,  20,  66, 160, 22, "Message:")
        txt_msg  = gui.create_textbox(hwnd, 185,  64, 335, 28)

        # ── Status label (updated dynamically) ───────────────────────────
        gui.create_label  (hwnd,  20, 108, 100, 22, "Status:")
        lbl_status = gui.create_label(hwnd, 125, 108, 395, 22, "Waiting…")

        # ── Buttons ───────────────────────────────────────────────────────
        gui.create_button (hwnd,  20, 160, 130, 36, "Say Hello",      control_id=1)
        gui.create_button (hwnd, 165, 160, 130, 36, "Clear",          control_id=2)
        gui.create_button (hwnd, 310, 160, 130, 36, "About",          control_id=3)
        gui.create_button (hwnd, 455, 160,  65, 36, "Quit",           control_id=99)

        click_count = [0]

        # ── Handler: Say Hello ────────────────────────────────────────────
        @gui.on_command(control_id=1)
        def on_hello(h, ctrl_id, notif, ctrl_hwnd):
            name = _read(txt_name).strip() or "stranger"
            msg  = _read(txt_msg ).strip() or "(no message)"
            click_count[0] += 1
            gui.set_window_title(h, f"wingui - Hello #{click_count[0]}")
            _write(lbl_status, f"Said hello {click_count[0]} time(s)")
            gui.show_message_box(
                f"Hello, {name}!\n\n{msg}",
                "Greeting 🎉",
            )

        # ── Handler: Clear ────────────────────────────────────────────────
        @gui.on_command(control_id=2)
        def on_clear(h, ctrl_id, notif, ctrl_hwnd):
            _write(txt_name, "")
            _write(txt_msg,  "")
            _write(lbl_status, "Cleared.")
            gui.set_window_title(h, "wingui - Hello World")

        # ── Handler: About ────────────────────────────────────────────────
        @gui.on_command(control_id=3)
        def on_about(h, ctrl_id, notif, ctrl_hwnd):
            gui.show_message_box(
                "wingui v1.0.0\n\n"
                "Native Win32 GUI for Python.\n"
                "All GUI logic runs in NASM x86-64 Assembly\n"
                "via a pure ctypes shim — no third-party deps.\n\n"
                "Author: Divyanshu Sinha\n"
                "License: LGPL v3+",
                "About wingui",
            )

        # ── Handler: Quit ─────────────────────────────────────────────────
        @gui.on_command(control_id=99)
        def on_quit(h, ctrl_id, notif, ctrl_hwnd):
            gui.close_window(h)

        gui.run_message_loop()

    print(green("Demo closed.\n"))


# ---------------------------------------------------------------------------
# Launch the example gallery (example.py)
# ---------------------------------------------------------------------------
def _run_examples() -> None:
    """Import and run the interactive gallery from example.py."""
    gallery_path = os.path.join(_HERE, "example.py")
    if not os.path.isfile(gallery_path):
        # Also try 'examples.py' as an alternate name
        gallery_path = os.path.join(_HERE, "examples.py")

    if not os.path.isfile(gallery_path):
        print(red("✗  example.py not found in the package directory."))
        print(dim(f"   Looked in: {_HERE}"))
        return

    # Run as a standalone script so its __name__ == "__main__" guard fires
    import runpy
    runpy.run_path(gallery_path, run_name="__main__")


# ---------------------------------------------------------------------------
# Interactive quick-start launcher
# ---------------------------------------------------------------------------
_BANNER = r"""
 __        ___       ____  _   _ ___
 \ \      / (_)_ __ / ___|| | | |_ _|
  \ \ /\ / /| | '_ \| |  _| | | || |
   \ V  V / | | | | | |_| | |_| || |
    \_/\_/  |_|_| |_|\____|\___/|___|

  Native Win32 GUI for Python — v1.0.0
"""

_MENU = """\
  ┌───────────────────────────────────────┐
  │  1.  Run Hello World demo             │
  │  2.  Open the 22-example gallery      │
  │  3.  Verify DLL installation          │
  │  4.  Show quick-start code snippet    │
  │  0.  Exit                             │
  └───────────────────────────────────────┘"""

_SNIPPET = '''\
    from wingui import WinGUI

    with WinGUI() as gui:
        hwnd = gui.create_window(640, 400, "My App")

        gui.create_label  (hwnd, 20, 20, 200, 22, "Your name:")
        txt = gui.create_textbox(hwnd, 20, 48, 300, 28)
        gui.create_button (hwnd, 20, 96, 130, 36, "Say Hello", control_id=1)

        @gui.on_command(control_id=1)
        def on_hello(hwnd, ctrl_id, notif, ctrl_hwnd):
            import ctypes
            buf = ctypes.create_unicode_buffer(256)
            ctypes.WinDLL("user32").GetWindowTextW(txt, buf, 256)
            gui.show_message_box(f"Hello, {buf.value or \'stranger\'}!", "Hi")

        gui.run_message_loop()
'''


def _interactive() -> None:
    print(bold(cyan(_BANNER)))

    dll_ok = _check_dll(verbose=False)
    if dll_ok:
        dll_path = _find_dll()
        print(green(f"  ✓  {os.path.basename(dll_path)} ready"))
    else:
        print(red("  ✗  wingui32.dll not found or failed to load"))
        print(yellow("     Select option 3 for build instructions.\n"))

    while True:
        print()
        print(_MENU)
        print()
        try:
            raw = input(bold("  Choice: ")).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break

        if raw == "0":
            print("  Goodbye!")
            break

        elif raw == "1":
            if not dll_ok:
                print(red("\n  DLL not ready — select option 3 for build instructions."))
                continue
            try:
                _run_demo()
            except Exception:
                traceback.print_exc()

        elif raw == "2":
            if not dll_ok:
                print(red("\n  DLL not ready — select option 3 for build instructions."))
                continue
            try:
                _run_examples()
            except Exception:
                traceback.print_exc()

        elif raw == "3":
            print()
            _check_dll(verbose=True)

        elif raw == "4":
            print()
            print(bold("  Quick-start snippet:"))
            print()
            for line in _SNIPPET.splitlines():
                print(cyan("  " + line))
            print()

        else:
            print(f"  '{raw}' is not a valid option — choose 0–4.")


# ---------------------------------------------------------------------------
# CLI argument parsing (kept minimal — no argparse dependency)
# ---------------------------------------------------------------------------
def _parse_args() -> str:
    """Return one of: 'interactive', 'demo', 'examples', 'check', 'help'."""
    argv = sys.argv[1:]
    if not argv:
        return "interactive"
    flag = argv[0].lower()
    mapping = {
        "--demo":     "demo",
        "--examples": "examples",
        "--check":    "check",
        "--help":     "help",
        "-h":         "help",
    }
    return mapping.get(flag, "help")


def _print_help() -> None:
    print(__doc__)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main() -> None:
    mode = _parse_args()

    if mode == "help":
        _print_help()
        return

    if mode == "check":
        print()
        ok = _check_dll(verbose=True)
        print()
        sys.exit(0 if ok else 1)

    if mode == "demo":
        if not _check_dll(verbose=False):
            print(red("wingui32.dll not found or could not be loaded."))
            print(yellow(_BUILD_HINT))
            sys.exit(1)
        _run_demo()
        return

    if mode == "examples":
        if not _check_dll(verbose=False):
            print(red("wingui32.dll not found or could not be loaded."))
            print(yellow(_BUILD_HINT))
            sys.exit(1)
        _run_examples()
        return

    # default — interactive launcher
    _interactive()


if __name__ == "__main__":
    main()
