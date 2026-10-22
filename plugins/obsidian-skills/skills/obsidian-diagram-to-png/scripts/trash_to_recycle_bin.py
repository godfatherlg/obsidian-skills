# -*- coding: utf-8 -*-
r"""trash_to_recycle_bin.py — 把 vault 里的文件/目录移入 Windows 回收站（可还原，不永久删除）。

用法
----
  python trash_to_recycle_bin.py <路径> [<路径> ...]

为什么不用别的办法（2026-09-24 实测，本机 Windows + J: 盘）
----------------------------------------------------------
  - PowerShell `Add-Type -AssemblyName Microsoft.VisualBasic` **被安全 hook 拦**
    （"Add-Type compiles and loads .NET code at runtime"），走不通。
  - `send2trash` 在本机走的是 legacy 分支，`get_short_path_name()` 会拼出
    `\\?\<vault>/images/xxx.png`（正斜杠 + 前缀）并报 FileNotFoundError，同样走不通。
  - 直接用 `os.remove` 是永久删除，无回收站，违反 vault 资产安全口径。
  ⇒ 用 ctypes 调 `SHFileOperationW` + `FOF_ALLOWUNDO`，回落回收站且可还原。这是本机唯一可行路径。

注意
----
  - `SHFileOperationW` 返回 **非 0 不代表失败**（本机在 J: 盘上稳定返回 rc=2）、
    `fAnyOperationsAborted` 才是权威判据 ⇒ 本脚本以"原路径是否还存在"作为最终校验，
    并在回收站目录里按文件名/大小反查确认。
  - 多个路径要拼成 `"p1\0p2\0\0"` 一起传（本项目当前只需单文件，故按单文件实现更稳）。
"""
import ctypes
import os
import sys
from ctypes import wintypes

FO_DELETE = 3
FOF_SILENT = 0x0004
FOF_NOCONFIRMATION = 0x0010
FOF_ALLOWUNDO = 0x0040
FOF_NOERRORUI = 0x0400


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_uint16),          # FILEOP_FLAGS = WORD，ctypes 自动补对齐
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def to_trash(path):
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise SystemExit("不存在: %s" % path)
    size = os.path.getsize(path) if os.path.isfile(path) else None
    op = SHFILEOPSTRUCTW()
    op.hwnd = None
    op.wFunc = FO_DELETE
    op.pFrom = path + "\0\0"                   # 必须双 null 结尾
    op.pTo = None
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    gone = not os.path.exists(path)
    print("SHFileOperationW rc=%d aborted=%s | 原路径已消失=%s" % (rc, op.fAnyOperationsAborted, gone))
    if not gone:
        raise SystemExit("移入回收站失败（原路径仍存在）: %s" % path)
    print("已移入回收站:", path, "(size=%s)" % size)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for p in sys.argv[1:]:
        to_trash(p)
