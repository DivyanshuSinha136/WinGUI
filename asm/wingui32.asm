; ╔══════════════════════════════════════════════════════════════════════════╗
; ║  wingui32.asm  -  UTF-8 input  +  Modern UI  (all bugs fixed)            ║
; ╠══════════════════════════════════════════════════════════════════════════╣
; ║                                                                          ║
; ║  KEY FIXES vs earlier versions                                           ║
; ║  ──────────────────────────────                                          ║
; ║  1. SetProcessDpiAwarenessContext loaded via GetProcAddress at runtime.  ║
; ║     A static extern causes a hard DLL-load failure on Windows < 1703     ║
; ║     because the symbol may not be present in user32.dll.                 ║
; ║                                                                          ║
; ║  2. GetModuleHandleExW(FLAG_FROM_ADDRESS, WindowProc, hInstance) used    ║
; ║     instead of GetModuleHandleW(NULL).  The NULL form returns the host   ║
; ║     EXE handle.  RegisterClassExW must use OUR DLL handle so that        ║
; ║     CreateWindowExW can find the class.                                  ║
; ║                                                                          ║
; ║  3. hInstance = NULL for system control classes (BUTTON / EDIT /         ║
; ║     STATIC).  Passing our DLL handle causes ERROR_CANNOT_FIND_WND_CLASS. ║
; ║                                                                          ║
; ║  4. WS_EX_COMPOSITED removed.  Caused ERROR_INVALID_WINDOW_HANDLE        ║
; ║     when child controls are created before the message loop runs.        ║
; ║                                                                          ║
; ║  5. CreateWindowExW child stack layout corrected:                        ║
; ║     shadow(32) + 8 args(64) = 96 bytes at correct offsets.               ║
; ║                                                                          ║
; ║  UTF-8 INPUT                                                             ║
; ║     All *A Win32 calls replaced with *W.                                 ║
; ║     UTF-8 const char* converted via MultiByteToWideChar(CP_UTF8).        ║
; ║     Python: pass text.encode("utf-8") -- ctypes c_char_p.                ║
; ║                                                                          ║
; ║  MODERN UI                                                               ║
; ║     InitCommonControlsEx(ICC_STANDARD_CLASSES)  - ComCtl32 v6 controls   ║
; ║     CreateFontW("Segoe UI", -13, ClearType)     - sent via WM_SETFONT    ║
; ║     CreateSolidBrush(0x00F3F3F3)               - window background       ║
; ║     WM_CTLCOLORSTATIC  - #1A1A1A text on #F3F3F3                         ║
; ║     WM_CTLCOLORBTN     - NULL_BRUSH so Visual Styles paints buttons      ║
; ║                                                                          ║
; ║  BUILD                                                                   ║
; ║     nasm -f win64 wingui32.asm -o wingui32.obj                           ║
; ║     gcc  -shared -o wingui32.dll wingui32.obj                            ║
; ║          -luser32 -lkernel32 -lgdi32 -lcomctl32                          ║
; ║                                                                          ║
; ║  RSP ALIGNMENT (Microsoft x64 ABI)                                       ║
; ║     On ENTRY  RSP mod 16 = 8  (return address just pushed)               ║
; ║     Before every CALL  RSP mod 16 must = 0                               ║
; ║     Shadow = 32 bytes above RSP, always reserved.                        ║
; ║     Stack args start at [rsp+32], [rsp+40], ...                          ║
; ╚══════════════════════════════════════════════════════════════════════════╝

bits 64
default rel

; ── imports ───────────────────────────────────────────────────────────────────
extern GetModuleHandleW
extern GetModuleHandleExW
extern RegisterClassExW
extern CreateWindowExW
extern ShowWindow
extern UpdateWindow
extern GetMessageW
extern TranslateMessage
extern DispatchMessageW
extern PostQuitMessage
extern DefWindowProcW
extern LoadCursorW
extern LoadIconW
extern MessageBoxW
extern DestroyWindow
extern SetWindowTextW
extern SendMessageW
extern SetBkColor
extern SetTextColor
extern MultiByteToWideChar
extern GetProcAddress
extern LoadLibraryA
extern CreateFontW
extern CreateSolidBrush
extern GetStockObject
extern DeleteObject
extern InitCommonControlsEx

; ── constants ─────────────────────────────────────────────────────────────────
WS_OVERLAPPEDWINDOW     equ 0x00CF0000
WS_VISIBLE              equ 0x10000000
WS_CHILD                equ 0x40000000
WS_BORDER               equ 0x00800000
ES_AUTOHSCROLL          equ 0x0080
BS_PUSHBUTTON           equ 0x00000000
CS_HREDRAW              equ 0x0002
CS_VREDRAW              equ 0x0001
SW_SHOWNORMAL           equ 1
IDC_ARROW               equ 32512
IDI_APPLICATION         equ 32512
WM_DESTROY              equ 0x0002
WM_CLOSE                equ 0x0010
WM_COMMAND              equ 0x0111
WM_SETFONT              equ 0x0030
WM_CTLCOLORSTATIC       equ 0x0138
WM_CTLCOLORBTN          equ 0x0135
CW_USEDEFAULT           equ 0x80000000
NULL_BRUSH              equ 5
CP_UTF8                 equ 65001
WCHAR_BUF_CCH           equ 1024
ICC_STANDARD_CLASSES    equ 0x00004000
CLR_BACKGROUND          equ 0x00F3F3F3
CLR_TEXT                equ 0x001A1A1A
FONT_HEIGHT             equ -13
FW_NORMAL               equ 400
DEFAULT_CHARSET         equ 1
OUT_DEFAULT_PRECIS      equ 0
CLIP_DEFAULT_PRECIS     equ 0
CLEARTYPE_QUALITY       equ 5
DEFAULT_PITCH           equ 0
FF_SWISS                equ 32
GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS  equ 0x00000004
DPI_AWARENESS_CTX_PER_MONITOR_V2       equ -4

; ── read-only data (UTF-16LE) ─────────────────────────────────────────────────
section .data
    class_name      dw 'W','i','n','G','U','I','_','C','l','a','s','s', 0
    window_name     dw 'W','i','n','d','o','w', 0
    btn_class       dw 'B','U','T','T','O','N', 0
    edit_class      dw 'E','D','I','T', 0
    static_class    dw 'S','T','A','T','I','C', 0
    font_face       dw 'S','e','g','o','e',' ','U','I', 0

    ; ASCII for dynamic DPI load
    user32_dll_name db 'user32.dll', 0
    dpi_func_name   db 'SetProcessDpiAwarenessContext', 0

; ── uninitialised data ────────────────────────────────────────────────────────
section .bss
    alignb 8
    hInstance           resq 1
    g_hwnd              resq 1
    msg_buf             resb 48
    callback_ptr        resq 1
    class_registered    resb 1
    alignb 8
    wndclass            resb 80
    g_hfont             resq 1
    g_hbr_bg            resq 1
    g_hbr_null          resq 1
    alignb 2
    wchar_buf           resw WCHAR_BUF_CCH
    wchar_buf2          resw WCHAR_BUF_CCH

section .text

global create_window
global show_window
global run_message_loop
global create_button
global create_label
global create_textbox
global set_window_title
global show_message_box
global close_window
global set_callback
global WindowProc

; ══════════════════════════════════════════════════════════════════════════════
; utf8_to_wchar  -  UTF-8 const char* -> wchar_buf
;   IN  rcx = UTF-8 source  OUT rax = wchar_buf or 0
;   RSP: 8 | rbp->0 | rbx->8(odd) | sub40->0
; ══════════════════════════════════════════════════════════════════════════════
utf8_to_wchar:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    mov     rbx, rcx
    mov     ecx,  CP_UTF8
    xor     edx,  edx
    mov     r8,   rbx
    mov     r9,   -1
    lea     rax,  [wchar_buf]
    mov     [rsp+32], rax
    mov     dword [rsp+40], WCHAR_BUF_CCH
    call    MultiByteToWideChar
    test    eax, eax
    jz      .fail
    lea     rax, [wchar_buf]
    jmp     .done
.fail:
    xor     eax, eax
.done:
    add     rsp, 40
    pop     rbx
    pop     rbp
    ret

; ══════════════════════════════════════════════════════════════════════════════
; utf8_to_wchar2  -  same but writes to wchar_buf2 (for show_message_box)
; ══════════════════════════════════════════════════════════════════════════════
utf8_to_wchar2:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    mov     rbx, rcx
    mov     ecx,  CP_UTF8
    xor     edx,  edx
    mov     r8,   rbx
    mov     r9,   -1
    lea     rax,  [wchar_buf2]
    mov     [rsp+32], rax
    mov     dword [rsp+40], WCHAR_BUF_CCH
    call    MultiByteToWideChar
    test    eax, eax
    jz      .fail
    lea     rax, [wchar_buf2]
    jmp     .done
.fail:
    xor     eax, eax
.done:
    add     rsp, 40
    pop     rbx
    pop     rbp
    ret

; ══════════════════════════════════════════════════════════════════════════════
; init_modern_ui  -  one-time setup called from create_window
;   RSP: 8 | rbp->0 | rbx,r12,r13,r14 (4 even) | sub32->0
; ══════════════════════════════════════════════════════════════════════════════
init_modern_ui:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    sub     rsp, 32

    ; 1. DPI awareness via GetProcAddress (no hard import = no load failure)
    lea     rcx, [user32_dll_name]
    call    LoadLibraryA
    test    rax, rax
    jz      .dpi_skip
    mov     rbx, rax
    mov     rcx, rbx
    lea     rdx, [dpi_func_name]
    call    GetProcAddress
    test    rax, rax
    jz      .dpi_skip
    mov     ecx, DPI_AWARENESS_CTX_PER_MONITOR_V2
    movsxd  rcx, ecx
    call    rax
.dpi_skip:

    ; 2. InitCommonControlsEx
    sub     rsp, 16
    mov     dword [rsp],   8
    mov     dword [rsp+4], ICC_STANDARD_CLASSES
    mov     rcx,  rsp
    call    InitCommonControlsEx
    add     rsp, 16

    ; 3. CreateFontW("Segoe UI", -13, ClearType)
    ;    14 params: 4 regs + 10 stack = shadow(32)+80 = 112 bytes, 112%16=0
    sub     rsp, 112
    mov     ecx,  FONT_HEIGHT
    xor     edx,  edx
    xor     r8d,  r8d
    xor     r9d,  r9d
    mov     dword [rsp+32],  FW_NORMAL
    mov     dword [rsp+40],  0
    mov     dword [rsp+48],  0
    mov     dword [rsp+56],  0
    mov     dword [rsp+64],  DEFAULT_CHARSET
    mov     dword [rsp+72],  OUT_DEFAULT_PRECIS
    mov     dword [rsp+80],  CLIP_DEFAULT_PRECIS
    mov     dword [rsp+88],  CLEARTYPE_QUALITY
    mov     dword [rsp+96],  (DEFAULT_PITCH | FF_SWISS)
    lea     rax,  [font_face]
    mov     [rsp+104], rax
    call    CreateFontW
    add     rsp, 112
    mov     [g_hfont], rax

    ; 4. Background brush
    mov     ecx, CLR_BACKGROUND
    call    CreateSolidBrush
    mov     [g_hbr_bg], rax

    ; 5. NULL_BRUSH stock object
    mov     ecx, NULL_BRUSH
    call    GetStockObject
    mov     [g_hbr_null], rax

    add     rsp, 32
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

; ══════════════════════════════════════════════════════════════════════════════
; HWND create_window(INT width[ecx], INT height[edx], const char* title[r8])
;   RSP: 8 | rbp->0 | rbx,r12,r13,r14 (4 even) | sub32->0
;        CreateWindowExW: sub64->0  [32=X 40=Y 48=nW 56=nH 64=hParent 72=hMenu 80=hInst 88=lp]
; ══════════════════════════════════════════════════════════════════════════════
create_window:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    sub     rsp, 32

    mov     ebx,  ecx
    mov     r12d, edx
    mov     r13,  r8

    ; Get OUR DLL's HMODULE via address of WindowProc
    cmp     qword [hInstance], 0
    jne     .have_hinstance
    mov     ecx,  GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS
    lea     rdx,  [WindowProc]
    lea     r8,   [hInstance]
    call    GetModuleHandleExW
    test    eax, eax
    jnz     .have_hinstance
    ; Fallback
    xor     ecx, ecx
    call    GetModuleHandleW
    test    rax, rax
    jz      .fail
    mov     [hInstance], rax
.have_hinstance:

    cmp     byte [class_registered], 1
    je      .class_ok

    call    init_modern_ui

    ; Zero WNDCLASSEXW
    lea     rdi, [wndclass]
    xor     eax, eax
    mov     ecx, 20
    rep     stosd

    lea     rdi, [wndclass]
    mov     dword [rdi],    80
    mov     dword [rdi+4],  (CS_HREDRAW | CS_VREDRAW)
    lea     rax,  [WindowProc]
    mov     [rdi+8],   rax
    mov     rax,  [hInstance]
    mov     [rdi+24],  rax
    mov     rax,  [g_hbr_bg]
    mov     [rdi+48],  rax
    lea     rax,  [class_name]
    mov     [rdi+64],  rax

    xor     ecx, ecx
    mov     edx, IDI_APPLICATION
    call    LoadIconW
    lea     rdi, [wndclass]
    mov     [rdi+32], rax
    mov     [rdi+72], rax

    xor     ecx, ecx
    mov     edx, IDC_ARROW
    call    LoadCursorW
    test    rax, rax
    jz      .fail
    lea     rdi, [wndclass]
    mov     [rdi+40], rax

    lea     rcx, [wndclass]
    call    RegisterClassExW
    test    eax, eax
    jz      .fail

    mov     byte [class_registered], 1

.class_ok:
    test    ebx,  ebx
    jnz     .w_ok
    mov     ebx,  800
.w_ok:
    test    r12d, r12d
    jnz     .h_ok
    mov     r12d, 600
.h_ok:

    test    r13, r13
    jz      .default_title
    mov     rcx, r13
    call    utf8_to_wchar
    test    rax, rax
    jz      .default_title
    mov     r14, rax
    jmp     .do_create
.default_title:
    lea     r14, [window_name]

.do_create:
    sub     rsp, 64
    mov     dword [rsp+32], CW_USEDEFAULT
    mov     dword [rsp+40], CW_USEDEFAULT
    mov     [rsp+48], ebx
    mov     [rsp+56], r12d
    mov     qword [rsp+64], 0
    mov     qword [rsp+72], 0
    mov     rax, [hInstance]
    mov     [rsp+80], rax
    mov     qword [rsp+88], 0
    xor     ecx,  ecx
    lea     rdx,  [class_name]
    mov     r8,   r14
    mov     r9d,  (WS_OVERLAPPEDWINDOW | WS_VISIBLE)
    call    CreateWindowExW
    add     rsp, 64

    test    rax, rax
    jz      .fail
    mov     [g_hwnd], rax

    mov     rcx, [g_hwnd]
    call    UpdateWindow

    mov     rax, [g_hwnd]
    jmp     .done
.fail:
    xor     eax, eax
.done:
    add     rsp, 32
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

; ══════════════════════════════════════════════════════════════════════════════
; void show_window(HWND[rcx])   0->g_hwnd
;   RSP: 8 | rbp->0 | rbx,rsi (2 even) | sub32->0
; ══════════════════════════════════════════════════════════════════════════════
show_window:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    test    rcx, rcx
    jnz     .have
    mov     rcx, [g_hwnd]
.have:
    mov     rbx, rcx
    mov     rcx, rbx
    mov     edx, SW_SHOWNORMAL
    call    ShowWindow
    mov     rcx, rbx
    call    UpdateWindow
    add     rsp, 32
    pop     rsi
    pop     rbx
    pop     rbp
    ret

; ══════════════════════════════════════════════════════════════════════════════
; void run_message_loop()
;   RSP: 8 | rbp->0 | rbx->8(odd) | sub40->0
; ══════════════════════════════════════════════════════════════════════════════
run_message_loop:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
.loop:
    lea     rcx, [msg_buf]
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    call    GetMessageW
    test    eax, eax
    jle     .done
    lea     rcx, [msg_buf]
    call    TranslateMessage
    lea     rcx, [msg_buf]
    call    DispatchMessageW
    jmp     .loop
.done:
    add     rsp, 40
    pop     rbx
    pop     rbp
    ret

; ══════════════════════════════════════════════════════════════════════════════
; send_font  -  sends WM_SETFONT(g_hfont, TRUE) to child HWND in rcx
;   RSP: 8 | rbp->0 | rbx->8(odd) | sub40->0
; ══════════════════════════════════════════════════════════════════════════════
send_font:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    mov     rbx, rcx
    mov     rcx, rbx
    mov     edx, WM_SETFONT
    mov     r8,  [g_hfont]
    mov     r9d, 1
    call    SendMessageW
    add     rsp, 40
    pop     rbx
    pop     rbp
    ret

; ══════════════════════════════════════════════════════════════════════════════
; Child control helpers
;
; CreateWindowExW: 12 params = 4 regs + 8 stack
; sub rsp, 96  (shadow32 + 8x8=64 = 96, 96%16=0)
;   [rsp+32] X   [rsp+40] Y   [rsp+48] nW   [rsp+56] nH
;   [rsp+64] hWndParent   [rsp+72] hMenu(id)
;   [rsp+80] hInstance=NULL   [rsp+88] lpParam=NULL
;
; Frame: 8 | rbp->0 | 7 pushes(odd)->8 | sub40->0 | sub96->0
; ══════════════════════════════════════════════════════════════════════════════

; create_button(HWND parent[rcx], int x[edx], int y[r8d], int w[r9d],
;               int h[rbp+48], char* text[rbp+56], HMENU id[rbp+64])
; Strategy: create control with NULL text, then set text via SetWindowTextW.
; This avoids calling utf8_to_wchar before CreateWindowExW, which was
; corrupting the frame and causing ERROR_INVALID_WINDOW_HANDLE (1400).
create_button:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    push    rsi
    push    rdi
    sub     rsp, 40
    mov     rbx,  rcx           ; parent HWND
    mov     r12d, edx           ; x
    mov     r13d, r8d           ; y
    mov     r14d, r9d           ; w
    mov     r15d, [rbp+48]      ; h
    mov     rsi,  [rbp+56]      ; UTF-8 text (save for later)
    mov     rdi,  [rbp+64]      ; control id

    ; Create with NULL text first
    sub     rsp, 96
    mov     [rsp+32],  r12d
    mov     [rsp+40],  r13d
    mov     [rsp+48],  r14d
    mov     [rsp+56],  r15d
    mov     [rsp+64],  rbx      ; hWndParent
    mov     [rsp+72],  rdi      ; hMenu = control id
    mov     qword [rsp+80], 0   ; hInstance = NULL
    mov     qword [rsp+88], 0   ; lpParam
    xor     ecx,  ecx           ; dwExStyle
    lea     rdx,  [btn_class]   ; "BUTTON"
    xor     r8d,  r8d           ; lpWindowName = NULL
    mov     r9d,  (WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON)
    call    CreateWindowExW
    add     rsp, 96

    test    rax, rax
    jz      .done
    mov     r14, rax            ; save child HWND

    ; Set font
    mov     rcx, r14
    call    send_font

    ; Set text via SetWindowTextW (UTF-8 -> WCHAR conversion safe here)
    test    rsi, rsi
    jz      .no_text
    mov     rcx, rsi
    call    utf8_to_wchar
    test    rax, rax
    jz      .no_text
    mov     rcx, r14            ; child HWND
    mov     rdx, rax            ; WCHAR* text
    call    SetWindowTextW
.no_text:
    mov     rax, r14            ; return child HWND
.done:
    add     rsp, 40
    pop     rdi
    pop     rsi
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

; create_label(HWND parent[rcx], int x[edx], int y[r8d], int w[r9d],
;              int h[rbp+48], char* text[rbp+56])
; Strategy: create with NULL text, then set via SetWindowTextW.
create_label:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    push    rsi
    push    rdi
    sub     rsp, 40
    mov     rbx,  rcx           ; parent HWND
    mov     r12d, edx           ; x
    mov     r13d, r8d           ; y
    mov     r14d, r9d           ; w
    mov     r15d, [rbp+48]      ; h
    mov     rsi,  [rbp+56]      ; UTF-8 text (save for after creation)

    ; Create STATIC with NULL text first
    sub     rsp, 96
    mov     [rsp+32],  r12d
    mov     [rsp+40],  r13d
    mov     [rsp+48],  r14d
    mov     [rsp+56],  r15d
    mov     [rsp+64],  rbx      ; hWndParent
    mov     qword [rsp+72], 0   ; hMenu = NULL
    mov     qword [rsp+80], 0   ; hInstance = NULL
    mov     qword [rsp+88], 0   ; lpParam = NULL
    xor     ecx,  ecx           ; dwExStyle
    lea     rdx,  [static_class]; "STATIC"
    xor     r8d,  r8d           ; lpWindowName = NULL
    mov     r9d,  (WS_CHILD | WS_VISIBLE)
    call    CreateWindowExW
    add     rsp, 96

    test    rax, rax
    jz      .done
    mov     r14, rax            ; save child HWND

    ; Set font
    mov     rcx, r14
    call    send_font

    ; Set text via SetWindowTextW
    test    rsi, rsi
    jz      .no_text
    mov     rcx, rsi
    call    utf8_to_wchar
    test    rax, rax
    jz      .no_text
    mov     rcx, r14            ; child HWND
    mov     rdx, rax            ; WCHAR* text
    call    SetWindowTextW
.no_text:
    mov     rax, r14
.done:
    add     rsp, 40
    pop     rdi
    pop     rsi
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

; create_textbox(HWND parent[rcx], int x[edx], int y[r8d], int w[r9d],
;                int h[rbp+48])
create_textbox:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    push    rsi
    push    rdi
    sub     rsp, 40
    mov     rbx,  rcx
    mov     r12d, edx
    mov     r13d, r8d
    mov     r14d, r9d
    mov     r15d, [rbp+48]
    sub     rsp, 96
    mov     [rsp+32],  r12d
    mov     [rsp+40],  r13d
    mov     [rsp+48],  r14d
    mov     [rsp+56],  r15d
    mov     [rsp+64],  rbx
    mov     qword [rsp+72], 0
    mov     qword [rsp+80], 0
    mov     qword [rsp+88], 0
    xor     ecx,  ecx
    lea     rdx,  [edit_class]
    xor     r8d,  r8d
    mov     r9d,  (WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL)
    call    CreateWindowExW
    add     rsp, 96
    test    rax, rax
    jz      .done
    mov     r12, rax
    mov     rcx, r12
    call    send_font
    mov     rax, r12
.done:
    add     rsp, 40
    pop     rdi
    pop     rsi
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

; ══════════════════════════════════════════════════════════════════════════════
; BOOL set_window_title(HWND hwnd[rcx], char* title[rdx])
;   RSP: 8 | rbp->0 | rbx,r12 (2 even) | sub32->0
; ══════════════════════════════════════════════════════════════════════════════
set_window_title:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    sub     rsp, 32
    mov     rbx, rcx
    mov     r12, rdx
    mov     rcx, r12
    call    utf8_to_wchar
    test    rax, rax
    jz      .fail
    mov     rcx, rbx
    mov     rdx, rax
    call    SetWindowTextW
    jmp     .done
.fail:
    xor     eax, eax
.done:
    add     rsp, 32
    pop     r12
    pop     rbx
    pop     rbp
    ret

; ══════════════════════════════════════════════════════════════════════════════
; INT show_message_box(char* text[rcx], char* caption[rdx])
;   RSP: 8 | rbp->0 | rbx,r12,r13,r14 (4 even) | sub32->0
; ══════════════════════════════════════════════════════════════════════════════
show_message_box:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    sub     rsp, 32
    mov     rbx, rcx
    mov     r12, rdx
    mov     rcx, rbx
    call    utf8_to_wchar
    test    rax, rax
    jz      .fail
    mov     r13, rax
    mov     rcx, r12
    call    utf8_to_wchar2
    test    rax, rax
    jz      .fail
    mov     r14, rax
    mov     rcx, [g_hwnd]
    mov     rdx, r13
    mov     r8,  r14
    xor     r9d, r9d
    call    MessageBoxW
    jmp     .done
.fail:
    xor     eax, eax
.done:
    add     rsp, 32
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rbp
    ret

; ══════════════════════════════════════════════════════════════════════════════
; void close_window(HWND[rcx])   0->g_hwnd
;   RSP: 8 | rbp->0 | rbx,rsi (2 even) | sub32->0
; ══════════════════════════════════════════════════════════════════════════════
close_window:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    test    rcx, rcx
    jnz     .ok
    mov     rcx, [g_hwnd]
.ok:
    call    DestroyWindow
    mov     rcx, [g_hfont]
    test    rcx, rcx
    jz      .no_font
    call    DeleteObject
    mov     qword [g_hfont], 0
.no_font:
    mov     rcx, [g_hbr_bg]
    test    rcx, rcx
    jz      .no_brush
    call    DeleteObject
    mov     qword [g_hbr_bg], 0
.no_brush:
    add     rsp, 32
    pop     rsi
    pop     rbx
    pop     rbp
    ret

; ══════════════════════════════════════════════════════════════════════════════
; void set_callback(void* fn[rcx])
; ══════════════════════════════════════════════════════════════════════════════
set_callback:
    mov     [callback_ptr], rcx
    ret

; ══════════════════════════════════════════════════════════════════════════════
; LRESULT CALLBACK WindowProc(HWND[rcx], UINT[edx], WPARAM[r8], LPARAM[r9])
;   RSP: 8 | rbp->0 | rbx->8(odd) | sub40->0
;   Spill: [rbp-8]=rbx [rbp-16]=hwnd [rbp-24]=msg [rbp-32]=wp [rbp-40]=lp
; ══════════════════════════════════════════════════════════════════════════════
WindowProc:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40

    mov     [rbp-16], rcx
    mov     [rbp-24], edx
    mov     [rbp-32], r8
    mov     [rbp-40], r9

    cmp     edx, WM_DESTROY
    je      .wm_destroy
    cmp     edx, WM_CLOSE
    je      .wm_close
    cmp     edx, WM_COMMAND
    je      .wm_command
    cmp     edx, WM_CTLCOLORSTATIC
    je      .wm_ctlcolorstatic
    cmp     edx, WM_CTLCOLORBTN
    je      .wm_ctlcolorbtn

.default:
    mov     rcx, [rbp-16]
    mov     edx, [rbp-24]
    mov     r8,  [rbp-32]
    mov     r9,  [rbp-40]
    call    DefWindowProcW
    jmp     .done

.wm_ctlcolorstatic:
    mov     rcx, [rbp-32]
    mov     edx, CLR_TEXT
    call    SetTextColor
    mov     rcx, [rbp-32]
    mov     edx, CLR_BACKGROUND
    call    SetBkColor
    mov     rax, [g_hbr_bg]
    jmp     .done

.wm_ctlcolorbtn:
    mov     rax, [g_hbr_null]
    jmp     .done

.wm_destroy:
    xor     ecx, ecx
    call    PostQuitMessage
    xor     eax, eax
    jmp     .done

.wm_close:
    mov     rcx, [rbp-16]
    call    DestroyWindow
    xor     eax, eax
    jmp     .done

.wm_command:
    mov     rax, [callback_ptr]
    test    rax, rax
    jz      .default
    mov     rbx, rax
    mov     rcx, [rbp-16]
    mov     rdx, [rbp-32]
    mov     r9,  [rbp-40]
    mov     r8,  rdx
    shr     r8,  16
    movzx   edx, dx
    call    rbx
    xor     eax, eax

.done:
    add     rsp, 40
    pop     rbx
    pop     rbp
    ret
