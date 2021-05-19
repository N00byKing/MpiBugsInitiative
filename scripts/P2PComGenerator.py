#! /usr/bin/python3
import sys
from generator_utils import make_file

template = """// @{generatedby}@
/* ///////////////////////// The MPI Bugs Initiative ////////////////////////

  Origin: MBI

  Description: @{shortdesc}@
    @{longdesc}@

BEGIN_MPI_FEATURES
	P2P!basic: @{p2pfeature}@ 
	P2P!nonblocking: @{ip2pfeature}@
	P2P!persistent: @{persfeature}@
	P2P!probe: Lacking
	COLL!basic: Lacking
	COLL!nonblocking: Lacking
	COLL!persistent: Lacking
	COLL!probe: Lacking
	COLL!tools: Yes
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
	int src=0, dest=1;

  MPI_Init(&argc, &argv);
  MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  printf("Hello from rank %d \\n", rank);

  if (nprocs < 2)
    printf("MBI ERROR: This test needs at least 2 processes to produce a bug!\\n");
 
  MPI_Comm newcom; 
  MPI_Comm_split(MPI_COMM_WORLD, 0, nprocs - rank, &newcom);
  @{change_com}@
  @{change_srcdest}@

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

#SEND
send = ['MPI_Send'] 
isend = ['MPI_Isend'] 
perssend = ['MPI_Send_init']  
#RECV
recv = ['MPI_Recv'] 
irecv = ['MPI_Irecv']  
persrecv = ['MPI_Recv_init']  

init = {}
start = {}
operation = {}
fini = {}
free = {}

init['MPI_Send'] = lambda n: f'int buf{n}[buff_size];'
start['MPI_Send'] = lambda n: ""
operation['MPI_Send'] = lambda n: f'MPI_Send(buf{n}, buff_size, MPI_INT, dest, 0, newcom);'
fini['MPI_Send'] = lambda n: ""
free['MPI_Send'] = lambda n: ""

init['MPI_Recv'] = lambda n: f'int buf{n}[buff_size]; MPI_Status sta{n};'
start['MPI_Recv'] = lambda n: ""
operation['MPI_Recv'] = lambda n: f'MPI_Recv(buf{n}, buff_size, MPI_INT, src, 0, newcom, &sta{n});'
fini['MPI_Recv'] = lambda n: ""
free['MPI_Recv'] = lambda n: ""

init['MPI_Isend'] = lambda n: f'int buf{n}[buff_size]; MPI_Request req{n};'
start['MPI_Isend'] = lambda n: ""
operation['MPI_Isend'] = lambda n: f'MPI_Isend(buf{n}, buff_size, MPI_INT, dest, 0, newcom, &req{n});'
fini['MPI_Isend'] = lambda n: f'MPI_Wait(&req{n}, MPI_STATUS_IGNORE);'
free['MPI_Isend'] = lambda n: ""

init['MPI_Irecv'] = lambda n: f'int buf{n}[buff_size]; MPI_Request req{n};'
start['MPI_Irecv'] = lambda n: "" 
operation['MPI_Irecv'] = lambda n: f'MPI_Irecv(buf{n}, buff_size, MPI_INT, src, 0, newcom, &req{n});'
fini['MPI_Irecv'] = lambda n: f'MPI_Wait(&req{n}, MPI_STATUS_IGNORE);'
free['MPI_Irecv'] = lambda n: "" 

init['MPI_Send_init'] = lambda n: f'int buf{n}[buff_size]; MPI_Request req{n};'
operation['MPI_Send_init'] = lambda n: f'MPI_Send_init(buf{n}, buff_size, MPI_INT, dest, 0, newcom, &req{n});' 
start['MPI_Send_init'] = lambda n: f'MPI_Start(&req{n});'
fini['MPI_Send_init'] = lambda n: f'MPI_Wait(&req{n}, MPI_STATUS_IGNORE);'
free['MPI_Send_init'] = lambda n: f'MPI_Request_free(&req{n});'

init['MPI_Recv_init'] = lambda n: f'int buf{n}[buff_size]; MPI_Request req{n};'
start['MPI_Recv_init'] = lambda n: f'MPI_Start(&req{n});'
operation['MPI_Recv_init'] = lambda n: f'MPI_Recv_init(buf{n}, buff_size, MPI_INT, src, 0, newcom, &req{n});'
fini['MPI_Recv_init'] = lambda n: f'MPI_Wait(&req{n}, MPI_STATUS_IGNORE);'
free['MPI_Recv_init'] = lambda n: f'MPI_Request_free(&req{n});'


for p1 in send + isend + perssend:
    for p2 in recv + irecv + persrecv:
        patterns = {}
        patterns = {'p1': p1, 'p2': p2}
        patterns['generatedby'] = f'DO NOT EDIT: this file was generated by {sys.argv[0]}. DO NOT EDIT.'  
        patterns['p2pfeature'] = 'Yes' if p1 in send or p2 in recv  else 'Lacking'
        patterns['ip2pfeature'] = 'Yes' if p1 in isend or p2 in irecv  else 'Lacking' 
        patterns['persfeature'] = 'Yes' if p1 in perssend or p2 in persrecv  else 'Lacking' 
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
        patterns['change_srcdest'] = "" 

    		# Generate the incorrect matching 
        replace = patterns 
        replace['shortdesc'] = 'Point to point @{p1}@ and @{p2}@ have a communicator mismatch' 
        replace['longdesc'] = 'Process 1 uses newcom as the communicator while process 0 uses MPI_COMM_WORLD.' 
        replace['outcome'] = 'ERROR: CommunicatorMatching' 
        replace['errormsg'] = 'P2P Communicator mismatch. @{p1}@ at @{filename}@:@{line:MBIERROR1}@ and @{p2}@ at @{filename}@:@{line:MBIERROR2}@ have newcom or MPI_COMM_WORLD as a communicator.' 
        replace['change_com'] = 'if (rank==0)\n    newcom = MPI_COMM_WORLD; /* MBIERROR */'
        make_file(template, f'P2PComMatching_{p1}_{p2}_nok.c', replace)

    		# Generate the code with an invalid communicator 
        replace = patterns 
        replace['shortdesc'] = 'Point to point @{p1}@ and @{p2}@ have an invalid communicator' 
        replace['longdesc'] = 'Point to point @{p1}@ and @{p2}@ have an invalid communicator.' 
        replace['outcome'] = 'ERROR: InvalidCommunicator' 
        replace['errormsg'] = 'Invalid Communicator. @{p1}@ at @{filename}@:@{line:MBIERROR1}@ and @{p2}@ at @{filename}@:@{line:MBIERROR2}@ use a communicator that is freed line @{line:MBIERROR}@.' 
        replace['change_com'] = 'MPI_Comm_free(&newcom);  /* MBIERROR */'
        make_file(template, f'P2PInvalidCom_{p1}_{p2}_nok.c', replace)

    		# Generate the code with an invalid dest 
        replace = patterns 
        replace['shortdesc'] = 'Point to point @{p1}@ has an invalid argument' 
        replace['longdesc'] = 'Point to point @{p1}@ and @{p2}@ have an invalid communicator.' 
        replace['outcome'] = 'ERROR: InvalidSrcDest' 
        replace['errormsg'] = 'InvalidSrcDest. @{p1}@ at @{filename}@:@{line:MBIERROR1}@ performs a send with a dest not in communicator (dest is changed line @{line:MBIERROR}@).' 
        replace['change_com'] = ""
        replace['change_srcdest'] = 'dest=4; /* MBIERROR */'
        make_file(template, f'P2PInvalidDest_{p1}_{p2}_nok.c', replace)
    		# Generate the code with an invalid src 
        replace = patterns 
        replace['shortdesc'] = 'Point to point @{p2}@ has an invalid argument'
        replace['longdesc'] = 'Point to point @{p1}@ and @{p2}@ have an invalid communicator.' 
        replace['outcome'] = 'ERROR: InvalidSrcDest' 
        replace['errormsg'] = 'InvalidSrcDest. @{p2}@ at @{filename}@:@{line:MBIERROR2}@ performs a recv with a negative integer as source (src is changed line @{line:MBIERROR}@).' 
        replace['change_srcdest'] = 'src=-1; /* MBIERROR */'
        make_file(template, f'P2PInvalidSrc_{p1}_{p2}_nok.c', replace)