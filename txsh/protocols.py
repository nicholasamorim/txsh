from collections import namedtuple

from twisted.internet import protocol, defer


class DeferredProcess(defer.Deferred):
    def __init__(self, proto):
        self.proto = proto

        # defer.Deferred is an old-style class
        defer.Deferred.__init__(self)

    def signal(self, sig):
        self.proto.transport.signalProcess(sig)


class TxShProcessProtocol(protocol.ProcessProtocol):
    Output = namedtuple('Output', ['status', 'stdout', 'stderr'])

    def __init__(self, cmd, *args, **kwargs):
        self.cmd = cmd
        # self.args = args
        self._stdin = kwargs.get('_stdin', None)
        self._debug = kwargs.get('_debug', False)
        self._process_deferred = DeferredProcess(self)
        self._status = None
        self._stdout = []
        self._stderr = []

    def sendSignal(self, signal):
        """
        """
        self.transport.signalProcess(signal)

    def connectionMade(self):
        """Write to stdin ?
        """
        if self._stdin is not None:
            self.transport.write(self._stdin)

        self.transport.closeStdin()

    def outConnectionLost(self):
        """This is called when the program closes its stdout pipe.
        This usually happens when the program terminates.
        """
        if self._debug:
            print 'outconnectionlost'

    def errConnectionLost(self):
        """Same as outConnectionLost, but for stderr instead of stdout.
        """
        if self._debug:
            print 'errconnectionLost'

    def outReceived(self, data):
        if self._debug:
            print 'outReceived', data
        self._stdout.append(data)

    def errReceived(self, data):
        if self._debug:
            print 'errReceived', data
        self._stderr.append(data)

    def processExited(self, status):
        """This is called when the child process has been reaped, and receives
        information about the process' exit status. The status is passed in the
        form of a Failure instance, created with a .value that either holds a
        ProcessDone object if the process terminated normally (it died of
        natural causes instead of receiving a signal, and if the exit code
        was 0), or a ProcessTerminated object (with an .exitCode attribute)
        if something went wrong.
        """
        if self._debug:
            print 'processExited', status

        if status.value.signal:
            self._status = status.value.signal
            return

        self._status = getattr(status.value, 'exitCode', 0)

    def processEnded(self, status):
        """This is called when all the file descriptors associated with the
        child process have been closed and the process has been reaped. This
        means it is the last callback which will be made onto a
        ProcessProtocol. The status parameter has the same meaning as it
        does for processExited.
        """
        if self._debug:
            print 'onProcessEnded', status

        output = self.Output(
            self._status,
            ''.join(self._stdout),
            ''.join(self._stderr))
        self._process_deferred.callback(output)