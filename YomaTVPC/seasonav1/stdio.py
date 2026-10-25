"""Canales de yt-dlp por tubería sin crear una consola de Windows."""
import os
import sys


def prepare():
    for name, code, mode in (("stdin", -10, "r"), ("stdout", -11, "w"), ("stderr", -12, "w")):
        stream = getattr(sys, name)
        if stream is None:
            if os.name == "nt":
                import ctypes
                import msvcrt
                from ctypes import wintypes
                kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel.GetStdHandle.argtypes = [wintypes.DWORD]
                kernel.GetStdHandle.restype = wintypes.HANDLE
                kernel.GetFileType.argtypes = [wintypes.HANDLE]
                kernel.GetFileType.restype = wintypes.DWORD
                kernel.GetCurrentProcess.restype = wintypes.HANDLE
                kernel.DuplicateHandle.argtypes = [wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE,
                                                  ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
                kernel.DuplicateHandle.restype = wintypes.BOOL
                handle = kernel.GetStdHandle(code & 0xffffffff)
                if handle and kernel.GetFileType(handle):
                    duplicate = wintypes.HANDLE()
                    process = kernel.GetCurrentProcess()
                    if kernel.DuplicateHandle(process, handle, process, ctypes.byref(duplicate), 0, False, 2):
                        descriptor = msvcrt.open_osfhandle(duplicate.value, os.O_RDONLY if mode == "r" else os.O_WRONLY)
                        stream = os.fdopen(descriptor, mode, encoding="utf-8", errors="replace", buffering=1)
            if stream is None:
                stream = open(os.devnull, mode, encoding="utf-8")
            setattr(sys, name, stream)
            setattr(sys, "__" + name + "__", stream)
        if name != "stdin" and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
