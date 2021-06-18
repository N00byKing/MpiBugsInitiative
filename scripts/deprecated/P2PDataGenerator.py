#! /usr/bin/python3
import sys
from generator_utils import *

template = """// @{generatedby}@
/* ///////////////////////// The MPI Bugs Initiative ////////////////////////

  Origin: MBI

  Description: @{shortdesc}@
    @{longdesc}@

BEGIN_MPI_FEATURES
	P2P!basic: @{p2pfeature}@ 
	P2P!nonblocking: @{ip2pfeature}@
	P2P!persistent: @{persfeature}@
	COLL!basic: Lacking
	COLL!nonblocking: Lacking
	COLL!persistent: Lacking
	COLL!tools: Lacking
	RMA: Lacking
END_MPI_FEATURES

BEGIN_MBI_TESTS
  $ mpirun -np 2 ${EXE}
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
	int src=0, dest=1;
	int stag = 0, rtag = 0;
 	int buff_size = 1;
	MPI_Comm newcom = MPI_COMM_WORLD;

  MPI_Init(&argc, &argv);
  MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  printf("Hello from rank %d \\n", rank);

  if (nprocs < 2)
    printf("MBI ERROR: This test needs at least 2 processes to produce a bug!\\n");
  
	MPI_Datatype type = MPI_INT;
  @{change_type}@

  @{init1}@
  @{init2}@
	if (rank == 0) {
  	@{operation1}@ /* MBIERROR1 */
	  @{start1}@
	  @{fini1}@
	}else if (rank == 1) {
  	@{operation2}@ /* MBIERROR2 */
	  @{start2}@
	  @{fini2}@
	}
  @{free1}@
  @{free2}@

  MPI_Finalize();
  printf("Rank %d finished normally\\n", rank);
  return 0;
}
"""


for p1 in send + isend + psend:
    for p2 in recv + irecv + precv:
        patterns = {}
        patterns = {'p1': p1, 'p2': p2}
        patterns['generatedby'] = f'DO NOT EDIT: this file was generated by {sys.argv[0]}. DO NOT EDIT.'  
        patterns['p2pfeature'] = 'Yes' if p1 in send or p2 in recv  else 'Lacking'
        patterns['ip2pfeature'] = 'Yes' if p1 in isend or p2 in irecv  else 'Lacking' 
        patterns['persfeature'] = 'Yes' if p1 in psend or p2 in precv  else 'Lacking' 
        patterns['p1'] = p1 
        patterns['p2'] = p2 
        patterns['init1'] = init[p1]("1") 
        patterns['init2'] = init[p2]("2")
        patterns['start1'] = start[p1]("1") 
        patterns['start2'] = start[p2]("2")
        patterns['fini1'] = fini[p1]("1") 
        patterns['fini2'] = fini[p2]("2") 
        patterns['operation1'] = operation[p1]("1") #send
        patterns['operation2'] = operation[p2]("2") #recv
        patterns['free1'] = free[p1]("1") 
        patterns['free2'] = free[p2]("2") 

    		# Generate the incorrect matching 
        replace = patterns 
        replace['shortdesc'] = 'Point to point @{p1}@ and @{p2}@ have a datatype mismatch' 
        replace['longdesc'] = 'Process 0 uses MPI_FLOAT as the datatype while process 1 uses MPI_INT.' 
        replace['outcome'] = 'ERROR: DatatypeMatching' 
        replace['errormsg'] = 'P2P Datatype mismatch. @{p1}@ at @{filename}@:@{line:MBIERROR1}@ and @{p2}@ at @{filename}@:@{line:MBIERROR2}@ have MPI_INT and MPI_FLOAT as a datatype' 
        replace['change_type'] = 'if (rank == 0)\n    type = MPI_FLOAT;'
        make_file(template, f'P2PDataMatching_{p1}_{p2}_nok.c', replace)
