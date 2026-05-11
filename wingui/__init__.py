"""
wingui
=======
Native Win32 GUI for Python.

All GUI logic is implemented in NASM x86-64 Assembly (wingui_production.asm)
and compiled to wingui2.dll.  This package is a pure ctypes shim — zero
middleware, zero third-party dependencies.

Quick start (OOP style)
-----------------------
    from wingui import WinGUI

    gui  = WinGUI()
    hwnd = gui.create_window(800, 600, "My App")
    btn  = gui.create_button(hwnd, 10, 10, 100, 30, "Click Me", control_id=1)

    @gui.on_command(control_id=1)
    def on_click(hwnd, ctrl_id, notif, ctrl_hwnd):
        gui.show_message_box("Hello!", "Info")

    gui.run_message_loop()

Quick start (flat API)
----------------------
    import wingui

    hwnd = wingui.create_window(800, 600, "My App")
    wingui.create_button(hwnd, 10, 10, 100, 30, "OK", control_id=1)

    @wingui.on_command(control_id=1)
    def on_ok(hwnd, ctrl_id, notif, ctrl_hwnd):
        wingui.show_message_box("Done!", "Info")

    wingui.run_message_loop()

Platform
--------
Windows only (x86-64).  Importing on any other platform raises ImportError.
"""

from .wingui import (
    # OOP interface
    WinGUI,

    # Flat / module-level API
    create_window,
    show_window,
    run_message_loop,
    create_button,
    create_label,
    create_textbox,
    set_window_title,
    show_message_box,
    close_window,
    set_callback,
    on_command,

    # ctypes callback type (useful for type annotations)
    CommandCallbackType,
)

__all__ = [
    # OOP
    "WinGUI",
    # Flat API
    "create_window",
    "show_window",
    "run_message_loop",
    "create_button",
    "create_label",
    "create_textbox",
    "set_window_title",
    "show_message_box",
    "close_window",
    "set_callback",
    "on_command",
    # Types
    "CommandCallbackType",
]

__version__  = "1.0.0"
__author__   = "Divyanshu Sinha"
__email__    = "divyanshu.sinha631@gmail.com"
__license__  = "LGPL v3+"
