/* Handwritten sequential part. */

`include "quartz_counter_comb.sv"

typedef state__1B_1B_1B_1B_3A_4S state;
typedef req__1B_1B_2S req;

module counter(input clk, input en, input resetn, output [2:0] count);
    state s;
    req r;

    assign r.resetn = resetn;
    assign r.en = en;
    assign count = s.count;

    always @(posedge clk)
      s <= counter_comb_inner(Pair#(state, req)::mk (s, r));
endmodule
