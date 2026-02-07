"""Tests for shadowed Ansible modules in FTL2.

Shadowed modules are Ansible modules that are transparently replaced
with native FTL2 implementations. Unlike excluded modules (which raise
errors), shadowed modules "just work" - they silently redirect to the
native implementation.
"""

import pytest

from ftl2 import automation
from ftl2.module_loading.shadowed import (
    SHADOWED_MODULES,
    get_native_method,
    is_shadowed,
)


class TestShadowedModulesRegistry:
    """Tests for the shadowed modules registry."""

    def test_wait_for_connection_is_shadowed(self):
        """Test that wait_for_connection is in the shadowed registry."""
        assert is_shadowed("wait_for_connection")
        assert is_shadowed("ansible.builtin.wait_for_connection")

    def test_ping_is_shadowed(self):
        """Test that ping is in the shadowed registry."""
        assert is_shadowed("ping")
        assert is_shadowed("ansible.builtin.ping")

    def test_non_shadowed_module_returns_false(self):
        """Test that non-shadowed modules return False."""
        assert not is_shadowed("file")
        assert not is_shadowed("debug")
        assert not is_shadowed("ansible.builtin.file")

    def test_get_native_method_wait_for_connection(self):
        """Test getting native method for wait_for_connection."""
        assert get_native_method("wait_for_connection") == "wait_for_ssh"
        assert get_native_method("ansible.builtin.wait_for_connection") == "wait_for_ssh"

    def test_get_native_method_ping(self):
        """Test getting native method for ping."""
        assert get_native_method("ping") == "ping"
        assert get_native_method("ansible.builtin.ping") == "ping"

    def test_get_native_method_non_shadowed_returns_none(self):
        """Test that non-shadowed modules return None."""
        assert get_native_method("file") is None
        assert get_native_method("debug") is None


class TestShadowedModuleIntegration:
    """Integration tests for shadowed module execution."""

    @pytest.mark.asyncio
    async def test_wait_for_connection_calls_wait_for_ssh(self):
        """Test that wait_for_connection transparently calls wait_for_ssh."""
        async with automation(print_summary=False, quiet=True) as ftl:
            # This should work (not raise ExcludedModuleError)
            # and return the same result as wait_for_ssh
            try:
                result = await ftl.local.wait_for_connection(timeout=5)
                assert "elapsed" in result
                assert result["changed"] is False
            except TimeoutError:
                pytest.skip("SSH not running on localhost")

    @pytest.mark.asyncio
    async def test_wait_for_connection_fqcn_works(self):
        """Test that FQCN version also works."""
        async with automation(print_summary=False, quiet=True) as ftl:
            try:
                result = await ftl.local.ansible.builtin.wait_for_connection(timeout=5)
                assert "elapsed" in result
                assert result["changed"] is False
            except TimeoutError:
                pytest.skip("SSH not running on localhost")

    @pytest.mark.asyncio
    async def test_ping_returns_pong(self):
        """Test that ping returns {"ping": "pong"}."""
        async with automation(print_summary=False, quiet=True) as ftl:
            result = await ftl.local.ping()
            assert result == {"ping": "pong"}

    @pytest.mark.asyncio
    async def test_ping_fqcn_works(self):
        """Test that FQCN version of ping also works."""
        async with automation(print_summary=False, quiet=True) as ftl:
            result = await ftl.local.ansible.builtin.ping()
            assert result == {"ping": "pong"}

    @pytest.mark.asyncio
    async def test_wait_for_connection_with_delay(self):
        """Test that delay parameter works."""
        import time

        async with automation(print_summary=False, quiet=True) as ftl:
            start = time.monotonic()
            try:
                # With 1 second delay
                result = await ftl.local.wait_for_connection(timeout=5, delay=1)
                elapsed = time.monotonic() - start
                # Should have waited at least 1 second for delay
                assert elapsed >= 1.0
            except TimeoutError:
                pytest.skip("SSH not running on localhost")


class TestWaitForSSHParameters:
    """Tests for wait_for_ssh parameter compatibility with Ansible."""

    @pytest.mark.asyncio
    async def test_timeout_parameter(self):
        """Test that timeout parameter works."""
        async with automation(
            inventory={"test": {"hosts": {"unreachable": {"ansible_host": "192.0.2.1"}}}},
            print_summary=False,
            quiet=True,
        ) as ftl:
            import time

            start = time.monotonic()
            with pytest.raises(TimeoutError):
                await ftl.unreachable.wait_for_ssh(timeout=2)
            elapsed = time.monotonic() - start
            # Should have timed out after ~2 seconds (with some tolerance for slow CI)
            assert elapsed >= 2.0
            assert elapsed < 10.0

    @pytest.mark.asyncio
    async def test_sleep_parameter(self):
        """Test that sleep parameter controls retry interval."""
        async with automation(
            inventory={"test": {"hosts": {"unreachable": {"ansible_host": "192.0.2.1"}}}},
            print_summary=False,
            quiet=True,
        ) as ftl:
            import time

            # With sleep=2, should only retry once in 3 seconds
            start = time.monotonic()
            with pytest.raises(TimeoutError):
                await ftl.unreachable.wait_for_ssh(timeout=3, sleep=2)
            elapsed = time.monotonic() - start
            assert elapsed >= 3.0

    @pytest.mark.asyncio
    async def test_delay_parameter(self):
        """Test that delay parameter waits before first check."""
        async with automation(
            inventory={"test": {"hosts": {"unreachable": {"ansible_host": "192.0.2.1"}}}},
            print_summary=False,
            quiet=True,
        ) as ftl:
            import time

            start = time.monotonic()
            with pytest.raises(TimeoutError):
                # 1 second delay + 2 second timeout
                await ftl.unreachable.wait_for_ssh(timeout=2, delay=1)
            elapsed = time.monotonic() - start
            # Should have waited at least delay + timeout
            assert elapsed >= 3.0

    @pytest.mark.asyncio
    async def test_returns_dict_with_elapsed(self):
        """Test that wait_for_ssh returns dict with elapsed time."""
        async with automation(print_summary=False, quiet=True) as ftl:
            try:
                result = await ftl.local.wait_for_ssh(timeout=5)
                assert isinstance(result, dict)
                assert "elapsed" in result
                assert isinstance(result["elapsed"], int)
                assert result["changed"] is False
            except TimeoutError:
                pytest.skip("SSH not running on localhost")


class TestPingImplementation:
    """Tests for the ping native method implementation."""

    @pytest.mark.asyncio
    async def test_ping_executes_command(self):
        """Test that ping actually executes a command to verify connectivity."""
        async with automation(print_summary=False, quiet=True) as ftl:
            # This should execute 'echo pong' and return the result
            result = await ftl.local.ping()
            assert result == {"ping": "pong"}

    @pytest.mark.asyncio
    async def test_ping_via_shadowed_module(self):
        """Test that ansible.builtin.ping transparently calls native ping."""
        async with automation(print_summary=False, quiet=True) as ftl:
            result = await ftl.local.ansible.builtin.ping()
            assert result == {"ping": "pong"}

    @pytest.mark.asyncio
    async def test_ping_fails_on_unreachable_host(self):
        """Test that ping raises ConnectionError on unreachable host."""
        from ftl2.exceptions import ConnectionError as FTL2ConnectionError

        async with automation(
            inventory={"test": {"hosts": {"unreachable": {"ansible_host": "192.0.2.1"}}}},
            print_summary=False,
            quiet=True,
        ) as ftl:
            # Ping should fail on unreachable host
            with pytest.raises((FTL2ConnectionError, TimeoutError, Exception)):
                await ftl.unreachable.ping()
