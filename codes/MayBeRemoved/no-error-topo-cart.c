////////////////// MPI bugs collection header //////////////////
//
// Origin: MPI Correctness Benchmark
//
// Description: Creates a cartesian communicator, and creates new communicators
// for lines and columns
//
//// List of features
// P2P: Lacking
// iP2P: Lacking
// PERS: Lacking
// COLL: Lacking
// iCOLL: Lacking
// TOPO: Correct
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
// mpierr: never
// resleak: never
// livelock: never
// datarace: never
/*
  BEGIN_MBI_TESTS
   $ mpirun -np 4 ${EXE}
   | OK
  END_MBI_TESTS
*/
////////////////// End of MPI bugs collection header //////////////////
//////////////////       original file begins        //////////////////

#include <math.h>
#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv) {

  int rank, newrank, Rrank, Crank, size, ndim = 2, dim, periods[2] = {0, 0},
                                         reorder = 0, coords[2];
  int remain_dims[2];
  MPI_Comm newcomm, Rcomm, Ccomm;

  MPI_Init(&argc, &argv);

  MPI_Comm_size(MPI_COMM_WORLD, &size);
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);

  // Define the dimensions of the square grid
  dim = sqrt(size);

  if (rank == 0)
    fprintf(stderr, "Dimensions of the grid:%d x %d  - %d processes\n", dim,
            dim, size);

  int dims[2] = {dim, dim};

  MPI_Cart_create(MPI_COMM_WORLD, ndim, dims, periods, reorder, &newcomm);

  if (newcomm == MPI_COMM_NULL)
    fprintf(stderr, "newcomm is null for P%d (process not in the grid)\n",
            rank);

  if (rank < (dim * dim)) {
    MPI_Comm_rank(newcomm, &newrank);
    MPI_Cart_coords(newcomm, newrank, ndim, coords);

    /* Create 1D row subgrids*/
    remain_dims[0] = 0;
    remain_dims[1] = 1; // belongs to subgrid
    MPI_Cart_sub(newcomm, remain_dims, &Rcomm);
    /* Create 1D column subgrids*/
    remain_dims[0] = 1;
    remain_dims[1] = 0;
    MPI_Cart_sub(newcomm, remain_dims, &Ccomm);

    MPI_Comm_rank(Rcomm, &Rrank);
    MPI_Comm_rank(Ccomm, &Crank);
    printf("rank=%d, newrank=%d, (%d,%d), Rrank:%d Crank:%d\n", rank, newrank,
           coords[0], coords[1], Rrank, Crank);
  }

  if (newcomm != MPI_COMM_NULL)
    MPI_Comm_free(&newcomm);
  if (Rcomm != MPI_COMM_NULL)
    MPI_Comm_free(&Rcomm);
  if (Ccomm != MPI_COMM_NULL)
    MPI_Comm_free(&Ccomm);

  MPI_Finalize();
  return 0;
}
