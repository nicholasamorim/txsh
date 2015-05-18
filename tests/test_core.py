from mock import MagicMock
from twisted.trial import unittest

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
        pass

    def test_clear(self):
        pass

    def test_is_string(self):
        pass

    def test_the_call(self):
        pass
