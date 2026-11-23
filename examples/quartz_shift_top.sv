/* Handwritten sequential part. */

`include "quartz_shift_comb.sv"

typedef state__1B_1B_1B_1B_3A_4S state;
typedef req__1B_1B_2S req;

module shift(clk, d, q);
    input clk;
    input d;
    output [2:0] q;

    state s;
    state next;
    req r;

    assign r.clk = clk;
    assign r.d = d;
    assign next = shift_comb_inner(Pair#(state, req)::mk (s, r));
    assign q = next.q;

    always @(posedge clk)
        s <= next;

endmodule
