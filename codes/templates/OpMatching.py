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

#define buff_size 128

int main(int argc, char **argv) {
  int nprocs = -1;
  int rank = -1;

  MPI_Init(&argc, &argv);
  MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  printf("Hello from rank %d \\n", rank);

  if (nprocs < 2)
    printf("MBI ERROR: This test needs at least 2 processes to produce a bug!\\n");

  MPI_Op op = MPI_SUM;
  @{change_op}@

  @{init}@
  @{operation}@ /* MBIERROR */

  MPI_Finalize();
  printf("Rank %d finished normally\\n", rank);
  return 0;
}
"""

collectives = ['MPI_Reduce', 'MPI_Allreduce']
icollectives = []  # 'ireduce']

init = {}
operation = {}

init['MPI_Reduce'] = lambda n: f"int sum{n}, val{n} = 1;"
operation['MPI_Reduce'] = lambda n: f"MPI_Reduce(&sum{n}, &val{n}, 1, op, MPI_SUM, 0, MPI_COMM_WORLD);"

init['MPI_Allreduce'] = lambda n: f"int sum{n}, val{n} = 1;"
operation['MPI_Allreduce'] = lambda n: f"MPI_Allreduce(&sum{n}, &val{n}, 1, MPI_INT, op, MPI_COMM_WORLD);"

for coll in collectives + icollectives:
    patterns = {}
    patterns = {'coll': coll}
    patterns['generatedby'] = f'DO NOT EDIT: this file was generated by {sys.argv[0]}. DO NOT EDIT.'
    patterns['collfeature'] = 'Correct' if coll in collectives else 'Lacking'
    patterns['icollfeature'] = 'Correct' if coll in icollectives else 'Lacking'
    patterns['coll'] = coll
    patterns['init'] = init[coll]("1")
    patterns['operation'] = operation[coll]("1")

    # Generate the correct code => the same code is generated from ComMatching.py
   # replace = patterns
   # replace['shortdesc'] = 'Collective @{coll}@ with a correct operator'
   # replace['longdesc'] = f'All ranks call {coll} with the same operator'
   # replace['outcome'] = 'OK'
   # replace['errormsg'] = ''
   # replace['change_op'] = '/* No error injected here */'
   # make_file(template, f'CollOpMatching_{coll}_ok.c', replace)

    # Generate the incorrect matching
    replace = patterns
    replace['shortdesc'] = 'Collective @{coll}@ with an operator  mismatch'
    replace['longdesc'] = f'Odd ranks use MPI_SUM as the operator while even ranks use MPI_MAX'
    replace['outcome'] = 'ERROR: OpMismatch'
    replace['errormsg'] = 'Collective operator mistmatch. @{coll}@ at @{filename}@:@{line:MBIERROR}@ has MPI_MAX or MPI_SUM as an operator.'
    replace['change_op'] = 'if (rank % 2)\n    op = MPI_MAX;'
    make_file(template, f'CollOpMatching_{coll}_nok.c', replace)
