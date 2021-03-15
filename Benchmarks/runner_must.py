import shutil, os, sys, stat, subprocess, re, argparse

def mustrun(cmd, to, filename, binary, id, distributed=False):
    try:
        subprocess.run("mpicc {} -o {} > {}_{}.txt 2>&1".format(filename,binary,binary,id), shell=True, check=True)
    except subprocess.CalledProcessError:
        return 'CUN'
    if distributed:
        cmd = re.sub("mpirun", "mustrun --must:distributed", cmd)
    else:
        cmd = re.sub("mpirun", "mustrun", cmd)
    cmd = re.sub('\${EXE}', binary, cmd)
    cmd = re.sub('\$zero_buffer', "", cmd)
    cmd = re.sub('\$infty_buffer', "", cmd)	
    print("\nRUNNING : {}\n".format(cmd))
    ret = None	
    try:
        ret = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, timeout=to)
    except subprocess.TimeoutExpired:
        if not os.path.isfile("./MUST_Output.html"):   
            return 'timeout'
        else:
            print("Timeout but an output was found")

    if not os.path.isfile("./MUST_Output.html"):
        return 'RSF'
    os.rename("./MUST_Output.html", "{}_{}.txt".format(binary,id))        
            
    if int(subprocess.check_output("grep deadlock {}_{}.txt | wc -l".format(binary,id), shell=True)) > 0:
        return 'deadlock'
    
    elif int(subprocess.check_output("grep 'not freed' {}_{}.txt | wc -l".format(binary,id), shell=True)) > 0:
        return 'resleak'

    elif int(subprocess.check_output("grep 'conflicting roots' {}_{}.txt | wc -l".format(binary,id), shell=True)) > 0:
        return 'compliance'

    elif int(subprocess.check_output("grep 'unknown datatype' {}_{}.txt | wc -l".format(binary,id), shell=True)) > 0:
        return 'mpierr'
    elif int(subprocess.check_output("grep 'has to be a non-negative integer' {}_{}.txt | wc -l".format(binary,id), shell=True)) > 0:
        return 'mpierr'
    elif int(subprocess.check_output("grep 'must use equal type signatures' {}_{}.txt | wc -l".format(binary,id), shell=True)) > 0:
        return 'mpierr'
    
    elif ret!= None and ret.stdout!= None and re.search('caught MPI error', ret.stdout.decode('UTF-8')) != None:
        return 'mpierr'     
    
    elif int(subprocess.check_output("grep 'Error' {}_{}.txt | wc -l".format(binary,id), shell=True)) > 0:
        return 'other'

    elif ret!= None and ret.stderr!= None and re.search('MUST-ERROR', ret.stderr.decode('UTF-8')) != None:
        return 'RSF'
    
    else:
        return 'noerror'