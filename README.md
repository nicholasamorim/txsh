## txsh 

txsh is a project *largely* inspired by [sh] (https://github.com/amoffat/sh). txsh is a dynamic wrapper around [Twisted] (http://twistedmatrix.com) [ProcessProtocol] (https://twistedmatrix.com/documents/current/api/twisted.internet.protocol.ProcessProtocol.html) and [spawnProcess] (http://twistedmatrix.com/documents/current/api/twisted.internet.interfaces.IReactorProcess.spawnProcess.html) that allows you to call any program as if it were a function and return a deferred with its exit code and output:

```python
from twisted.internet import reactor
from txsh import ls

def my_callback(exc_info):
    print 'Exit Code:', exc_info.status
    print 'Output:', exc_info.stdout
    print 'Errors:', exc_info.stderr
    reactor.stop()

d = ls()
d.addCallback(my_callback)

reactor.run()
```

txsh is **not** a collection of system commands implemented in Twisted.

# Installation

    $> pip install txsh

# Complete documentation @ http://nicholasamorim.github.com/txsh
