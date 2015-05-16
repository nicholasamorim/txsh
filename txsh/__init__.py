#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from types import ModuleType

from core import Environment


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
