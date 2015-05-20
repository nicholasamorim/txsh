#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import namedtuple

from twisted.python import log
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
        self.proto.sendSignal(sig)


class TxShProcessProtocol(protocol.ProcessProtocol):
    """This is the protocol responsible to communicate with the
    process when it's set to run. An instance of this is passed
    into reactor.spawnProcess.
    """
    Output = namedtuple('Output', ['status', 'stdout', 'stderr'])

    def __init__(self, *args, **kwargs):
        """
        """
        self._stdin = kwargs.get('stdin', None)
        self._debug = kwargs.get('debug', False)
        self._process_deferred = DeferredProcess(self)
        self._status = None

        self._stdout = kwargs.get('stdout', None)
        self._stderr = kwargs.get('stderr', None)
        if self._stdout is None:
            self._stdout = []
        if self._stderr is None:
            self._stderr = []

    def write_stream(self, obj, data):
        """Writes stream to several types of object.
        """
        if isinstance(obj, list):
            obj.append(data)
        elif isinstance(obj, defer.Deferred):
            obj.callback(data)
        elif isinstance(obj, defer.DeferredQueue):
            obj.put(data)
        elif callable(obj):
            obj(data)
        else:
            obj.write(data)  # file-like object

    def close_streams(self):
        """
        """
        streams = [self._stdout, self._stderr]
        for stream in streams:
            try:
                stream.close()
            except AttributeError:
                pass

    def write_to_stdout(self, data):
        """Writes data to stdout.
        """
        self.write_stream(self._stdout, data)

    def write_to_stderr(self, data):
        """Writes data to stderr.
        """
        self.write_stream(self._stderr, data)

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
            log.msg('outconnectionlost called.')

    def errConnectionLost(self):
        """Same as outConnectionLost, but for stderr instead of stdout.
        """
        if self._debug:
            log.msg('errConnectionLost called.')

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
            log.msg('outReceived called with data: ', data)
        self.write_to_stdout(data)

    def errReceived(self, data):
        """This is called with data from the process stderr pipe.
        It behaves just like outReceived.

        :param data: A chunk of data coming from stderr.
        """
        if self._debug:
            log.msg('errReceived called with data: ', data)
        self.write_to_stderr(data)

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
            log.msg('processExited called with status: ', status)

        if status.value.signal:
            self._status = status.value.signal
            return

        self._status = getattr(status.value, 'exitCode', 0)

    def get_output(self, obj):
        """If stdout or stdout redirection is activated, this will
        return none.
        """

        return ''.join(obj) if type(obj) is list else None

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
            log.msg('onProcessEnded', status)

        self.close_streams()
        stdout = self.get_output(self._stdout)
        stderr = self.get_output(self._stderr)

        output = self.Output(self._status, stdout, stderr)
        self._process_deferred.callback(output)
