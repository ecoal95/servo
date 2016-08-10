#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import os
import sys

if len(sys.argv) != 2:
    print("usage: ./{} PATH/TO/OBJDIR".format(sys.argv[0]))
    sys.exit(1)

OBJDIR = sys.argv[1]


def gnu_symbolify(source, ident):
    return "_ZN" + str(len(source.CLASS)) + source.CLASS + str(len(ident)) + ident + "E"


def msvc64_symbolify(source, ident):
    return "?" + ident + "@" + source.CLASS + "@@2PEAV" + source.TYPE + "@@EA"


def msvc32_symbolify(source, ident):
    return "?" + ident + "@" + source.CLASS + "@@2PAV" + source.TYPE + "@@A"


class GkAtomSource:
    PATTERN = re.compile('^GK_ATOM\((.+),\s*"(.*)"\)')
    FILE = "dist/include/nsGkAtomList.h"
    CLASS = "nsGkAtoms"
    TYPE = "nsIAtom"


class CSSPseudoElementsAtomSource:
    PATTERN = re.compile('^CSS_PSEUDO_ELEMENT\((.+),\s*"(.*)",')
    FILE = "dist/include/nsCSSPseudoElementList.h"
    CLASS = "nsCSSPseudoElements"
    # NB: nsICSSPseudoElement is effectively the same as a nsIAtom, but we need
    # this for MSVC name mangling.
    TYPE = "nsICSSPseudoElement"


class CSSAnonBoxesAtomSource:
    PATTERN = re.compile('^CSS_ANON_BOX\((.+),\s*"(.*)"\)')
    FILE = "dist/include/nsCSSAnonBoxList.h"
    CLASS = "nsGKAtoms"
    TYPE = "nsICSSAnonBoxPseudo"

    @staticmethod
    def msvc64_symbolify(ident):
        # FIXME
        return "?" + ident + "@nsGkAtoms@@2PEAVnsIAtom@@EA"

    @staticmethod
    def msvc32_symbolify(ident):
        # FIXME
        return "?" + ident + "@nsGkAtoms@@2PAVnsIAtom@@A"


SOURCES = [
    GkAtomSource,
    CSSPseudoElementsAtomSource,
    CSSAnonBoxesAtomSource,
]


def map_atom(ident):
    if ident in {"box", "loop", "match", "mod", "ref",
                 "self", "type", "use", "where", "in"}:
        return ident + "_"
    return ident


class Atom:
    def __init__(self, source, ident, value):
        self.ident = "{}_{}".format(source.CLASS, ident)
        self.value = value
        self.cpp_class = source.CLASS
        # FIXME(emilio): This is crap, and we really could/should just store a
        # reference to the source, but...
        self._gnu_symbol = gnu_symbolify(source, ident)
        self._msvc32_symbol = msvc32_symbolify(source, ident)
        self._msvc64_symbol = msvc64_symbolify(source, ident)
        self._type = source.TYPE

    def get_gnu_symbol(self):
        return self._gnu_symbol

    def get_msvc32_symbol(self):
        return self._msvc32_symbol

    def get_msvc64_symbol(self):
        return self._msvc64_symbol

    def get_type(self):
        return self._type

atoms = []
for source in SOURCES:
    with open(os.path.join(OBJDIR, source.FILE)) as f:
        for line in f.readlines():
            result = re.match(source.PATTERN, line)
            if result:
                atoms.append(Atom(source, result.group(1), result.group(2)))


def write_items(f, func):
    f.write("        extern {\n")
    for atom in atoms:
        f.write(TEMPLATE.format(name=atom.ident,
                                link_name=func(atom),
                                type=atom.get_type()))
    f.write("        }\n")


TEMPLATE = """
            #[link_name = "{link_name}"]
            pub static {name}: *mut {type};
"""[1:]

with open("atom_macro.rs", "wb") as f:
    f.write("use gecko_bindings::structs::nsIAtom;\n\n")
    f.write("use Atom;\n\n")
    for source in SOURCES:
        if source.TYPE != "nsIAtom":
            f.write("pub enum {} {{}}\n\n".format(source.TYPE))
    f.write("""
            #[inline(always)] pub fn unsafe_atom_from_static(ptr: *mut nsIAtom) -> Atom {
                unsafe { Atom::from_static(ptr) }
            }\n\n")
            """)
    f.write("cfg_if! {\n")
    f.write("    if #[cfg(not(target_env = \"msvc\"))] {\n")
    write_items(f, Atom.get_gnu_symbol)
    f.write("    } else if #[cfg(target_pointer_width = \"64\")] {\n")
    write_items(f, Atom.get_msvc64_symbol)
    f.write("    } else {\n")
    write_items(f, Atom.get_msvc32_symbol)
    f.write("    }\n")
    f.write("}\n\n")
    f.write("#[macro_export]\n")
    f.write("macro_rules! atom {\n")
    f.writelines(['("%s") => { $crate::atom_macro::unsafe_atom_from_static($crate::atom_macro::%s as *mut _) };\n'
                 % (atom.value, atom.ident) for atom in atoms])
    f.write("}\n")
