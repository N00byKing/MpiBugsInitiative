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
	P2P!nonblocking: @{ip2pfeature}@
	P2P!persistent: @{persfeature}@
	COLL!basic: Lacking
	COLL!nonblocking: @{icollfeature}@
	COLL!persistent: @{cpersfeature}@
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

  int dest = (rank == nprocs - 1) ? (0) : (rank + 1);
  int src = (rank == 0) ? (nprocs - 1) : (rank - 1); 

  @{init1}@
  @{init2}@

  @{operation1}@ /* MBIERROR */ 
  @{start1}@
  @{operation2}@ 
  @{start2}@

	@{fini1}@ 
	@{fini2}@  

	@{free1}@
	@{free2}@

  MPI_Finalize();
  printf("Rank %d finished normally\\n", rank);
  return 0;
}
"""

#SEND
isend = ['MPI_Isend']  
perssend = ['MPI_Send_init']  
#RECV
irecv = ['MPI_Irecv']  
persrecv = ['MPI_Recv_init']  
#COLL
pers=[]
#icoll=['MPI_Ireduce', 'MPI_Ibarrier']
icoll=['MPI_Ireduce']

init = {}
start = {}
operation = {}
fini = {}
free = {}


init['MPI_Send_init'] = lambda n: f'int buf{n}[buff_size]; MPI_Request req{n};'
operation['MPI_Send_init'] = lambda n: f'MPI_Send_init(buf{n}, buff_size, MPI_INT, dest, 0, MPI_COMM_WORLD, &req{n});' 
start['MPI_Send_init'] = lambda n: f'MPI_Start(&req{n});'
fini['MPI_Send_init'] = lambda n: f'MPI_Wait(&req{n}, MPI_STATUS_IGNORE);'
free['MPI_Send_init'] = lambda n: f'if(req{n} != MPI_REQUEST_NULL) MPI_Request_free(&req{n});'

init['MPI_Isend'] = lambda n: f'int buf{n}[buff_size]; MPI_Request req{n};'
start['MPI_Isend'] = lambda n: "" 
operation['MPI_Isend'] = lambda n: f'MPI_Isend(buf{n}, buff_size, MPI_INT, dest, 0, MPI_COMM_WORLD, &req{n});'
fini['MPI_Isend'] = lambda n: f'MPI_Wait(&req{n}, MPI_STATUS_IGNORE);'
free['MPI_Isend'] = lambda n: f'if(req{n} != MPI_REQUEST_NULL) MPI_Request_free(&req{n});'

init['MPI_Irecv'] = lambda n: f'int buf{n}[buff_size]; MPI_Request req{n};'
start['MPI_Irecv'] = lambda n: "" 
operation['MPI_Irecv'] = lambda n: f'MPI_Irecv(buf{n}, buff_size, MPI_INT, src, 0, MPI_COMM_WORLD, &req{n});'
fini['MPI_Irecv'] = lambda n: f' MPI_Wait(&req{n}, MPI_STATUS_IGNORE);'
free['MPI_Irecv'] = lambda n: f'if(req{n} != MPI_REQUEST_NULL) MPI_Request_free(&req{n});'

init['MPI_Recv_init'] = lambda n: f'int buf{n}[buff_size]; MPI_Request req{n};'
start['MPI_Recv_init'] = lambda n: f'MPI_Start(&req{n});'
operation['MPI_Recv_init'] = lambda n: f'MPI_Recv_init(buf{n}, buff_size, MPI_INT, src, 0, MPI_COMM_WORLD, &req{n});'
fini['MPI_Recv_init'] = lambda n: f'MPI_Wait(&req{n}, MPI_STATUS_IGNORE);'
free['MPI_Recv_init'] = lambda n: f'if(req{n} != MPI_REQUEST_NULL) MPI_Request_free(&req{n});'

init['MPI_Ireduce'] = lambda n: f'MPI_Request req{n}; MPI_Status sta{n}; int sum{n}, val{n} = 1;'
start['MPI_Ireduce'] = lambda n: "" 
operation['MPI_Ireduce'] = lambda n: f'MPI_Ireduce(&sum{n}, &val{n}, 1, MPI_INT, MPI_SUM, 0, MPI_COMM_WORLD, &req{n});'
fini['MPI_Ireduce'] = lambda n: f'MPI_Wait(&req{n},&sta{n});'
free['MPI_Ireduce'] = lambda n: f'if(req{n} != MPI_REQUEST_NULL) MPI_Request_free(&req{n});'

init['MPI_Ibarrier'] = lambda n: f'MPI_Request req{n}; MPI_Status sta{n};'
start['MPI_Ibarrier'] = lambda n: "" 
operation['MPI_Ibarrier'] = lambda n: f'MPI_Ibarrier(MPI_COMM_WORLD, &req{n});'
fini['MPI_Ibarrier'] = lambda n: f'MPI_Wait(&req{n},&sta{n});'
free['MPI_Ibarrier'] = lambda n: f'if(req{n} != MPI_REQUEST_NULL) MPI_Request_free(&req{n});'

for s in isend + perssend:
    for r in irecv + persrecv:
        patterns = {}
        patterns = {'s': s, 'r': r}
        patterns['generatedby'] = f'DO NOT EDIT: this file was generated by {sys.argv[0]}. DO NOT EDIT.'  
        patterns['persfeature'] = 'Yes' if s in perssend or r in persrecv  else 'Lacking'
        patterns['ip2pfeature'] = 'Yes' if s in isend or r in irecv  else 'Lacking' 
        patterns['icollfeature'] = 'Lacking' 
        patterns['cpersfeature'] = 'Lacking' 
        patterns['s'] = s 
        patterns['r'] = r 
        patterns['init1'] = init[s]("1") 
        patterns['init2'] = init[r]("2") 
        patterns['start1'] = start[s]("1") 
        startPers = patterns['start1'] 
        patterns['start2'] = start[r]("2")
        patterns['operation1'] = operation[s]("1") 
        patterns['operation2'] = operation[r]("2") 
        patterns['fini1'] = fini[s]("1") 
        wait = patterns['fini1'] 
        patterns['fini2'] = fini[r]("2") 
        patterns['free1'] = free[s]("1") 
        Reqfree = patterns['free1'] 
        patterns['free2'] = free[r]("2") 

				# Generate the correct code
        replace = patterns 
        replace['shortdesc'] = 'Correct matching' 
        replace['longdesc'] = f'No error'
        replace['outcome'] = 'OK' 
        replace['errormsg'] = 'OK' 
        make_file(template, f'P2PCallMatching_{s}_{r}_ok.c', replace)

				# Generate the code with a missing wait
        replace = patterns 
        replace['shortdesc'] = 'Missing wait' 
        replace['longdesc'] = 'Missing Wait. @{s}@ at @{filename}@:@{line:MBIERROR}@ has no completion.' 
        replace['outcome'] = 'ERROR: MissingWait' 
        replace['errormsg'] = 'ERROR: MissingWait' 
        replace['fini1'] =  ' /* MBIERROR MISSING: ' + wait + ' */' 
        make_file(template, f'MissingWait_{s}_{r}_nok.c', replace)
		
        if s in perssend:
			  		# Generate the code with a missing start - persistent only
            replace = patterns
            replace['shortdesc'] = 'Missing start'
            replace['longdesc'] = 'Missing start. @{s}@ at @{filename}@:@{line:MBIERROR}@ has no start'
            replace['outcome'] = 'ERROR: MissingStart'
            replace['errormsg'] = 'ERROR: MissingStart'
            replace['fini1'] = fini[s]("1")
            replace['start1'] = ' /* MBIERROR MISSING: ' + startPers + ' */'
            make_file(template, f'MissingStart_{s}_{r}_nok.c', replace) 
			  		# Generate the code with a missing free - persistent only
            replace = patterns
            replace['shortdesc'] = 'Missing free'
            replace['longdesc'] = 'Missing free. @{s}@ at @{filename}@:@{line:MBIERROR}@ has no free'
            replace['outcome'] = 'ERROR: RequestLeak'
            replace['errormsg'] = 'ERROR: RequestLeak'
            replace['start1'] = start[s]("1")
            replace['free1'] = ' /* MBIERROR MISSING: ' + Reqfree + ' */'
            make_file(template, f'RequestLeak_{s}_{r}_nok.c', replace) 


# Collectives only
for c in pers + icoll:
    patterns = {}
    patterns = {'c': c}
    patterns['generatedby'] = f'DO NOT EDIT: this file was generated by {sys.argv[0]}. DO NOT EDIT.'
    patterns['persfeature'] = 'Lacking'
    patterns['ip2pfeature'] = 'Lacking'
    patterns['cpersfeature'] = 'Yes' if c in pers else 'Lacking'
    patterns['icollfeature'] = 'Yes' if c in icoll else 'Lacking'
    patterns['c'] = c
    patterns['init1'] = init[c]("1")
    patterns['operation1'] = operation[c]("1")
    patterns['start1'] = start[c]("1") 
    patterns['fini1'] = fini[c]("1")
    patterns['free1'] = free[c]("1")
    start = patterns['start1']
    wait = patterns['fini1'] 
    free = patterns['free1'] 
    patterns['init2'] = ""
    patterns['operation2'] = ""
    patterns['start2'] = ""
    patterns['fini2'] = "" 
    patterns['free2'] = "" 

		# Generate the code with a missing wait 
    replace = patterns
    replace['shortdesc'] = 'Missing wait'
    replace['longdesc'] = 'Missing Wait. @{c}@ at @{filename}@:@{line:MBIERROR}@ has no completion' 
    replace['outcome'] = 'ERROR: MissingWait'
    replace['errormsg'] = 'ERROR: MissingWait'
    replace['fini1'] = ' /* MBIERROR MISSING: ' + wait + ' */' 
    make_file(template, f'MissingWait_{c}_nok.c', replace)

    if c in pers:		
			  # Generate the code with a missing start - persistent only
        replace = patterns 
        replace['shortdesc'] = 'Missing start functio' 
        replace['longdesc'] = 'Missing Start. @{c}@ at @{filename}@:@{line:MBIERROR}@ has no start' 
        replace['outcome'] = 'ERROR: MissingStart'
        replace['errormsg'] = 'ERROR: MissingStart'
        replace['fini1'] = fini[c]("1") 
        replace['start1'] = ' /* MBIERROR MISSING: ' + start + ' */' 
        make_file(template, f'MissingStart_{c}_nok.c', replace)

			  # Generate the code with a resleak (no free) - persistent only
        replace = patterns
        replace['shortdesc'] = 'Missing free'
        replace['longdesc'] = 'Missing free. @{c}@ at @{filename}@:@{line:MBIERROR}@ has no free' 
        replace['outcome'] = 'ERROR: RequestLeak'
        replace['errormsg'] = 'ERROR: RequestLeak'
        replace['start1'] = start[c]("1")
        replace['free1'] = ' /* MBIERROR MISSING: ' + free + ' */' 
        make_file(template, f'RequestLeak_{c}_nok.c', replace)
