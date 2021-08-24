#! /usr/bin/python3
import sys
from generator_utils import *

template = """// @{generatedby}@
/* ///////////////////////// The MPI Bugs Initiative ////////////////////////

  Origin: MBI

  Description: @{shortdesc}@
    @{longdesc}@

	Version of MPI: Conforms to MPI 2, requires MPI 3 implementation (for lock_all/unlock_all epochs)

BEGIN_MPI_FEATURES
	P2P!basic: Lacking 
	P2P!nonblocking: Lacking
	P2P!persistent: Lacking
	COLL!basic: Lacking
	COLL!nonblocking: Lacking
	COLL!persistent: Lacking
	COLL!tools: Lacking
	RMA: @{rmafeature}@
END_MPI_FEATURES

BEGIN_MBI_TESTS
  $ mpirun -np 3 ${EXE}
  | @{outcome}@
  | @{errormsg}@
END_MBI_TESTS
//////////////////////       End of MBI headers        /////////////////// */

#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>


int main(int argc, char **argv) {
  int nprocs = -1;
  int rank = -1;
	MPI_Win win;
  int W; // Window buffer
	int target=1;
  int NUM_ELEMT=1;

  MPI_Init(&argc, &argv);
  MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  printf("Hello from rank %d \\n", rank);

  if (nprocs < 2)
    printf("MBI ERROR: This test needs at least 2 processes to produce a bug!\\n");

	MPI_Datatype type = MPI_INT;
  W = 4;

  MPI_Win_create(&W, NUM_ELEMT * sizeof(int), sizeof(int), MPI_INFO_NULL, MPI_COMM_WORLD, &win);

  @{epoch}@

	@{init1}@
	@{init2}@

	if (rank == 0) {
 		@{operation1}@ /* MBIERROR1 */
	}else if (rank == 2){
 		@{operation2}@ /* MBIERROR2 */
	}

	@{add_store}@ /* MBIERROR3 */ 

  @{finEpoch}@
	

  MPI_Win_free(&win);

  MPI_Finalize();
  printf("Rank %d finished normally\\n", rank);
  return 0;
}
"""


for e in epoch:
    for p1 in put: 
        for p2 in get + put:
            patterns = {}
            patterns = {'e': e, 'p1': p1, 'p2': p2}
            patterns['generatedby'] = f'DO NOT EDIT: this file was generated by {sys.argv[0]}. DO NOT EDIT.'  
            patterns['rmafeature'] = 'Yes'
            patterns['p1'] = p1 
            patterns['p2'] = p2 
            patterns['e'] = e 
            patterns['epoch'] = epoch[e]("1") 
            patterns['finEpoch'] = finEpoch[e]("1") 
            patterns['init1'] = init[p1]("1") #put
            patterns['init2'] = init[p2]("2") #get or put
            patterns['operation1'] = operation[p1]("1") #put
            patterns['operation2'] = operation[p2]("2") #get or put
            patterns['add_store'] = "" 

    		    # Generate a data race (Put + Get/Put)
            replace = patterns 
            replace['shortdesc'] = 'Global Concurrency error.' 
            replace['longdesc'] = 'Global Concurrency error. @{p2}@ conflicts with @{p1}@ on the target side' 
            replace['outcome'] = 'ERROR: GlobalConcurrency' 
            replace['errormsg'] = 'Global Concurrency error. @{p2}@ at @{filename}@:@{line:MBIERROR2}@ conflicts with @{p1}@ line @{line:MBIERROR1}@ on the target side'
            make_file(template, f'GlobalConcurrency_{e}_{p1}_{p2}_nok.c', replace)

    		    # Generate a data race (Get/Put + store)
            replace = patterns 
            replace['shortdesc'] = 'Global Concurrency error.' 
            replace['longdesc'] = 'Global Concurrency error. @{p2}@ conflicts with a store on the target side' 
            replace['outcome'] = 'ERROR: GlobalConcurrency' 
            replace['errormsg'] = 'Global Concurrency error. @{p2}@ at @{filename}@:@{line:MBIERROR2}@ conflicts with the store line @{line:MBIERROR3}@ on the target side'
            replace['add_store'] = 'if(rank == target){ W++;}' 
            replace['operation1'] = ""
            make_file(template, f'GlobalConcurrency_{e}_{p2}_store_nok.c', replace)
