////////////////// MPI bugs collection header //////////////////
//
// Origin: Hermes
//
// Description: Heat conduction demo program. Solves the heat equation on a 2D
// grid.
//              This code is supposed to deadlock
//
//// List of features
// P2P: Correct
// iP2P: Lacking
// PERS: Lacking
// COLL: Correct
// iCOLL: Lacking
// TOPO: Lacking
// IO: Lacking
// RMA: Lacking
// PROB: Lacking
// COM: Lacking
// GRP: Lacking
// DATA: Correct
// OP: Lacking
//
//// List of errors
// deadlock: transient
// numstab: never
// segfault: never
// mpierr: never
// resleak: never
// livelock: never
// various: transient
/*
  BEGIN_MBI_TESTS
   $ mpirun -np 4 ${EXE}
   | ERROR: deadlock
  END_MBI_TESTS
*/
////////////////// End of MPI bugs collection header //////////////////
//////////////////       original file begins        //////////////////

#include <math.h>
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* This type represents the grid and its description */
typedef struct {
  /* current theta array */
  double **theta;
  /* new theta array */
  double **thetanew;
  /* domain size (number of grid cells) in x and y */
  int xsize;
  int ysize;
  /* size of a grid cell */
  double dx;
  double dy;
  /* "heat equation constant" */
  double k;
} heatGrid;

/* This type defines everything thats needed for MPI */
typedef struct {
  /* Own rank, used to only let master do output*/
  int rank;
  /* Comm for a cartesian distribution of the grid*/
  MPI_Comm cart;
  /* Neighbors in communicator*/
  int up, down, left, right;
  /* Start of a processes sub-grid (x, y)*/
  int start_x;
  int start_y;
  /* Number of cells in x or y direction for this process*/
  int num_cells_x;
  int num_cells_y;
  /* Datatype used to transfer a data column*/
  MPI_Datatype columntype;
} dataMPI;

void heatAllocate(heatGrid *grid, int xsize, int ysize);
void heatDeallocate(heatGrid *grid);
void heatInitialize(heatGrid *grid);
double heatInitFunc(double x);
void heatPrint(heatGrid *grid);
void heatTimestep(heatGrid *grid, dataMPI *mympi, double dt, double *dthetamax);
void heatBoundary(heatGrid *grid, dataMPI *mympi);
void heatOutput(heatGrid *grid, int filenumber);
void heatTotalEnergy(heatGrid *grid, double *energy);
void heatMPISetup(int *pargc, char ***pargv, heatGrid *grid,
                  dataMPI *configMPI);
void heatMPIFree(dataMPI *configMPI);
void heatMPIGather(heatGrid *grid, dataMPI *configMPI);

/******************************************************
 * Allocate the heatGrid and initialize all variables.
 ******************************************************/
void heatAllocate(heatGrid *grid, int ysize, int xsize) {
  int i, j;

  grid->ysize = ysize;
  grid->xsize = xsize;
  grid->theta = (double **)malloc(sizeof(double *) * (ysize + 2));
  grid->thetanew = (double **)malloc(sizeof(double *) * (ysize + 2));
  grid->theta[0] = (double *)malloc(sizeof(double) * (ysize + 2) * (xsize + 2));
  grid->thetanew[0] =
      (double *)malloc(sizeof(double) * (ysize + 2) * (xsize + 2));

  for (i = 0; i < ysize + 2; i++) {
    grid->theta[i] = grid->theta[0] + i * (xsize + 2);
    grid->thetanew[i] = grid->thetanew[0] + i * (xsize + 2);

    for (j = 0; j < xsize + 2; j++) {
      grid->theta[i][j] = 0.0;
      grid->thetanew[i][j] = 0.0;
    }
  }

  grid->dy = 1.0;
  grid->dx = 1.0;
  grid->k = 1.0;
}

/******************************************************
 * Deallocate the heatGrid.
 ******************************************************/
void heatDeallocate(heatGrid *grid) {
  free(grid->theta[0]);
  free(grid->theta);
  grid->theta = NULL;
  free(grid->thetanew[0]);
  free(grid->thetanew);
  grid->thetanew = NULL;
}

/******************************************************
 * Initialize the grid with some meaninful start values.
 ******************************************************/
void heatInitialize(heatGrid *grid) {
  double ycenter, xcenter, radius, cr;
  int x, y, i, j;

  /* initialize with a circle */
  for (i = 0; i < grid->ysize + 2; i++)
    for (j = 0; j < grid->xsize + 2; j++)
      grid->theta[i][j] = 0.0;

  ycenter = (grid->ysize - 10) * grid->dy / 2.0;
  xcenter = (grid->xsize + 6) * grid->dx / 2.0;
  radius = fmin(grid->ysize * grid->dy, grid->xsize * grid->dx) * 0.25;

  for (x = 1; x <= grid->xsize; x++) {
    for (y = 1; y <= grid->ysize; y++) {
      cr = sqrt((y - ycenter) * (y - ycenter) + (x - xcenter) * (x - xcenter));
      if (cr < radius) {
        /* smooth boundary */
        grid->theta[y][x] = grid->theta[y][x] + 2.0 * heatInitFunc(cr / radius);
      }
    }
  }
}

/******************************************************
 * Polynomial function for the initialization a smooth heat profile, 0 <= x
 *<= 1.
 ******************************************************/
double heatInitFunc(double x) {
  return (-4.0 * x * x * x + 4.0 * x * x - 1.0 * x + 1.0);
}

/******************************************************
 * Print grid to console.
 ******************************************************/
void heatPrint(heatGrid *grid) {
  int x, y;

  /* print header */
  for (x = 1; x <= grid->xsize; x++)
    printf("====");
  printf("\n");

  /* print data */
  for (y = 1; y <= grid->ysize; y++) {
    for (x = 1; x <= grid->xsize; x++) {
      if (grid->theta[y][x] < 1.e-100)
        printf("  . ");
      else
        printf("%4.1f", grid->theta[y][x]);
    }
    printf("\n");
  }
}

/******************************************************
 * Calculate one timestep of size dt on the grid.
 *
 * for each grid point:
 *
 *                                  ( d2T   d2T )
 *          thetanew =  theta + k * ( --- + --- ) * dt
 *                                  ( dx2   dy2 )
 *                                  _____________
 *                                        |
 *                                        |
 *  dthetamax returns the max. value of this term
 *  (useful as exit condition for the time stepping)
 ******************************************************/
void heatTimestep(heatGrid *grid, dataMPI *mympi, double dt,
                  double *dthetamax) {
  int x, y, redo;
  double dtheta;
  double mymax = 0.0;

  *dthetamax = 0.0;

  /* calculate the time step: read from theta, write new timestep to thetanew */
  /* Only calculate on a processes sub-grid */
  for (redo = 0; redo < 10000; redo++) {
    for (y = mympi->start_y; y < mympi->start_y + mympi->num_cells_y; y++) {
      for (x = mympi->start_x; x < mympi->start_x + mympi->num_cells_x; x++) {
        dtheta = (grid->theta[y][x - 1] + grid->theta[y][x + 1] -
                  2 * grid->theta[y][x]) /
                     (grid->dx * grid->dx) +
                 (grid->theta[y - 1][x] + grid->theta[y + 1][x] -
                  2 * grid->theta[y][x]) /
                     (grid->dy * grid->dy);
        grid->thetanew[y][x] = grid->theta[y][x] + grid->k * dtheta * dt;

        mymax = fmax(fabs(dtheta),
                     mymax); /* save max theta for the exit condition */
      }
    }
  }

  /* update theta: copy thetanew to theta */
  for (y = mympi->start_y; y < mympi->start_y + mympi->num_cells_y; y++)
    for (x = mympi->start_x; x < mympi->start_x + mympi->num_cells_x; x++)
      grid->theta[y][x] = grid->thetanew[y][x];

  /* Calculate maximum dtheta of all processes and distribute it */
  if (mympi->rank != 0) {
    MPI_Status status;
    MPI_Send(&mymax, 1, MPI_DOUBLE, 0, 567, mympi->cart);
    MPI_Recv(dthetamax, 1, MPI_DOUBLE, 0, 234, mympi->cart, &status);
  } else {
    MPI_Status status;
    int i, size;
    double tempmax;
    MPI_Comm_size(mympi->cart, &size);
    for (i = 1; i < size; i++) {
      MPI_Recv(&tempmax, 1, MPI_DOUBLE, i, 567, mympi->cart, &status);
      mymax = fmax(mymax, tempmax);
    }

    *dthetamax = mymax;

    for (i = 1; i < size; i++) {
      MPI_Send(dthetamax, 1, MPI_DOUBLE, i, 234, mympi->cart);
    }
  }
}

/******************************************************
 * Set periodic boundary conditions.
 *
 * The grid arrays are allocated with additional "ghost cells"
 * in each spatial dimension. The lower boundary is copied to
 * the upper ghost cells (and vice versa) for each dimension:
 *
 *    ___________         ___________
 *   |  _______ |        |  stuvwx  |
 *   | |abcdef| |        |f|abcdef|a|
 *   | |ghijkl| |        |l|ghijkl|g|
 *   | |mnopqr| |   ->   |r|mnopqr|m|
 *   | |stuvwx| |        |x|stuvwx|s|
 *   |__________|        |__abcdef__|
 *
 * For MPI:
 * ========
 *
 * Each process has ghost cells around its sub-grid
 * e.g., Sub-grid & ghost cells for process "P_i":
 *
 *      __________________
 *     |Overall-grid      |
 *     |       ...        |
 *     |    __________    |
 *     |   |G ______ c|   |
 *     |   |h| P_i  |e|   |
 *     |   |o| Sub- |l|   |
 *     |...|s| Grid |l|...|
 *     |   |t|______|s|   |
 *     |   |__________|   |
 *     |       ...        |
 *     |__________________|
 *
 * Ghost cells are received from the neighbors.
 * Neighbors in turn receive border of the process.
 *
 * e.g., Border exchange for Process 0:
 *         _____
 *        |     |
 *        |  4  |
 *        |     |
 *        |FGHIJ|
 *  _____ ======= _____
 * |    v||abcde||q    |
 * |    w||f   g||r    |
 * |  2 x||h 0 i||s 1  |
 * |    y||j   k||t    |
 * |____z||lmnop||u____|
 *        =======
 *        |ABCDE|
 *        |     |
 *        |  3  |
 *        |_____|
 *
 * 0 sends (e,g,i,k,p) to 1
 * 0 receives (q,r,s,t,u) from 1 (put into its ghost cells)
 * 0 sends (a,f,h,j,l) to 2
 * 0 receives (v,w,x,y,z) from 2 (put into its ghost cells)
 * ....
 *
 ******************************************************/
void heatBoundary(heatGrid *grid, dataMPI *mympi) {
  MPI_Status status;
  MPI_Request reqs[4];
  MPI_Status stats[4];

  /*Send uppermost data row to top neighbor*/
  MPI_Isend(&(grid->theta[mympi->start_y][mympi->start_x]),
            mympi->num_cells_x + 1, MPI_DOUBLE, mympi->up, 123, mympi->cart,
            &(reqs[0]));
  /*Receive lower ghost cell row from bottom neighbor*/
  MPI_Recv(&(grid->theta[mympi->start_y + mympi->num_cells_y][mympi->start_x]),
           mympi->num_cells_x + 1, MPI_DOUBLE, mympi->down, 123, mympi->cart,
           &status);

  /*Send lowermost data row to bottom neighbor*/
  MPI_Isend(
      &(grid->theta[mympi->start_y + mympi->num_cells_y - 1][mympi->start_x]),
      mympi->num_cells_x + 1, MPI_DOUBLE, mympi->down, 123, mympi->cart,
      &(reqs[1]));
  /*Receive upper ghost cell row from top neighbor*/
  MPI_Recv(&(grid->theta[mympi->start_y - 1][mympi->start_x]),
           mympi->num_cells_x + 1, MPI_DOUBLE, mympi->up, 123, mympi->cart,
           &status);

  /*Send leftmost data column to left neighbor*/
  MPI_Isend(&(grid->theta[mympi->start_y][mympi->start_x]), 1,
            mympi->columntype, mympi->left, 123, mympi->cart, &(reqs[2]));
  /*Receive right ghost cell column from right neighbor*/
  MPI_Recv(&(grid->theta[mympi->start_y][mympi->start_x + mympi->num_cells_x]),
           1, mympi->columntype, mympi->right, 123, mympi->cart, &status);

  /*Send rightmost data column to right neighbor*/
  MPI_Isend(
      &(grid->theta[mympi->start_y][mympi->start_x + mympi->num_cells_x - 1]),
      1, mympi->columntype, mympi->right, 123, mympi->cart, &(reqs[3]));
  /*Receive left ghost cell column from left neighbor*/
  MPI_Recv(&(grid->theta[mympi->start_y][mympi->start_x - 1]), 1,
           mympi->columntype, MPI_ANY_SOURCE, MPI_ANY_TAG, mympi->cart,
           &status);

  MPI_Waitall(3, reqs, stats);
}

/******************************************************
 * Calculate the total energy (sum of theta in all grid cells)
 ******************************************************/
void heatTotalEnergy(heatGrid *grid, double *energy) {
  int x, y;

  *energy = 0.0;
  for (y = 1; y <= grid->ysize; y++)
    for (x = 1; x <= grid->xsize; x++)
      *energy += grid->theta[y][x];
}

/******************************************************
 * Function to setup MPI data.
 *
 * (1) Initializes MPI
 * (2) Creates a cartesian communicator for border exchange
 * (3) Distributes the overall grid to the processes
 * (4) Sets up helpful data-type and MPI buffer
 *
 ******************************************************/
void heatMPISetup(int *pargc, char ***pargv, heatGrid *grid,
                  dataMPI *configMPI) {
  int size, dims[2] = {0, 0}, periods[2] = {1, 1}, coords[2];
  int buf_size;
  char *buf;

  /* ==== (1) ==== */
  /* Base init*/
  MPI_Init(pargc, pargv);
  MPI_Comm_rank(MPI_COMM_WORLD, &configMPI->rank);
  MPI_Comm_size(MPI_COMM_WORLD, &size);

  /* ==== (2) ==== */
  /* Create cartesian communicator*/
  MPI_Dims_create(size, 2, dims);
  MPI_Cart_create(MPI_COMM_WORLD, 2, dims, periods, 0, &configMPI->cart);

  /* Store neighbors in the grid */
  MPI_Cart_shift(configMPI->cart, 0, 1, &configMPI->left, &configMPI->right);
  MPI_Cart_shift(configMPI->cart, 1, 1, &configMPI->up, &configMPI->down);

  /* ==== (3) ==== */
  /* Distribute overall grid to processes */
  MPI_Cart_coords(configMPI->cart, configMPI->rank, 2,
                  coords); /*My coordinate*/

  configMPI->start_x = 1 + (grid->xsize / dims[0]) * coords[0];
  if (coords[0] + 1 != dims[0])
    /* coords 0 to N-1 get an equal distribution*/
    configMPI->num_cells_x = grid->xsize / (dims[0]);
  else
    /* last coord gets the rest */
    configMPI->num_cells_x = grid->xsize - configMPI->start_x + 1;

  configMPI->start_y = 1 + (grid->ysize / dims[1]) * coords[1];
  if (coords[1] + 1 != dims[1])
    /* coords 0 to N-1 get an equal distribution*/
    configMPI->num_cells_y = grid->ysize / (dims[1]);
  else
    /* last coord gets the rest */
    configMPI->num_cells_y = grid->ysize - configMPI->start_y + 1;

  /* ==== (4) ==== */
  /* Create datatype to communicate one column */
  MPI_Type_vector(configMPI->num_cells_y, /* #blocks */
                  1,                      /* #elements per block */
                  grid->xsize + 2,        /* #stride */
                  MPI_DOUBLE,             /* old type */
                  &configMPI->columntype /* new type */);
  MPI_Type_commit(&configMPI->columntype);
}

/******************************************************
 * Function to free and finalize MPI.
 ******************************************************/
void heatMPIFree(dataMPI *configMPI) {
  int buf_size;
  char *buf;

  MPI_Type_free(&configMPI->columntype);
  MPI_Comm_free(&configMPI->cart);
  MPI_Finalize();
}

/******************************************************
 * Gathers all data on process 0
 *
 * For output and total energy calculation it is
 * necessary to receive all sub-grids on process 0.
 *
 * It is a simple, but non-optimal implementation.
 ******************************************************/
void heatMPIGather(heatGrid *grid, dataMPI *mympi) {
  int block_size[4]; /*stores: x_start,y_start, num_cells_x, num_cells_y*/
  MPI_Datatype blocktype;
  MPI_Status status;
  int i, size;

  /*Slaves send data*/
  if (mympi->rank != 0) {
    /*Prepare block info to be sent*/
    block_size[0] = mympi->start_x;
    block_size[1] = mympi->start_y;
    block_size[2] = mympi->num_cells_x;
    block_size[3] = mympi->num_cells_y;

    /* Create datatype to communicate one block*/
    MPI_Type_vector(mympi->num_cells_y - 1, /* #blocks */
                    mympi->num_cells_x,     /* #elements per block */
                    grid->xsize + 2,        /* #stride */
                    MPI_DOUBLE,             /* old type */
                    &blocktype /* new type */);
    MPI_Type_commit(&blocktype);

    MPI_Send(block_size, 4, MPI_INT, 0, 123, MPI_COMM_WORLD);
    MPI_Send(&grid->theta[mympi->start_y][mympi->start_x], 1, blocktype, 0, 123,
             MPI_COMM_WORLD);

    MPI_Type_free(&blocktype);
  } else
  /*Master Receives data*/
  {
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    for (i = 1; i < size; i++) {
      /*Receive Block Info*/
      MPI_Recv(block_size, 4, MPI_INT, i, 123, MPI_COMM_WORLD, &status);

      /* Create datatype to communicate one block*/
      MPI_Type_vector(block_size[3],   /* #blocks */
                      block_size[2],   /* #elements per block */
                      grid->xsize + 2, /* #stride */
                      MPI_DOUBLE,      /* old type */
                      &blocktype /* new type */);
      MPI_Type_commit(&blocktype);

      MPI_Recv(&grid->theta[block_size[1]][block_size[0]], 1, blocktype, i, 123,
               MPI_COMM_WORLD, &status);

      MPI_Type_free(&blocktype);
    }
  }
}

/******************************************************
 * Main program and time stepping loop.
 ******************************************************/
int main(int argc, char **argv) {
  heatGrid mygrid;
  double dt, dthetamax, energyInitial, energyFinal;
  int step, noutput;
  dataMPI mympi;

  /* create heatGrid and initialize variables */
  heatAllocate(&mygrid, 20, 20);
  heatInitialize(&mygrid);
  dt = 0.05;
  dthetamax = 100.0;
  step = 0;
  noutput = 1;

  /* setup MPI */
  heatMPISetup(&argc, &argv, &mygrid, &mympi);

  /* Work only for master process
   * No Gather necessary here, all initialize equally*/
  if (mympi.rank == 0) {
    /* output of initial grid */
    printf("intial grid:\n");
    heatPrint(&mygrid);

    /* energy of initial grid */
    heatTotalEnergy(&mygrid, &energyInitial);
  }

  /* time stepping loop */
  while (dthetamax > 0.4) {
    step = step + 1;
    heatBoundary(&mygrid, &mympi);
    heatTimestep(&mygrid, &mympi, dt, &dthetamax);
    break;
  }

  /* Gather data on process 0 for output*/
  heatMPIGather(&mygrid, &mympi);

  /* Work only for master process*/
  if (mympi.rank == 0) {
    /* output of final grid */
    printf("\ngrid after %d iterations:\n", step);
    heatPrint(&mygrid);

    /* energy of final grid */
    heatTotalEnergy(&mygrid, &energyFinal);

    printf("\n= Energy Conservation Check =\n");
    printf(" initial Energy: %10.3f\n", energyInitial);
    printf("   final Energy: %10.3f\n", energyFinal);
    printf("     Difference: %10.3f\n", energyFinal - energyInitial);
  }

  heatDeallocate(&mygrid);

  /* Finalize MPI*/
  heatMPIFree(&mympi);

  return 0;
}
