////////////////// MPI bugs collection header //////////////////
//
// Origin: ISP (http://formalverification.cs.utah.edu/ISP_Tests/)
//
// Description: P0 and P1 are blocked in waitall and recv functions. recv(0) and
// send(0) in P1 should be inverted.
//
//				 Communication pattern:
//
// Feat_persistent: Lacking
//				   P0          P1        P2
//				 barrier     barrier   barrier
//				 Irecv(any)  Isend(0)  recv(1)
//				 Irecv(any)  Isend(2)
//				 waitall     waitany
//				 send(1)     recv(0)
//                     send(0)
//                     wait
//				 barrier     barrier
//
//
//// List of features
// P2P: Incorrect
// iP2P: Incorrect
// PERS: Lacking
// COLL: Correct
// iCOLL: Lacking
// TOPO: Lacking
// IO: Lacking
// RMA: Lacking
// PROB: Lacking
// COM: Lacking
// GRP: Lacking
// DATA: Lacking
// OP: Lacking
//
//// List of errors
// deadlock: transient
// numstab: never
// segfault: never
// mpierr: never
// resleak: never
// livelock: never
// datarace: never
/*
  BEGIN_MBI_TESTS
   $ mpirun -np 3 ${EXE}
   | ERROR: deadlock
  END_MBI_TESTS
*/
////////////////// End of MPI bugs collection header //////////////////
//////////////////       original file begins        //////////////////

#include <mpi.h>
#include <stdio.h>
#include <string.h>

#ifndef MPI_MAX_PROCESSOR_NAME
#define MPI_MAX_PROCESSOR_NAME 1024
#endif

#define buf_size 128

int main(int argc, char **argv) {
  int nprocs = -1;
  int rank = -1;
  char processor_name[MPI_MAX_PROCESSOR_NAME];
  int namelen = 128;
  int buf0[buf_size];
  int buf1[buf_size];
  int done;
  MPI_Status statuses[2];
  MPI_Request reqs[2];

  MPI_Init(&argc, &argv);
  MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  MPI_Get_processor_name(processor_name, &namelen);
  printf("rank %d is alive on %s\n", rank, processor_name);

  MPI_Barrier(MPI_COMM_WORLD);

  if (nprocs < 3) {
    printf("\033[0;31m! This test needs at least 3 processes !\033[0;0m\n");
  } else if (rank == 0) {
    MPI_Irecv(buf0, buf_size, MPI_INT, MPI_ANY_SOURCE, 0, MPI_COMM_WORLD,
              &reqs[0]);
    MPI_Irecv(buf1, buf_size, MPI_INT, MPI_ANY_SOURCE, 0, MPI_COMM_WORLD,
              &reqs[1]);
    MPI_Waitall(2, reqs, statuses);
    MPI_Send(buf1, buf_size, MPI_INT, 1, 1, MPI_COMM_WORLD);
  } else if (rank == 1) {
    memset(buf0, 0, buf_size * sizeof(int));
    MPI_Isend(buf0, buf_size, MPI_INT, 0, 0, MPI_COMM_WORLD, &reqs[0]);
    MPI_Isend(buf0, buf_size, MPI_INT, 2, 1, MPI_COMM_WORLD, &reqs[1]);
    MPI_Waitany(2, reqs, &done, statuses);
    MPI_Recv(buf1, buf_size, MPI_INT, 0, 1, MPI_COMM_WORLD, statuses);
    MPI_Send(buf0, buf_size, MPI_INT, 0, 0, MPI_COMM_WORLD);
    MPI_Wait(&reqs[(done + 1) % 2], statuses);
  } else if (rank == 2) {
    MPI_Recv(buf1, buf_size, MPI_INT, 1, 1, MPI_COMM_WORLD, statuses);
  }

  MPI_Barrier(MPI_COMM_WORLD);

  MPI_Finalize();
  printf("\033[0;32mrank %d Finished normally\033[0;0m\n", rank);
  return 0;
}
