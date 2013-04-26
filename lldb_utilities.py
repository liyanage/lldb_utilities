#
# LLDB custom Python commands collection
#
# Load it with something like this in your ~/.lldbinit file:
# 
# command script import ~/git/lldb_utilities/lldb_utilities.py
#
# Maintained at http://github.com/liyanage/lldb_utilities/
# 

import lldb
import subprocess
#import AppKit

def copy_string_to_clipboard(string):
    pbcopy = subprocess.Popen('pbcopy', stdin=subprocess.PIPE)
    pbcopy.communicate(string)

# def copy_string_to_clipboard(string):
#     pb = AppKit.NSPasteboard.generalPasteboard()
#     pb.clearContents()
#     pb.writeObjects_(AppKit.NSArray.arrayWithObject_(string))

def copy_object_description_to_clipboard(debugger, command, result, internal_dict):
    """Print the description of an Objective-C object and copy it to the clipboard (Like "po")."""
    frame = debugger.GetSelectedTarget().GetProcess().GetSelectedThread().GetSelectedFrame()
    value = frame.EvaluateExpression(command)
    object_description = value.GetObjectDescription()
    print object_description
    copy_string_to_clipboard(object_description)

def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('command script add -f lldb_utilities.copy_object_description_to_clipboard poc')
