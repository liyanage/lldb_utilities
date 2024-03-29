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
import shlex
import argparse
import tempfile
import os
import re
import sys
import time



# >>> lldb.thread.GetStopDescription(200)
# 'EXC_RESOURCE (RESOURCE_TYPE_MEMORY: high watermark memory limit exceeded) (limit=1000 MB)'

class IgnoreBreakpointByReasonDescriptionStopHook:
    """
    Use like this::

        (lldb) target stop-hook add -P lldb_utilities.IgnoreBreakpointByReasonDescriptionStopHook -k ignore_string -v EXC_RESOURCE
    """

    def __init__(self, target: lldb.SBTarget, extra_args: lldb.SBStructuredData, _):
        self.ignore_string = extra_args.GetValueForKey('ignore_string').GetStringValue(200)
    
    def handle_stop(self, exe_ctx: lldb.SBExecutionContext, stream: lldb.SBStream):
        description_text = exe_ctx.thread.GetStopDescription(200)
        if self.ignore_string in description_text:
            stream.Print(f'{type(self)}: auto-continuing breakpoint because description text contains "{self.ignore_string}": "{description_text}"\n')
            return False
        else:
            return True


class IgnoreMemoryResourceExceptionBreakpointStopHook:
    """
    Use like this::

        (lldb) target stop-hook add -P lldb_utilities.IgnoreMemoryResourceExceptionBreakpointStopHook
    """

    EXC_RESOURCE = 11

    def __init__(self, target: lldb.SBTarget, extra_args: lldb.SBStructuredData, _):
        pass
    
    def handle_stop(self, exe_ctx: lldb.SBExecutionContext, stream: lldb.SBStream):
        if exe_ctx.thread.stop_reason == lldb.eStopReasonException:
            if exe_ctx.thread.GetStopReasonDataAtIndex(0) == self.EXC_RESOURCE:
                stream.Print(f'{type(self)}: auto-continuing breakpoint because it is a memory resource exception\n')
                return False
        return True


class DebuggerCommand:

    def __init__(self, debugger, command, execution_context, result, internal_dict):
        self.debugger = debugger
        self.command = command
        self.execution_context = execution_context
        self.result = result
        self.internal_dict = internal_dict
        self.expression = None
        self.args = None

    def run(self):
        pass

    def needs_expression(self):
        return True

    def parse_command(self):
        parser = self.argument_parser()
        split_args = shlex.split(self.command)
        try:
            self.args = parser.parse_args(split_args)
        except SystemExit as e:
            self.result.PutCString('Failed to parse arguments: {}'.format(e))
            self.result.SetStatus(lldb.eReturnStatusFailed)
            return False
        
        if self.needs_expression():
            self.expression = ' '.join(self.args.expression)
        
        return True

    def temporary_directory(self):
        return self.frame().EvaluateExpression('(NSString *)NSTemporaryDirectory()').GetObjectDescription()

    def frame(self):
        return self.target().GetProcess().GetSelectedThread().GetSelectedFrame()
    
    def target(self):
        return self.debugger.GetSelectedTarget()

    def temporary_file_path(self, prefix=None, suffix=None):
        try:
            (handle, path) = tempfile.mkstemp(dir=self.temporary_directory(), prefix=prefix, suffix=suffix)
            os.close(handle)
            return path
        except:
            print('Unable to create temporary file', file=sys.stderr)
            return None

    def value_for_expression(self, expression):
        return self.frame().EvaluateExpression(expression)

    def copy_object_expression_result_to_clipboard(self, expression):
        file_path = self.temporary_file_path(prefix='lldb-clipboard-', suffix='.dat')
        cmd = '(BOOL)[({}) writeToFile:@"{}" atomically:YES]'.format(expression, file_path)
        value = self.value_for_expression(cmd)
        did_write = value.GetValueAsSigned()
        if not did_write:
            self.result.PutCString('Failed to write to {} (permission error?)'.format(self.args.output))
            self.result.SetStatus(lldb.eReturnStatusFailed)
            return
        
        with open(file_path) as f:
            po = subprocess.Popen(['pbcopy'], stdin=f)
            po.communicate()
        os.remove(file_path)

    @classmethod
    def handle_debugger_command(cls, debugger, command, execution_context, result, internal_dict):
        cmd = cls(debugger, command, execution_context, result, internal_dict)
        if not cmd.parse_command():
            return
        cmd.run()

    @classmethod
    def command_name(cls):
        return '_'.join([i.lower() for i in re.findall(r'([A-Z][a-z]+)', re.sub(r'^DebuggerCommand', '', cls.__name__))])

    @classmethod
    def help_string(cls):
        return cls.argument_parser().format_help()

    @classmethod
    def argument_parser(cls):
        parser = argparse.ArgumentParser(prog=cls.command_name(), description=cls.__doc__)
        cls.configure_argument_parser(parser)
        return parser

    @classmethod
    def configure_argument_parser(cls, parser):
        pass


class DebuggerCommandDumpNsdata(DebuggerCommand):
    """Dumps NSData instances to a file"""

    def run(self):
        if self.args.output:
            self.args.output = os.path.expanduser(self.args.output)
        else:
            self.args.output = self.temporary_file_path(prefix='nsdata-', suffix='.dat')

        can_write = True
        if not self.args.output:
            can_write = False
            self.args.output = os.path.join(self.temporary_directory(), 'tmp.dat')

        cmd = '(BOOL)[({}) writeToFile:@"{}" atomically:YES]'.format(self.expression, self.args.output)

        if not can_write:
            self.result.PutCString('Unable to create temp file output in {}, try manually with:\np {}'.format(self.temporary_directory(), cmd))
            return

        value = self.value_for_expression(cmd)
        did_write = value.GetValueAsSigned()
        if not did_write:
            self.result.PutCString('Failed to write to {} (permission error?)'.format(self.args.output))
            self.result.SetStatus(lldb.eReturnStatusFailed)
            return

        self.result.PutCString(self.args.output)

        if self.args.reveal:
            cmd = '(void)[[NSWorkspace sharedWorkspace] activateFileViewerSelectingURLs:@[(NSURL *)[NSURL fileURLWithPath:@"{}"]]]'.format(self.args.output)
            self.value_for_expression(cmd)

        if self.args.clipboard:
            self.copy_object_expression_result_to_clipboard('@"{}"'.format(self.args.output))
        
    @classmethod
    def configure_argument_parser(cls, parser):
        parser.add_argument('expression', nargs='+')
        parser.add_argument('-output', help='output path')
        parser.add_argument('-clipboard', action='store_true', help='copy output path to clipboard')
        parser.add_argument('-reveal', action='store_true', help='reveal output file in Finder')


class DebuggerCommandCopyObjectDescriptionToClipboard(DebuggerCommand):
    """Print the description of an Objective-C object and copy it to the clipboard (Like "po")"""

    def run(self):
        value = self.value_for_expression(self.command)
        object_description = value.GetObjectDescription()
        self.result.PutCString(object_description)
        self.copy_object_expression_result_to_clipboard('[({}) description]'.format(self.command))

    @classmethod
    def configure_argument_parser(cls, parser):
        parser.add_argument('expression', nargs='+')

    @classmethod
    def command_name(cls):
        return 'poc'


class DebuggerCommandCopyDescriptionToClipboard(DebuggerCommand):
    """Print the description of an expression and copy it to the clipboard (Like "p")"""

    def run(self):
        value = self.value_for_expression(self.command)
        stream = lldb.SBStream()
        value.GetDescription(stream)
        description = stream.GetData()

        (description,) = re.findall(r'^[^=]+= (.*)', description)
        
        readable_description = re.findall(r'^0x\w+ (.+)', description)
        if readable_description:
            description = readable_description[0]

        self.result.PutCString(description)

    @classmethod
    def configure_argument_parser(cls, parser):
        parser.add_argument('expression', nargs='+')

    @classmethod
    def command_name(cls):
        return 'pp'


class DebuggerCommandTempdir(DebuggerCommand):
    """Print the value of NSTemporaryDirectory() and copy it to the clipboard"""

    def run(self):
        path = self.temporary_directory()
        self.result.PutCString(path)
        self.copy_object_expression_result_to_clipboard('@"{}"'.format(path))

    def needs_expression(self):
        return False


class DebuggerCommandPrintFlags(DebuggerCommand):
    """Print the names of the enabled CPU status register flags.
       For x86_64, see http://en.wikipedia.org/wiki/FLAGS_register,
       for arm64, see http://en.wikipedia.org/wiki/ARM_architecture#Registers
    """

    def run(self):
        flag_names = None
        status_register_name = None
        triple = self.target().triple

        if triple.startswith('x86_64'):
            flag_names = ['CF', None, 'PF', None, 'AF', None, 'ZF', 'SF', 'TF', 'IF', 'DF', 'OF', 'IOPL1', 'IOPL2', 'NT', None, 'RF', 'VM', 'AC', 'VIF', 'VIP', 'ID']
            status_register_name = 'rflags'
        elif triple.startswith('arm64'):
            flag_names = [None for i in range(28)] + ['Q', 'V', 'C', 'Z', 'N']
            status_register_name = 'cpsr'
        else:
            print('Unknown architecture', file=sys.stderr)
            return

        value = self.frame().register[status_register_name].unsigned
        enabled_status_flags = [flag_name for i, flag_name in enumerate(flag_names) if value & (1 << i) and flag_name]
        self.result.PutCString(' '.join(enabled_status_flags))

    def needs_expression(self):
        return False

    @classmethod
    def command_name(cls):
        return 'pflags'


def invocation_proxy(original_function):
    def call_proxy(*args):
        original_function(*args)
    return call_proxy

def register_handlers(debugger, namespace_name):
    namespace_module = sys.modules[namespace_name]
    for k in dir(namespace_module):
        v = getattr(namespace_module, k)
        if not (k.startswith('DebuggerCommand') and callable(getattr(v, 'handle_debugger_command', None))):
            continue
        command_name = v.command_name()
        if not command_name:
            continue

        # Passing the handle_debugger_command bound class method directly
        # to lldb's "command script add" doesn't work, so we create
        # a new dummy forwarding function and insert that into a 
        # known namespace. Passing that to LLDB works. Additionally,
        # having a separate function for each command lets us assign
        # the appropriate documentation to its docstring.
        function_proxy = invocation_proxy(v.handle_debugger_command)
        function_proxy.__doc__ = v.help_string()
        function_proxy.__name__ = command_name
        function_name = 'command_handler_{}'.format(command_name)
        setattr(namespace_module, function_name, function_proxy)

        cmd = 'command script add -f lldb_utilities.{} {}'.format(function_name, command_name)
        if debugger:
            debugger.HandleCommand(cmd)


def __lldb_init_module(debugger, internal_dict):
    register_handlers(debugger, __name__)
