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
    """C-specific build tools"""
    
    run_make = {
        "command": "run_make",
        "description": "Build C project using make command"
    }
    
    run_cmake = {
        "command": "run_cmake", 
        "description": "Build C project using cmake (configure + make)"
    }
    
    run_gcc = {
        "command": "run_gcc",
        "description": "Compile C project directly with gcc"
    }
    
    apt_install = {
        "command": "apt_install package_name",
        "description": "Install system packages using apt-get"
    }
