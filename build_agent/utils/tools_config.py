# Copyright (2025) Bytedance Ltd. and/or its affiliates 

# Licensed under the Apache License, Version 2.0 (the "License"); 
# you may not use this file except in compliance with the License. 
# You may obtain a copy of the License at 

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software 
# distributed under the License is distributed on an "AS IS" BASIS, 
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
# See the License for the specific language governing permissions and 
# limitations under the License. 


from enum import Enum
class Tools(Enum):
    waiting_list_add = {
        "command": "waitinglist add -p package_name -t apt [-v version_constraints]",
        "description": "Add item into waiting list using apt-get. The -t apt flag is REQUIRED. Version constraints are optional (defaults to latest)."
    }
    waiting_list_add_file = {
        "command": "waitinglist addfile file_path",
        "description": "Add all entries from a file similar to requirements.txt format to the waiting list."
    }
    waiting_list_clear = {
        "command": "waitinglist clear",
        "description": "Used to clear all the items in the waiting list."
    }
    waiting_list_show = {
        "command": "waitinglist show",
        "description": "Used to show all the items in the waiting list."
    }
    conflict_solve_u = {
        "command": "conflictlist solve -u",
        "description": "Keep the original version constraint that exists in the waiting list, and discard the other version constraints with the same name and tool in the conflict list."
    }
    conflict_clear = {
        "command": "conflictlist clear",
        "description": "Used to clear all the items in the conflict list."
    }
    conflict_list_show = {
        "command": "conflictlist show",
        "description": "Used to show all the items in the conflict list."
    }
    download = {
        "command": 'download',
        "description": "Download all pending elements in the waiting list at once."
    }
    runtest = {
        "command": 'runtest',
        "description": "Check if the configured environment is correct."
    }
    clear_configuration = {
        "command": 'clear_configuration',
        "description": "Reset all the configuration to the initial clean C build environment."
    }
