#! /usr/bin/python3
import sys
from generator_utils import *

template = """// @{generatedby}@
/* ///////////////////////// The MPI Bugs Initiative ////////////////////////

  Origin: MBI

  Description: @{shortdesc}@
    @{longdesc}@

	Version of MPI: Conforms to MPI 1.1, does not require MPI 2 implementation

BEGIN_MPI_FEATURES
	P2P!basic: @{p2pfeature}@ 
	P2P!nonblocking: @{ip2pfeature}@
	P2P!persistent: Lacking
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
	MPI_Status sta;
	int src,dest;
	int stag=0, rtag=0;
	int buff_size = 1;

  MPI_Init(&argc, &argv);
  MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  printf("Hello from rank %d \\n", rank);

  if (nprocs < 2)
    printf("MBI ERROR: This test needs at least 2 processes to produce a bug!\\n");

	MPI_Comm newcom = MPI_COMM_WORLD;
	MPI_Datatype type = MPI_INT;

  @{init1a}@
  @{init1b}@
  @{init1c}@
  @{init2a}@
  @{init2b}@
  @{init2c}@

	if (rank == 0) {
		dest=1, src=1;
  	@{operation1a}@ /* MBIERROR1 */
  	@{operation1b}@ 
  	@{operation1c}@ 
    @{fini1a}@
    @{fini1b}@
    @{fini1c}@
	}else if (rank == 1){
		dest=0, src=0;
  	@{operation2a}@ /* MBIERROR2 */
  	@{operation2b}@ 
  	@{operation2c}@ 
    @{fini2a}@
    @{fini2b}@
    @{fini2c}@
	}
  @{free1a}@
  @{free1b}@
  @{free1c}@
  @{free2a}@
  @{free2b}@
  @{free2c}@

  MPI_Finalize();
  printf("Rank %d finished normally\\n", rank);
  return 0;
}
"""


for p in probe:
    for s in send + isend:
        for r in recv + irecv:
            patterns = {}
            patterns = {'p':p, 's': s, 'r': r}
            patterns['generatedby'] = f'DO NOT EDIT: this file was generated by {sys.argv[0]}. DO NOT EDIT.'
            patterns['p2pfeature'] = 'Yes' if s in send or r in recv else 'Lacking'
            patterns['ip2pfeature'] = 'Yes' if s in isend or r in irecv else 'Lacking'
            patterns['s'] = s
            patterns['r'] = r
            patterns['p'] = p
            patterns['init1a'] = init[p]("1")
            patterns['init1b'] = init[s]("1")
            patterns['init1c'] = init[r]("2")
            patterns['init2a'] = init[p]("1")
            patterns['init2b'] = init[r]("3")
            patterns['init2c'] = init[s]("4")
            patterns['fini1a'] = fini[p]("1")
            patterns['fini1b'] = fini[s]("1")
            patterns['fini1c'] = fini[r]("2")
            patterns['fini2a'] = fini[p]("1")
            patterns['fini2b'] = fini[r]("3")
            patterns['fini2c'] = fini[s]("4")
            patterns['free1a'] = free[p]("1")
            patterns['free1b'] = free[s]("1")
            patterns['free1c'] = free[r]("2")
            patterns['free2a'] = free[p]("1")
            patterns['free2b'] = free[r]("3")
            patterns['free2c'] = free[s]("4")
            patterns['operation1a'] = operation[p]("1")
            patterns['operation1b'] = operation[s]("1")
            patterns['operation1c'] = operation[r]("2")
            patterns['operation2a'] = operation[p]("1")
            patterns['operation2b'] = operation[r]("3")
            patterns['operation2c'] = operation[s]("4")
    
            # Generate the incorrect matching 
            replace = patterns 
            replace['shortdesc'] = 'MPI_Probe is called before MPI_Recv.'
            replace['longdesc'] = 'MPI_Probe is a blocking call that returns only after a matching message has been found. By calling MPI_Probe before MPI_Recv, a deadlock is created.'
            replace['outcome'] = 'ERROR: CallMatching' 
            replace['errormsg'] = 'P2P mistmatch. @{p}@ at @{filename}@:@{line:MBIERROR1}@ and @{filename}@:@{line:MBIERROR2}@ are called before @{r}@.' 
            make_file(template, f'P2PCallMatching_{p}_{r}_{s}_nok.c', replace)

            # Generate a correct matching 
            replace = patterns 
            replace['shortdesc'] = 'Correct use of MPI_Probe.'
            replace['longdesc'] = 'Correct use of MPI_Probe.'
            replace['outcome'] = 'OK' 
            replace['errormsg'] = 'OK'
            replace['operation1a'] = operation[s]("1")
            replace['operation1b'] = operation[p]("1")
            make_file(template, f'P2PCallMatching_{p}_{r}_{s}_ok.c', replace)
