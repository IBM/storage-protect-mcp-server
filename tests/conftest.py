"""
Pytest configuration and global hooks for the test suite.
"""

import sys

# Windows sandbox shim:
# On Windows, Python's asyncio ProactorEventLoop uses a loopback socket pair for its self-pipe.
# In sandboxed / restricted test environments without loopback network permissions,
# socket._fallback_socketpair hangs indefinitely on accept().
# We patch BaseProactorEventLoop with an in-memory dummy pipe and clamp IocpProactor.select
# timeout so that asyncio.run() and asyncio.to_thread() execute cleanly and quickly in
# sandboxed test runs without hanging.
if sys.platform == "win32":
    try:
        import signal
        from asyncio.proactor_events import BaseProactorEventLoop
        from asyncio.windows_events import IocpProactor

        class _DummySock:
            def fileno(self):
                return -1

            def setblocking(self, b):
                pass

            def close(self):
                pass

        def _fake_make_self_pipe(self):
            self._ssock = _DummySock()
            self._csock = _DummySock()
            self._internal_fds += 1

        orig_select = IocpProactor.select

        def _clamped_select(self, timeout=None):
            if timeout is None or timeout > 0.05:
                timeout = 0.05
            return orig_select(self, timeout)

        orig_set_wakeup = signal.set_wakeup_fd
        signal.set_wakeup_fd = lambda fd: -1 if fd == -1 else orig_set_wakeup(fd)

        BaseProactorEventLoop._make_self_pipe = _fake_make_self_pipe
        BaseProactorEventLoop._loop_self_reading = lambda self, f=None: None
        BaseProactorEventLoop._write_to_self = lambda self: None
        IocpProactor.select = _clamped_select
    except Exception:
        pass
