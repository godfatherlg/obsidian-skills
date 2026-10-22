"""发 obsidian:// 跳行 URI 并主动激活 Obsidian 主窗口。

用法: python jump_activate.py "<vault相对路径>" <行号>

要点:
  1. 直调 Obsidian.exe 传 URI（本机唯一有 Processed URI 收据的通路）
  2. sleep 后再置前主窗口，缓解"要用户再点一下 ob 才跳"
  3. 按窗口标题（含 ' - OB - Obsidian' 且可见）定位主窗口 hwnd
  4. 置前时保持窗口原状态：只在最小化时 SW_RESTORE，最大化时不动
     （2026-09-10 广哥反馈"ob 总是变成窗口化"根因即无条件 ShowWindow(hwnd, 9)）
"""
import subprocess
import sys
import time
import urllib.parse
import ctypes

EXE = r'<ObsidianInstallDir>\Obsidian.exe'
VAULT_ID = '<vault-id>'

user32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32


def build_uri(rel, line):
    return ('obsidian://adv-uri?vault=' + VAULT_ID
            + '&filepath=' + urllib.parse.quote(rel, safe='')
            + '&line=%d&column=1&openmode=true&view-mode=source' % line)


def find_main_hwnd():
    """找可见、标题含 ' - OB - Obsidian' 的主窗口句柄（标题带版本号，不用 endswith）"""
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n <= 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        t = buf.value
        if ' - OB - Obsidian' in t:
            found.append((hwnd, t))
        return True

    user32.EnumWindows(cb, None)
    return found[0] if found else (None, None)


def activate(hwnd):
    """绕过前台锁定的窗口置前（保持原窗口的最大化/还原状态）"""
    if not hwnd:
        return False
    # 仅在最小化时才 ShowWindow(SW_RESTORE)：
    # 对已最大化的窗口调 SW_RESTORE 会取消最大化 → Obsidian 变成"窗口化"
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    fg = user32.GetForegroundWindow()
    tf = user32.GetWindowThreadProcessId(fg, None)
    tm = k32.GetCurrentThreadId()
    attached = False
    if tf and tf != tm:
        attached = bool(user32.AttachThreadInput(tm, tf, True))
    ok = bool(user32.SetForegroundWindow(hwnd))
    if attached:
        user32.AttachThreadInput(tm, tf, False)
    return ok


def main():
    if len(sys.argv) < 3:
        print('usage: jump_activate.py <rel_path> <line>')
        return 1
    rel, line = sys.argv[1], int(sys.argv[2])
    uri = build_uri(rel, line)

    r = subprocess.run([EXE, uri], capture_output=True, timeout=20)
    ok = 'Processed' in r.stdout.decode('utf-8', 'replace')
    print('send ret=%s processed=%s' % (r.returncode, ok))

    time.sleep(2.5)
    hwnd, title = find_main_hwnd()
    print('hwnd=%s title=%s' % (hwnd, title))
    print('activate=%s' % activate(hwnd))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
