import os
import sys
from types import ModuleType

from twisted.python import log
from twisted.internet import reactor

from resolvers import resolve_command, which
from protocols import TxShProcessProtocol, DeferredProcess


class Command(object):
    @staticmethod
    def factory(cmd, **default_kwargs):
        """
        """
        cmd = resolve_command(cmd)
        return Command(cmd)

    def __init__(self, cmd):
        """
        """
        self.cmd = cmd
        self._args = []

    def __str__(self):
        """
        """
        return '{} {}'.format(
            self.cmd, ' '.join(self._args))

    def bake(self, *args, **kwargs):
        """
        """
        new_cmd = Command(self.cmd)
        new_cmd._bake(*args, **kwargs)
        return new_cmd

    def _bake(self, *args, **kwargs):
        """
        """
        self._args = self.build_arguments(*args, **kwargs)

    def clear(self):
        """
        """
        self._args = []
        return self

    def build_arguments(self, *cmd_args, **cmd_kwargs):
        """
        """
        args = []
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

    def _spawn(self, p, args, env=None):
        """
        """
        return reactor.spawnProcess(p, self.cmd, args, env=env)

    def _make_protocol(self, stdin=None):
        """
        """
        return TxShProcessProtocol(
            self.cmd,
            _stdin=stdin,
            debug=False)

    def __call__(self, *args, **kwargs):
        env = kwargs.get('_env', os.environ)

        if args and isinstance(args[0], DeferredProcess):
            # This is a piped call.
            d = args[0]
            d.addCallback(lambda exc: exc.stdout)
            d.addCallback(lambda stdout: self._make_protocol(stdout))
            d.addCallback(
                lambda protocol: self._spawn(protocol, [self.cmd], env))
            d.addErrback(log.err)
            d.addCallback(lambda process: process.proto._process_deferred)
            d.addErrback(log.err)
            return d

        txsh_protocol = self._make_protocol()
        # Twisted requires the first arg to be the command itself
        args = self.build_arguments(*args, **kwargs)
        args.insert(0, self.cmd)
        args.extend(self._args)
        process = self._spawn(txsh_protocol, args, env)
        return process.proto._process_deferred


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
