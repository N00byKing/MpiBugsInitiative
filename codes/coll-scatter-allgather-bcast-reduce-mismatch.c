////////////////// MPI bugs collection header //////////////////
//
// Origin: CIVL
//
// Description: Not all processes are executing the collective operations in the same order. 
//
//// List of features
// P2P: Lacking
// iP2P: Lacking
// PERS: Lacking
// COLL: Incorrect
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
   $ mpirun -np 4 ${EXE}
   | ERROR: deadlock
  END_MBI_TESTS
*/
////////////////// End of MPI bugs collection header //////////////////
//////////////////       original file begins        //////////////////


#include<mpi.h>
#include<stdlib.h>
#include<assert.h>
#include<stdio.h>


int main(int argc, char * argv[])
{
				int rank;
				int procs;
				int* sendBuf;
				int* rcvBuf;
				int* sum;

				MPI_Init(&argc,&argv);
				MPI_Comm_size(MPI_COMM_WORLD, &procs);
				MPI_Comm_rank(MPI_COMM_WORLD, &rank);

				if (rank == 0) {
								sendBuf = (int*)malloc(sizeof(int)*procs);
								sum = (int*)malloc(sizeof(int)*procs);
								for(int i=0; i < procs; i++){
												sendBuf[i] = i;
												sum[i] = 0;
								}
				}else{
								sum = (int*)malloc(sizeof(int)*procs);
								sendBuf = (int*)malloc(sizeof(int));
				}
				rcvBuf = (int*)malloc(sizeof(int)*procs);

				MPI_Scatter(sendBuf, 1, MPI_INT, rcvBuf, 1, MPI_INT, 0, MPI_COMM_WORLD);

				*sendBuf = *rcvBuf;

				if(rank % 2)
								MPI_Allgather(sendBuf, 1, MPI_INT, rcvBuf, 1, MPI_INT, MPI_COMM_WORLD);
				else
								MPI_Bcast(sum, 1, MPI_INT, 0, MPI_COMM_WORLD);

				printf("Vector process %d is: (", rank);
				for(int i=0; i<procs; i++){
								printf("%d", rcvBuf[i]);
								if(i != procs-1)
												printf(", ");
				}
				printf(")\n");

				if(rank % 2)
								MPI_Bcast(sum, 1, MPI_INT, 0, MPI_COMM_WORLD);
				else
								MPI_Allgather(sendBuf, 1, MPI_INT, rcvBuf, 1, MPI_INT, MPI_COMM_WORLD);

				MPI_Reduce(rcvBuf, sum, procs, MPI_INT, MPI_SUM, 0, MPI_COMM_WORLD);

				if(rank == 0){
								printf("Vector sum is: (");
								for(int i=0; i<procs; i++){
												printf("%d", sum[i]);
												if(i != procs-1)
																printf(", ");
								}
								printf(")\n");
				}

				free(sendBuf);
				free(rcvBuf);
				free(sum);
				return 0;
}
