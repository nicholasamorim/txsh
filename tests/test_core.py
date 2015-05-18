from mock import MagicMock
from twisted.trial import unittest
from twisted.internet import defer

from txsh.core import Command


class TestCommand(unittest.TestCase):
    def test_bake(self):
        mock_spawn = MagicMock()
        Command._spawn = mock_spawn
        cmd = Command('ls').bake('-l')
        cmd()
        called_args = mock_spawn.call_args[0]
        self.assertEqual(called_args[1], ["ls", "-l"])

        cmd = Command('ls').bake('-l', '-h')
        cmd()
        called_args = mock_spawn.call_args[0]
        self.assertEqual(called_args[1], ["ls", "-l", "-h"])

        cmd = Command('ls').bake('-l', '-h', '--help')
        cmd()
        called_args = mock_spawn.call_args[0]
        self.assertEqual(called_args[1], ["ls", "-l", "-h", "--help"])

    def test_build_arguments(self):
        cmd = Command('ls')
        args = ['-l', '-h']
        kwargs = dict(help=True, o=True, x=1, test_arg="http://")

        built = cmd.build_arguments(*args, **kwargs)
        joined = ' '.join(built)
        self.assertIn("--help", joined)
        self.assertIn("-l", joined)
        self.assertIn("-h", joined)
        self.assertIn("-x 1", joined)
        self.assertIn("-o", joined)
        self.assertIn("--test-arg http://", joined)

    def test_clear(self):
        cmd = Command('ls').bake('-l')
        cmd.clear()
        self.assertEqual(cmd._args, [])

    def test_is_string(self):
        cmd = Command("ls")
        self.assertTrue(cmd._is_string("uh"))
        self.assertTrue(cmd._is_string(u"uh"))
        self.assertFalse(cmd._is_string(1))
        self.assertFalse(cmd._is_string(defer.Deferred()))
        self.assertFalse(cmd._is_string(defer.DeferredQueue()))

    def test_the_call(self):
        pass

    def test_string_representation(self):
        cmd = Command("git")

        self.assertEqual(str(cmd), "git")
        git_branch = cmd.branch
        self.assertEqual(str(git_branch), "git branch")
        git_branch_verbose = git_branch.bake("-v")
        self.assertEqual(str(git_branch_verbose), "git branch -v")

    def test_subcommand(self):
        cmd = Command("git")
        git_branch = cmd.branch
        self.assertEqual(git_branch.cmd, "git")
        self.assertEqual(git_branch.subcommand, "branch")
