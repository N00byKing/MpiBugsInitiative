#! /usr/bin/python3
import sys
from generator_utils import make_file

template = """// @{generatedby}@
/* ///////////////////////// The MPI Bugs Initiative ////////////////////////

  Origin: MBI

  Description: @{shortdesc}@
    @{longdesc}@

BEGIN_MPI_FEATURES
	P2P!basic: Lacking
	P2P!nonblocking: Lacking
	P2P!persistent: Lacking
	COLL!basic: @{collfeature}@
	COLL!nonblocking: @{icollfeature}@
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

	int dbs = sizeof(int)*nprocs; /* Size of the dynamic buffers for alltoall and friends */  
	int root = 0;

  @{init}@
  @{change_root}@

  @{operation}@ 
	@{fini}@

  MPI_Finalize();
  printf("Rank %d finished normally\\n", rank);
  return 0;
}
"""

collectives = ['MPI_Bcast', 'MPI_Reduce', 'MPI_Gather', 'MPI_Scatter']
icollectives = ['MPI_Ireduce', 'MPI_Ibcast', 'MPI_Igather']

init = {}
operation = {}
fini = {}

init['MPI_Bcast'] = lambda n: f'int buf{n}[buff_size];'
operation['MPI_Bcast'] = lambda n: f'MPI_Bcast(&buf{n}, buff_size, MPI_INT, root, MPI_COMM_WORLD);'
fini['MPI_Bcast'] = lambda n: ""

init['MPI_Reduce'] = lambda n: f"int sum{n}, val{n} = 1;"
operation['MPI_Reduce'] = lambda n: f"MPI_Reduce(&sum{n}, &val{n}, 1, MPI_INT, MPI_SUM, root, MPI_COMM_WORLD);"
fini['MPI_Reduce'] = lambda n: ""

init['MPI_Gather'] = lambda n: f"int val{n}, buf{n}[buff_size];"
operation['MPI_Gather'] = lambda n: f"MPI_Gather(&val{n}, 1, MPI_INT, buf{n},1, MPI_INT, root, MPI_COMM_WORLD);"
fini['MPI_Gather'] = lambda n: ""

init['MPI_Scatter'] = lambda n: f"int val{n}, buf{n}[buff_size];"
operation['MPI_Scatter'] = lambda n: f"MPI_Scatter(&buf{n}, 1, MPI_INT, &val{n}, 1, MPI_INT, root, MPI_COMM_WORLD);"
fini['MPI_Scatter'] = lambda n: ""

init['MPI_Ireduce'] = lambda n: f"MPI_Request req{n}; MPI_Status sta{n}; int sum{n}, val{n} = 1;"
operation['MPI_Ireduce'] = lambda n: f"MPI_Ireduce(&sum{n}, &val{n}, 1, MPI_INT, MPI_SUM, root, MPI_COMM_WORLD, &req{n}); MPI_Wait(&req{n},&sta{n});"
fini['MPI_Ireduce'] = lambda n: ""

init['MPI_Ibcast'] = lambda n: f'int buf{n}[128]; MPI_Request req{n};MPI_Status sta{n};'
operation['MPI_Ibcast'] = lambda n: f'MPI_Ibcast(&buf{n}, buff_size, MPI_INT, root, MPI_COMM_WORLD, &req{n});MPI_Wait(&req{n},&sta{n});'
fini['MPI_Ibcast'] = lambda n: ""

init['MPI_Igather'] = lambda n: f"int val{n}, buf{n}[buff_size];MPI_Request req{n};MPI_Status sta{n};"
operation['MPI_Igather'] = lambda n: f"MPI_Igather(&val{n}, 1, MPI_INT, buf{n},1, MPI_INT, root, MPI_COMM_WORLD, &req{n}); MPI_Wait(&req{n},&sta{n});"
fini['MPI_Igather'] = lambda n: ""

# Generate code with one collective
for coll in collectives + icollectives:
    patterns = {}
    patterns = {'coll': coll}
    patterns['generatedby'] = f'DO NOT EDIT: this file was generated by {sys.argv[0]}. DO NOT EDIT.'
    patterns['collfeature'] = 'Yes' if coll in collectives else 'Lacking'
    patterns['icollfeature'] = 'Yes' if coll in icollectives else 'Lacking'
    patterns['coll'] = coll
    patterns['init'] = init[coll]("1")
    patterns['fini'] = fini[coll]("1")
    patterns['operation'] = operation[coll]("1")
    patterns['change_root'] = '' 

    # Generate the correct code ==> to remove?
    replace = patterns
    replace['shortdesc'] = 'Collective @{coll}@ with correct arguments'
    replace['longdesc'] = f'All ranks in MPI_COMM_WORLD call {coll} with correct arguments'
    replace['outcome'] = 'OK'
    replace['errormsg'] = ''
    replace['change_root'] = '/* No error injected here */'
    make_file(template, f'CollCorrect_{coll}.c', replace)

    # Generate an incorrect root matching
    replace = patterns
    replace['shortdesc'] = 'Collective @{coll}@ with a root mismatch' 
    replace['longdesc'] = f'Odd ranks use 0 as a root while even ranks use 1 as a root' 
    replace['outcome'] = 'ERROR: RootMatching' 
    replace['errormsg'] = 'Collective root mistmatch. @{coll}@ at @{filename}@:@{line:MBIERROR}@ has 0 or 1 as a root.' 
    replace['change_root'] = 'if (rank % 2)\n		root = 1; /* MBIERROR */'
    make_file(template, f'CollRootMatching_{coll}_nok.c', replace)

    # Generate the call with root=-1 
    replace = patterns
    replace['shortdesc'] = f'Collective {coll} with root = -1'
    replace['longdesc'] = f'Collective {coll} with root = -1'
    replace['outcome'] = 'ERROR: InvalidRoot'
    replace['errormsg'] = 'Invalid collective root.  @{coll}@ at @{filename}@:@{line:MBIERROR}@ has -1 as a root while communicator MPI_COMM_WORLD requires ranks in range 0 to 1.'
    replace['change_root'] = 'root = -1; /* MBIERROR */'
    make_file(template, f'CollRootNeg_{coll}_nok.c', replace)

    # Generate the call with root=2 
    replace = patterns
    replace['shortdesc'] = f'Collective {coll} with root out of the communicator'
    replace['longdesc'] = f'Collective {coll} with root = 2 (there is only 2 ranks)'
    replace['outcome'] = 'ERROR: InvalidRoot'
    replace['errormsg'] = 'Invalid collective root.  @{coll}@ at @{filename}@:@{line:MBIERROR}@ has 2 as a root while communicator MPI_COMM_WORLD requires ranks in range 0 to 1.' 
    replace['change_root'] = 'root = nprocs; /* MBIERROR */'
    make_file(template, f'CollRootTooLarge_{coll}_nok.c', replace)
