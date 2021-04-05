////////////////// MPI bugs collection header //////////////////
//
// Origin: MUST
//
// Description: Creates a cartesian communicator with a negative entry (-1) in
// the dims attribute, which is a usage error
//
//// List of features
// P2P: Lacking
// iP2P: Lacking
// PERS: Lacking
// COLL: Lacking
// iCOLL: Lacking
// TOPO: Incorrect
// IO: Lacking
// RMA: Lacking
// PROB: Lacking
// COM: Correct
// GRP: Lacking
// DATA: Lacking
// OP: Lacking
//
//// List of errors
// deadlock: never
// numstab: never
// segfault: never
// mpierr: transient
// resleak: never
// livelock: never
// datarace: never
//
// Test: mpirun -np 2 ${EXE}
// Expect: mpierr
//
////////////////// End of MPI bugs collection header //////////////////
//////////////////       original file begins        //////////////////

#include <mpi.h>
#include <stdio.h>

#ifndef MPI_MAX_PROCESSOR_NAME
#define MPI_MAX_PROCESSOR_NAME 1024
#endif

int main(int argc, char **argv) {
  int nprocs = -1;
  int rank = -1;
  char processor_name[MPI_MAX_PROCESSOR_NAME];
  int namelen = 128;

  MPI_Init(&argc, &argv);
  MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  MPI_Get_processor_name(processor_name, &namelen);
  printf("rank %d is alive on %s\n", rank, processor_name);

  if (nprocs < 2) {
    printf("\033[0;31m! This test needs at least 2 processes !\033[0;0m\n");
    MPI_Finalize();
    return 1;
  }

  // create a cartesian communicator
  MPI_Comm comm;
  int dims[3], periods[3];
  int source, dest;
  dims[0] = nprocs;
  dims[1] = -1; /*!!!HERE COMES THE ERROR FROM*/
  dims[2] = -1;
  periods[0] = 1;
  periods[1] = 1;
  periods[2] = 1;

  //!!! Warning happens here
  MPI_Cart_create(MPI_COMM_WORLD, 3,
                  dims /*!!!HERE THE ERROR IS PASSED TO MPI*/, periods, 0,
                  &comm);
  MPI_Comm_free(&comm);

  MPI_Finalize();
  printf("\033[0;32mrank %d Finished normally\033[0;0m\n", rank);
  return 0;
}
