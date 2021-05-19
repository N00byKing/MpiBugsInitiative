import re
import os
import sys
from MBIutils import *

class Tool(AbstractTool):
    def ensure_image(self):
        id = subprocess.run("source /etc/os-release && echo $ID", shell=True, capture_output=True)
        ver = subprocess.run("source /etc/os-release && echo $VERSION_ID", shell=True, capture_output=True)
        if id.stdout == "ubuntu" and ver.stdout == "18.04":
            print("This is an Ubuntu 18.04 OS. Good.")
        else:
            print("Please run this script in a ubuntu:18.04 image. Run these commands:")
            print("  docker image pull ubuntu:18.04")
            print("  docker run -it --rm --name MIB --volume $(pwd):/MBI ubuntu:18.04 /MBI/MBI.py -x aislinn")
            sys.exit(1)

    def run(self, execcmd, filename, binary, id, timeout):
        cachefile = f'{binary}_{id}'

        execcmd = re.sub("mpirun", "aislinn", execcmd)
        execcmd = re.sub('\${EXE}', binary, execcmd)
        execcmd = re.sub('\$zero_buffer', "--send-protocol=rendezvous", execcmd)
        execcmd = re.sub('\$infty_buffer', "--send-protocol=eager", execcmd)
        execcmd = re.sub('-np ', '-p=', execcmd)

        run_cmd(
            buildcmd=f"aislinn-cc -g {filename} -o {binary}",
            execcmd=execcmd,
            cachefile=cachefile,
            binary=binary,
            timeout=timeout)

        if os.path.exists("./report.html"):
            os.rename("./report.html", f"{binary}_{id}.html")

    def parse(self, cachefile):
        if os.path.exists(f'{cachefile}.timeout'):
            outcome = 'timeout'
        if not os.path.exists(f'{cachefile}.txt'):
            return 'failure'

        with open(f'{cachefile}.txt', 'r') as infile:
            output = infile.read()

        if re.search('No errors found', output):
            return 'OK'

        if re.search('Deadlock', output):
            return 'deadlock'
        if re.search('Collective operation mismatch', output):
            return 'deadlock'
        if re.search('Mixing blocking and nonblocking collective operation', output):
            return 'deadlock'
        if re.search('Pending message', output):
            return 'deadlock'

        if re.search('Invalid rank', output):
            return 'mpierr'
        if re.search('Invalid datatype', output):
            return 'mpierr'
        if re.search('Invalid communicator', output):
            return 'mpierr'
        if re.search('Invalid color', output):
            return 'mpierr'
        if re.search('Invalid operation', output):
            return 'mpierr'
        if re.search('Invalid count', output):
            return 'mpierr'

        if re.search('Collective operation: root mismatch', output):
            return 'various'

        if re.search('Unkown function call', output):
            return 'UNIMPLEMENTED'

        return 'other'
