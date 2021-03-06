////////////////// MPI bugs collection header //////////////////
//
// Origin: ISP (http://formalverification.cs.utah.edu/ISP_Tests/)
//
// Description: Correct use of MPI_Sendrecv
//
// Communication pattern:
//
// Feat_persistent: Lacking
//        P0              P1
//		sendrecv(1,1)  sendrecv(0,0)
//		sendrecv(1,1)  sendrecv(0,0)
//		sendrecv(1,1)  sendrecv(0,0)
//
//
//// List of features
// P2P: Correct
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
//
//// List of errors
// deadlock: never
// numstab: never
// segfault: never
// mpierr: never
// resleak: never
// livelock: never
// datarace: never
/*
  BEGIN_MBI_TESTS
   $ mpirun -np 3 ${EXE}
   | OK
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
  MPI_Status status;

  MPI_Init(&argc, &argv);
  MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  MPI_Get_processor_name(processor_name, &namelen);
  printf("rank %d is alive on %s\n", rank, processor_name);

  if (nprocs < 1) {
    printf("\033[0;31m! This test requires at least 2 processes\033[0;0m\n");
  } else {
    if (rank == 0) {
      memset(buf0, 0, buf_size * sizeof(int));

      MPI_Sendrecv(buf0, buf_size, MPI_INT, 1, 0, buf1, buf_size, MPI_INT, 1, 0,
                   MPI_COMM_WORLD, &status);

      MPI_Sendrecv(buf1, buf_size, MPI_INT, 1, 0, buf0, buf_size, MPI_INT, 1, 0,
                   MPI_COMM_WORLD, &status);

      MPI_Sendrecv(buf0, buf_size, MPI_INT, 1, 0, buf1, buf_size, MPI_INT, 1, 0,
                   MPI_COMM_WORLD, &status);
    } else {
      if (rank == 1) {
        memset(buf1, 1, buf_size * sizeof(int));

        MPI_Sendrecv(buf1, buf_size, MPI_INT, 0, 0, buf0, buf_size, MPI_INT, 0,
                     0, MPI_COMM_WORLD, &status);

        MPI_Sendrecv(buf0, buf_size, MPI_INT, 0, 0, buf1, buf_size, MPI_INT, 0,
                     0, MPI_COMM_WORLD, &status);

        MPI_Sendrecv(buf1, buf_size, MPI_INT, 0, 0, buf0, buf_size, MPI_INT, 0,
                     0, MPI_COMM_WORLD, &status);
      }
    }
  }

  MPI_Finalize();
  printf("\033[0;32mrank %d Finished normally\033[0;0m\n", rank);
  return 0;
}
