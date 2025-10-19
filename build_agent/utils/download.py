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


# from apt_download import run_apt
# from pip_download import run_pip
import subprocess

TIME_OUT_LABEL= ' seconds. Partial output:'

def match_timeout(text):
    if 'timeout' in text.lower() or 'timed out' in text.lower() or 'failed to fetch' in text.lower() or 'could not resolve' in text.lower():
        return True
    else:
        return False

def download(session, waiting_list, conflict_list):
    successful_download = list()
    failed_download = list()
    tool_error = list()
    # if errorformat_list.size() > 0:
    #     errorformat_list.get_message()
    #     return -1
    if conflict_list.size() > 0:
        conflict_list.get_message(waiting_list)
        return -1
    if waiting_list.size() == 0:
        print('╔═══════════════════════════════════════════════════════════════════════╗')
        print('║                    WAITING LIST IS EMPTY                              ║')
        print('╟───────────────────────────────────────────────────────────────────────╢')
        print('║  All packages have already been processed.                            ║')
        print('║                                                                        ║')
        print('║  ⚠️  DO NOT CALL "download" AGAIN!                                    ║')
        print('║                                                                        ║')
        print('║  Why?                                                                  ║')
        print('║  • download processes ALL packages in waiting list at once            ║')
        print('║  • Calling it multiple times wastes time and may cause errors         ║')
        print('║  • The list is now empty - nothing left to download                   ║')
        print('║                                                                        ║')
        print('║  📝 What to do instead:                                               ║')
        print('║                                                                        ║')
        print('║  Option 1: If all packages installed successfully                     ║')
        print('║    → Proceed to build: ./configure, cmake, or make                    ║')
        print('║                                                                        ║')
        print('║  Option 2: If some packages failed                                    ║')
        print('║    → Try alternatives or fix errors above                             ║')
        print('║    → Then add to waiting list and call download once                  ║')
        print('║                                                                        ║')
        print('║  Option 3: If you need to add MORE packages                           ║')
        print('║    → Use: waitinglist add -p package_name -t apt                      ║')
        print('║    → Then call download ONCE                                          ║')
        print('╚═══════════════════════════════════════════════════════════════════════╝')
        return [], [], []  # Return immediately if empty
    while waiting_list.size() > 0:
        pop_item = waiting_list.pop()
        success = False
        result = ''
        if pop_item.tool.strip().lower() == 'pip':
            # success, result = run_pip(pop_item.package_name, pop_item.version_constraints)
            command = f'python /home/tools/pip_download.py -p {pop_item.package_name}'
            if pop_item.version_constraints and len(pop_item.version_constraints) > 0:
                command += f' -v "{pop_item.version_constraints}"'
            success, result = session.execute_simple(command)
            # print(success)
            # print(pop_item.othererror)
        elif pop_item.tool.strip().lower() == 'apt':
            # success, result = run_apt(pop_item.package_name, pop_item.version_constraints)
            command = f'python /home/tools/apt_download.py -p {pop_item.package_name}'
            if pop_item.version_constraints and len(pop_item.version_constraints) > 0:
                command += f' -v "{pop_item.package_name}"'
            success, result = session.execute_simple(command)
        else:
            print(f'Please check the tool: {pop_item.tool.lower()}, packege_name: {pop_item.package_name}, version_constraints: {pop_item.version_constraints}')
            tool_error.append(pop_item)

        if pop_item.timeouterror == 2:
            failed_download.append([pop_item, result])
            print(f'The third-party library "{pop_item.package_name}{pop_item.version_constraints if pop_item.version_constraints else ""}" (using tool {pop_item.tool}) has been added to the failed list due to three download timeout errors.')
            continue  # Continue processing other packages instead of breaking
        if pop_item.othererror == 2:
            failed_download.append([pop_item, result])
            print(f'The third-party library "{pop_item.package_name}{pop_item.version_constraints if pop_item.version_constraints else ""}" (using tool {pop_item.tool}) has been added to the failed list due to three download non-timeout errors.')
            continue  # Continue processing other packages instead of breaking
        if success:
            successful_download.append(pop_item)
            print(f'"{pop_item.package_name}{pop_item.version_constraints if pop_item.version_constraints else ""}" installed successfully.')
        else:
            timeout = match_timeout(result)
            if timeout:
                pop_item.timeouterror += 1
                waiting_list.add(pop_item.package_name, pop_item.version_constraints, pop_item.tool, conflict_list, pop_item.timeouterror, pop_item.othererror)
                print(f'"{pop_item.package_name}{pop_item.version_constraints if pop_item.version_constraints else ""}" installed failed due to timeout errors.')
            else:
                pop_item.othererror += 1
                waiting_list.add(pop_item.package_name, pop_item.version_constraints, pop_item.tool, conflict_list, pop_item.timeouterror, pop_item.othererror)
                print(f'"{pop_item.package_name}{pop_item.version_constraints if pop_item.version_constraints else ""}" installed failed due to non-timeout errors')
    
    print('=' * 75)
    print('DOWNLOAD SUMMARY')
    print('=' * 75)
    
    if len(successful_download) > 0:
        print(f'\n✅ Successfully installed: {len(successful_download)} package(s)')
        for item in successful_download:
            print(f'   • {item.package_name}{item.version_constraints if item.version_constraints else ""} (using {item.tool})')
    else:
        print('\n⚠️  No packages were successfully installed in this round.')
        if len(failed_download) > 0:
            print(f'   • {len(failed_download)} package(s) failed after 3 attempts')
            print('   • Check error messages above or try alternative packages')
    
    print('\n' + '=' * 75)
    print('⚠️  IMPORTANT: DO NOT CALL "download" AGAIN!')
    print('=' * 75)
    print('Why?')
    print('• All packages in waiting list have been processed')
    print('• Calling download again will find empty list and waste time')
    print('• If packages failed, fix errors or try alternatives first')
    print('\n📝 Next steps:')
    if len(successful_download) > 0 and len(failed_download) == 0:
        print('   ✅ All packages installed → Proceed to build (./configure, cmake, make)')
    elif len(failed_download) > 0:
        print('   ⚠️  Some packages failed → Review errors above')
        print('   → Try alternative packages or fix dependency issues')
        print('   → Add alternatives to waiting list, then call download once')
    else:
        print('   ⚠️  No packages installed → Check waiting list or try alternatives')
    print('=' * 75)
    
    if len(failed_download) > 0:
        # print('@'*100)
        print('In this round, the following third-party libraries failed to download. They are:')
        for item in failed_download:
            print('-'*100)
            print(f'{item[0].package_name}{item[0].version_constraints if item[0].version_constraints else ""} (using tool {item[0].tool})')
            msg = list()
            for line in item[1].splitlines():
                if len(line.strip()) > 0:
                    msg.append(line.strip())
            msg = '\n'.join(msg[-10:])
            print(f"Failed message:\n {msg}")
            print('-'*100)
    else:
        print('No third-party libraries failed to download in this round.')
    
    if len(tool_error) > 0:
        print('In this round, the download tools for the following third-party libraries could not be found (only pip or apt can be selected).')
        for item in tool_error:
            print(f'{item.package_name}{item.version_constraints if item.version_constraints else ""} (using tool {item.tool})')
    else:
        pass
    return successful_download, failed_download, tool_error

if __name__ == '__main__':
    from waiting_list import WaitingList
    # from errorformat_list import ErrorformatList
    from conflict_list import ConflictList
    waiting_list = WaitingList()
    waiting_list.add('numpy', '>2.0,<3.0', 'pip')
    waiting_list.add('pytorch', None, 'pip')
    waiting_list.add('tmux', None, 'apt')
    waiting_list.add('unknown', None, 'Pips')
    waiting_list.get_message()
    successful_download, failed_download, tool_error = download(waiting_list, ConflictList())
    print('-'*100)
    for item in successful_download:
        print(item.package_name)
        print(item.version_constraints)
        print(item.tool)
        print(item.timeouterror)
        print(item.othererror)
    print('-'*100)
    for item in failed_download:
        print(item.package_name)
        print(item.version_constraints)
        print(item.tool)
        print(item.timeouterror)
        print(item.othererror)
    print('-'*100)
    for item in tool_error:
        print(item.package_name)
        print(item.version_constraints)
        print(item.tool)
        print(item.timeouterror)
        print(item.othererror)
    