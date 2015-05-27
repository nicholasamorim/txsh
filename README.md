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

### Examples

```python
from txsh import ls, curl, wc, git, sudo

# arguments should go separated
d = ls("-l", "-h") # ls -l -h

# Keyword arguments are also supported
d = ls(help=True)  # ls --help

# Underscores will be replaced by dashes
d = curl(connect_timeout=10, url="http://something")
# curl --connect-timeout 10 --url http:/something

# You can pipe
d = wc(ls())

# You can have subcommands
d = git.branch()  # Same as git("branch")
d = sudo.ls("-h")  # Same as sudo("ls", "-h")

# You can bake
ll = ls.bake("-l", "-h")
d = ll()  # Now ll will always output ls -l -h

# You can redirect stderr or stdout to a file using special args _out and _err
d = ls("-l", _out=open('output.log', 'wb'))

# In fact, you can use any file-like object like a StringIO.

# A callabble.
def alert(error):
    pass  # Do something

d = ls("-l", _err=alert) # Will redirect stderr to alert function.

# If you pass a string, we will simply assume it's a filename.
d = ls("-l", _out="output.log", _err="error.log")

# You can also pass a DeferredQueue or a simple Deferred.
queue = DeferredQueue()
my_defer = Deferred()
d = ls("-l", _out=queue, _err=my_defer)
# When stdout is ready, it will call queue.put
# When stderr is ready, it will call my_defer.callback
```

txsh is **not** a collection of system commands implemented in Twisted.

# Installation

    $> pip install txsh


### To-Do
    - Proper documentation / tutorials.
    - Tests
    - Passing of any object, Queue, or any iterable (list, set, dictionary, etc) to stdin
    - Custom success exit codes
    - Raising Failures if exit_code is not successful so user can add errbacks to deal with them.
    - Glob Expansion
    - Advanced piping
    - usePTY
    - Python 3
