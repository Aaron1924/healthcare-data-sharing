# pygroupsig

Welcome to _pygroupsig_, an extensible library for group signatures. Below,
you can find basic information about how to use the library.

## Compilation

This library has been developed from scratch in Python _except_ for **mcl**.
We have built a wrapper around the original [mcl](https://github.com/herumi/mcl)
library written in C/C++ using Python ctypes.

To build **mcl**, run the following commands.

```bash
git clone https://github.com/herumi/mcl.git
cd mcl
cmake -B build .
make -C build
```

## Usage

## Tests

```
python -m unittest
```

(Note: To build with debug flags, add the `-DCMAKE_BUILD_TYPE=Debug` modifier to
cmake in the prevous sequence of commands.)

Tests can alternatively be run with `ctest` from the build directory, or with
`ctest -T memcheck` to check memory-related bugs.
