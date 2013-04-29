This is a collection of custom LLDB commands implemented using LLDB’s Python API.

Pull requests for improvements and additions are welcome. You can learn about the API at http://lldb.llvm.org/python-reference.html.

# Installation

Clone this repository or your personal fork to somewhere on your system:

    git clone http://github.com/liyanage/lldb_utilities/ ~/git/lldb_utilities

Create a `.lldbinit` file in your home directory that loads the custom module:

    ln -s ~/git/lldb_utilities/lldbinit ~/.lldbinit

Launch Xcode, run your target, drop into LLDB and try out the commands as shown below.

# Usage

## Help

Below is a list of the commands that are currently available. You can issue

    command script list

to see a list. For each command, you can get help with LLDB’s `help` command, for example:

    help poc

## Options

Some commands have option switches. You can shorten these as long as the shortened
version is unambiguous, for example you can shorten

    dump_nsdata -reveal -clipboard foo

to

    dump_nsdata -r -c foo

## Whitespace and Quoting

Some commands expect an expression that yields some object value, in this example `[NSData data]`:

    dump_nsdata -c [NSData data]

Parsing of command options follows shell rules (using Python’s [shlex](http://docs.python.org/2/library/shlex.html) module),
which means that expressions with spaces like the one above get split up and you would
normally have to prevent that with quotes:

    dump_nsdata -c "[NSData data]"

As a convenience, you can omit these quotes and the system will reassemble the expression
by joining the split pieces with spaces. In some cases that approach doesn’t produce the
correct results:

    dump_nsdata [NSData dataWithContentsOfFile:@"/foo   bar"]
    
In these cases, you should quote:

    dump_nsdata '[NSData dataWithContentsOfFile:@"/foo   bar"]'


# Commands

## poc

The `poc` command is derived from the built-in `po` command. Just like `po` it prints out
an Objective-C object’s description. In additon to that, it also copies the description
to the clipboard so you can paste it into an e-mail message or bug report.

    (lldb) poc NSApp
    <NSApplication: 0x100427590>

the string “&lt;NSApplication: 0x100427590>” is now also on the clipboard.

## dump_nsdata

This command invokes `[data writeToFile:@"xxx" atomically:YES]` for you. Without any options,
it creates a temporary file inside the directory returned by `NSTemporaryDirectory()`:

    (lldb) dump_nsdata [NSData data]
    /var/folders/j5/hjm915bx2gd9prgxz9c3fn700000gn/T/nsdata-N4c1ja.dat

You can override that with the `-o` ("output") option:

    (lldb) dump_nsdata -o ~/Desktop/foo.bin someData
    /Users/you/Desktop/foo.bin

The `-r` ("reveal") option reveals the resulting file in the Finder.

The `-c` ("clipboard") option copies the path to the resulting file to the clipboard.

You can combine these options:

    (lldb) dump_nsdata -c -r -o ~/Desktop/foo.bin someData
    /Users/you/Desktop/foo.bin

## tempdir

This command prints and copies the return value of `NSTemporaryDirectory()`.

# Extending lldb_utilities

You can write your own commands based on the infrastructure provided by lldb_utilities.py.

To add a command, create a new `DebuggerCommand` subclass and implement the `run` method:

    class DebuggerCommandMyCommand(DebuggerCommand):
        """Do something awesome."""

        def run(self):
            # use the lldb API here and do something useful
            self.result.PutCString('produce some text output')

Your command implementation will automatically be mapped to an LLDB command whose name
is derived from the class name, in this case `my_command`. Take a look at the existing
classes to see how to use the convenience methods provided by the base class.