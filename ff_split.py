#!/usr/bin/env python3
"""Split a yosys JSON netlist at its synchronous elements.

This tool takes in a flattened yosys `write_json` netlist (as produced
by `read_verilog <file>.v; proc; write_json <file>.json`).

In this format, flip flops appear as `$dff` cells, and latches as `$dlatch`
cells.

The tool then partitions the design into:

  * a combinational module  : every original top-level port, all combinational
                              cells, and a synchronous interface.
  * a synchronous module    : only the flip flops / latches.
  * a top-level module      : instantiates the two and wires them together,
                              exposing only the original ports.

The top-level module is useful for checking equivalence between the
partitioned and original designs.

Interface naming convention:

  clkN              clock nets, enumerated in first-seen order (clk1, clk2...).
                    output of the combinational module, input of the sync
                    module.  Use --list-clocks to see which net became which.
  i_clkN_<sig>      D-side of a sync element (the signal going *in* to the
                    flip flop clocked by clkN, named after the driving wire).
                    output of the combinational module, input of the sync one.
  o_clkN_<sig>      Q-side of a sync element (the signal coming *out* of the
                    flip flop clocked by clkN).  Input of the combinational
                    module, output of the sync one.

Each output JSON file is standalone-readable by yosys `read_json`; the
`*_split.json` top-level file additionally embeds the combinational and
sync modules so that `read_json *_split.json` alone pulls in everything.

Only `$dff` and `$dlatch` sequential cells are accepted; anything fancier
(resets, enables, set/reset cells) aborts instead of being mishandled.

If your source netlist has those, synthesize them away first (fold resets and
enables into the D logic, e.g. with a stdcell mapping that emits bare DFFs).

Requires Python 3.8+ and (for --verify) yosys on PATH.
"""

import argparse
import copy
import json
import re
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

# Yosys constant bits: 0 = constant 1'b0, 1 = constant 1'b1.
CONST_BITS = (0, 1)

# Supported sequential cell types -> name of the port that carries the clock
# (for $dlatch, the level-enable plays the role of the clock).
FF_CLOCK_PORTS = OrderedDict(
    [
        ("$dff", "CLK"),
        ("$dlatch", "EN"),
    ]
)


def top_module_name(design):
    """Pick the top module of a loaded design: the non-empty module that no
    other module instantiates."""
    modules = design["modules"]
    instantiated = set()
    for module in modules.values():
        for cell in module.get("cells", {}).values():
            if cell["type"] in modules:
                instantiated.add(cell["type"])
    candidates = [
        name for name, module in modules.items()
        if module.get("cells") and name not in instantiated
    ]
    if len(candidates) != 1:
        raise KeyError(candidates or list(modules))
    return candidates[0]


def die(message):
    print("ff_split: error: {}".format(message), file=sys.stderr)
    sys.exit(1)


def is_sequential(cell_type):
    """True for yosys cell types that hold state (whether supported or not).

    Catches $dff/$dlatch variants plus every yosys sequential primitive
    ($aldff, $adff, $sdff, $dffsr, $dffss, $sr, $dFFE, $_DFF_*_, ...) so the
    splitter aborts instead of dumping unknown state into the combinational
    half.  Case-insensitive for gate-library style names.
    """
    if cell_type in FF_CLOCK_PORTS:
        return True
    # dff covers $aldff/$adff/$dffsr/$dffss/$_DFF_*_/$_DFFSR_*_ ...;
    # sr covers $sr and $_SR_*_ (anchored at a non-alphanumeric edge so
    # combinational cells merely containing "sr" do not match).
    return bool(re.search(r"dff|latch|ffr|(^|[^A-Za-z0-9])sr([^A-Za-z0-9]|$)",
                          cell_type, re.IGNORECASE))


def sanitize(name):
    """Turn a (possibly escaped, possibly multi-character) yosys net name
    into a safe verilog identifier."""
    name = name.strip().lstrip("\\").strip()
    name = re.sub(r"[^A-Za-z0-9_]+", "_", name)
    return name.strip("_") or "net"


class NameAllocator:
    """Hands out unique port names, keeping them stable given the same input."""

    def __init__(self, taken):
        self.used = set(taken)

    def alloc(self, base):
        stem = sanitize(base)
        candidate = stem
        index = 2
        while candidate in self.used:
            candidate = "{}_{}".format(stem, index)
            index += 1
        self.used.add(candidate)
        return candidate


def normalize_bit(bit):
    """Canonical form for one entry of a bit vector.

    Older yosys (0.9, how the example netlists were emitted) writes the
    constants as the integers 0/1; the documented format (and yosys 0.33)
    uses the strings "0", "1", "x", "z".  A plain integer is always a real
    net id -- net ids start at 2, so 0/1 as integers are unambiguous.
    """
    if bit in (0, "0"):
        return 0
    if bit in (1, "1"):
        return 1
    if bit is None or bit in ("x", "z", "X", "Z"):
        return None
    return bit


def normalize_module(module):
    """Rewrite every bit vector in place through normalize_bit()."""
    for details in module["ports"].values():
        details["bits"] = [normalize_bit(b) for b in details["bits"]]
    for cell in module["cells"].values():
        cell["connections"] = {
            port: [normalize_bit(b) for b in bits]
            for port, bits in cell["connections"].items()
        }
    for details in module["netnames"].values():
        details["bits"] = [normalize_bit(b) for b in details["bits"]]


def load_single_module(path, module_name=None):
    """Read a yosys JSON file and pick the module to partition."""
    with open(path) as handle:
        design = json.load(handle)
    modules = design["modules"]
    if module_name is None:
        try:
            module_name = top_module_name(design)
        except KeyError:
            die(
                "cannot guess top module, candidates {}. use --module".format(
                    modules.keys()
                )
            )
    if module_name not in modules:
        die("module '{}' not in {}".format(module_name, sorted(modules)))
    module = modules[module_name]
    normalize_module(module)
    return module_name, module


def preferred_net_names(module):
    """Return {net_id: suggested base name} using the module's netnames.

    Bit k of a multi-bit wire N is suggested as N_k so per-bit flip flop
    ports such as i_clk1_pcpi_rs2_24 stay readable.
    """
    best = {}
    port_of_bit = {}
    for port_name, details in module["ports"].items():
        if len(details["bits"]) == 1:
            port_of_bit.setdefault(details["bits"][0], port_name)
    for netname, details in module["netnames"].items():
        bits = details["bits"]
        hidden = bool(details.get("hide_name")) or netname.startswith("$")
        for position, bit in enumerate(bits):
            if bit is None or bit in CONST_BITS:
                continue
            if len(bits) == 1:
                base = netname
            else:
                base = "{}_{}".format(netname, position)
            # prefer: visible names, netname equal to the port name, short,
            # alphabetical
            rank = (
                1 if hidden else 0,
                0 if port_of_bit.get(bit) == netname else 1,
                len(netname),
                netname,
            )
            previous = best.get(bit)
            if previous is None or rank < previous[0]:
                best[bit] = (rank, base)
    return {bit: base for bit, (_, base) in best.items()}


def clock_name(index, net_id, net_names):
    """Name the clock wires.  index counts from 1.

    This is the hook to edit if the auto-generated clock net names are too
    cumbersome and you want something smarter than clk1, clk2, clk3; net_names
    lists the (possibly autogenerated) names attached to the clock net.
    """
    return "clk{}".format(index)


def enumerate_clocks(module, ff_cells):
    """Enumerate the distinct clock wires driving the sync elements.

    These are the clocks of the original always @(posedge ...) blocks: every
    $dff CLK pin / $dlatch EN pin is a clock input.  Returns an OrderedDict
    {net_id: (chosen_name, driven_by_comb)} in first-seen order (cell order,
    then port order).  driven_by_comb is False when the clock net is simply
    one of the original top-level input bits (e.g. the primary clock pin);
    in that case the combinational half has nothing to drive and the clock
    is not re-exported as a port there.
    """
    net_names = preferred_net_names(module)
    input_bits = set()
    for details in module["ports"].values():
        if details["direction"] == "input":
            input_bits.update(details["bits"])
    driven_bits = set()
    for cell in module["cells"].values():
        for port, bits in cell["connections"].items():
            if cell["port_directions"].get(port) == "output":
                driven_bits.update(bits)

    clock_nets = OrderedDict()
    for cell_name, cell in ff_cells.items():
        clk_port = FF_CLOCK_PORTS[cell["type"]]
        bits = cell["connections"][clk_port]
        if len(bits) != 1 or bits[0] is None:
            die("cell {} clock port {} is not a single net".format(cell_name, clk_port))
        if bits[0] in CONST_BITS:
            die("cell {} is clocked by a constant".format(cell_name))
        clock_nets.setdefault(bits[0], None)
    used_names = set(module["ports"].keys())
    for index, net_id in enumerate(clock_nets, start=1):
        if net_id not in input_bits and net_id not in driven_bits:
            die("clock net {} ({}) is neither a primary input nor driven".format(
                net_id, net_names.get(net_id, "?")))
        name = clock_name(index, net_id, net_names.get(net_id, str(net_id)))
        suffix = 2
        while name in used_names:
            name = "{}_{}".format(clock_name(index, net_id, ""), suffix)
            suffix += 1
        used_names.add(name)
        clock_nets[net_id] = (name, net_id not in input_bits)
    return clock_nets


def new_cell(cell_type, connections, port_directions, parameters):
    return {
        "hide_name": 1,
        "type": cell_type,
        "parameters": parameters,
        "attributes": {},
        "port_directions": port_directions,
        "connections": connections,
    }


def port_entry(direction, bits):
    return {"direction": direction, "bits": list(bits)}


def collect_module_nets(module):
    """Every net id referenced by ports or cells of a module."""
    nets = set()
    for details in module["ports"].values():
        nets.update(b for b in details["bits"] if b is not None and b not in CONST_BITS)
    for cell in module["cells"].values():
        for bits in cell["connections"].values():
            nets.update(b for b in bits if b is not None and b not in CONST_BITS)
    return nets


def build_netnames(module, source_module, extra_names):
    """Netnames for a derived module: every port gets its own entry (yosys
    derives wire declarations from them), plus original names for internal
    wires that survived into this module."""
    netnames = OrderedDict()
    for port_name, details in module["ports"].items():
        # Drop constant bits: yosys derives the port declaration from the
        # ports section, and a netname that claims to name a constant would
        # confuse write_verilog.
        bits = [b for b in details["bits"] if b is not None and b not in CONST_BITS]
        if bits:
            netnames[port_name] = {"hide_name": 0, "bits": bits, "attributes": {}}
    used_nets = collect_module_nets(module)
    for netname, details in source_module["netnames"].items():
        if netname in netnames or netname in extra_names:
            continue
        bits = details["bits"]
        if not bits or any(b is None or b not in used_nets for b in bits):
            continue
        netnames[netname] = copy.deepcopy(details)
    for netname, bits in extra_names.items():
        if netname not in netnames:
            netnames[netname] = {"hide_name": 0, "bits": list(bits), "attributes": {}}
    return netnames


class FlipFlop:
    """One bit of one sync element, plus the wire names it contributes."""

    def __init__(self, cell_name, cell, index, d_net, q_net, clk_net, in_name, out_name):
        self.cell_name = cell_name
        self.cell = cell
        self.index = index
        self.d_net = d_net  # net after any constant buffering
        self.q_net = q_net
        self.clk_net = clk_net
        self.in_name = in_name
        self.out_name = out_name


def split_module(modname, module):
    """Partition one module; returns (comb, sync, top) module dicts."""
    cells = module["cells"]
    # first check that json has been reduced
    for cell_name, cell in cells.items():
        if cell["type"] not in FF_CLOCK_PORTS and is_sequential(cell["type"]):
            die(
                "cell {} of type {} is sequential but not a plain $dff/$dlatch; "
                "fold its reset/enable into the D logic first".format(
                    cell_name, cell["type"]
                )
            )
    ff_cells = OrderedDict()
    for n, c in cells.items():
        if c["type"] in FF_CLOCK_PORTS:
            ff_cells[n] = c
    if not ff_cells:
        die("module {} contains no $dff/$dlatch cells to split on".format(modname))

    clock_nets = enumerate_clocks(module, ff_cells)
    base_names = preferred_net_names(module)

    # ---- collect one record per sync element *bit* -------------------------
    # i_*/o_* names must not collide with original ports or with clock wire
    # names (a design with a port literally named clk1 would collide).
    orig_port_names = list(module["ports"].keys())
    orig_port_names.extend(name for name, _ in clock_nets.values())
    in_alloc = NameAllocator(orig_port_names)
    out_alloc = NameAllocator(orig_port_names)
    net_id_cursor = max(collect_module_nets(module)) + 1

    flip_flops = []
    buffer_cells = {}
    # Aggregate all the sync element nets, so we can re-name nets in the
    # case of a degenerate q -> d "no logic wire".
    #
    # The problem is that yosys write_verilog emits the net
    # as both `input` and a block-assigned `reg`.
    #
    # When such a situation is encountered, use the same mechanism that constants
    # usee, e.g. an explicit $pos pass-through of the Q net. This means every FF
    # bit uniformly receives its D through an i_* port and degenerate wires stay
    # visible to downstream tools instead of being aliased away.
    q_nets = set(
        bit
        for cell in ff_cells.values()
        for bit in cell["connections"]["Q"]
        if bit is not None and bit not in CONST_BITS
    )
    for cell_name, cell in ff_cells.items():
        clk_port = FF_CLOCK_PORTS[cell["type"]]
        d_bits = cell["connections"]["D"]
        q_bits = cell["connections"]["Q"]
        if len(d_bits) != len(q_bits):
            die("cell {} has mismatched D/Q widths".format(cell_name))
        clk_net = cell["connections"][clk_port][0]
        for index, (d_bit, q_bit) in enumerate(zip(d_bits, q_bits)):
            if q_bit is None or q_bit in CONST_BITS:
                die("cell {} bit {} has a constant/undef output".format(cell_name, index))
            d_net = d_bit
            if d_bit is None:
                die("cell {} bit {} has an undef input".format(cell_name, index))
            if d_bit in CONST_BITS or d_bit in q_nets:
                # Keep the "input to the sync element" a real wire driven by
                # the combinational partition: drive the constant (or the
                # upstream flop's Q net) through a buffer cell that stays in
                # the combinational partition.
                d_net = net_id_cursor
                net_id_cursor += 1
                buffer_cells["{}$ffsplit_buf${}${}".format(
                    modname, cell_name.replace("$", "_"), index
                )] = new_cell(
                    "$pos",
                    {"A": [d_bit], "Y": [d_net]},
                    {"A": "input", "Y": "output"},
                    {"A_SIGNED": 0, "A_WIDTH": 1, "Y_WIDTH": 1},
                )
            q_base = base_names.get(q_bit, "{}_q{}".format(sanitize(cell_name), index))
            # d basenames seem to typically be less readable and it's nice if corresponding ff signals have matching names
            # d_base = base_names.get(d_bit, "{}_d{}".format(sanitize(cell_name), index))
            d_base = q_base
            clk_label = clock_nets[clk_net][0]
            flip_flops.append(
                FlipFlop(
                    cell_name,
                    cell,
                    index,
                    d_net,
                    q_bit,
                    clk_net,
                    in_alloc.alloc("i_{}_{}".format(clk_label, d_base)),
                    out_alloc.alloc("o_{}_{}".format(clk_label, q_base)),
                )
            )
    for flip_flop in flip_flops:
        flip_flop.clk = clock_nets[flip_flop.clk_net][0]

    # ---- combinational partition -------------------------------------------
    comb = {
        "attributes": {},
        "ports": OrderedDict(),
        "cells": OrderedDict(
            [(n, copy.deepcopy(c)) for n, c in cells.items() if n not in ff_cells]
        ),
        "netnames": OrderedDict(),
    }
    comb["cells"].update(buffer_cells)
    for name, details in module["ports"].items():
        comb["ports"][name] = port_entry(details["direction"], details["bits"])
    for net_id, (name, driven_by_comb) in clock_nets.items():
        if driven_by_comb:
            comb["ports"][name] = port_entry("output", [net_id])
    for flip_flop in flip_flops:
        comb["ports"][flip_flop.in_name] = port_entry("output", [flip_flop.d_net])
        comb["ports"][flip_flop.out_name] = port_entry("input", [flip_flop.q_net])

    # yosys refuses to flatten a design where an instance output port drives
    # constant bits, so an original output port that was tied to a constant
    # (e.g. pcpi_wait = 1'b0) gets that constant re-driven inside the
    # combinational half through a buffer cell.
    const_nets = {}
    for name in module["ports"]:
        details = comb["ports"][name]
        if details["direction"] != "output":
            continue
        for index, bit in enumerate(details["bits"]):
            if bit not in CONST_BITS:
                continue
            if bit not in const_nets:
                const_nets[bit] = net_id_cursor
                net_id_cursor += 1
                # $pos is the plain buffer cell: Y = A, re-driving the
                # constant onto a real net.
                comb["cells"]["{}$ffsplit_const${}".format(modname, bit)] = new_cell(
                    "$pos",
                    {"A": [bit], "Y": [const_nets[bit]]},
                    {"A": "input", "Y": "output"},
                    {"A_SIGNED": 0, "A_WIDTH": 1, "Y_WIDTH": 1},
                )
            details["bits"][index] = const_nets[bit]
    comb_extra = {name: [net_id] for net_id, (name, _) in clock_nets.items()}
    for flip_flop in flip_flops:
        comb_extra[flip_flop.in_name] = [flip_flop.d_net]
        comb_extra[flip_flop.out_name] = [flip_flop.q_net]
    comb["netnames"] = build_netnames(comb, module, comb_extra)

    # ---- synchronous partition ---------------------------------------------
    sync = {
        "attributes": {},
        "ports": OrderedDict(),
        "cells": OrderedDict(),
        "netnames": OrderedDict(),
    }
    for net_id, (name, _) in clock_nets.items():
        sync["ports"][name] = port_entry("input", [net_id])
    # Every flip-flop D now sits on its own interface net (constants and
    # flop-to-flop Q nets were given fresh driver nets above), so declaring
    # the i_* input port is always sound: sync never also drives that net.
    for flip_flop in flip_flops:
        sync["ports"][flip_flop.in_name] = port_entry("input", [flip_flop.d_net])
        sync["ports"][flip_flop.out_name] = port_entry("output", [flip_flop.q_net])
        if flip_flop.cell_name not in sync["cells"]:
            new = copy.deepcopy(flip_flop.cell)
            new["connections"] = OrderedDict(new["connections"])
            sync["cells"][flip_flop.cell_name] = new
        new = sync["cells"][flip_flop.cell_name]
        new["connections"]["D"] = list(new["connections"]["D"])
        new["connections"]["D"][flip_flop.index] = flip_flop.d_net
    sync_extra = {name: [net_id] for net_id, (name, _) in clock_nets.items()}
    for flip_flop in flip_flops:
        sync_extra[flip_flop.in_name] = [flip_flop.d_net]
        sync_extra[flip_flop.out_name] = [flip_flop.q_net]
    sync["netnames"] = build_netnames(sync, module, sync_extra)

    # ---- top level ----------------------------------------------------------
    comb_name = modname + "_comb"
    sync_name = modname + "_sync"
    top_name = modname
    top = {
        "attributes": {},
        "ports": OrderedDict(),
        "cells": OrderedDict(),
        "netnames": OrderedDict(),
    }
    for name, details in module["ports"].items():
        top["ports"][name] = port_entry(details["direction"], details["bits"])

    def instance(name, sub_module):
        connections = OrderedDict()
        directions = OrderedDict()
        for port_name, details in sub_module["ports"].items():
            connections[port_name] = list(details["bits"])
            directions[port_name] = details["direction"]
        return {
            "hide_name": 0,
            "type": sub_module["name"],
            "parameters": {},
            "attributes": {},
            "port_directions": directions,
            "connections": connections,
        }

    comb["name"] = comb_name
    sync["name"] = sync_name
    top["cells"]["comb"] = instance("comb", comb)
    top["cells"]["sync"] = instance("sync", sync)
    # Original ports reuse the (possibly constant-materialized) bits of the
    # matching comb ports, so the comb instance is the single driver of any
    # formerly constant-tied output; input ports keep the original bits and
    # may stay constants, which yosys handles fine.
    for name in module["ports"]:
        top["ports"][name] = port_entry(
            comb["ports"][name]["direction"], comb["ports"][name]["bits"]
        )

    # After partitioning, outputs end up with more than one driver. This is perhaps
    # best illustrated with a simple example.
    #
    # module one_ff(input clk, input d, output reg q);
    #   always @(posedge clk) q <= d;
    # endmodule
    #
    # This is partitioned as follows:
    #
    # module one_ff_comb(input clk, input d, output q,
    #                    output i_clk1_d, input o_clk1_q);
    #   assign q = o_clk1_q;      // original output port: must be driven inside comb...
    #   assign i_clk1_d = d;      // ...and the FF-input pass-through output
    # endmodule
    #
    # module one_ff_sync(input clk1, input i_clk1_d, output reg o_clk1_q);
    #   always @(posedge clk1) o_clk1_q <= i_clk1_d;
    # endmodule
    #
    # module naive_split(input clk, input d, output q);
    #   one_ff_comb comb (.clk(clk), .d(d), .q(q), .i_clk1_d(), .o_clk1_q(q));
    #   one_ff_sync sync (.clk1(clk), .i_clk1_d(d), .o_clk1_q(q));
    # endmodule
    #
    # Above we can see .o_clk1_q(q) happens twice.
    #
    # This is resolved according to the following priority order:
    #   sync's Q > top-level input port > comb   [1]
    #
    # In each case, the losing driver moves to a dummy "read-by-nobody" net.
    #
    #   * In the case of an FF output net aliased with an original output
    #     port, the FF output wins (example: pcpi_wr dff output in `mul` example)
    #     The comb port is retained as a dummy net to preserve symmetry
    #   * an FF input net that is also an original input port: (e.g. d in
    #     examples/const_d): the top port wins, comb-side i_* output is
    #     moved to a dummy
    #   * an FF whose input is another FF's output (direct flop-to-flop
    #     connection): sync drives the net from the source Q. comb's
    #     mirrored pass-through driver is moved.
    #
    def real(bits):
        return [b for b in bits if b is not None and b not in CONST_BITS]

    interface = {}  # instance -> {port: bits}
    for inst in ("comb", "sync"):
        interface[inst] = {
            p: list(bits) for p, bits in
            top["cells"][inst]["connections"].items()
            if p not in module["ports"]
        }
    drivers = {}  # (instance, port) -> True
    for inst in ("comb", "sync"):
        for port_name in interface[inst]:
            table = comb["ports"] if inst == "comb" else sync["ports"]
            if table[port_name]["direction"] == "output":
                drivers[(inst, port_name)] = True
    top_input_bits = set()
    for details in top["ports"].values():
        if details["direction"] == "input":
            top_input_bits.update(real(details["bits"]))

    interface_nets = set()
    for bits in interface["comb"].values():
        interface_nets.update(bits)
    for bits in interface["sync"].values():
        interface_nets.update(bits)

    # Resolve the ordering of top input vs comb as per equation [1] in comment above
    for net in sorted(interface_nets):
        net_drivers = [
            (inst, port) for (inst, port) in drivers
            if net in interface[inst][port]
        ]
        port_drives = net in top_input_bits
        if len(net_drivers) + (1 if port_drives else 0) < 2:
            continue
        if any(inst == "sync" for inst, _ in net_drivers):
            winner = ("sync", "source Q wins")
        elif not port_drives:
            winner = ("comb", "only comb drives")
        else:
            winner = (None, "top input port wins")
        for inst, port in net_drivers:
            if inst == winner[0]:
                continue
            fresh = net_id_cursor
            net_id_cursor += 1
            connection = top["cells"][inst]["connections"][port]
            for index, bit in enumerate(connection):
                if bit == net:
                    connection[index] = fresh

    # Resolve sync-Q vs top-level port as per [1]
    # When a top output port bit sits on a sync Q net (the port value *is* a flip flop
    # output, e.g. pcpi_wr), the top port keeps that net -- sync drives it
    # directly, which is exactly the right value -- and only the comb
    # instance's copy of the port, which its internal pass-through drives,
    # moves to a fresh dead-end net.
    sync_driven_bits = set()
    for port, bits in interface["sync"].items():
        if sync["ports"][port]["direction"] == "output":
            sync_driven_bits.update(bits)
    comb_instance = top["cells"]["comb"]["connections"]
    for name in module["ports"]:
        if comb["ports"][name]["direction"] != "output":
            continue
        connection = comb_instance[name]
        for index, bit in enumerate(connection):
            if bit in sync_driven_bits:
                connection[index] = net_id_cursor
                net_id_cursor += 1

    def top_bits(bits):
        return [b for b in bits if b is not None and b not in CONST_BITS]

    top_extra = {}
    for name, details in top["ports"].items():
        bits = [b for b in details["bits"] if b not in CONST_BITS and b is not None]
        if bits:
            top_extra[name] = bits
    for net_id, (name, _) in clock_nets.items():
        top_extra[name] = top_bits([net_id])
    for flip_flop in flip_flops:
        top_extra[flip_flop.in_name] = top_bits([flip_flop.d_net])
        top_extra[flip_flop.out_name] = top_bits([flip_flop.q_net])
    top["netnames"] = build_netnames(top, module, top_extra)

    stats = {
        "flip_flops": len(flip_flops),
        "clocks": OrderedDict(
            (net_id, name) for net_id, (name, _) in clock_nets.items()
        ),
        "comb_cells": len(comb["cells"]),
        "sync_cells": len(sync["cells"]),
    }
    return comb_name, sync_name, top_name, comb, sync, top, stats


def denormalize_bit(bit):
    """Inverse of normalize_bit(), for writing JSON files.

    The documented yosys JSON format spells constants as the strings "0"/
    "1"/"x"; writing them back as integers 0/1 makes yosys 0.33's read_json
    treat them as net ids.
    """
    if bit == 0:
        return "0"
    if bit == 1:
        return "1"
    if bit is None:
        return "x"
    return bit


def denormalize_module(module):
    """Return a copy of a module with bit vectors in write form."""
    module = {k: v for k, v in module.items() if k != "name"}
    module["ports"] = {
        name: {"direction": details["direction"],
               "bits": [denormalize_bit(b) for b in details["bits"]]}
        for name, details in module["ports"].items()
    }
    module["cells"] = {
        name: {
            **{k: v for k, v in cell.items() if k != "connections"},
            "connections": {
                port: [denormalize_bit(b) for b in bits]
                for port, bits in cell["connections"].items()
            },
        }
        for name, cell in module["cells"].items()
    }
    module["netnames"] = {
        name: {**details, "bits": [denormalize_bit(b) for b in details["bits"]]}
        for name, details in module["netnames"].items()
    }
    return module


def dump_module_design(filename, modules):
    """Write a standalone yosys-readable JSON netlist."""
    design = OrderedDict([("creator", "ff_split.py"), ("modules", OrderedDict())])
    for name, module in modules:
        design["modules"][name] = denormalize_module(module)
    with open(filename, "w") as handle:
        json.dump(design, handle, indent=1)
        handle.write("\n")


def yosys_verify(json_path, verilog_path):
    """Confirm yosys can read the file back and write a verilog netlist.

    opt_merge/opt_clean are required for yosys <= ~0.10: its write_verilog
    emits one `assign` per redundant driver of a net (interface pass-
    throughs), which strict simulators reject with MULTIDRIVEN.  Merging
    identical cells first collapses them to a single driver; newer yosys
    backends already coalesce and these passes become a no-op.
    """
    script = "read_json {}; opt_merge; opt_clean -purge; write_verilog -noattr {}".format(
        json_path, verilog_path
    )
    result = subprocess.run(
        ["yosys", "-q", "-p", script], check=False,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        die("yosys failed to read back {}".format(json_path))


def main():
    parser = argparse.ArgumentParser(
        description="Partition a yosys JSON netlist into combinational and "
        "flip-flop halves (for quartz-style synchronous partitioning).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input_json", type=Path, help="input yosys JSON netlist")
    parser.add_argument(
        "--module", default=None, help="top module name (default: sole non-empty module)"
    )
    parser.add_argument(
        "-o", "--outdir", type=Path, default=None,
        help="output directory (default: alongside the input)",
    )
    parser.add_argument(
        "--stem", default=None,
        help="output filename stem (default: input file stem)",
    )
    parser.add_argument(
        "--list-clocks", action="store_true",
        help="only enumerate clock wires and exit",
    )
    # store_true/store_false pair instead of BooleanOptionalAction, which
    # is Python 3.9+ only.
    verify_group = parser.add_mutually_exclusive_group()
    verify_group.add_argument(
        "--verify", dest="verify", action="store_true", default=True,
        help="read each output back with yosys and emit a .v next to it "
        "(default)",
    )
    verify_group.add_argument(
        "--no-verify", dest="verify", action="store_false",
        help="skip the yosys read-back check",
    )
    args = parser.parse_args()

    modname, module = load_single_module(args.input_json, args.module)
    outdir = args.outdir or args.input_json.parent
    stem = args.stem or args.input_json.stem
    outdir.mkdir(parents=True, exist_ok=True)

    if args.list_clocks:
        ff_cells = OrderedDict(
            (n, c) for n, c in module["cells"].items() if c["type"] in FF_CLOCK_PORTS
        )
        if not ff_cells:
            die("no $dff/$dlatch cells found")
        net_names = preferred_net_names(module)
        for net_id, (name, driven) in enumerate_clocks(module, ff_cells).items():
            print("{}: net {} ({}{})".format(
                name, net_id, net_names.get(net_id, "?"),
                "" if driven else ", primary input"))
        return 0

    result = split_module(modname, module)
    comb_name, sync_name, top_name, comb, sync, top, stats = result

    comb_json = outdir / "{}_comb.json".format(stem)
    sync_json = outdir / "{}_sync.json".format(stem)
    top_json = outdir / "{}_top.json".format(stem)
    split_json = outdir / "{}_split.json".format(stem)
    dump_module_design(comb_json, [(comb_name, comb)])
    dump_module_design(sync_json, [(sync_name, sync)])
    dump_module_design(top_json, [(top_name, top)])
    dump_module_design(split_json, [(comb_name, comb), (sync_name, sync), (top_name, top)])

    print("module {} -> {}".format(modname, top_name))
    print("  combinational: {} ({} cells, {} ports) -> {}".format(
        comb_name, stats["comb_cells"], len(comb["ports"]), comb_json))
    print("  synchronous  : {} ({} cells, {} ports) -> {}".format(
        sync_name, stats["sync_cells"], len(sync["ports"]), sync_json))
    print("  top          : {} ({} ports) -> {}".format(
        top_name, len(top["ports"]), top_json))
    print("  split        : {} ({} ports) -> {}".format(
        top_name, len(top["ports"]), split_json))
    print("  clocks: {}".format(
        ", ".join("{}(net {})".format(name, net_id)
                  for net_id, name in stats["clocks"].items())))
    print("  {} sync bits -> i_*/o_* ports".format(stats["flip_flops"]))

    if args.verify:
        for json_path in (comb_json, sync_json, top_json, split_json):
            v_path = json_path.with_suffix(".v")
            yosys_verify(json_path, v_path)
            print("  yosys round-trip OK: {} -> {}".format(json_path, v_path))
    return 0


if __name__ == "__main__":
    main()
