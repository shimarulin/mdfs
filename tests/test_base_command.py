"""Tests for BaseCommand abstract base class."""

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

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
