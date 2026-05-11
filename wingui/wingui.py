"""
wingui.py — Python ctypes interface for wingui32.asm
========================================================

Architecture
------------
All GUI logic lives in **wingui32.dll**, compiled from NASM x86-64 Assembly.
This module is a pure ctypes shim — zero GUI logic of its own.

DLL features (transparent to callers):
  • UTF-8 strings accepted natively — pass any Python str, no manual encode.
  • Modern UI: Visual Styles (ComCtl32 v6), Segoe UI 10pt font, DPI-aware,
    modern #F3F3F3 background, themed buttons and labels.

Build the DLL (MSYS2 / MinGW-w64)
----------------------------------
    nasm -f win64 wingui32.asm -o wingui32.obj
    gcc  -shared -o wingui32.dll wingui32.obj ^
         -luser32 -lkernel32 -lgdi32 -lcomctl32

Build the DLL (MSVC)
---------------------
    nasm -f win64 wingui32.asm -o wingui32.obj
    link /DLL /OUT:wingui32.dll ^
         /EXPORT:create_window  /EXPORT:show_window      ^
         /EXPORT:run_message_loop /EXPORT:create_button  ^
         /EXPORT:create_label   /EXPORT:create_textbox   ^
         /EXPORT:set_window_title /EXPORT:show_message_box ^
         /EXPORT:close_window   /EXPORT:set_callback     ^
         wingui32.obj user32.lib kernel32.lib gdi32.lib comctl32.lib

Quick start (OOP style)
-----------------------
    from wingui import WinGUI

    with WinGUI() as gui:
        hwnd = gui.create_window(800, 600, "My App — 你好 🌍")

        gui.create_label (hwnd, 20, 20, 200, 20, "Enter your name:")
        txt = gui.create_textbox(hwnd, 20, 48, 200, 28)
        gui.create_button(hwnd, 20, 90, 100, 32, "Say Hello", control_id=1)

        @gui.on_command(control_id=1)
        def on_hello(hwnd, ctrl_id, notif, ctrl_hwnd):
            import ctypes
            buf = ctypes.create_unicode_buffer(256)
            ctypes.WinDLL("user32").GetWindowTextW(txt, buf, 256)
            name = buf.value or "stranger"
            gui.show_message_box(f"Hello, {name}! 👋", "Greeting")

        gui.run_message_loop()

Quick start (flat API)
----------------------
    import wingui

    hwnd = wingui.create_window(640, 400, "Flat API")
    wingui.create_button(hwnd, 20, 20, 100, 32, "OK", control_id=1)

    @wingui.on_command(control_id=1)
    def on_ok(hwnd, ctrl_id, notif, ctrl_hwnd):
        wingui.show_message_box("Done!", "Info")

    wingui.run_message_loop()
"""

import ctypes
import ctypes.wintypes as wt
import os
import sys
import threading
import traceback
from types import TracebackType
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Platform guard
# ---------------------------------------------------------------------------
if sys.platform != "win32":
    raise ImportError(
        "wingui is a Windows-only module — "
        f"current platform is {sys.platform!r}"
    )

# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------
__version__ = "1.0.0"
__author__  = "Divyanshu Sinha"
__email__   = "divyanshu.sinha631@gmail.com"
__license__ = "LGPL-3+"

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
#
# HWND / HMENU are c_size_t, NOT wt.HWND (c_void_p).
#
# ctypes maps c_void_p return values to Python int OR None (for zero).
# That None breaks "if hwnd == 0" guards and causes false failures when a
# control gets a low-numbered handle.  c_size_t always returns a plain int:
# 0 = failure, anything else = valid handle.  Safe on both x86 and x64.
#
HWND      = ctypes.c_size_t   # 64-bit on x64 — always a plain int
HMENU     = ctypes.c_size_t   # same
HINSTANCE = ctypes.c_void_p
BOOL      = wt.BOOL
INT       = ctypes.c_int
WORD      = ctypes.c_uint16
UINT      = ctypes.c_uint32
LPCSTR    = ctypes.c_char_p   # UTF-8 bytes going into the DLL

# ---------------------------------------------------------------------------
# Callback type
# ---------------------------------------------------------------------------
#: WM_COMMAND callback type.  Signature::
#:
#:     def handler(hwnd, ctrl_id, notif, ctrl_hwnd) -> None: ...
#:
#: Keep a Python reference alive for the window's lifetime — ctypes will not
#: prevent GC, and the DLL would then hold a dangling pointer.
CommandCallbackType = ctypes.WINFUNCTYPE(
    None,   # void return
    HWND,   # hwnd       — parent window
    WORD,   # ctrl_id    — control identifier
    WORD,   # notif      — notification code  (BN_CLICKED = 0 for buttons)
    HWND,   # ctrl_hwnd  — child control
)

# ---------------------------------------------------------------------------
# DLL loader
# ---------------------------------------------------------------------------

def _load_dll(path: Optional[str] = None) -> ctypes.CDLL:
    """Load wingui32.dll (or legacy wingui2.dll) from *path* or next to this file.

    Parameters
    ----------
    path:
        Explicit path to the DLL.  When *None* the loader searches the
        directory containing this file for ``wingui32.dll`` then
        ``wingui2.dll``.

    Returns
    -------
    ctypes.CDLL

    Raises
    ------
    FileNotFoundError
        When no DLL is found.
    OSError
        When the DLL exists but fails to load (wrong bitness, missing
        ``gdi32`` / ``comctl32`` dependency, etc.).
    """
    if path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        # Support both the new name (wingui32.dll) and the legacy name (wingui2.dll)
        for _name in ("wingui32.dll", "wingui2.dll"):
            _candidate = os.path.join(here, _name)
            if os.path.isfile(_candidate):
                path = _candidate
                break
        else:
            raise FileNotFoundError(
                f"wingui32.dll (or wingui2.dll) not found in '{here}'.\n"
                "Build it first:\n"
                "  nasm -f win64 wingui32.asm -o wingui32.obj\n"
                "  gcc -shared -o wingui32.dll wingui32.obj"
                " -luser32 -lkernel32 -lgdi32 -lcomctl32"
            )
    if not os.path.isfile(path):
        raise FileNotFoundError(f"DLL not found at '{path}'.")
    return ctypes.CDLL(path)


# ---------------------------------------------------------------------------
# Encoding helper
# ---------------------------------------------------------------------------

def _enc(s: str) -> bytes:
    """Encode *s* as UTF-8 bytes for the DLL.

    The v3 DLL accepts UTF-8 ``const char*`` and converts to UTF-16LE
    internally via MultiByteToWideChar before any Win32 W-API call.
    Full Unicode — emoji, CJK, Arabic, etc. — is supported.
    """
    return s.encode("utf-8")


# ===========================================================================
# WinGUI  —  high-level wrapper
# ===========================================================================

class WinGUI:
    """High-level Pythonic wrapper around the wingui32 Assembly DLL.

    Supports both plain usage and the **context manager** protocol.
    In context-manager mode the window is closed and GDI resources are
    freed automatically when the ``with`` block exits.

    Parameters
    ----------
    dll_path:
        Optional explicit path to ``wingui32.dll``.  When *None* (default)
        the DLL is located automatically next to this file.

    Examples
    --------
    OOP style::

        gui  = WinGUI()
        hwnd = gui.create_window(800, 600, "Hello")
        gui.create_button(hwnd, 20, 20, 100, 35, "OK", control_id=1)

        @gui.on_command(control_id=1)
        def on_ok(hwnd, ctrl_id, notif, ctrl_hwnd):
            gui.show_message_box("Clicked!", "Info")

        gui.run_message_loop()

    Context-manager style (resources freed automatically)::

        with WinGUI() as gui:
            hwnd = gui.create_window(800, 600, "Managed")
            gui.create_button(hwnd, 20, 20, 100, 35, "Quit", control_id=99)

            @gui.on_command(control_id=99)
            def on_quit(h, c, n, ch):
                gui.close_window(h)

            gui.run_message_loop()
    """

    # ------------------------------------------------------------------
    # Construction / teardown
    # ------------------------------------------------------------------

    def __init__(self, dll_path: Optional[str] = None) -> None:
        self._dll: ctypes.CDLL = _load_dll(dll_path)
        self._hwnd: Optional[int] = None
        self._setup_prototypes()
        self._callback_map: dict[
            tuple[Optional[int], Optional[int]], list[Callable]
        ] = {}
        self._raw_callback: Optional[CommandCallbackType] = None  # keep alive!
        self._loop_thread:  Optional[threading.Thread]    = None

    # ── context manager ──────────────────────────────────────────────

    def __enter__(self) -> "WinGUI":
        """Enter the context manager — returns *self*."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val:  Optional[BaseException],
        exc_tb:   Optional[TracebackType],
    ) -> bool:
        """Close the window and free GDI resources on block exit.

        Exceptions from inside the ``with`` block are never suppressed.
        """
        try:
            if self._hwnd and self._hwnd != 0:
                self._dll.close_window(self._hwnd)
        except Exception:
            traceback.print_exc()
        return False

    # ------------------------------------------------------------------
    # Prototype binding
    # ------------------------------------------------------------------

    def _setup_prototypes(self) -> None:
        """Bind ctypes argtypes / restype for every DLL export.

        Called once in ``__init__``.  Explicit prototypes let ctypes validate
        argument types and marshal integers correctly on x64.

        All string parameters are ``c_char_p`` (UTF-8 bytes) because the v3
        DLL converts UTF-8 → UTF-16LE internally via MultiByteToWideChar.
        HWND / HMENU parameters use ``c_size_t`` (see module-level note).
        """
        dll = self._dll

        # HWND create_window(INT width, INT height, LPCSTR title_utf8)
        dll.create_window.restype  = HWND
        dll.create_window.argtypes = [INT, INT, LPCSTR]

        # void show_window(HWND hwnd)
        dll.show_window.restype  = None
        dll.show_window.argtypes = [HWND]

        # void run_message_loop()
        # Blocks on GetMessageW / DispatchMessageW until WM_QUIT.
        dll.run_message_loop.restype  = None
        dll.run_message_loop.argtypes = []

        # HWND create_button(HWND parent, INT x, INT y, INT w, INT h,
        #                    LPCSTR text_utf8, HMENU control_id)
        # Creates WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON + WM_SETFONT Segoe UI.
        # hInstance for BUTTON class = NULL (system-registered class).
        dll.create_button.restype  = HWND
        dll.create_button.argtypes = [HWND, INT, INT, INT, INT, LPCSTR, HMENU]

        # HWND create_label(HWND parent, INT x, INT y, INT w, INT h,
        #                   LPCSTR text_utf8)
        # Creates WS_CHILD | WS_VISIBLE STATIC + WM_SETFONT Segoe UI.
        # hInstance = NULL (system-registered class).
        dll.create_label.restype  = HWND
        dll.create_label.argtypes = [HWND, INT, INT, INT, INT, LPCSTR]

        # HWND create_textbox(HWND parent, INT x, INT y, INT w, INT h)
        # Creates ES_AUTOHSCROLL EDIT control + WM_SETFONT Segoe UI.
        # Read/write via user32.GetWindowTextW / SetWindowTextW.
        dll.create_textbox.restype  = HWND
        dll.create_textbox.argtypes = [HWND, INT, INT, INT, INT]

        # BOOL set_window_title(HWND hwnd, LPCSTR title_utf8)
        # Converts UTF-8 → UTF-16LE and calls SetWindowTextW.
        dll.set_window_title.restype  = BOOL
        dll.set_window_title.argtypes = [HWND, LPCSTR]

        # INT show_message_box(LPCSTR text_utf8, LPCSTR caption_utf8)
        # Both strings converted to WCHAR.  Returns MessageBoxW result code.
        dll.show_message_box.restype  = INT
        dll.show_message_box.argtypes = [LPCSTR, LPCSTR]

        # void close_window(HWND hwnd)
        # DestroyWindow → PostQuitMessage(0).  Also frees font + brush.
        # Pass 0 to close the internally stored main window.
        dll.close_window.restype  = None
        dll.close_window.argtypes = [HWND]

        # void set_callback(void* fn)
        # Raw WM_COMMAND hook.  Prefer @on_command over this.
        dll.set_callback.restype  = None
        dll.set_callback.argtypes = [ctypes.c_void_p]

    # ------------------------------------------------------------------
    # Window lifecycle
    # ------------------------------------------------------------------

    def create_window(
        self,
        width:  int = 800,
        height: int = 600,
        title:  str = "Window",
    ) -> int:
        """Create and show the main application window.

        On first call the DLL performs one-time modern UI initialisation:
        SetProcessDpiAwarenessContext, InitCommonControlsEx,
        CreateFontW("Segoe UI" 10pt ClearType), CreateSolidBrush(#F3F3F3).

        Parameters
        ----------
        width, height:
            Window dimensions in pixels.
        title:
            Title bar text.  Full Unicode accepted (UTF-8 → UTF-16LE in DLL).

        Returns
        -------
        int
            The window HWND.  Store it to pass to control-creation methods.

        Raises
        ------
        OSError
            When CreateWindowExW returns NULL.
        """
        hwnd = self._dll.create_window(width, height, _enc(title))
        if hwnd == 0:
            import ctypes as _ct
            _err = _ct.WinDLL("kernel32").GetLastError()
            raise OSError(
                f"create_window failed — Win32 error {_err} (0x{_err:08X})\n"
                "Check the DLL is built with -lgdi32 and -lcomctl32."
            )
        self._hwnd = hwnd
        return hwnd

    def show_window(self, hwnd: Optional[int] = None) -> None:
        """Call ShowWindow + UpdateWindow on *hwnd*.

        Pass *None* to target the internally stored main window.
        Usually unnecessary — create_window already includes WS_VISIBLE.
        """
        self._dll.show_window(hwnd or 0)

    def run_message_loop(self, threaded: bool = False) -> None:
        """Enter the Win32 message pump.

        Parameters
        ----------
        threaded:
            ``False`` (default) — blocks until the window is closed.
            ``True``            — runs the pump on a daemon thread and
                                  returns immediately (for tests / scripts).

        Warning
        -------
        Win32 requires the message loop on the same thread that called
        CreateWindowExW.  Only use ``threaded=True`` from that thread.
        """
        if threaded:
            self._loop_thread = threading.Thread(
                target=self._dll.run_message_loop,
                daemon=True,
                name="wingui-message-loop",
            )
            self._loop_thread.start()
        else:
            self._dll.run_message_loop()

    # ------------------------------------------------------------------
    # Control factory methods
    # ------------------------------------------------------------------

    def create_button(
        self,
        parent:     int,
        x:          int,
        y:          int,
        width:      int,
        height:     int,
        text:       str,
        control_id: int = 0,
    ) -> int:
        """Create a themed push-button child control.

        Parameters
        ----------
        parent:
            HWND of the parent window.
        x, y:
            Position in pixels relative to the client area.
        width, height:
            Button dimensions in pixels.
        text:
            Button label.  Full Unicode supported.
        control_id:
            Unique non-zero integer — appears as ``ctrl_id`` in callbacks.

        Returns
        -------
        int
            The button HWND.

        Raises
        ------
        OSError
            When CreateWindowExW returns NULL for the button.
        """
        child = self._dll.create_button(
            parent, x, y, width, height, _enc(text), control_id
        )
        if child == 0:
            import ctypes as _ct
            _err = _ct.WinDLL("kernel32").GetLastError()
            raise OSError(
                f"create_button failed (control_id={control_id!r}) — "
                f"Win32 error {_err} (0x{_err:08X})"
            )
        return child

    def create_label(
        self,
        parent: int,
        x:      int,
        y:      int,
        width:  int,
        height: int,
        text:   str,
    ) -> int:
        """Create a read-only STATIC text label.

        Text colour #1A1A1A, background #F3F3F3 set via WM_CTLCOLORSTATIC.

        Parameters
        ----------
        parent:
            HWND of the parent window.
        x, y:
            Position in pixels.
        width, height:
            Label dimensions in pixels.
        text:
            Label text.  Full Unicode supported.

        Returns
        -------
        int
            The label HWND.

        Raises
        ------
        OSError
            When CreateWindowExW returns NULL for the label.
        """
        child = self._dll.create_label(parent, x, y, width, height, _enc(text))
        if child == 0:
            import ctypes as _ct
            _err = _ct.WinDLL("kernel32").GetLastError()
            raise OSError(
                f"create_label failed — Win32 error {_err} (0x{_err:08X})\n"
                f"  parent hwnd = {parent!r}\n"
                f"  Common causes:\n"
                f"    1400 = parent HWND invalid (rebuild DLL, see below)\n"
                f"    1407 = class not found (hInstance wrong in DLL)\n"
                f"  Rebuild: nasm -f win64 wingui32.asm -o wingui32.obj\n"
                f"           gcc -shared -o wingui32.dll wingui32.obj"
                f" -luser32 -lkernel32 -lgdi32 -lcomctl32"
            )
        return child

    def create_textbox(
        self,
        parent: int,
        x:      int,
        y:      int,
        width:  int,
        height: int,
    ) -> int:
        """Create an editable single-line EDIT control.

        The EDIT control operates in Wide mode (CreateWindowExW) — use
        ``user32.GetWindowTextW`` / ``SetWindowTextW`` to read/write content.

        Parameters
        ----------
        parent:
            HWND of the parent window.
        x, y:
            Position in pixels.
        width, height:
            Textbox dimensions in pixels.

        Returns
        -------
        int
            The textbox HWND.

        Raises
        ------
        OSError
            When CreateWindowExW returns NULL.
        """
        child = self._dll.create_textbox(parent, x, y, width, height)
        if child == 0:
            import ctypes as _ct
            _err = _ct.WinDLL("kernel32").GetLastError()
            raise OSError(
                f"create_textbox failed — Win32 error {_err} (0x{_err:08X})"
            )
        return child

    # ------------------------------------------------------------------
    # Window state
    # ------------------------------------------------------------------

    def set_window_title(self, hwnd: int, title: str) -> None:
        """Update the title-bar text at runtime (UTF-8 → SetWindowTextW).

        Raises
        ------
        OSError
            When SetWindowTextW returns zero.
        """
        ok = self._dll.set_window_title(hwnd, _enc(title))
        if not ok:
            raise OSError(
                f"set_window_title failed for hwnd={hwnd!r}"
            )

    def show_message_box(self, text: str, caption: str = "Info") -> int:
        """Show a modal MessageBoxW and wait for the user to dismiss it.

        Parameters
        ----------
        text:
            Message body.  Use \\n for line breaks.
        caption:
            Dialog title.  Defaults to "Info".

        Returns
        -------
        int
            MessageBoxW return code (IDOK=1, IDCANCEL=2, …).
        """
        return self._dll.show_message_box(_enc(text), _enc(caption))

    def close_window(self, hwnd: Optional[int] = None) -> None:
        """Destroy *hwnd* — triggers WM_DESTROY → PostQuitMessage(0).

        Pass *None* to close the internally stored main window.
        Also frees the Segoe UI font and background brush GDI handles.
        """
        self._dll.close_window(hwnd or 0)
        if hwnd is None or hwnd == self._hwnd:
            self._hwnd = None

    # ------------------------------------------------------------------
    # Event / callback system
    # ------------------------------------------------------------------

    def set_callback(self, fn: Callable) -> None:
        """Install a single raw WM_COMMAND callback (replaces @on_command).

        The callable receives::

            fn(hwnd, ctrl_id, notif, ctrl_hwnd) -> None

        The wrapped ctypes object is kept alive on ``self._raw_callback``.
        """
        def _wrapper(hwnd, ctrl_id, notif, ctrl_hwnd):
            try:
                fn(hwnd, ctrl_id, notif, ctrl_hwnd)
            except Exception:
                traceback.print_exc()

        self._raw_callback = CommandCallbackType(_wrapper)
        self._dll.set_callback(self._raw_callback)

    def on_command(
        self,
        control_id: Optional[int] = None,
        notif:      Optional[int] = None,
    ) -> Callable:
        """Decorator factory that registers a WM_COMMAND handler.

        Parameters
        ----------
        control_id:
            Only fire for this control ID.  *None* = any control.
        notif:
            Only fire for this notification code.  *None* = any code.
            BN_CLICKED = 0 for push-buttons.

        Multiple handlers per control_id are supported and called in
        registration order.  A handler that raises does not block others.
        The decorator is transparent — it returns the original function.

        Examples
        --------
        ::

            @gui.on_command(control_id=1)
            def on_save(hwnd, ctrl_id, notif, ctrl_hwnd):
                ...

            # Catch-all
            @gui.on_command()
            def on_any(hwnd, ctrl_id, notif, ctrl_hwnd):
                ...

            # Filter by notification code
            @gui.on_command(control_id=3, notif=0)   # BN_CLICKED
            def on_click_only(hwnd, ctrl_id, notif, ctrl_hwnd):
                ...
        """
        def decorator(fn: Callable) -> Callable:
            key = (control_id, notif)
            self._callback_map.setdefault(key, []).append(fn)
            self._install_dispatch_callback()
            return fn
        return decorator

    def _install_dispatch_callback(self) -> None:
        """Re-install the fan-out dispatcher as the DLL callback.

        Called automatically by on_command.  Do not call directly.
        """
        def _dispatch(hwnd, ctrl_id, notif_code, ctrl_hwnd):
            for (filt_id, filt_notif), handlers in self._callback_map.items():
                if (filt_id    is None or filt_id    == ctrl_id) and \
                   (filt_notif is None or filt_notif == notif_code):
                    for handler in handlers:
                        try:
                            handler(hwnd, ctrl_id, notif_code, ctrl_hwnd)
                        except Exception:
                            traceback.print_exc()

        self._raw_callback = CommandCallbackType(_dispatch)
        self._dll.set_callback(self._raw_callback)


# ===========================================================================
# Module-level flat API  (singleton WinGUI instance)
# ===========================================================================

_instance: Optional[WinGUI] = None


def _get_instance() -> WinGUI:
    """Return (or create) the module-level singleton WinGUI instance."""
    global _instance
    if _instance is None:
        _instance = WinGUI()
    return _instance


def create_window(width: int = 800, height: int = 600, title: str = "Window") -> int:
    """Create the main window via the module singleton."""
    return _get_instance().create_window(width, height, title)

def show_window(hwnd: Optional[int] = None) -> None:
    """Show *hwnd* via the module singleton."""
    _get_instance().show_window(hwnd)

def run_message_loop(threaded: bool = False) -> None:
    """Run the message pump via the module singleton."""
    _get_instance().run_message_loop(threaded)

def create_button(parent, x, y, w, h, text, control_id=0) -> int:
    """Create a button via the module singleton."""
    return _get_instance().create_button(parent, x, y, w, h, text, control_id)

def create_label(parent, x, y, w, h, text) -> int:
    """Create a label via the module singleton."""
    return _get_instance().create_label(parent, x, y, w, h, text)

def create_textbox(parent, x, y, w, h) -> int:
    """Create a textbox via the module singleton."""
    return _get_instance().create_textbox(parent, x, y, w, h)

def set_window_title(hwnd, title: str) -> None:
    """Update the window title via the module singleton."""
    _get_instance().set_window_title(hwnd, title)

def show_message_box(text: str, caption: str = "Info") -> int:
    """Show a message box via the module singleton."""
    return _get_instance().show_message_box(text, caption)

def close_window(hwnd=None) -> None:
    """Close the window via the module singleton."""
    _get_instance().close_window(hwnd)

def set_callback(fn: Callable) -> None:
    """Install a raw callback via the module singleton."""
    _get_instance().set_callback(fn)

def on_command(control_id=None, notif=None) -> Callable:
    """Register a WM_COMMAND handler via the module singleton."""
    return _get_instance().on_command(control_id, notif)


# ===========================================================================
# Smoke test  —  python wingui.py
# ===========================================================================

if __name__ == "__main__":
    import ctypes as _ct

    _user32 = _ct.WinDLL("user32")

    def _read(hwnd: int) -> str:
        buf = _ct.create_unicode_buffer(512)
        _user32.GetWindowTextW(hwnd, buf, 512)
        return buf.value

    with WinGUI() as gui:
        hwnd = gui.create_window(660, 420, "wingui v3 — smoke test 🧪")

        gui.create_label  (hwnd,  20,  20, 220, 22, "Name (any script):")
        txt_name = gui.create_textbox(hwnd, 20,  48, 300, 28)

        gui.create_label  (hwnd,  20,  96, 220, 22, "Message:")
        txt_msg  = gui.create_textbox(hwnd, 20, 122, 600, 28)

        gui.create_button (hwnd,  20, 172, 130, 36, "Say Hello 👋", control_id=1)
        gui.create_button (hwnd, 170, 172, 130, 36, "Clear",        control_id=2)
        gui.create_button (hwnd, 500, 172, 100, 36, "Quit",         control_id=99)

        @gui.on_command(control_id=1)
        def on_hello(h, c, n, ch):
            name = _read(txt_name) or "stranger"
            msg  = _read(txt_msg)  or "(no message)"
            gui.show_message_box(f"Hello, {name}!\n\n{msg}", "Greeting 🎉")

        @gui.on_command(control_id=2)
        def on_clear(h, c, n, ch):
            _user32.SetWindowTextW(txt_name, "")
            _user32.SetWindowTextW(txt_msg,  "")

        @gui.on_command(control_id=99)
        def on_quit(h, c, n, ch):
            gui.close_window(h)

        gui.run_message_loop()
