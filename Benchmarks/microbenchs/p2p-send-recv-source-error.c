////////////////// MPI bugs collection header //////////////////
//
// Origin: MUST
//
// Description: Performs a send, recv with a negative integer as source in the
//              recv call. Thats not allowed and causes an error.
//
//// List of features
// P2P: Incorrect
// iP2P: Lacking
// PERS: Lacking
// COLL: Lacking  
// iCOLL: Lacking
// TOPO: Lacking
// IO: Lacking
// RMA: Lacking
// PROB: Lacking
// COM: Lacking
// GRP: Lacking
// DATA: Lacking
// OP: Lacking
// HYB: Lacking
// LOOP: Lacking
// SP: Lacking
//
//// List of errors
// deadlock: never
// numstab: never
// segfault: never
// mpierr: transient
// resleak: never
// livelock: never
// compliance: always
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

int main(int argc, char** argv)
{
  int nprocs = -1;
  int rank   = -1;
  char processor_name[MPI_MAX_PROCESSOR_NAME];
  int namelen = 128;
  MPI_Status status;

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

  if (rank == 0) {
    MPI_Send(&nprocs, 1, MPI_INT, 1, 42, MPI_COMM_WORLD);
  }

  if (rank == 1) {
    int recvFrom = -1;
    while (recvFrom == MPI_PROC_NULL || recvFrom == MPI_ANY_SOURCE)
      recvFrom--;
    MPI_Recv(&nprocs, 1, MPI_INT, recvFrom, 42, MPI_COMM_WORLD, &status);
  }

  MPI_Finalize();
  printf("\033[0;32mrank %d Finished normally\033[0;0m\n", rank);
  return 0;
}