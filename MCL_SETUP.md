# MCL Library Setup Guide

This guide explains how to set up the MCL library for the pygroupsig project.

## Issue

The pygroupsig module requires the MCL library to be available on your system. By default, it looks for the library in `/usr/local/lib/mcl/`, but this location may not exist on your system.

## Solution

We've provided two ways to run the application with the correct MCL library path:

### Option 1: Using the Shell Script

```bash
./run_api.sh
```

This script:
1. Sets the `MCL_LIB_PATH` environment variable to point to the `mcl/build/lib` directory
2. Adds the MCL library path to `LD_LIBRARY_PATH`
3. Runs the FastAPI application

### Option 2: Using the Python Script

```bash
python run_api.py
```

This script:
1. Sets the `MCL_LIB_PATH` environment variable to point to the `mcl/build/lib` directory
2. Adds the MCL library path to `LD_LIBRARY_PATH`
3. Runs the FastAPI application using uvicorn

### Option 3: Setting Environment Variables Manually

If you prefer to set the environment variables manually, you can do so with:

```bash
export MCL_LIB_PATH="$(pwd)/mcl/build/lib"
export LD_LIBRARY_PATH="$(pwd)/mcl/build/lib:$LD_LIBRARY_PATH"
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

## Troubleshooting

If you still encounter issues with the MCL library, check the following:

1. Make sure the MCL library is built correctly:
   ```bash
   ls -la mcl/build/lib
   ```
   You should see `libmcl.so` and `libmclbn384_256.so` in the output.

2. If the library is not built, you can build it with:
   ```bash
   cd mcl
   mkdir -p build
   cd build
   cmake ..
   make
   cd ../..
   ```

3. If you're using WSL (Windows Subsystem for Linux), make sure the paths are correctly translated between Windows and Linux formats.

4. Check the output of the `constants.py` file for any error messages related to loading the MCL library.

## Manual Installation (Alternative)

If you prefer to install the MCL library system-wide, you can do so with:

```bash
cd mcl
mkdir -p build
cd build
cmake ..
make
sudo make install
cd ../..
```

This will install the MCL library to `/usr/local/lib/mcl/`, which is the default location that pygroupsig looks for.
