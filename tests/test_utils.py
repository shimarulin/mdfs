"""Tests for MDFS utility functions."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

from mdfs.utils import (
    timestamp,
    sanitize_label,
    make_filename,
    get_clipboard,
    find_mdfs_root,
    mdfs_dir,
    rules_dir,
    contexts_dir,
    responses_dir,
    print_actions,
)


class TestTimestamp(unittest.TestCase):
    """Tests for timestamp generation."""

    def test_format(self):
        """Test timestamp has correct format YYYY-MM-DD_HHMMSS."""
        ts = timestamp()
        self.assertRegex(ts, r"\d{4}-\d{2}-\d{2}_\d{6}")

    def test_returns_string(self):
        """Test timestamp returns string."""
        ts = timestamp()
        self.assertIsInstance(ts, str)


class TestGetClipboard(unittest.TestCase):
    """Tests for clipboard reading across different platforms."""

    @patch("mdfs.utils.platform.system")
    @patch("mdfs.utils.shutil.which")
    @patch("mdfs.utils.subprocess.run")
    def test_macos_success(self, mock_run, mock_which, mock_system):
        """Test successful clipboard read on macOS."""
        mock_system.return_value = "Darwin"
        mock_which.return_value = "/usr/bin/pbpaste"
        mock_run.return_value = MagicMock(stdout="clipboard content\n")

        result = get_clipboard()
        self.assertEqual(result, "clipboard content\n")
        mock_run.assert_called_once()

    @patch("mdfs.utils.platform.system")
    @patch("mdfs.utils.shutil.which")
    def test_macos_pbpaste_not_found(self, mock_which, mock_system):
        """Test error when pbpaste not found on macOS."""
        mock_system.return_value = "Darwin"
        mock_which.return_value = None

        with self.assertRaises(SystemExit):
            get_clipboard()

    @patch("mdfs.utils.platform.system")
    @patch("mdfs.utils.shutil.which")
    @patch("mdfs.utils.subprocess.run")
    def test_linux_wl_paste_success(self, mock_run, mock_which, mock_system):
        """Test successful clipboard read with wl-paste on Linux."""
        mock_system.return_value = "Linux"
        mock_which.side_effect = lambda cmd: cmd if cmd == "wl-paste" else None
        mock_run.return_value = MagicMock(returncode=0, stdout="wayland content")

        result = get_clipboard()
        self.assertEqual(result, "wayland content")

    @patch("mdfs.utils.platform.system")
    @patch("mdfs.utils.shutil.which")
    @patch("mdfs.utils.subprocess.run")
    def test_linux_xclip_fallback(self, mock_run, mock_which, mock_system):
        """Test fallback to xclip when wl-paste not available."""
        mock_system.return_value = "Linux"
        
        def which_side_effect(cmd):
            return cmd if cmd == "xclip" else None
        
        mock_which.side_effect = which_side_effect
        mock_run.return_value = MagicMock(returncode=0, stdout="xclip content")

        result = get_clipboard()
        self.assertEqual(result, "xclip content")

    @patch("mdfs.utils.platform.system")
    @patch("mdfs.utils.shutil.which")
    @patch("mdfs.utils.subprocess.run")
    def test_linux_xsel_fallback(self, mock_run, mock_which, mock_system):
        """Test fallback to xsel when wl-paste and xclip not available."""
        mock_system.return_value = "Linux"
        
        def which_side_effect(cmd):
            return cmd if cmd == "xsel" else None
        
        mock_which.side_effect = which_side_effect
        mock_run.return_value = MagicMock(returncode=0, stdout="xsel content")

        result = get_clipboard()
        self.assertEqual(result, "xsel content")

    @patch("mdfs.utils.platform.system")
    @patch("mdfs.utils.shutil.which")
    def test_linux_no_clipboard_tools(self, mock_which, mock_system):
        """Test error when no clipboard tools available on Linux."""
        mock_system.return_value = "Linux"
        mock_which.return_value = None

        with self.assertRaises(SystemExit):
            get_clipboard()

    @patch("mdfs.utils.platform.system")
    def test_unsupported_os(self, mock_system):
        """Test error on unsupported OS."""
        mock_system.return_value = "Windows"

        with self.assertRaises(SystemExit):
            get_clipboard()

    @patch("mdfs.utils.platform.system")
    @patch("mdfs.utils.shutil.which")
    @patch("mdfs.utils.subprocess.run")
    def test_empty_clipboard(self, mock_run, mock_which, mock_system):
        """Test handling of empty clipboard."""
        mock_system.return_value = "Darwin"
        mock_which.return_value = "/usr/bin/pbpaste"
        mock_run.return_value = MagicMock(stdout="")

        result = get_clipboard()
        self.assertEqual(result, "")

    @patch("mdfs.utils.platform.system")
    @patch("mdfs.utils.shutil.which")
    @patch("mdfs.utils.subprocess.run")
    def test_subprocess_timeout_fallback(self, mock_run, mock_which, mock_system):
        """Test timeout on clipboard tool falls back to next."""
        mock_system.return_value = "Linux"
        
        def which_side_effect(cmd):
            return "/usr/bin/" + cmd if cmd in ("wl-paste", "xclip") else None
        
        mock_which.side_effect = which_side_effect
        
        # First call (wl-paste) times out, second (xclip) succeeds
        from subprocess import TimeoutExpired
        mock_run.side_effect = [
            TimeoutExpired("wl-paste", 5),
            MagicMock(returncode=0, stdout="xclip content")
        ]

        result = get_clipboard()
        self.assertEqual(result, "xclip content")


class TestFindMdfsRoot(unittest.TestCase):
    """Tests for finding .mdfs root directory."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_finds_mdfs_in_current_dir(self):
        """Test finding .mdfs in current directory."""
        mdfs = Path(self.tmpdir) / ".mdfs"
        mdfs.mkdir()

        result = find_mdfs_root(self.tmpdir)
        self.assertEqual(result, Path(self.tmpdir).resolve())

    def test_finds_mdfs_in_parent_dir(self):
        """Test finding .mdfs in parent directory."""
        mdfs = Path(self.tmpdir) / ".mdfs"
        mdfs.mkdir()
        
        subdir = Path(self.tmpdir) / "sub"
        subdir.mkdir()

        result = find_mdfs_root(subdir)
        self.assertEqual(result, Path(self.tmpdir).resolve())

    def test_finds_mdfs_multiple_levels_up(self):
        """Test finding .mdfs multiple levels up."""
        mdfs = Path(self.tmpdir) / ".mdfs"
        mdfs.mkdir()
        
        deep_dir = Path(self.tmpdir) / "a" / "b" / "c"
        deep_dir.mkdir(parents=True)

        result = find_mdfs_root(deep_dir)
        self.assertEqual(result, Path(self.tmpdir).resolve())

    def test_not_found_raises_system_exit(self):
        """Test SystemExit when .mdfs not found."""
        subdir = Path(self.tmpdir) / "sub"
        subdir.mkdir()

        with self.assertRaises(SystemExit):
            find_mdfs_root(subdir)

    def test_uses_current_dir_when_none(self):
        """Test uses current working directory when start is None."""
        mdfs = Path(self.tmpdir) / ".mdfs"
        mdfs.mkdir()
        
        # Change to tmpdir for this test
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(self.tmpdir)
            result = find_mdfs_root(None)
            self.assertEqual(result, Path(self.tmpdir).resolve())
        finally:
            os.chdir(old_cwd)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestPathHelpers(unittest.TestCase):
    """Tests for path helper functions."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def test_mdfs_dir(self):
        """Test mdfs_dir returns correct path."""
        result = mdfs_dir(self.tmpdir)
        self.assertEqual(result, self.tmpdir / ".mdfs")

    def test_rules_dir(self):
        """Test rules_dir returns correct path."""
        result = rules_dir(self.tmpdir)
        self.assertEqual(result, self.tmpdir / ".mdfs" / "rules")

    def test_contexts_dir(self):
        """Test contexts_dir returns correct path."""
        result = contexts_dir(self.tmpdir)
        self.assertEqual(result, self.tmpdir / ".mdfs" / "contexts")

    def test_responses_dir(self):
        """Test responses_dir returns correct path."""
        result = responses_dir(self.tmpdir)
        self.assertEqual(result, self.tmpdir / ".mdfs" / "responses")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestPrintActions(unittest.TestCase):
    """Tests for action printing."""

    def test_print_write_action(self):
        """Test printing write action."""
        from mdfs.core.extractor import Action
        
        actions = [Action("write", "src/main.py")]
        
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            print_actions(actions)
            output = mock_stdout.getvalue()
            self.assertIn("📄", output)
            self.assertIn("write", output)
            self.assertIn("src/main.py", output)

    def test_print_patch_action(self):
        """Test printing patch action."""
        from mdfs.core.extractor import Action
        
        actions = [Action("patch", "src/utils.py")]
        
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            print_actions(actions)
            output = mock_stdout.getvalue()
            self.assertIn("🩹", output)
            self.assertIn("patch", output)
            self.assertIn("src/utils.py", output)

    def test_print_error_action(self):
        """Test printing error action."""
        from mdfs.core.extractor import Action
        
        actions = [Action("error", "src/bad.py", "file not found")]
        
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            print_actions(actions)
            output = mock_stdout.getvalue()
            self.assertIn("❌", output)
            self.assertIn("error", output)
            self.assertIn("src/bad.py", output)
            self.assertIn("file not found", output)

    def test_print_multiple_actions(self):
        """Test printing multiple actions."""
        from mdfs.core.extractor import Action
        
        actions = [
            Action("write", "a.py"),
            Action("patch", "b.py"),
            Action("error", "c.py", "error details"),
        ]
        
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            print_actions(actions)
            output = mock_stdout.getvalue()
            self.assertIn("a.py", output)
            self.assertIn("b.py", output)
            self.assertIn("c.py", output)

    def test_print_action_without_detail(self):
        """Test printing action without detail string."""
        from mdfs.core.extractor import Action
        
        actions = [Action("write", "src/main.py", "")]
        
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            print_actions(actions)
            output = mock_stdout.getvalue()
            # Should not have " — " when detail is empty
            self.assertNotIn(" — ", output)


if __name__ == "__main__":
    unittest.main()
