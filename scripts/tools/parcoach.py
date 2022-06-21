import re
import os
from MBIutils import *

class Tool(AbstractTool):
    def identify(self):
        return "PARCOACH wrapper"

    def ensure_image(self):
        AbstractTool.ensure_image(self, "-x parcoach")

    def build(self, rootdir, cached=True):
        if cached and os.path.exists(f"{rootdir}/builds/parcoach/src/aSSA/aSSA.so"):
            print("No need to rebuild ParCoach.")
            return

        here = os.getcwd() # Save where we were
        os.chdir(rootdir)
        # Get a GIT checkout. Either create it, or refresh it
        if os.path.exists("tools/parcoach/.git"):
            subprocess.run("cd tools/parcoach && git pull &&  cd ../..", shell=True, check=True)
        else:
            subprocess.run("rm -rf tools/parcoach && git clone --depth=1 https://github.com/N00byKing/parcoach.git --branch=llvm13_compat tools/parcoach", shell=True, check=True)

        # Go to where we want to install it, and build it out-of-tree (we're in the docker)
        subprocess.run(f"rm -rf {rootdir}/builds/parcoach && mkdir -p {rootdir}/builds/parcoach", shell=True, check=True)
        os.chdir(f'{rootdir}/builds/parcoach')
        subprocess.run(f"cmake {rootdir}/tools/parcoach -DCMAKE_C_COMPILER=clang-13 -DLLVM_DIR={rootdir}/tools/Parcoach/llvm-project/build", shell=True, check=True)
        subprocess.run("make -j$(nproc) VERBOSE=1", shell=True, check=True)

        # Back to our previous directory
        os.chdir(here)

    def run(self, execcmd, filename, binary, id, timeout, batchinfo):
        cachefile = f'{binary}_{id}'

        run_cmd(
            buildcmd=f"clang-13 -c -g -emit-llvm {filename} -I/usr/lib/x86_64-linux-gnu/mpich/include/ -o {binary}.bc",
            execcmd=f"opt-13 -enable-new-pm=0 -load ../../builds/parcoach/src/aSSA/aSSA.so -parcoach -check-mpi {binary}.bc -o /dev/null",
            cachefile=cachefile,
            filename=filename,
            binary=binary,
            timeout=timeout,
            batchinfo=batchinfo)

        subprocess.run("rm -f *.bc core", shell=True, check=True)

    def parse(self, cachefile):
        if os.path.exists(f'{cachefile}.timeout') or os.path.exists(f'logs/parcoach/{cachefile}.timeout'):
            outcome = 'timeout'
        if not (os.path.exists(f'{cachefile}.txt') or os.path.exists(f'logs/parcoach/{cachefile}.txt')):
            return 'failure'

        with open(f'{cachefile}.txt' if os.path.exists(f'{cachefile}.txt') else f'logs/parcoach/{cachefile}.txt', 'r') as infile:
            output = infile.read()

        if re.search('MBI_MSG_RACE', output):
            return 'MBI_MSG_RACE'

        if re.search('Compilation of .*? raised an error \(retcode: ', output):
            return 'UNIMPLEMENTED'

        if re.search('0 warning\(s\) issued', output):
            return 'OK'

        if re.search('missing info for external function', output):
            return 'UNIMPLEMENTED'

        return 'deadlock'
