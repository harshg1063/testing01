# Use to Copy Gotham Build from Linux to all target Windows machines
import logging
import os
import subprocess
import sys


def scp_file(build, target_windows):
    p = subprocess.Popen(f"scp -r /work/{build} exec@{target_windows}:C:/Users/exec/Desktop/", shell=True)
    sts = os.waitpid(p.pid, 0)
    #print(sts)

windows_list = [
    "tgtwin5d",
    "tgtwin6d",
    "tgtwin7d",
    "tgtwin8d",
    "tgtwin10p",
    "tgtwin11i",
    "tgtwin12p",
    "tgtwin13i",
    "tgtwin14p",
    "tgtwin15i",
    "tgtwin16p",
    "tgtwin17i",
    "tgtwin18p",
    "tgtwin19i",
    "tgtwin20p",
    "tgtwin21i",
    "tgtwin22p",
    "tgtwin23i",
    "tgtwin24p",
    "tgtwin25i",
    "tgtwin10m",
    "tgtwin11m",
    "tgtwin13m"
]

#Pass the build folder name here
build = sys.argv[1]

for target in windows_list:
    try:
        scp_file(build, target)
        print("--------------------------------------------------------------")
        print(f"{build} transfer to {target} successfully\n\n")
    except Exception as e:
        logging.warning(f"Failed to transfer build to the target windows {target}: " + str(e))
