import sys

from libs.testrail.testrail_misc import TestRailMisc

tr_misc = TestRailMisc()

closed_runs = tr_misc.close_runs_by_name(sys.argv[1])

if len(closed_runs) == 0:
    print("No runs to close were found")
else:
    print("Closed {} runs:".format(len(closed_runs)))
    for run_record in closed_runs:
        print(run_record["url"])

