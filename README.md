This is a collection of custom LLDB commands implemented using LLDB’s Python API.

Pull requests for improvements and additions are welcome. You can learn about the API at http://lldb.llvm.org/python-reference.html.

# Installation

Clone this repository or your personal fork to somewhere on your system:

    git clone http://github.com/liyanage/lldb_utilities/ ~/git/lldb_utilities

Create a `.lldbinit` file in your home directory that loads the custom module:

    ln -s ~/git/lldb_utilities/lldbinit ~/.lldbinit

Launch Xcode, run your target, drop into LLDB and try out the commands as shown below.

# Commands

Here’s a list of the commands that are currently available.

## poc

The `poc` command is derived from the built-in `po` command. Just like `po` it prints out
an Objective-C object’s description. In additon to that, it also copies the description
to the clipboard so you can paste it into an e-mail message or bug report.

    (lldb) poc NSApp
    <NSApplication: 0x100427590>

the string “&lt;NSApplication: 0x100427590>” is now also on the clipboard.

