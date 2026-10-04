"""Conservative C++ syntax denominator for source sweeps.

Uses the Tree-sitter C++ grammar, not a regex pretending to parse C++. Parse
errors and missing nodes remain inventory rows. The unpreprocessed syntax tree
does not establish active build branches, generated functions or call reachability.
"""
import hashlib
import itertools
import re

MARKER = re.compile(r'Submit_Unsupported|\bTODO\b|unsupported|not\s+implemented|\bstub\w*\b', re.I)


def normalize_parser_source(text):
    """Work around known Tree-sitter grammar gaps without moving offsets.

    These constructs are valid in the compiled sources but the standalone C++
    grammar lacks the preprocessor expansion or compiler builtin needed to
    recognize them. Replacements retain byte and newline counts so syntax-tree
    locations still index the original source used for identities and review.
    Unknown syntax remains an explicit parse-error row.
    """
    original = text

    def padded(match, replacement):
        assert len(replacement) <= len(match.group(0))
        return replacement + (' ' * (len(match.group(0)) - len(replacement)))

    # The grammar expects a name for fixed-underlying-type enums even though
    # C++ permits anonymous declarations such as `enum : uint32_t { ... }`.
    text = re.sub(r'\benum\s*:\s*[A-Za-z_][A-Za-z_0-9:]*',
                  lambda match: padded(match, 'enum RVAnon'), text)
    # va_arg is parsed as a compiler builtin with a restricted type grammar.
    # Replace its type operand with an expression and treat it as an ordinary
    # same-width call. Port uses contain only non-parenthesized type operands.
    def va_arg_call(match):
        first = match.group(1)
        replacement = 'rv_arg(' + first + ',0)'
        return padded(match, replacement)
    text = re.sub(r'\bva_arg\(([^,()\n]+),\s*[^()\n]+\)', va_arg_call, text)
    # inttypes format tokens and build-label macros expand to string literals.
    # Supply a same-width empty literal so adjacent-string syntax stays valid.
    def string_macro(match):
        return padded(match, '""')
    text = re.sub(r'\bPRI(?:d|i|o|u|x|X)(?:8|16|32|64|LEAST8|LEAST16|LEAST32|LEAST64|FAST8|FAST16|FAST32|FAST64|MAX|PTR)\b',
                  string_macro, text)
    text = re.sub(r'(?<="\s)RENEGADE_BUILD_[A-Za-z_0-9]+(?=\s")',
                  string_macro, text)
    # Miles declares callbacks through an empty calling-convention macro.
    text = re.sub(r'\bAILCALLBACK\b', lambda match: ' ' * len(match.group(0)), text)
    # Additional valid constructs rejected by the standalone grammar: unnamed
    # pointer parameters with defaults, brace defaults on const references, and
    # placement-new arrays whose element type is itself a pointer.
    text = re.sub(r'(\b[A-Za-z_][A-Za-z_0-9:<>]*\s+\*)\s+(?==)',
                  lambda match: match.group(1) + 'x' +
                  (' ' * (len(match.group(0)) - len(match.group(1)) - 1)), text)
    text = re.sub(r'=\s*\{\}', lambda match: padded(match, '= 0'), text)
    text = re.sub(r'(?<=\w)\s+\*(?=\[[A-Za-z_])',
                  lambda match: ' ' * len(match.group(0)), text)
    # Never rewrite directive operands: blanking a macro name in #ifdef would
    # create a parser error that the source itself does not contain.
    original_lines = original.splitlines(keepends=True)
    normalized_lines = text.splitlines(keepends=True)
    text = ''.join(old if old.lstrip().startswith('#') else new
                   for old, new in zip(original_lines, normalized_lines))
    return text


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def parser():
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_cpp
    except ImportError as error:
        raise RuntimeError('Install tools/sweep-parser-requirements.txt in a local venv '
                           'to run the complete function inventory') from error
    return Parser(Language(tree_sitter_cpp.language()))


def conditional_macro_view(text, macro, enabled):
    """Select simple #if MACRO/#if !MACRO branches without moving bytes.

    This is intentionally narrower than a C preprocessor. Unknown directives
    remain in active text; nested text under an inactive managed branch is
    blanked. Running both values retains definitions from both supported build
    profiles while removing impossible cross-branch syntax.
    """
    lines = text.splitlines(keepends=True)
    stack = []
    active = True
    output = []
    positive = re.compile(r'^\s*#\s*(?:if\s+' + re.escape(macro) +
                          r'|ifdef\s+' + re.escape(macro) + r'|if\s+defined\s*\(\s*' +
                          re.escape(macro) + r'\s*\))\s*(?://.*)?$')
    negative = re.compile(r'^\s*#\s*(?:if\s+!' + re.escape(macro) +
                          r'|ifndef\s+' + re.escape(macro) + r'|if\s+!defined\s*\(\s*' +
                          re.escape(macro) + r'\s*\))\s*(?://.*)?$')

    def blank(line):
        return ''.join(char if char in '\r\n' else ' ' for char in line)

    for line in lines:
        stripped = line.rstrip('\r\n')
        directive = re.match(r'^\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b', stripped)
        if directive and directive.group(1) in ('if', 'ifdef', 'ifndef'):
            condition = enabled if positive.match(stripped) else (
                not enabled if negative.match(stripped) else None)
            stack.append({'parent': active, 'managed': condition is not None,
                          'condition': condition})
            if condition is not None:
                active = active and condition
                output.append(blank(line))
            else:
                output.append(line if active else blank(line))
        elif directive and directive.group(1) == 'else' and stack:
            frame = stack[-1]
            if frame['managed']:
                active = frame['parent'] and not frame['condition']
                output.append(blank(line))
            else:
                output.append(line if active else blank(line))
        elif directive and directive.group(1) == 'elif' and stack:
            frame = stack[-1]
            if frame['managed']:
                # No target-macro elif exists in the audited source. Retain an
                # explicit uncertainty if one is introduced instead of guessing.
                active = False
                output.append(line if frame['parent'] else blank(line))
            else:
                output.append(line if active else blank(line))
        elif directive and directive.group(1) == 'endif' and stack:
            frame = stack.pop()
            was_managed = frame['managed']
            active = frame['parent']
            output.append(blank(line) if was_managed or not active else line)
        else:
            output.append(line if active else blank(line))
    if stack:
        raise ValueError('Unbalanced preprocessor directives')
    result = ''.join(output)
    if len(result.encode()) != len(text.encode()):
        raise ValueError('Conditional view changed source offsets')
    return result


def function_inventory(text, cpp_parser=None, identity_text=None):
    source = (identity_text if identity_text is not None else text).encode('utf-8')
    parser_source = normalize_parser_source(text).encode('utf-8')
    if len(parser_source) != len(source):
        raise ValueError('Parser normalization changed source offsets')
    tree = (cpp_parser or parser()).parse(parser_source)

    def value(node):
        return source[node.start_byte:node.end_byte].decode('utf-8', errors='replace')

    functions, errors = [], []
    for node in walk(tree.root_node):
        if node.type == 'ERROR' or node.is_missing:
            errors.append({'line': node.start_point.row + 1,
                           'start_byte': node.start_byte, 'end_byte': node.end_byte,
                           'end_line': node.end_point.row + 1,
                           'node_type': node.type, 'missing': node.is_missing,
                           'snippet': value(node)[:160]})
        if node.type not in ('function_definition', 'lambda_expression'):
            continue
        body = node.child_by_field_name('body')
        declarator = node.child_by_field_name('declarator')
        scopes = []
        parent = node.parent
        while parent:
            if parent.type in ('namespace_definition', 'class_specifier', 'struct_specifier'):
                name = parent.child_by_field_name('name')
                if name:
                    scopes.append(value(name))
            parent = parent.parent
        if body is None:
            clause = next((n.type for n in node.named_children if n.type in
                           ('default_method_clause', 'delete_method_clause')), None)
            if clause:
                functions.append({'line': node.start_point.row + 1,
                                  'start_byte': node.start_byte, 'end_byte': node.end_byte,
                                  'end_line': node.end_point.row + 1,
                                  'node_type': node.type, 'body_kind': clause,
                                  'scope': '::'.join(reversed(scopes)),
                                  'declarator': value(declarator) if declarator else '<unknown>',
                                  'definition_sha256': hashlib.sha256(
                                      source[node.start_byte:node.end_byte]).hexdigest(),
                                  'signals': [], 'literal_returns': [],
                                  'nonfinal_return_lines': [], 'markers': [], 'calls': [],
                                  'parse_has_error': node.has_error})
            else:
                errors.append({'line': node.start_point.row + 1,
                               'start_byte': node.start_byte, 'end_byte': node.end_byte,
                               'end_line': node.end_point.row + 1,
                               'node_type': 'function_without_body', 'missing': True,
                               'snippet': value(node)[:160]})
            continue
        statements = [n for n in body.named_children if n.type != 'comment']
        # A nested function/lambda's return belongs to that nested definition.
        def own_nodes(current):
            for child in current.children:
                if child.type in ('function_definition', 'lambda_expression'):
                    continue
                yield child
                yield from own_nodes(child)
        returns = [n for n in own_nodes(body) if n.type == 'return_statement']
        calls = []
        for call in (n for n in own_nodes(body) if n.type == 'call_expression'):
            callee = call.child_by_field_name('function')
            if callee:
                calls.append({'line': call.start_point.row + 1,
                              'callee': value(callee), 'callee_node_type': callee.type})
        literal_returns = []
        for returned in returns:
            children = returned.named_children
            if len(children) == 1 and children[0].type in (
                    'number_literal', 'true', 'false', 'null', 'nullptr', 'string_literal', 'char_literal'):
                literal_returns.append({'line': returned.start_point.row + 1,
                                        'expression': value(children[0])})
        final_return = statements[-1] if statements and statements[-1].type == 'return_statement' else None
        early = [r.start_point.row + 1 for r in returns
                 if final_return is None or r.start_byte != final_return.start_byte]
        markers = [{'line': body.start_point.row + 1 + value(body).count('\n', 0, match.start()),
                    'text': match[0]} for match in MARKER.finditer(value(body))]
        signals = []
        if literal_returns:
            signals.append('literal_return')
        if early:
            signals.append('nonfinal_return_candidate')
        if not statements:
            signals.append('empty_body')
        if markers:
            signals.append('unsupported_or_todo_marker')
        functions.append({'line': node.start_point.row + 1,
                          'start_byte': node.start_byte, 'end_byte': node.end_byte,
                          'end_line': node.end_point.row + 1,
                          'node_type': node.type,
                          'scope': '::'.join(reversed(scopes)),
                          'declarator': value(declarator) if declarator else '<lambda>',
                          'definition_sha256': hashlib.sha256(
                              source[node.start_byte:node.end_byte]).hexdigest(),
                          'body_kind': 'compound_statement',
                          'body_sha256': hashlib.sha256(
                              source[body.start_byte:body.end_byte]).hexdigest(),
                          'signals': signals, 'literal_returns': literal_returns,
                          'nonfinal_return_lines': early, 'markers': markers, 'calls': calls,
                          'parse_has_error': node.has_error})
    return {'functions': functions, 'parse_errors': errors,
            'root_has_error': tree.root_node.has_error}


def function_inventory_for_boolean_profiles(text, macros, cpp_parser=None):
    """Union definitions and uncertainties from all values of build flags."""
    if isinstance(macros, str):
        macros = [macros]
    profiles = [dict(zip(macros, values))
                for values in itertools.product((False, True), repeat=len(macros))]
    inventories = []
    for profile in profiles:
        view = text
        for macro, enabled in profile.items():
            view = conditional_macro_view(view, macro, enabled)
        inventories.append(function_inventory(view, cpp_parser, identity_text=text))
    functions = {}
    errors = {}
    for inventory in inventories:
        for row in inventory['functions']:
            functions[(row['start_byte'], row['end_byte'], row['node_type'])] = row
        for row in inventory['parse_errors']:
            errors[(row['start_byte'], row['end_byte'], row['node_type'], row['missing'])] = row
    return {'functions': sorted(functions.values(), key=lambda row: (row['start_byte'], row['end_byte'])),
            'parse_errors': sorted(errors.values(), key=lambda row: (row['start_byte'], row['end_byte'])),
            'root_has_error': any(inventory['root_has_error'] for inventory in inventories),
            'profiles': profiles}
