/* Handwritten sequential part. */

`include "quartz_counter_comb.sv"

typedef state__1B_1B_1B_1B_3A_4S state;
typedef req__1B_1B_2S req;

module counter(input clk, input en, input resetn, output [2:0] count);
    state s;
    state next_state;
    req r;

    assign r.resetn = resetn;
    assign r.en = en;

    // the below should work, but it doesn't because the count gets updated
    // a cycle later!
    // assign count = s.count
    assign count[0] = s.o_clk1_q_0;
    assign count[1] = s.o_clk1_q_1;
    assign count[2] = s.o_clk1_q_2;

    always @(posedge clk)
      s <= counter_comb_inner(Pair#(state, req)::mk (s, r));

endmodule
