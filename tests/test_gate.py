"""Tests for gate building system."""

import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

from ftl2.exceptions import GateError, ModuleNotFound
from ftl2.gate import GateBuildConfig, GateBuilder


class TestGateBuildConfig:
    """Tests for GateBuildConfig dataclass."""

    def test_minimal_config(self):
        """Test creating config with minimal parameters."""
        config = GateBuildConfig()

        assert config.modules == []
        assert config.module_dirs == []
        assert config.dependencies == []
        assert config.interpreter == sys.executable
        assert config.local_interpreter == sys.executable

    def test_config_with_modules(self):
        """Test creating config with modules."""
        config = GateBuildConfig(modules=["ping", "setup"], module_dirs=[Path("/opt/modules")])

        assert config.modules == ["ping", "setup"]
        assert config.module_dirs == [Path("/opt/modules")]

    def test_config_with_dependencies(self):
        """Test creating config with dependencies."""
        config = GateBuildConfig(dependencies=["requests>=2.0", "pyyaml"])

        assert config.dependencies == ["requests>=2.0", "pyyaml"]

    def test_config_path_conversion(self):
        """Test that string paths are converted to Path objects."""
        config = GateBuildConfig(module_dirs=["/opt/modules", "/tmp/modules"])

        assert all(isinstance(d, Path) for d in config.module_dirs)
        assert config.module_dirs == [Path("/opt/modules"), Path("/tmp/modules")]

    def test_compute_hash_empty_config(self):
        """Test hash computation for empty configuration."""
        config = GateBuildConfig()
        hash1 = config.compute_hash()

        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256 hex digest length

    def test_compute_hash_deterministic(self):
        """Test that hash computation is deterministic."""
        config1 = GateBuildConfig(modules=["ping"], dependencies=["requests"])
        config2 = GateBuildConfig(modules=["ping"], dependencies=["requests"])

        assert config1.compute_hash() == config2.compute_hash()

    def test_compute_hash_different_configs(self):
        """Test that different configs produce different hashes."""
        config1 = GateBuildConfig(modules=["ping"])
        config2 = GateBuildConfig(modules=["setup"])

        assert config1.compute_hash() != config2.compute_hash()

    def test_compute_hash_includes_all_fields(self):
        """Test that hash includes all configuration fields."""
        base_config = GateBuildConfig()
        base_hash = base_config.compute_hash()

        # Changing any field should change hash
        config_with_module = GateBuildConfig(modules=["ping"])
        assert config_with_module.compute_hash() != base_hash

        config_with_dir = GateBuildConfig(module_dirs=[Path("/opt")])
        assert config_with_dir.compute_hash() != base_hash

        config_with_dep = GateBuildConfig(dependencies=["requests"])
        assert config_with_dep.compute_hash() != base_hash

        config_with_interp = GateBuildConfig(interpreter="/usr/bin/python3")
        assert config_with_interp.compute_hash() != base_hash


class TestGateBuilder:
    """Tests for GateBuilder class."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_module_dir(self):
        """Create temporary module directory with test module."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_dir = Path(tmpdir)

            # Create a simple test module
            test_module = module_dir / "test_module.py"
            test_module.write_text('#!/usr/bin/env python3\nprint("test module")\n')

            yield module_dir

    def test_create_builder(self, temp_cache_dir):
        """Test creating a gate builder."""
        builder = GateBuilder(cache_dir=temp_cache_dir)

        # Use resolve() to handle symlinks (e.g., /var vs /private/var on macOS)
        assert builder.cache_dir.resolve() == temp_cache_dir.resolve()
        assert builder.cache_dir.exists()

    def test_build_minimal_gate(self, temp_cache_dir):
        """Test building a gate with no modules or dependencies."""
        builder = GateBuilder(cache_dir=temp_cache_dir)
        config = GateBuildConfig()

        gate_path, gate_hash = builder.build(config)

        assert Path(gate_path).exists()
        assert gate_path.endswith(".pyz")
        assert len(gate_hash) == 64

    def test_build_gate_caching(self, temp_cache_dir):
        """Test that identical configs reuse cached gates."""
        builder = GateBuilder(cache_dir=temp_cache_dir)
        config = GateBuildConfig()

        # Build first time
        gate_path1, gate_hash1 = builder.build(config)

        # Build again with same config
        gate_path2, gate_hash2 = builder.build(config)

        assert gate_path1 == gate_path2
        assert gate_hash1 == gate_hash2

    def test_build_gate_with_module(self, temp_cache_dir, temp_module_dir):
        """Test building a gate with a module."""
        builder = GateBuilder(cache_dir=temp_cache_dir)
        config = GateBuildConfig(modules=["test_module"], module_dirs=[temp_module_dir])

        gate_path, gate_hash = builder.build(config)

        assert Path(gate_path).exists()

        # Verify gate is a valid zip file
        with zipfile.ZipFile(gate_path, "r") as zf:
            namelist = zf.namelist()
            # Should contain __main__.py and the module
            assert "__main__.py" in namelist
            assert any("test_module.py" in name for name in namelist)

    def test_build_gate_module_not_found(self, temp_cache_dir):
        """Test error when module cannot be found."""
        builder = GateBuilder(cache_dir=temp_cache_dir)
        config = GateBuildConfig(modules=["nonexistent"], module_dirs=[Path("/tmp/nonexistent")])

        with pytest.raises((ModuleNotFound, GateError)):
            builder.build(config)

    def test_build_gate_different_interpreters(self, temp_cache_dir):
        """Test that different interpreters produce different gates."""
        builder = GateBuilder(cache_dir=temp_cache_dir)

        config1 = GateBuildConfig(interpreter="/usr/bin/python3")
        config2 = GateBuildConfig(interpreter="/opt/python3/bin/python3")

        gate_path1, gate_hash1 = builder.build(config1)
        gate_path2, gate_hash2 = builder.build(config2)

        assert gate_hash1 != gate_hash2
        assert gate_path1 != gate_path2

    def test_gate_structure(self, temp_cache_dir, temp_module_dir):
        """Test that built gate has correct internal structure."""
        builder = GateBuilder(cache_dir=temp_cache_dir)
        config = GateBuildConfig(modules=["test_module"], module_dirs=[temp_module_dir])

        gate_path, _ = builder.build(config)

        # Verify gate structure
        with zipfile.ZipFile(gate_path, "r") as zf:
            namelist = zf.namelist()

            # Must have __main__.py entry point
            assert "__main__.py" in namelist

            # Must have ftl_gate package
            assert "ftl_gate/__init__.py" in namelist

            # Must have the test module
            assert any("test_module.py" in name for name in namelist)

    def test_gate_hash_consistency(self, temp_cache_dir, temp_module_dir):
        """Test that gate hash matches config hash."""
        builder = GateBuilder(cache_dir=temp_cache_dir)
        config = GateBuildConfig(modules=["test_module"], module_dirs=[temp_module_dir])

        gate_path, gate_hash = builder.build(config)

        # Hash from builder should match hash from config
        assert gate_hash == config.compute_hash()

        # Gate filename should contain the hash
        assert gate_hash in gate_path

    def test_multiple_modules(self, temp_cache_dir, temp_module_dir):
        """Test building a gate with multiple modules."""
        # Create additional module
        module2 = temp_module_dir / "module2.py"
        module2.write_text('print("module 2")\n')

        builder = GateBuilder(cache_dir=temp_cache_dir)
        config = GateBuildConfig(modules=["test_module", "module2"], module_dirs=[temp_module_dir])

        gate_path, _ = builder.build(config)

        # Verify both modules are in gate
        with zipfile.ZipFile(gate_path, "r") as zf:
            namelist = zf.namelist()
            assert any("test_module.py" in name for name in namelist)
            assert any("module2.py" in name for name in namelist)
