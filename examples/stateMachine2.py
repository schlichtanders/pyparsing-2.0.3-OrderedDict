# stateMachine.py
# 
# module to define .pystate import handler
#
#import imputil
import sys
import os
import types
import urllib.parse

DEBUG = False

from pyparsingOD import Word, Group, ZeroOrMore, alphas, \
    alphanums, ParserElement, ParseException, ParseSyntaxException, \
    Empty, LineEnd, OneOrMore, col, Keyword, pythonStyleComment, \
    StringEnd, traceParseAction


ident = Word(alphas+"_", alphanums+"_$")

pythonKeywords = """and as assert break class continue def 
    del elif else except exec finally for from global if import 
    in is lambda None not or pass print raise return try while with 
    yield True False"""
pythonKeywords = set(pythonKeywords.split())
def no_keywords_allowed(s,l,t):
    wd = t[0]
    if wd in pythonKeywords:
        errmsg = "cannot not use keyword '%s' " \
                                "as an identifier" % wd
        raise ParseException(s,l,errmsg)
ident.setParseAction(no_keywords_allowed)

stateTransition = ident("fromState") + "->" + ident("toState")
stateMachine = Keyword("statemachine") + \
    ident("name") + ":" + \
    OneOrMore(Group(stateTransition))("transitions")

namedStateTransition = (ident("fromState") + \
    "-(" + ident("transition") + ")->" + \
    ident("toState"))
namedStateMachine = Keyword("statemachine") + \
    ident("name") + ":" + \
    OneOrMore(Group(namedStateTransition))("transitions")

def expand_state_definition(source, loc, tokens):
    indent = " " * (col(loc,source)-1)
    statedef = []
    
    # build list of states
    states = set()
    fromTo = {}
    for tn in tokens.transitions:
        states.add(tn.fromState)
        states.add(tn.toState)
        fromTo[tn.fromState] = tn.toState
    
    # define base class for state classes
    baseStateClass = tokens.name + "State"
    statedef.extend([
        "class %s(object):" % baseStateClass,
        "    def __str__(self):",
        "        return self.__class__.__name__",
        "    def next_state(self):",
        "        return self._next_state_class()" ])
    
    # define all state classes
    statedef.extend(
        "class %s(%s): pass" % (s,baseStateClass) 
            for s in states )
    statedef.extend(
        "%s._next_state_class = %s" % (s,fromTo[s]) 
            for s in states if s in fromTo )
           
    return indent + ("\n"+indent).join(statedef)+"\n"
    
stateMachine.setParseAction(expand_state_definition)

def expand_named_state_definition(source,loc,tokens):
    indent = " " * (col(loc,source)-1)
    statedef = []
    # build list of states and transitions
    states = set()
    transitions = set()
    
    baseStateClass = tokens.name + "State"
    
    fromTo = {}
    for tn in tokens.transitions:
        states.add(tn.fromState)
        states.add(tn.toState)
        transitions.add(tn.transition)
        if tn.fromState in fromTo:
            fromTo[tn.fromState][tn.transition] = tn.toState
        else:
            fromTo[tn.fromState] = {tn.transition:tn.toState}

    # add entries for terminal states
    for s in states:
        if s not in fromTo:
            fromTo[s] = {}
    
    # define state transition class
    statedef.extend([
        "class %sTransition:" % baseStateClass,
        "    def __str__(self):",
        "        return self.transitionName",
        ])
    statedef.extend(
        "%s = %sTransition()" % (tn,baseStateClass) 
            for tn in transitions)
    statedef.extend("%s.transitionName = '%s'" % (tn,tn) 
            for tn in transitions)

    # define base class for state classes
    excmsg = "'" + tokens.name + \
        '.%s does not support transition "%s"' \
        "'% (self, tn)"
    statedef.extend([
        "class %s(object):" % baseStateClass,
        "    def __str__(self):",
        "        return self.__class__.__name__",
        "    def next_state(self,tn):",
        "        try:",
        "            return self.tnmap[tn]()",
        "        except KeyError:",
        "            raise Exception(%s)" % excmsg,
        "    def __getattr__(self,name):",
        "        raise Exception(%s)" % excmsg,
        ])
    
    # define all state classes
    for s in states:
        statedef.append("class %s(%s): pass" % 
                                    (s,baseStateClass))

    # define state transition maps and transition methods
    for s in states:
        trns = list(fromTo[s].items())
        statedef.append("%s.tnmap = {%s}" % 
            (s, ",".join("%s:%s" % tn for tn in trns)) )
        statedef.extend([
            "%s.%s = staticmethod(lambda : %s())" % 
                                            (s,tn_,to_)
                for tn_,to_ in trns
            ])

    return indent + ("\n"+indent).join(statedef) + "\n"

namedStateMachine.setParseAction(
            expand_named_state_definition)

#======================================================================
# NEW STUFF - Matt Anderson, 2009-11-26
#======================================================================
class SuffixImporter(object):

    """An importer designed using the mechanism defined in :pep:`302`. I read
    the PEP, and also used Doug Hellmann's PyMOTW article `Modules and
    Imports`_, as a pattern.

    .. _`Modules and Imports`: http://www.doughellmann.com/PyMOTW/sys/imports.html   

    Define a subclass that specifies a :attr:`suffix` attribute, and
    implements a :meth:`process_filedata` method. Then call the classmethod
    :meth:`register` on your class to actually install it in the appropriate
    places in :mod:`sys`. """

    scheme = 'suffix'
    suffix = None
    path_entry = None

    @classmethod
    def trigger_url(cls):
        if cls.suffix is None:
            raise ValueError('%s.suffix is not set' % cls.__name__)
        return 'suffix:%s' % cls.suffix

    @classmethod
    def register(cls):
        sys.path_hooks.append(cls)
        sys.path.append(cls.trigger_url())

    def __init__(self, path_entry):
        pr = urllib.parse.urlparse(str(path_entry))
        if pr.scheme != self.scheme or pr.path != self.suffix:
            raise ImportError()
        self.path_entry = path_entry
        self._found = {}

    def checkpath_iter(self, fullname):
        for dirpath in sys.path:
            # if the value in sys.path_importer_cache is None, then this
            # path *should* be imported by the builtin mechanism, and the
            # entry is thus a path to a directory on the filesystem;
            # if it's not None, then some other importer is in charge, and
            # it probably isn't even a filesystem path
            if sys.path_importer_cache.get(dirpath,False) is None:
                checkpath = os.path.join(
                        dirpath,'%s.%s' % (fullname,self.suffix))
                yield checkpath
    
    def find_module(self, fullname, path=None):
        for checkpath in self.checkpath_iter(fullname):
            if os.path.isfile(checkpath):
                self._found[fullname] = checkpath
                return self
        return None

    def load_module(self, fullname):
        assert fullname in self._found
        if fullname in sys.modules:
            module = sys.modules[fullname]
        else:
            sys.modules[fullname] = module = types.ModuleType(fullname)
        data = None
        f = open(self._found[fullname])
        try:
            data = f.read()
        finally:
            f.close()

        module.__dict__.clear()
        module.__file__ = self._found[fullname]
        module.__name__ = fullname
        module.__loader__ = self
        self.process_filedata(module, data)
        return module

    def process_filedata(self, module, data):
        pass

class PystateImporter(SuffixImporter):
    suffix = 'pystate'

    def process_filedata(self, module, data):
        # MATT-NOTE: re-worked :func:`get_state_machine`

        # convert any statemachine expressions
        stateMachineExpr = (stateMachine | 
                            namedStateMachine).ignore(
                                            pythonStyleComment)
        generated_code = stateMachineExpr.transformString(data)

        if DEBUG: print(generated_code)

        # compile code object from generated code 
        # (strip trailing spaces and tabs, compile doesn't like 
        # dangling whitespace)
        COMPILE_MODE = 'exec'

        codeobj = compile(generated_code.rstrip(" \t"), 
                            module.__file__, 
                            COMPILE_MODE)

        exec(codeobj, module.__dict__)

PystateImporter.register()
