# the name of the target operating system
set(CMAKE_SYSTEM_NAME BlueGeneQ-static)

set(TOOLCHAIN_LOCATION /bgsys/drivers/ppcfloor/gnu-linux/bin)
set(TOOLCHAIN_PREFIX   powerpc64-bgq-linux-)

set(CMAKE_C_COMPILER       ${TOOLCHAIN_LOCATION}/${TOOLCHAIN_PREFIX}gcc)
set(CMAKE_CXX_COMPILER     ${TOOLCHAIN_LOCATION}/${TOOLCHAIN_PREFIX}g++)
set(CMAKE_Fortran_COMPILER ${TOOLCHAIN_LOCATION}/${TOOLCHAIN_PREFIX}gfortran)

# Make sure MPI_COMPILER wrapper matches the gnu compilers.
# Prefer local machine wrappers to driver wrappers here too.
find_program(MPI_COMPILER NAMES mpicxx mpic++ mpiCC mpicc
  PATHS
  /usr/local/bin
  /usr/bin
  /bgsys/drivers/ppcfloor/comm/gcc/bin)
