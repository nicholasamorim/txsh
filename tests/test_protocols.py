from mock import MagicMock
from twisted.trial import unittest

from txsh.protocols import TxShProcessProtocol, DeferredProcess


class TestTxShProcessProtocol(unittest.TestCase):
    def test_sendSignal(self):
        pass


class TestDeferredProcess(unittest.TestCase):
    def test_signal(self):
        proto = TxShProcessProtocol('test')
        proto.sendSignal = MagicMock()
        d = DeferredProcess(proto)
        d.signal('KILL')

        proto.sendSignal.assert_called_once_with('KILL')
