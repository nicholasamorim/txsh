import os
import sys
from types import ModuleType
from collections import namedtuple

from twisted.internet import reactor, protocol, defer


class TxShProcessProtocol(protocol.ProcessProtocol):
    Output = namedtuple('Output', ['status', 'stdout', 'stderr'])

    def __init__(self, cmd, *args, **kwargs):
        self.cmd = cmd
        # self.args = args
        self._in = kwargs.get('_in', None)
        self._debug = kwargs.get('debug', False)
        self._finished_defer = defer.Deferred()
        self._status = None
        self._stdout = []
        self._stderr = []

    def connectionMade(self):
        """Write to stdin ?
        """
        if self._in is not None:
            self.transport.write(self._in)
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
        self._finished_defer.callback(output)


def resolve_command(cmd):
    path = which(cmd)
    if not path:
        if "_" in cmd:
            path = which(cmd.replace('_', '-'))
        if not path:
            return None

    return path


class Command(object):
    @staticmethod
    def factory(cmd, **default_kwargs):
        cmd = resolve_command(cmd)
        return Command(cmd)

    def __init__(self, cmd):
        self.cmd = cmd

    def build_arguments(self, *cmd_args, **cmd_kwargs):
        args = [self.cmd]
        args.extend(cmd_args)

        for raw_key, value in cmd_kwargs.items():
            if len(raw_key) == 1:
                args.append('-{}'.format(raw_key))
                continue

            key = raw_key.replace('_', '-')
            args.append('--{}'.format(key))

            if value is True:
                # If True, it is enough.
                # e.g.: system=True translates to --system
                continue

            args.append(str(value))

        return args

    def __call__(self, *args, **kwargs):
        txsh_protocol = TxShProcessProtocol(self.cmd, debug=False)
        # Twisted requires the first arg to be the command itself
        args = self.build_arguments(*args, **kwargs)
        process = reactor.spawnProcess(txsh_protocol, self.cmd, args)
        return process.proto._finished_defer


def which(program):
    def is_exe(fpath):
        return (os.path.exists(fpath) and
                os.access(fpath, os.X_OK) and
                os.path.isfile(os.path.realpath(fpath)))

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        if "PATH" not in os.environ:
            return None
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


class Environment(dict):
    # this is a list of all of the names that the txsh module exports that will
    # not resolve to functions.  we don't want to accidentally shadow real
    # commands with functions/imports that we define in sh.py.  for example,
    # "import time" may override the time system program
    whitelist = set([
        "Command",
        "CommandNotFound",
        "DEFAULT_ENCODING",
        "DoneReadingForever",
        "ErrorReturnCode",
        "NotYetReadyToRead",
        "SignalException",
        "TimeoutException",
        "__project_url__",
        "__version__",
        "args",
        "glob",
        "pushd",
    ])

    def __init__(self, globs, baked_args={}):
        self.globs = globs
        self.baked_args = baked_args
        self.disable_whitelist = False

    def __setitem__(self, cmd, v):
        self.globs[cmd] = v

    def __getitem__(self, cmd):
        # if we first import "_disable_whitelist" from sh, we can import
        # anything defined in the global scope of sh.py.  this is useful
        # for our tests
        if cmd == "_disable_whitelist":
            self.disable_whitelist = True
            return None

        # we're trying to import something real (maybe), see if it's in our
        # global scope
        if cmd in self.whitelist or self.disable_whitelist:
            try:
                return self.globs[cmd]
            except KeyError:
                pass

        # somebody tried to be funny and do "from sh import *"
        if cmd == "__all__":
            raise AttributeError(
                "Cannot import * from txsh. "
                "Please import txsh or import programs individually.")

        if cmd.startswith("__") and cmd.endswith("__"):
            raise AttributeError

        # how about an environment variable?
        try:
            return os.environ[cmd]
        except KeyError:
            pass

        # is it a custom builtin?
        builtin = getattr(self, "custom_" + cmd, None)
        if builtin:
            return builtin

        return Command.factory(cmd)

    # methods that begin with "b_" are custom builtins and will override any
    # program that exists in our path.  this is useful for things like
    # common shell builtins that people are used to, but which aren't actually
    # full-fledged system binaries

    def custom_cd(self, path):
        os.chdir(path)

    def custom_which(self, program):
        return which(program)


class DynamicModule(ModuleType):
    def __init__(self, self_module, baked_args={}):
        for attr in ["__builtins__", "__doc__", "__name__", "__package__"]:
            setattr(self, attr, getattr(self_module, attr, None))

        self.__path__ = []
        self.__self_module = self_module
        self.__env = Environment(globals(), baked_args)

    def __setattr__(self, name, value):
        if hasattr(self, "__env"):
            self.__env[name] = value
        else:
            ModuleType.__setattr__(self, name, value)

    def __getattr__(self, name):
        if name == "__env":
            raise AttributeError
        return self.__env[name]

    # accept special keywords argument to define defaults for all operations
    # that will be processed with given by return SelfWrapper
    def __call__(self, **kwargs):
        return DynamicModule(self.__self_module, kwargs)

if __name__ == "__main__":
    pass
else:
    module = sys.modules[__name__]
    sys.modules[__name__] = DynamicModule(module)
