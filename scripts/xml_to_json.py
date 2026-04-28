import argparse
import copy
import json
import os
import uuid
from pprint import pprint

import untangle

class SuiteFailedException(Exception):
    pass

class MissingRequiredProperty(Exception):
    pass

schema_version = "1"
data_env = "RealData"
performance = False
required_property = ["suite_test_platform", "suite_test_stack", "suite_test_client", "suite_test_category"]
parser = argparse.ArgumentParser(description='Convert Junit XML to Dashboard json')
parser.add_argument('-f', dest='file_name', action='store', help='The XML file path')
parser.add_argument('-t', dest="testing", action="store_true", help="Testing, skip publication")

def send_payload(json_data):
    if not args.testing:
        fh = open(str(uuid.uuid4()) + ".json", "w+", encoding="utf-8")
        fh.write(json.dumps(json_data))
        file_path = os.path.realpath(fh.name)
        fh.close()

        os.system(hook_file_path + " " + file_path)
        os.remove(file_path)
    else:
        pprint(json_data)

args = parser.parse_args()
json_data = {"event": {}}
data = untangle.parse(args.file_name)
hook_file_path = "/qama/framework/bin/report_results"

json_data["event"]["host"] = data.testsuites.testsuite["hostname"]
json_data["event"]["timestamp"] = data.testsuites.testsuite["timestamp"]
json_data["event"]["schema_version"] = schema_version
json_data["event"]["suite_test_env"] = data_env
json_data["event"]["suite_test_owner"] = "QAMA Mobile/Web Test Automation"

for _property in data.testsuites.testsuite.properties.property:
    if _property["name"] == "performance":
        performance = _property["value"] == "True"
        continue
    json_data["event"][_property["name"]] = _property["value"]

if not set(required_property).issubset(set(json_data["event"])):
    raise MissingRequiredProperty("Missing these required property: " + str(set(required_property).difference(json_data["event"])))

pass_percentage = 1 - (int(data.testsuites.testsuite["errors"]) + int(data.testsuites.testsuite["failures"])) / int(data.testsuites.testsuite["tests"])
if not performance:
    json_data["event"]["suite_test_result"] = "success" if pass_percentage == 1 else "failed"
    json_data["event"]["suite_test_percentage_of_success"] = str(round(pass_percentage * 100, 2)) + "%"

elif performance and pass_percentage != 1:
    pass
    #raise SuiteFailedException("Failed performance run does not capture data")

if performance:
    testcase_data = {"performance":{}}
else:
    testcase_data = {}
    
for testcase in data.testsuites.testsuite.testcase:
    testcase_data["suite_test_name"] = testcase["classname"]
    testcase_data["suite_test_script_name"] = testcase["file"]
    if performance:
        testcase_data["suite_testcase_name"] = testcase["name"]
        system_error = testcase.system_err.cdata.split("\n")
        for line in system_error:
            if "[Performance]" in line:
                performance_fields = line.split("->")
                if performance_fields[1] in testcase_data["suite_testcase_name"]:
                    testcase_data["performance"][performance_fields[2]] = performance_fields[3]
            
        payload_data = copy.copy(json_data)
        payload_data["event"].update(testcase_data)
        send_payload(payload_data)

if not performance: 
    json_data["event"].update(testcase_data)
    send_payload(json_data)