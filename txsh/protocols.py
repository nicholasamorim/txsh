#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import namedtuple

from twisted.internet import protocol, defer


class DeferredProcess(defer.Deferred):
    """A specialized Deferred that adds a .signal method to a deferred.
    """
    def __init__(self, proto):
        self.proto = proto

        # defer.Deferred is an old-style class
        defer.Deferred.__init__(self)

    def signal(self, sig):
        """This is called when the user wants to send a
        signal to the process. The signal gets passed
        into the transport layer to the process.

        :param sig: A signal string, e.g.: KILL'
        """
        self.proto.transport.signalProcess(sig)


class TxShProcessProtocol(protocol.ProcessProtocol):
    """This is the protocol responsible to communicate with the
    process when it's set to run. An instance of this is passed
    into reactor.spawnProcess.
    """
    Output = namedtuple('Output', ['status', 'stdout', 'stderr'])

    def __init__(self, cmd, *args, **kwargs):
        """
        """
        self.cmd = cmd
        self._stdin = kwargs.get('_stdin', None)
        self._debug = kwargs.get('_debug', False)
        self._process_deferred = DeferredProcess(self)
        self._status = None
        self._stdout = []
        self._stderr = []

    def sendSignal(self, signal):
        """This is called when a signal is fired to our process.
        You can fire a signal in the `DeferredProcess` you receive
        back when calling the command.

            >>> d = ls()
            >>> d.signal('KILL')

        :param signal: A signal string, e.g: 'KILL'
        """
        self.transport.signalProcess(signal)

    def connectionMade(self):
        """This is called when the program is started.
        So this is the place we write to the stdin, if needed.
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
            print 'errConnectionLost called.'

    def outReceived(self, data):
        """This is called with data that was received from the process
        stdout pipe. Pipes tend to provide data in larger chunks than
        sockets (one kilobyte is a common buffer size), so you may not
        experience the "random dribs and drabs behavior typical of
        network sockets, but regardless you should be prepared to deal
        if you dont get all your data in a single call. To do it properly,
        outReceived ought to simply accumulate the data and put off doing
        anything with it until the process has finished.

        :param data: A chunk of data coming from stdout.
        """
        if self._debug:
            print 'outReceived called with data: ', data
        self._stdout.append(data)

    def errReceived(self, data):
        """This is called with data from the process stderr pipe.
        It behaves just like outReceived.

        :param data: A chunk of data coming from stderr.
        """
        if self._debug:
            print 'errReceived called with data: ', data
        self._stderr.append(data)

    def processExited(self, status):
        """This is called when the child process has been reaped, and receives
        information about the process' exit status. The status is passed in the
        form of a Failure instance, created with a .value that either holds a
        ProcessDone object if the process terminated normally (it died of
        natural causes instead of receiving a signal, and if the exit code
        was 0), or a ProcessTerminated object (with an .exitCode attribute)
        if something went wrong.

        :param status: A `failure.Failure` instance with a .value attribute
        that holds either a ProcessDone or a ProcessTerminated (with an
        .exitCode attribute).
        """
        if self._debug:
            print 'processExited called with status: ', status

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

        :param status: A `failure.Failure` instance with a .value attribute
        that holds either a ProcessDone or a ProcessTerminated (with an
        .exitCode attribute).
        """
        if self._debug:
            print 'onProcessEnded', status

        output = self.Output(
            self._status,
            ''.join(self._stdout),
            ''.join(self._stderr))
        self._process_deferred.callback(output)
