import re
import os
from MBIutils import *

class Tool(AbstractTool):
    def identify(self):
        return "CIVL wrapper"

    def ensure_image(self):
        AbstractTool.ensure_image(self, "-x civl")

    def build(self, rootdir, cached=True):
        if cached and os.path.exists("/root/.sarl"):
            return
        subprocess.run(f"cd {rootdir}/tools/CIVL-1.21_5476/lib && java -jar civl-1.21_5476.jar config", shell=True, check=True)
 
    def run(self, execcmd, filename, binary, id, timeout, batchinfo):
        cachefile = f'{binary}_{id}'

        execcmd = re.sub("mpirun", "java -jar ../../tools/CIVL-1.21_5476/lib/civl-1.21_5476.jar verify", execcmd)
        execcmd = re.sub('-np ', "-input_mpi_nprocs=", execcmd)
        execcmd = re.sub('\${EXE}', filename, execcmd)
        execcmd = re.sub('\$zero_buffer', "", execcmd)
        execcmd = re.sub('\$infty_buffer', "", execcmd)


        if run_cmd(buildcmd=None,
                   execcmd=execcmd,
                   cachefile=cachefile,
                   filename=filename,
                   binary=binary,
                   timeout=timeout,
                   batchinfo=batchinfo):
            # the test was actually run
            subprocess.run("killall -9 java 2>/dev/null", shell=True)


    def parse(self, cachefile):
        if os.path.exists(f'{cachefile}.timeout') or os.path.exists(f'logs/civl/{cachefile}.timeout'):
            outcome = 'timeout'
        if not (os.path.exists(f'{cachefile}.txt') or os.path.exists(f'logs/civl/{cachefile}.txt')):
            return 'failure'

        with open(f'{cachefile}.txt' if os.path.exists(f'{cachefile}.txt') else f'logs/civl/{cachefile}.txt', 'r') as infile:
            output = infile.read()

        if re.search('Compilation of .*? raised an error \(retcode: ', output):
            return 'UNIMPLEMENTED'
        if re.search("cannot be invoked without MPI_Init\(\) being called before", output):
            return 'mpierr'

        if re.search('DEADLOCK', output):
            return 'deadlock'

        if re.search('MBI_MSG_RACE', output):
            return 'MBI_MSG_RACE'

        if re.search('reaches an MPI collective routine .*? while at least one of others are collectively reaching MPI_', output):
            return 'collective mismatch'
        if re.search('which has an inconsistent datatype specification with at least one of others', output):
            return 'datatype mismatch'
        if re.search('of MPI routines is not consistent with the specified MPI_Datatype', output):
            return 'datatype mismatch'
        if re.search('which has a different root with at least one of others', output):
            return 'root mismatch'
        if re.search('has a different MPI_Op', output):
            return 'various'

        if re.search('MPI message leak', output):
            return 'resleak'

        if re.search('MEMORY_LEAK', output):
            return 'resleak'

        if re.search('The standard properties hold for all executions', output):
            return 'OK'

        if re.search('A CIVL internal error has occurred', output):
            return 'failure'

        if re.search('kind: UNDEFINED_VALUE, certainty: MAYBE', output) or re.search('kind: UNDEFINED_VALUE, certainty: PROVEABLE', output):
            return 'UNDEFINED_VALUE'
        if re.search('kind: DEREFERENCE, certainty: MAYBE', output) or re.search('kind: DEREFERENCE, certainty: PROVEABLE', output):
            return 'DEREFERENCE'
        if re.search('kind: MPI_ERROR, certainty: MAYBE', output) or re.search('kind: MPI_ERROR, certainty: PROVEABLE', output):
            return 'MPI_ERROR'

        if re.search('This feature is not yet implemented', output):
            return 'UNIMPLEMENTED'
        if re.search('doesn.t have a definition', output):
            return 'UNIMPLEMENTED'
        if re.search('Undeclared identifier', output):
            return 'UNIMPLEMENTED'

        # The following is categorized as a CIVL bug, because it reports an inexistant error when a communicator is tested for inequality 
        #
        # Error: Incompatible types for operator NEQ:
        # struct MPI_Comm
        # struct MPI_Comm
        # at CollInvalidDim_Cart_create_nok.c:67.7-27
        # if (comm != MPI_COMM_NULL)
        #     ^^^^^^^^^^^^^^^^^^^^^
        if re.search('Error: Incompatible types for operator NEQ:\nstruct MPI_Comm\nstruct MPI_Comm\nat', output):
            return 'failure'
        
        #  $ java -jar ../../tools/CIVL-1.21_5476/lib/civl-1.21_5476.jar verify -input_mpi_nprocs=2 /MBI/gencodes/CollOpNull_Reduce_nok.c
        # CIVL v1.20 of 2019-09-27 -- http://vsl.cis.udel.edu/civl
        # Hello from rank 0 
        # Hello from rank 1 
        # Exception in thread "main" java.lang.ArrayIndexOutOfBoundsException: Index -1 out of bounds for length 16
        #        at edu.udel.cis.vsl.civl.library.common.LibraryComponent.translateOperator(LibraryComponent.java:544)
        # (REPORTED to the CIVL authos on June 18 2021)
        if re.search('Exception in thread "main" java.lang.ArrayIndexOutOfBoundsException', output):
            return 'failure'

        print (f">>>>[ INCONCLUSIVE ]>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ({cachefile})")
        print(output)
        print ("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        return 'other'
