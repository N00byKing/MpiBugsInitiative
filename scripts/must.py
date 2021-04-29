import re
import os
from MBIutils import *

def must_filter(line, process):
    if re.search("ERROR: MUST detected a deadlock", line):
        pid = process.pid
        pgid = os.getpgid(pid)
        try:
            process.terminate()
            # Send the signal to all the processes in the group. The command and everything it forked
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass  # Ok, it's gone now

class Tool(AbstractTool):
    def run(self, execcmd, filename, binary, id, timeout):
        cachefile = f'{binary}_{id}'

        execcmd = re.sub("mpirun", "mustrun --must:distributed", execcmd)
        execcmd = re.sub('\${EXE}', binary, execcmd)
        execcmd = re.sub('\$zero_buffer', "", execcmd)
        execcmd = re.sub('\$infty_buffer', "", execcmd)

        subprocess.run("killall -9 mpirun 2>/dev/null", shell=True)

        run_cmd(
            buildcmd=f"mpicc {filename} -o {binary}",
            execcmd=execcmd,
            cachefile=cachefile,
            binary=binary,
            timeout=timeout,
            read_line_lambda=must_filter)

        if os.path.isfile("./MUST_Output.html"):
            os.rename(f"./MUST_Output.html", f"{cachefile}.html")

    def parse(self, cachefile):
        # do not report timeouts ASAP, as MUST still deadlocks when it detects a root mismatch
        if not os.path.exists(f'{cachefile}.txt') or not os.path.exists(f'{cachefile}.html'):
            return 'failure'

        with open(f'{cachefile}.html', 'r') as infile:
            html = infile.read()

        if re.search('deadlock', html):
            return 'deadlock'

        if re.search('not freed', html):
            return 'resleak'

        if re.search('conflicting roots', html):
            return 'various'

        if re.search('unknown datatype', html) or re.search('has to be a non-negative integer', html) or re.search('must use equal type signatures', html):
            return 'mpierr'

        with open(f'{cachefile}.txt', 'r') as infile:
            output = infile.read()

        if re.search('caught MPI error', output):
            return 'mpierr'

        if re.search('Error', html):
            return 'mpierr'

        # No interesting output found, so return the timeout as is if it exists
        if os.path.exists(f'{cachefile}.timeout'):
            return 'timeout'

        return 'OK' # This is dangerous to trust the tool that much