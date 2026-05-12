"""
WinGUI — Native Win32 GUI framework
Copyright (C) 2026 Divyanshu Sinha

Licensed under GNU LGPL v3.0
=============================

diag.py — WinGUI diagnostic
Run this INSTEAD of wingui.py to see the exact Win32 error code.

    python diag.py

It patches create_label / create_button / create_textbox to print
GetLastError() before Python raises OSError, so you can look up exactly
what Win32 is complaining about.
"""
import ctypes
import ctypes.wintypes as wt
import os
import sys

# ── locate the DLL ────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
DLL_PATH = os.path.join(HERE, "wingui32.dll")

if not os.path.isfile(DLL_PATH):
    sys.exit(f"[DIAG] wingui32.dll not found at {DLL_PATH!r}")

dll = ctypes.CDLL(DLL_PATH)
kernel32 = ctypes.WinDLL("kernel32")
user32   = ctypes.WinDLL("user32")

# ── bind prototypes (same as wingui2.py) ──────────────────────────────────────
HWND   = wt.HWND
HMENU  = ctypes.c_void_p
BOOL   = wt.BOOL
INT    = ctypes.c_int
LPCSTR = ctypes.c_char_p

dll.create_window.restype  = HWND
dll.create_window.argtypes = [INT, INT, LPCSTR]

dll.create_label.restype   = HWND
dll.create_label.argtypes  = [HWND, INT, INT, INT, INT, LPCSTR]

dll.create_button.restype  = HWND
dll.create_button.argtypes = [HWND, INT, INT, INT, INT, LPCSTR, HMENU]

dll.create_textbox.restype  = HWND
dll.create_textbox.argtypes = [HWND, INT, INT, INT, INT]

dll.run_message_loop.restype  = None
dll.run_message_loop.argtypes = []

dll.close_window.restype  = None
dll.close_window.argtypes = [HWND]

# CommandCallback so the window stays open
CommandCB = ctypes.WINFUNCTYPE(None, HWND, wt.WORD, wt.WORD, HWND)
dll.set_callback.restype  = None
dll.set_callback.argtypes = [ctypes.c_void_p]

# ── Win32 error helpers ───────────────────────────────────────────────────────
_FORMAT_MESSAGE = 0x00001300   # FORMAT_MESSAGE_FROM_SYSTEM | IGNORE_INSERTS | ALLOCATE_BUFFER

def win32_error_string(code: int) -> str:
    buf = ctypes.c_wchar_p()
    n = kernel32.FormatMessageW(
        _FORMAT_MESSAGE, None, code, 0,
        ctypes.byref(buf), 0, None
    )
    msg = buf.value.strip() if (n and buf.value) else "(no description)"
    kernel32.LocalFree(buf)
    return msg

def last_error() -> tuple[int, str]:
    code = kernel32.GetLastError()
    return code, win32_error_string(code)

# ── diagnostic helpers ────────────────────────────────────────────────────────
def diag_call(fn_name: str, result, *args_repr):
    if not result:
        code, msg = last_error()
        print(f"[DIAG] {fn_name}({', '.join(str(a) for a in args_repr)}) → NULL")
        print(f"       GetLastError() = {code}  (0x{code:08X})")
        print(f"       {msg}")
    else:
        print(f"[DIAG] {fn_name} → OK  hwnd=0x{result:016X}")
    return result

# ── run the same sequence as the smoke test ───────────────────────────────────
print("[DIAG] Creating window ...")
hwnd = dll.create_window(660, 420, b"WinGUI diag")
hwnd = diag_call("create_window", hwnd)
if not hwnd:
    sys.exit("[DIAG] create_window failed — cannot continue.")

print("\n[DIAG] create_label ...")
lbl = dll.create_label(hwnd, 20, 20, 220, 22, "Name:".encode("utf-8"))
lbl = diag_call("create_label", lbl, "parent", 20, 20, 220, 22)

print("\n[DIAG] create_button ...")
btn = dll.create_button(hwnd, 20, 60, 120, 32, "OK".encode("utf-8"), 1)
btn = diag_call("create_button", btn, "parent", 20, 60, 120, 32)

print("\n[DIAG] create_textbox ...")
txt = dll.create_textbox(hwnd, 20, 100, 300, 28)
txt = diag_call("create_textbox", txt, "parent", 20, 100, 300, 28)

# ── also print hInstance the DLL used ────────────────────────────────────────
# We can infer it: GetWindowLongPtrW(hwnd, GWLP_HINSTANCE = -6)
GWLP_HINSTANCE = -6
hinstance_of_window = user32.GetWindowLongPtrW(hwnd, GWLP_HINSTANCE)
our_module = kernel32.GetModuleHandleW(None)
print(f"\n[DIAG] hInstance of window  = 0x{hinstance_of_window & 0xFFFFFFFFFFFFFFFF:016X}")
print(f"[DIAG] GetModuleHandle(NULL) = 0x{our_module & 0xFFFFFFFFFFFFFFFF:016X}")

# ── check InitCommonControlsEx ran by testing if STATIC class exists ──────────
# Try CreateWindowExW ourselves with NULL hInstance to see what Python gets
print("\n[DIAG] Testing STATIC class directly from Python ctypes ...")
kernel32.SetLastError(0)
test_hwnd = user32.CreateWindowExW(
    0,          # dwExStyle
    "STATIC",   # class name
    "Test",     # window name
    0x50000000, # WS_CHILD | WS_VISIBLE
    0, 0, 100, 20,
    hwnd,       # parent
    None,       # hMenu
    None,       # hInstance = NULL
    None        # lpParam
)
code, msg = last_error()
if test_hwnd:
    print(f"[DIAG] Python STATIC → OK  hwnd=0x{test_hwnd:016X}  (class is available)")
    user32.DestroyWindow(test_hwnd)
else:
    print(f"[DIAG] Python STATIC → NULL  error={code} (0x{code:08X})  {msg}")

# ── install a minimal callback and run ────────────────────────────────────────
_cb_ref = None

def on_command(h, ctrl_id, notif, ctrl_hwnd):
    print(f"[DIAG] WM_COMMAND: ctrl_id={ctrl_id} notif={notif}")
    if ctrl_id == 99:
        dll.close_window(h)

_cb_ref = CommandCB(on_command)
dll.set_callback(_cb_ref)

print("\n[DIAG] Entering message loop — close the window to exit.")
dll.run_message_loop()
print("[DIAG] Done.")
