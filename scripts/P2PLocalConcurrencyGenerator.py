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
	int dest=0, src=0;
	int stag = 0, rtag = 0;
  int buff_size = 1;

  MPI_Init(&argc, &argv);
  MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  printf("Hello from rank %d \\n", rank);

  if (nprocs < 2)
    printf("MBI ERROR: This test needs at least 2 processes to produce a bug!\\n");

  MPI_Comm newcom = MPI_COMM_WORLD;
	MPI_Datatype type = MPI_INT;

  @{init1}@
  @{init2}@
	if (rank == 0) {
		dest = 1; src = 1;
  	@{operation1}@ 
		@{start1}@
		@{write1}@ /* MBIERROR1 */ 
		@{fini1}@
	}else if (rank == 1){
		dest = 0; src = 0;
  	@{operation2}@
		@{start2}@
		@{write2}@ /* MBIERROR2 */
		@{fini2}@
	}

  MPI_Finalize();
  printf("Rank %d finished normally\\n", rank);
  return 0;
}
"""


for s in send + isend + psend:
    for r in irecv + precv + recv:
        patterns = {}
        patterns = {'s': s, 'r': r}
        patterns['generatedby'] = f'DO NOT EDIT: this file was generated by {sys.argv[0]}. DO NOT EDIT.'
        patterns['p2pfeature'] = 'Yes' if s in send else 'Lacking'
        patterns['ip2pfeature'] = 'Yes' if r in irecv else 'Lacking'
        patterns['persfeature'] = 'Yes' if r in precv else 'Lacking'
        patterns['s'] = s
        patterns['r'] = r
        patterns['init1'] = init[s]("1")
        patterns['init2'] = init[r]("2")
        patterns['fini1'] = fini[s]("1")
        patterns['fini2'] = fini[r]("2")
        patterns['start1'] = start[s]("1")
        patterns['start2'] = start[r]("2")
        patterns['operation1'] = operation[s]("1")
        patterns['operation2'] = operation[r]("2")
        patterns['write1'] = write[s]("1")
        patterns['write2'] = write[r]("2")

        # Generate a message race
        if s in send and r in irecv + precv:
            replace = patterns 
            replace['shortdesc'] = ' Local Concurrency with a P2P'
            replace['longdesc'] = f'The message buffer in {r} is modified before the call has been completed.'
            replace['outcome'] = 'ERROR: LocalConcurrency' 
            replace['errormsg'] = 'Local Concurrency with a P2P. The receive buffer in @{r}@ is modified at @{filename}@:@{line:MBIERROR2}@ whereas there is no guarantee the message has been received.'
            make_file(template, f'P2PLocalConcurrency_{r}_{s}_nok.c', replace)
        if s in isend + psend and r in recv:
            replace = patterns 
            replace['shortdesc'] = ' Local Concurrency with a P2P'
            replace['longdesc'] = f'The message buffer in {s} is modified before the call has been completed.'
            replace['outcome'] = 'ERROR: LocalConcurrency' 
            replace['errormsg'] = 'Local Concurrency with a P2P. The send buffer in @{s}@ is modified at @{filename}@:@{line:MBIERROR1}@ whereas there is no guarantee the message has been sent.'
            make_file(template, f'P2PLocalConcurrency_{r}_{s}_nok.c', replace)
        if s in isend + psend and r in irecv + precv:
            replace = patterns 
            replace['shortdesc'] = ' Local Concurrency with a P2P'
            replace['longdesc'] = f'The message buffer in {s} and {r} are modified before the calls have completed.'
            replace['outcome'] = 'ERROR: LocalConcurrency' 
            replace['errormsg'] = 'Local Concurrency with a P2P. The message buffers in @{s}@ and @{r}@ are modified at @{filename}@:@{line:MBIERROR1}@ and @{filename}@:@{line:MBIERROR2}@ whereas there is no guarantee the calls have been completed.'
            make_file(template, f'P2PLocalConcurrency_{r}_{s}_nok.c', replace)
