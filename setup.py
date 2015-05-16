from setuptools import setup, find_packages

long_description = """
txsh is a dynamic wrapper around Twisted ProcessProtocol and
spawnProcess that allows you to call any program as if it were
a function and return a deferred with its exit code and output.
"""


setup(
    name="txsh",
    version='0.1',
    description="Twisted Process interface",
    long_description=long_description,
    author="Nicholas Amorim",
    author_email="nicholas@alienretro.com",
    url="https://github.com/nicholasamorim/txsh",
    license="MIT",
    packages=find_packages(),
    install_requires=['twisted>=10.2.0'],
    requires=['twisted(>=10.2.0)'],
    zip_safe=False,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Twisted",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        'Topic :: Software Development :: Libraries',
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
