import ctypes
import os
import sys

# src/bn_c384_256.cpp
MCLBN_FP_UNIT_SIZE: int = 6
MCLBN_FR_UNIT_SIZE: int = 4

# include/lib/curve_type.h
MCL_BLS12_381: int = 5

# include/lib/bn.h
MCLBN_COMPILED_TIME_VAR: int = MCLBN_FR_UNIT_SIZE * 10 + MCLBN_FP_UNIT_SIZE

# src/shim/pbc_ext.h (libgroupsig)
BLS12_381_P: str = "1 3685416753713387016781088315183077757961620795782546409894578378688607592378376318836054947676345821548104185464507 1339506544944476473020471379941921221584933875938349620426543736416511423956333506472724655353366534992391756441569"
BLS12_381_Q: str = "1 352701069587466618187139116011060144890029952792775240219908644239793785735715026873347600343865175952761926303160 3059144344244213709971259814753781636986470325476647558659373206291635324768958432433509563104347017837885763365758 1985150602287291935568054521177171638300868978215655730859378665066344726373823718423869104263333984641494340347905 927553665492332455747201965776037880757740193453592970025027978793976877002675564980949289727957565575433344219582"

# Get the absolute path to the mcl/build/lib directory
# For Windows paths in WSL, we need to convert from /mnt/c/... to C:\...
if os.path.exists('/mnt/c'):
    # We're in WSL
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    mcl_build_lib = os.path.join(project_root, "mcl", "build", "lib")
    print(f"Project root: {project_root}")
    print(f"MCL build lib path: {mcl_build_lib}")
else:
    # We're in a regular Linux environment
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    mcl_build_lib = os.path.join(project_root, "mcl", "build", "lib")

# In pygroupsig/utils/constants.py
LIB_PATH: str = os.environ.get("MCL_LIB_PATH", mcl_build_lib)
MCL_LIB: str = "libmcl.so"
MCL384_LIB: str = "libmclbn384_256.so"
lib: ctypes.CDLL | None = None


def load_library() -> None:
    global lib
    if not LIB_PATH:
        raise RuntimeError("Environment variable MCL_LIB_PATH missing.")

    print(f"Loading MCL libraries from: {LIB_PATH}")
    try:
        # Check if the library files exist
        mcl_lib_path = os.path.join(LIB_PATH, MCL_LIB)
        mcl384_lib_path = os.path.join(LIB_PATH, MCL384_LIB)

        if not os.path.exists(mcl_lib_path):
            print(f"Warning: {mcl_lib_path} does not exist")
            # Try to find the library in the system
            for path in sys.path:
                potential_path = os.path.join(path, MCL_LIB)
                if os.path.exists(potential_path):
                    print(f"Found {MCL_LIB} at {potential_path}")
                    mcl_lib_path = potential_path
                    break

        if not os.path.exists(mcl384_lib_path):
            print(f"Warning: {mcl384_lib_path} does not exist")
            # Try to find the library in the system
            for path in sys.path:
                potential_path = os.path.join(path, MCL384_LIB)
                if os.path.exists(potential_path):
                    print(f"Found {MCL384_LIB} at {potential_path}")
                    mcl384_lib_path = potential_path
                    break

        ctypes.CDLL(mcl_lib_path)
        lib = ctypes.CDLL(mcl384_lib_path)
        if lib.mclBn_init(MCL_BLS12_381, MCLBN_COMPILED_TIME_VAR):
            raise RuntimeError("mcl library could not be initialized")
    except Exception as e:
        print(f"Error loading MCL libraries: {e}")
        raise
