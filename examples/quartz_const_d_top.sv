/* Handwritten sequential part. */

`include "quartz_const_d_comb.sv"

typedef state__1B_1B_1B_1B_4S state;
typedef req__1B_1B_2S req;

module const_d(input clk, input d, output q0, output q1);
    state s;
    state next;
    req r;

    assign r.clk = clk;
    assign r.d = d;
    assign next = const_d_comb_inner(Pair#(state, req)::mk (s, r));
    assign q0 = next.q0;
    assign q1 = next.q1;

    always @(posedge clk)
        s <= next;

endmodule
