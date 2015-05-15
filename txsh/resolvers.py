#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os


def which(program):
    """
    """
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


def resolve_command(cmd):
    """
    """
    path = which(cmd)
    if not path:
        if "_" in cmd:
            path = which(cmd.replace('_', '-'))
        if not path:
            return None

    return path
