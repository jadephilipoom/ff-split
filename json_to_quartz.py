#! /usr/bin/env python3

import argparse
import json

DEBUG = False

# special prefixes for state ports
STATE_IN_PREFIX = 'o_clk'
STATE_OUT_PREFIX = 'i_clk'

# translations for basic bitwise operators (with and without notations)
BIT_BINOPS = {
    '$and': ('&', 'And'),
    '$xor': ('^', 'Xor'),
    '$or': ('|', 'Or'),
}
BIT_UNOPS = {
    '$not': ('~', 'Not'),
    '$pos': ('', ''), # this one seems to be just an assignment
}

PREFIX='''(* Automatically generated from Yosys JSON. *)
From Stdlib Require Import BinInt Bits String.
Require Import quartz.lang.sv.
Require Import quartz.lang.Syntax. Import type.
Import (notations) type expr eexpr.

'''

def debug(msg):
    if DEBUG:
        print(msg)

def translate_interface(ports):
    '''Translates port data to struct fields.'''
    lines = []
    for name, port in ports.items():
        if len(port['bits']) == 1:
            lines.append(f'  {name} : Bool;')
        else:
            bitlen = len(port['bits'])
            lines.append(f'  {name} : Array Bool {bitlen};')
    return lines

def translate_ports(ports):
    # classify the ports as true inputs, true outputs and state values
    inputs = {}
    outputs = {}
    state_inputs = {}
    state_outputs = {}
    for p in ports:
        if ports[p]['direction'] == 'input':
            if p.startswith(STATE_IN_PREFIX):
                state_inputs[p] = ports[p]
            else:
                inputs[p] = ports[p]
        elif ports[p]['direction'] == 'output':
            if p.startswith(STATE_OUT_PREFIX):
                state_outputs[p] = ports[p]
            else:
                outputs[p] = ports[p]
        else:
            raise ValueError(f'Could not classify port: {p}')

    # check that state inputs and outputs match up
    if len(state_inputs) != len(state_outputs):
        raise ValueError(f'Mismatched count of state input and output ports.')
    state_mapping = {}
    for inname in state_inputs:
        outname = inname.replace(STATE_IN_PREFIX, STATE_OUT_PREFIX)
        state_mapping[outname] = inname
        if outname not in state_outputs:
            print(ports.keys())
            raise ValueError(f'Could not find a matching state output port for {inname} (looking for name {outname})')
        if len(state_inputs[inname]['bits']) != len(state_outputs[outname]['bits']):
            raise ValueError(f'Ports {inname} and {outname} have incompatible bitlengths.')

    return inputs, outputs, state_inputs, state_outputs, state_mapping
    
def stringify_ports(inputs, outputs, state_inputs, state_outputs):
    lines = []

    # construct the request struct
    lines.append('Record req := {')
    lines.extend(translate_interface(inputs))
    lines.append('}.')
    lines.append('Definition Req := type.reify\'\' req.')
    lines.append('')

    # construct the state struct
    lines.append('Record state := {')
    lines.extend(translate_interface(state_inputs))
    lines.extend(translate_interface(outputs))
    lines.append('}.')
    lines.append('Definition State := type.reify\'\' state.')
    lines.append('')

    return '\n'.join(lines)

def get_rhs_exprs(inputs, state_inputs, use_notations):
    # build lookup tables for the port expressions
    rhs_tbl = {}
    for name, port in inputs.items():
        if len(port['bits']) == 1:
            rhs_tbl[port['bits'][0]] = f'#_d_{name}'
        else:
            idxw = len(port['bits']).bit_length()
            for i, bit in enumerate(port['bits']):
                rhs_tbl[bit] = f'(#_d_{name})[{idxw} \'d {i}]'
    for name, port in state_inputs.items():
        if len(port['bits']) == 1:
            rhs_tbl[port['bits'][0]] = f'#_st_{name}'
        else:
            idxw = len(port['bits']).bit_length()
            for i, bit in enumerate(port['bits']):
                tbl[bit] = f'(#_st_{name})[{idxlen} \'d {i}]'
    if not use_notations:
        rhs_tbl = {n:f'quartz_expr:({e})' for n, e in rhs_tbl.items()}
    return rhs_tbl

def get_cell_output_bits(cell):
    bits = []
    for name, direction in cell['port_directions'].items():
        if direction == 'output':
            bits.extend(cell['connections'][name])
    return bits

def get_cell_input_bits(cell):
    bits = []
    for name, direction in cell['port_directions'].items():
        if direction == 'input':
            bits.extend(cell['connections'][name])
    return bits

def get_expr(rhs_tbl, bit):
    if bit not in rhs_tbl:
        raise ValueError(f'Failed to resolve expression for signal {bit}')
    return rhs_tbl[bit]

def translate_bit_binop(cell, rhs_tbl, use_notations):
    assert int(cell['parameters']['A_SIGNED']) == 0
    assert int(cell['parameters']['B_SIGNED']) == 0
    assert int(cell['parameters']['A_WIDTH']) == 1
    assert int(cell['parameters']['B_WIDTH']) == 1
    assert int(cell['parameters']['Y_WIDTH']) == 1
    assert len(cell['connections']['A']) == 1
    assert len(cell['connections']['B']) == 1
    assert len(cell['connections']['Y']) == 1
    A = cell['connections']['A'][0]
    B = cell['connections']['B'][0]
    aexpr = get_expr(rhs_tbl, A)
    bexpr = get_expr(rhs_tbl, B)
    operator, opname = BIT_BINOPS[cell['type']]
    if use_notations:
        return f'{aexpr} {operator} {bexpr}'
    return f'(expr.Binop binop.{opname} {aexpr} {bexpr})'

def translate_bit_unop(cell, rhs_tbl, use_notations):
    assert int(cell['parameters']['A_SIGNED']) == 0
    assert int(cell['parameters']['A_WIDTH']) == 1
    assert int(cell['parameters']['Y_WIDTH']) == 1
    assert len(cell['connections']['A']) == 1
    assert len(cell['connections']['Y']) == 1
    A = cell['connections']['A'][0]
    aexpr = get_expr(rhs_tbl, A)
    operator, opname = BIT_UNOPS[cell['type']]
    if operator == '':
        return f'{aexpr}'
    if use_notations:
        return f'{operator} {aexpr}'
    return f'(expr.Unop unop.{opname} {aexpr})'


def translate_mux(cell, rhs_tbl, use_notations):
    assert int(cell['parameters']['WIDTH']) == 1
    assert len(cell['connections']['A']) == 1
    assert len(cell['connections']['B']) == 1
    assert len(cell['connections']['S']) == 1
    assert len(cell['connections']['Y']) == 1
    A = cell['connections']['A'][0]
    B = cell['connections']['B'][0]
    S = cell['connections']['S'][0]
    Y = cell['connections']['Y'][0]
    aexpr = get_expr(rhs_tbl, A)
    bexpr = get_expr(rhs_tbl, B)
    sexpr = get_expr(rhs_tbl, S)
    if use_notations:
        return f'if {sexpr} then {bexpr} else {aexpr}'
    return f'(expr.If {sexpr} {bexpr} {aexpr})'

def get_cell_expr(cell, rhs_tbl, use_notations):
    if cell['type'] in BIT_BINOPS:
        expr = translate_bit_binop(cell, rhs_tbl, use_notations)
    elif cell['type'] in BIT_UNOPS:
        expr = translate_bit_unop(cell, rhs_tbl, use_notations)
    elif cell['type'] == "$mux":
        expr = translate_mux(cell, rhs_tbl, use_notations)
    else:
        raise ValueError(f'Unknown cell type: {cell["type"]}')
    return expr

def translate_let(name, expr, use_notations):
    if use_notations:
        return f'  let {name} := {expr} in\n'
    return f'  eexpr.Let "{name}" {expr} (fun {name} =>\n'


def translate_cell(name, cell, lhs_tbl, rhs_tbl, out, use_notations):
    expr = get_cell_expr(cell, rhs_tbl, use_notations)
    outbits = get_cell_output_bits(cell)
    if len(outbits) != 1:
        # TODO: handle calls to other modules?
        raise NotImplementedError(f'Cells with more than one output bit are not currently supported (cell: {name})')

    Y = outbits[0]
    if Y not in lhs_tbl:
        # do not assign
        rhs_tbl[Y] = expr
        return

    name = lhs_tbl[Y]
    rhs_tbl[Y] = f'#{name}' if use_notations else f'(expr.Var {name})'
    out.write(translate_let(name, expr, use_notations))

def sanitize(name):
    '''Make a netname legal for a quartz variable name.'''
    return name.replace('.', '_')

def get_lhs_names(module):
    '''Make a table for names of bit signals that receive assignments.'''
    lhs_tbl = {}
    for netname, net in module['netnames'].items():
        if net['hide_name'] == 1:
            # we assume this is an internal expression that never gets assigned to
            continue
        if len(net['bits']) == 1:
            bit = net['bits'][0]
            lhs_tbl[bit] = sanitize(netname)
        else:
            # name signals with indices because assigning to a specific index
            # of an array in quartz is a giant pain
            for i, bit in enumerate(net['bits']):
                name = f'{netname}_{i}'
                while (name in module['netnames']) or (name in lhs_tbl):
                    name += '_'
                lhs_tbl[bit] = sanitize(name)
    return lhs_tbl

def get_output_ports(bit, outputs, state_outputs):
    ports = {name: port for name, port in outputs.items() if bit in port['bits']}
    ports.update({name: port for name, port in state_outputs.items() if bit in port['bits']})
    return ports

def topo_sort(g):
    '''Basic DFS-based recursive algorithm.'''
    out = []
    todo = set(g.keys())

    def visit(v):
        if v not in todo:
            return
        todo.remove(v)
        for child in g[v]:
            visit(child)
        out.append(v)

    while todo:
        # visit any unvisited node
        v = todo.pop()
        todo.add(v)
        visit(v)

    return out

def topo_sort_cells(cells, rhs_tbl):
    # first, map output bits to the cells that generate them
    bit_to_cell = {}
    for name, cell in cells.items():
        for bit in get_cell_output_bits(cell):
            if bit in bit_to_cell:
                raise ValueError(f'Signal {bit} is driven by multiple cells: {name} and {bits_to_cells["bit"]}')
            bit_to_cell[bit] = name

    # then, construct a DAG where nodes are cells and edges indicate dependency
    dag = {}
    for name, cell in cells.items():
         dag[name] = [bit_to_cell[b] for b in get_cell_input_bits(cell) if b in bit_to_cell]

    return topo_sort(dag)

def translate_module(mname, module, out, use_notations):
    inputs, outputs, state_inputs, state_outputs, state_mapping = translate_ports(module['ports'])
    lhs_tbl = get_lhs_names(module)
    rhs_tbl = get_rhs_exprs(inputs, state_inputs, use_notations)
    rhs_tbl["0"] = "(1 'd 0)" if use_notations else '(expr.Const (t:=Bits 1) (bits.of_Z _ 0))'
    rhs_tbl["1"] = "(1 'd 1)" if use_notations else '(expr.Const (t:=Bits 1) (bits.of_Z _ 1))'
    sorted_cells = topo_sort_cells(module["cells"], rhs_tbl)

    out.write(stringify_ports(inputs, outputs, state_inputs, state_outputs))
    out.write('\n')
    out.write(f'Definition {mname}_inner')
    out.write(' {var} : fn.fn var (Pair State Req) State := fn.Fn (fun (p: var (Pair State Req)) =>')
    close_parens = 1
    if use_notations:
        out.write('quartz_eexpr:(')
        close_parens += 1
    out.write('\n  ')

    if use_notations:
        out.write('  let _st := #p .1 in let _d := #p .2 in\n')
    else:
        st_expr = '(expr.Get (typeWithHole.PairL typeWithHole.HOLE _) (expr.Var p) expr.tt)'
        out.write(translate_let('_st', st_expr, use_notations))
        close_parens += 1
        d_expr = '(expr.Get (typeWithHole.PairR typeWithHole.HOLE _) (expr.Var p) expr.tt)'
        out.write(translate_let('_d', d_expr, use_notations))
        close_parens += 1

    # the .. notation calls ltac2 to reify the expression internally; assigning
    # variables early instead of using expr.Get every time helps the Rocq
    # expression parse in a more reasonable amount of time
    for name in state_inputs:
        expr = f'#_st..{name}' if use_notations else f'quartz_expr:(#_st..name)'
        out.write(translate_let(f'_st_{name}', expr, use_notations))
        if use_notations:
            close_parens += 1
    for name in inputs:
        expr = f'#_d..{name}' if use_notations else f'quartz_expr:(#_d..name)'
        out.write(translate_let(f'_d_{name}', expr, use_notations))
        if use_notations:
            close_parens += 1

    # translate the cells into bitwise operations
    for name in sorted_cells:
        cell = module['cells'][name]
        translate_cell(name, cell, lhs_tbl, rhs_tbl, out, use_notations)
        if use_notations:
            close_parens += 1

    outports = list(outputs.items()) + list(state_outputs.items())
    out.write(translate_let(f'_new_st', '#_st' if use_notations else '(expr.Var _st)', use_notations))
    if use_notations:
        close_parens += 1

    for name, p in outports:
        if name in state_outputs:
            # use the input port name, that's what the state struct has
            name = state_mapping[name]
        if len(p['bits']) == 1:
            expr = rhs_tbl[p['bits'][0]]
            if use_notations:
                out.write(f'  let _new_st <- #_new_st..{name} = {expr} in\n')
            else:
                out.write(f'  eexpr.Bind "_new_st" quartz_eexpr:(#_new_st..{name} = {expr}) (fun _new_st => in\n')
                close_parens += 1
        else:
            idxw = len(p['bits']).bit_length()
            expr = f'#_new_st..{name}'
            if not use_notations:
                expr = f'quartz_expr:({expr})'
            out.write(translate_let(f'{name}_upd', expr, use_notations))
            if use_notations:
                close_parens += 1
            for i, bit in enumerate(p['bits']):
                expr = rhs_tbl[bit]
                if use_notations:
                    out.write(f'  let {name}_upd <- (#{name}_upd)[{idxw} \'d {i}] = {expr} in\n')
                else:
                    out.write(f'  eexpr.Bind "{name}_upd" quartz_eexpr:((#{name}_upd)[{idxw} \'d {i}] = {expr}) (fun {name}_upd =>\n')
                    close_parens += 1
            if use_notations:
                out.write(f'  let _new_st <- #_new_st..{name} = #{name}_upd in\n')
            else:
                out.write(f'  eexpr.Bind "_new_st" quartz_eexpr:(_new_st..{name} = {name}_upd) (fun _new_st =>\n')
                close_parens += 1

    if use_notations:
        out.write('return #_new_st))')
    else:
        out.write('eexpr.Ret (expr.Var _new_st)')
        out.write(')' * close_parens)
    out.write('.\n\n')
    out.write(f'Definition {mname}')
    out.write(' {var fn}')
    out.write(f' := fns.package_global_fns\'\' var fn (@{mname}_inner).\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Translate a JSON representation of a netlist into a Rocq file that represents the same logic using quartz.')
    parser.add_argument('json', type=argparse.FileType('r'), help='JSON representation of a netlist, as supplied by Yosys. Logic must be purely combinational.')
    parser.add_argument('-o', '--out', required=False, default='-', type=argparse.FileType('w'), help='Destination Rocq file.')
    args = parser.parse_args()

    print(f'json_to_quartz: {args.json.name} -> {args.out.name}')
    args.out.write(PREFIX)
    modules = json.loads(args.json.read())['modules']
    for m in modules:
        translate_module(m, modules[m], args.out, True)
