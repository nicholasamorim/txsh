from mock import MagicMock
from twisted.trial import unittest
from twisted.internet import defer

from txsh.protocols import TxShProcessProtocol, DeferredProcess


class TestTxShProcessProtocol(unittest.TestCase):
    def test_sendSignal(self):
        pass

    def test_write_stdout(self):
        proto = TxShProcessProtocol()
        proto.outReceived("data!")
        self.assertIn("data!", proto._stdout)

        my_callback = MagicMock()
        proto = TxShProcessProtocol(stdout=my_callback)
        proto.write_to_stdout("data!")
        my_callback.assert_called_once_with("data!")

        my_callback = MagicMock()
        d = defer.Deferred()
        d.addCallback(my_callback)
        proto = TxShProcessProtocol(stdout=d)
        proto.write_to_stdout("data!")
        my_callback.assert_called_once_with("data!")

        d = defer.DeferredQueue()
        d.put = MagicMock()
        proto = TxShProcessProtocol(stdout=d)
        proto.write_to_stdout("data!")
        d.put.assert_called_once_with("data!")

    def test_write_stderr(self):
        proto = TxShProcessProtocol()
        proto.errReceived("data!")
        self.assertIn("data!", proto._stderr)

        my_callback = MagicMock()
        proto = TxShProcessProtocol(stderr=my_callback)
        proto.write_to_stderr("data!")
        my_callback.assert_called_once_with("data!")

        my_callback = MagicMock()
        d = defer.Deferred()
        d.addCallback(my_callback)
        proto = TxShProcessProtocol(stderr=d)
        proto.write_to_stderr("data!")
        my_callback.assert_called_once_with("data!")

        d = defer.DeferredQueue()
        d.put = MagicMock()
        proto = TxShProcessProtocol(stderr=d)
        proto.write_to_stderr("data!")
        d.put.assert_called_once_with("data!")


class TestDeferredProcess(unittest.TestCase):
    def test_signal(self):
        proto = TxShProcessProtocol('test')
        proto.sendSignal = MagicMock()
        d = DeferredProcess(proto)
        d.signal('KILL')

        proto.sendSignal.assert_called_once_with('KILL')
