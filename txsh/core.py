#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from twisted.internet import reactor

from resolvers import resolve_command, which
from protocols import TxShProcessProtocol, DeferredProcess


class Command(object):
    @staticmethod
    def factory(cmd, **default_kwargs):
        """This is used by the Environment class to get a new instance
        of this class. It resolves the command using `resolve_command`
        and returns an instance with it.

        :param cmd: A command string.
        """
        cmd = resolve_command(cmd)
        return Command(cmd)

    def __init__(self, cmd, subcommand=None):
        """
        """
        self.cmd = cmd
        self.subcommand = subcommand
        self._args = []

    def __str__(self):
        """Returns what the command would look like if ran into the shell.
        """
        if not self._args and not self.subcommand:
            return self.cmd
        elif not self._args and self.subcommand:
            return '{} {}'.format(
                self.cmd, self.subcommand)
        elif self._args and not self.subcommand:
            return '{} {}'.format(
                self.cmd, ' '.join(self._args))
        else:
            return '{} {} {}'.format(
                self.cmd, self.subcommand, ' '.join(self._args))

    def __getattr__(self, name):
        """Sugar for subcommands. This merely returns
        a new Command back with a subcommand inside.
        """
        return Command(self.cmd, name)

    def bake(self, *args, **kwargs):
        """Bakes arguments for subsequent runnings. An example:

            >>> ll = ls.bake("-l")
            >>> ll()  # This will always run "ls -l"

        This returns a new `Command` instance, leaving the original
        untouched.
        """
        new_cmd = Command(self.cmd, self.subcommand)
        new_cmd._bake(*args, **kwargs)
        return new_cmd

    def _bake(self, *args, **kwargs):
        """The internal method used to bake the argument list
        into a `Command` instance.

        :param args: A list of args, e.g: ['-l', '-h']
        :param kwargs: A list of kwargs, e.g: {'shell': True}
        """
        self._args = self.build_arguments(*args, **kwargs)

    def clear(self):
        """Clears any baked arguments of this instance. Probably not
        commonly used.
        """
        self._args = []
        return self

    def build_arguments(self, *cmd_args, **cmd_kwargs):
        """This builds the arguments. shell=True becomes --shell,
        level=2 becomes --level 2 (two separate arguments) and
        o=True becomes -o.

        Any keyword passed with underscores will have them replaced by
        dashes, e.g: please_forgive becomes --please-forgive
        """
        args = []
        args.extend(cmd_args)

        for raw_key, value in cmd_kwargs.items():
            if len(raw_key) == 1:
                args.append('-{}'.format(raw_key))
            else:
                key = raw_key.replace('_', '-')
                args.append('--{}'.format(key))

            if value is True:
                # If True, it is enough.
                # e.g.: system=True translates to --system
                continue

            args.append(str(value))

        return args

    def _spawn(self, protocol, args, env=None):
        """Returns an object which provides IProcessTransport.

        :param protocol: An instance of `TxShProcessProtocol`.
        :param args: The arguments to be passed into the process.
        :param env: The environment variables.
        """
        return reactor.spawnProcess(protocol, self.cmd, args, env=env)

    def _make_protocol(self, **kwargs):
        """Returns a `TxShProcessProtocol`.
        """
        return TxShProcessProtocol(**kwargs)

    def _is_string(self, obj):
        """Checks if a object is a string.
        """
        return isinstance(obj, unicode) or isinstance(obj, str)

    def __call__(self, *args, **kwargs):
        """Used when the import command is called. A few special (and optional)
        parameters can be passed. They are listed below:

        :param _in: Something to feed stdin (optional).
        :param _out: If passed, stdout will be redirected into this. It can be
        a file-like object, a Deferred, a DeferredQueue or a callable.
        If a string is passed, it will be assumed to be a filename that we
        can open and write to it. You will not receive the stdout at the
        callback if you opt to redirect it (it will be None).
        :param _err: If passed, stderr will be redirected into this. It can be
        a file-like object, a Deferred, a DeferredQueue or a callable.
        If a string is passed, it will be assumed to be a filename that we
        can open and write to it. You will not receive the stderr at the
        callback if you opt to redirect it (it will be None).
        :param _env: A dictionary of environment variables on which the process
        should run under. Defaults to `os.environ`.
        :param _debug: If true, debug messages will be printed.
        """
        env = kwargs.pop('_env', os.environ)
        debug = kwargs.pop('_debug', False)
        _in = kwargs.pop('_in', None)
        _out = kwargs.pop('_out', None)
        _err = kwargs.pop('_err', None)

        if self._is_string(_out):
            _out = open(_out, 'wb')

        if self._is_string(_err):
            _err = open(_err, 'wb')

        if args and isinstance(args[0], DeferredProcess):
            # This is a piped call.
            d = args[0]
            d.addCallback(lambda exc: exc.stdout)
            d.addCallback(lambda stdout: self._make_protocol(stdout, debug))
            d.addCallback(
                lambda protocol: self._spawn(protocol, [self.cmd], env))
            d.addCallback(lambda process: process.proto._process_deferred)
            return d

        txsh_protocol = self._make_protocol(
            stdin=_in, stdout=_out, stderr=_err, debug=debug)

        # Twisted requires the first arg to be the command itself
        args = self.build_arguments(*args, **kwargs)
        args.insert(0, self.cmd)
        if self.subcommand:
            args.insert(1, self.subcommand)
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

    # methods that begin with "custom_" are custom builtins and will
    # override any program that exists in our path.  this is useful
    # for things like common shell builtins that people are used to,
    # but which aren't actually full-fledged system binaries

    def custom_cd(self, path):
        os.chdir(path)

    def custom_which(self, program):
        return which(program)
