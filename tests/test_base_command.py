"""Tests for BaseCommand abstract base class."""

import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch, MagicMock

from mdfs.commands.base import BaseCommand


class ConcreteCommand(BaseCommand):
    """Concrete implementation of BaseCommand for testing."""
    
    def execute(self) -> int:
        return 0


class TestBaseCommandInitialization(unittest.TestCase):
    """Tests for BaseCommand initialization."""
    
    def test_init_with_valid_mdfs_directory(self):
        """BaseCommand initializes with valid .mdfs directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mdfs_dir = Path(tmpdir) / ".mdfs"
            mdfs_dir.mkdir()
            
            args = Namespace(dir=tmpdir)
            cmd = ConcreteCommand(args)
            
            assert cmd.root == Path(tmpdir).resolve()
            assert cmd.args == args
    
    def test_init_without_dir_argument(self):
        """BaseCommand initializes when dir argument is not provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mdfs_dir = Path(tmpdir) / ".mdfs"
            mdfs_dir.mkdir()
            
            with patch("mdfs.commands.base.find_mdfs_root") as mock_find:
                mock_find.return_value = Path(tmpdir).resolve()
                
                args = Namespace()
                cmd = ConcreteCommand(args)
                
                # Should call find_mdfs_root with None
                mock_find.assert_called_once_with(None)
                assert cmd.root == Path(tmpdir).resolve()
    
    def test_init_finds_mdfs_root(self):
        """BaseCommand correctly finds .mdfs root directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mdfs_dir = Path(tmpdir) / ".mdfs"
            mdfs_dir.mkdir()
            
            # Create nested directory
            nested = Path(tmpdir) / "src" / "nested"
            nested.mkdir(parents=True)
            
            args = Namespace(dir=str(nested))
            cmd = ConcreteCommand(args)
            
            # Should find the root .mdfs directory
            assert cmd.root == Path(tmpdir).resolve()


class TestBaseCommandError(unittest.TestCase):
    """Tests for BaseCommand.error() method."""
    
    def test_error_prints_message_and_exits(self):
        """BaseCommand.error() prints message and exits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mdfs_dir = Path(tmpdir) / ".mdfs"
            mdfs_dir.mkdir()
            
            args = Namespace(dir=tmpdir)
            cmd = ConcreteCommand(args)
            
            with patch("sys.exit") as mock_exit:
                with patch("builtins.print") as mock_print:
                    cmd.error("test error")
                    
                    # Should print error message to stderr
                    mock_print.assert_called_once()
                    call_args = mock_print.call_args
                    assert "test error" in call_args[0][0]
                    assert call_args[1]["file"] == sys.stderr
                    
                    # Should exit with code 1
                    mock_exit.assert_called_once_with(1)
    
    def test_error_with_custom_exit_code(self):
        """BaseCommand.error() respects custom exit code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mdfs_dir = Path(tmpdir) / ".mdfs"
            mdfs_dir.mkdir()
            
            args = Namespace(dir=tmpdir)
            cmd = ConcreteCommand(args)
            
            with patch("sys.exit") as mock_exit:
                with patch("builtins.print"):
                    cmd.error("test error", exit_code=42)
                    
                    # Should exit with custom code
                    mock_exit.assert_called_once_with(42)
    
    def test_error_message_format(self):
        """BaseCommand.error() formats message correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mdfs_dir = Path(tmpdir) / ".mdfs"
            mdfs_dir.mkdir()
            
            args = Namespace(dir=tmpdir)
            cmd = ConcreteCommand(args)
            
            with patch("sys.exit"):
                with patch("builtins.print") as mock_print:
                    cmd.error("critical issue")
                    
                    call_args = mock_print.call_args[0][0]
                    assert "Error:" in call_args
                    assert "critical issue" in call_args


class TestBaseCommandAbstract(unittest.TestCase):
    """Tests for BaseCommand abstract nature."""
    
    def test_cannot_instantiate_base_command(self):
        """Cannot instantiate BaseCommand directly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mdfs_dir = Path(tmpdir) / ".mdfs"
            mdfs_dir.mkdir()
            
            args = Namespace(dir=tmpdir)
            
            with self.assertRaises(TypeError):
                BaseCommand(args)


if __name__ == "__main__":
    unittest.main()
