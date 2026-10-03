"""Conservative C++ syntax denominator for source sweeps.

Uses the Tree-sitter C++ grammar, not a regex pretending to parse C++. Parse
errors and missing nodes remain inventory rows. The unpreprocessed syntax tree
does not establish active build branches, generated functions or call reachability.
"""
import hashlib
import re

MARKER = re.compile(r'Submit_Unsupported|\bTODO\b|unsupported|not\s+implemented|\bstub\w*\b', re.I)


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


def function_inventory(text, cpp_parser=None):
    source = text.encode('utf-8')
    tree = (cpp_parser or parser()).parse(source)

    def value(node):
        return source[node.start_byte:node.end_byte].decode('utf-8', errors='replace')

    functions, errors = [], []
    for node in walk(tree.root_node):
        if node.type == 'ERROR' or node.is_missing:
            errors.append({'line': node.start_point.row + 1,
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
                                  'end_line': node.end_point.row + 1,
                                  'node_type': node.type, 'body_kind': clause,
                                  'scope': '::'.join(reversed(scopes)),
                                  'declarator': value(declarator) if declarator else '<unknown>',
                                  'signals': [], 'literal_returns': [],
                                  'nonfinal_return_lines': [], 'markers': [], 'calls': [],
                                  'parse_has_error': node.has_error})
            else:
                errors.append({'line': node.start_point.row + 1,
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
                          'end_line': node.end_point.row + 1,
                          'node_type': node.type,
                          'scope': '::'.join(reversed(scopes)),
                          'declarator': value(declarator) if declarator else '<lambda>',
                          'body_kind': 'compound_statement',
                          'body_sha256': hashlib.sha256(
                              source[body.start_byte:body.end_byte]).hexdigest(),
                          'signals': signals, 'literal_returns': literal_returns,
                          'nonfinal_return_lines': early, 'markers': markers, 'calls': calls,
                          'parse_has_error': node.has_error})
    return {'functions': functions, 'parse_errors': errors,
            'root_has_error': tree.root_node.has_error}
