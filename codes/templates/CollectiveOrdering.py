#! /usr/bin/python3
import sys
from generator_utils import make_file

template = """// @{generatedby}@
/* ///////////////////////// The MPI Bugs Initiative ////////////////////////

  Origin: MBI

  Description: @{shortdesc}@
    @{longdesc}@

BEGIN_MPI_FEATURES
  P2P:   Lacking
  iP2P:  Lacking
  PERS:  Lacking
  COLL:  @{collfeature}@
  iCOLL: @{icollfeature}@
  TOPO:  Lacking
  RMA:   Lacking
  PROB:  Lacking
  COM:   Lacking
  GRP:   Lacking
  DATA:  Lacking
  OP:    Lacking
END_MPI_FEATURES

BEGIN_ERROR_LABELS
  deadlock:  ???
  numstab:   never
  mpierr:    never
  resleak:   never
  datarace:  never
  various:   never
END_ERROR_LABELS

BEGIN_MBI_TESTS
  $ mpirun -np 2 ${EXE}
  | @{outcome}@
  | @{errormsg}@
END_MBI_TESTS
//////////////////////       End of MBI headers        /////////////////// */

#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv) {
  int nprocs = -1;
  int rank = -1;
  int localsum, sum;

  MPI_Init(&argc, &argv);
  MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  printf("Hello from rank %d \\n", rank);

  if (nprocs < 2)
    printf("\\033[0;31m! This test needs at least 2 processes to produce a bug "
           "!\\033[0;0m\\n");

  localsum = 0;
  for (int i = 0; i <= rank; i++) {
    localsum += i;
  }
  printf("process %d has local sum of %d\\n", rank, localsum);

  if (rank % 2) {
    @{operation1a}@ /* MBIERROR1 */
    @{operation2a}@
  } else {
    @{operation1b}@ /* MBIERROR2 */
    @{operation2b}@
  }

  if (rank == 0)
    printf("total sum is %d\\n", sum);

  MPI_Finalize();
  printf("\\033[0;32mrank %d Finished normally\\033[0;0m\\n", rank);
  return 0;
}
"""

collectives = ['MPI_Barrier', 'MPI_Bcast', 'MPI_Reduce', 'MPI_Allreduce']
icollectives = []#'ibarrier', 'ireduce', 'iallreduce']

init = {}
operation = {}

init['MPI_Barrier'] = lambda n: ""
operation['MPI_Barrier'] = lambda n: 'MPI_Barrier(MPI_COMM_WORLD);'

init['MPI_Bcast'] = lambda n: f'int buf{n}[buff_size];'
operation['MPI_Bcast'] = lambda n: f'MPI_Bcast(buf{n}, buff_size, MPI_INT, 0, MPI_COMM_WORLD);'

init['MPI_Reduce'] = lambda n: f"int sum{n}, val{n} = 1;"
operation['MPI_Reduce'] = lambda n: f"MPI_Reduce(&sum{n}, &val{n}, 1, MPI_INT, MPI_SUM, 0, MPI_COMM_WORLD);"

init['MPI_Allreduce'] = lambda n: f"int sum{n}, val{n} = 1;"
operation['MPI_Allreduce'] = lambda n: f"MPI_Allreduce(&sum{n}, &val{n}, 1, MPI_INT, MPI_SUM, MPI_COMM_WORLD);"


for coll1 in collectives + icollectives:
  for coll2 in collectives + icollectives:
    patterns = {}
    patterns = {'coll1': coll1, 'coll2': coll2}
    patterns['generatedby'] = f'DO NOT EDIT: this file was generated by {sys.argv[0]}. DO NOT EDIT.'
    patterns['collfeature'] = 'Correct' if coll1 in collectives or coll2 in collectives else 'Lacking'
    patterns['icollfeature'] = 'Correct' if coll1 in icollectives or coll2 in icollectives else 'Lacking'
    patterns['coll1'] = coll1
    patterns['coll2'] = coll2
    patterns['init1'] = init[coll1]("1")
    patterns['init2'] = init[coll2]("2")
    patterns['operation1a'] = operation[coll1]("1")
    patterns['operation1b'] = operation[coll1]("1")
    patterns['operation2a'] = operation[coll2]("2")
    patterns['operation2b'] = operation[coll2]("2")

    if coll1 == coll2:
    	replace = patterns
    	replace['shortdesc'] = 'Correct collective ordering'
    	replace['longdesc'] = f'All ranks call {coll1} twice'
    	replace['outcome'] = 'OK'
    	replace['errormsg'] = ''
    	make_file(template, f'CollCallOrder_{coll1}_{coll2}_ok.c', replace)
    else: 
      # Generate the correct ordering
    	replace = patterns
    	replace['shortdesc'] = 'Correct collective ordering'
    	replace['longdesc'] = f'All ranks call {coll1} and then {coll2}'
    	replace['outcome'] = 'OK'
    	replace['errormsg'] = ''
    	make_file(template, f'CollCallOrder_{coll1}_{coll2}_ok.c', replace)

      # Generate the incorrect ordering
    	replace = patterns
    	replace['shortdesc'] = 'Incorrect collective ordering'
    	replace['longdesc'] = f'Odd ranks call {coll1} and then {coll2} while even ranks call these collectives in the other order'
    	replace['outcome'] = 'ERROR: CollectiveOrdering'
    	replace['errormsg'] = 'Collective mistmatch. @{coll1}@ at @{filename}@:@{line:MBIERROR1}@ is matched with @{coll2}@ line @{filename}@:@{line:MBIERROR2}@.'

    	replace['operation1b'] = operation[coll2]("1") # Inversion
    	replace['operation2b'] = operation[coll1]("2")
    	make_file(template, f'CollCallOrder_{coll1}_{coll2}_nok.c', replace)
