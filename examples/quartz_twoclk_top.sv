/* Handwritten sequential part. */

`include "quartz_twoclk_comb.sv"

typedef state__1B_1B_1B_1B_4S state;
typedef req__1B_1B_1B_3S req;

module twoclk(clk_a, clk_b, d, qa, qb);
    input clk_a;
    input clk_b;
    input d;
    output qa;
    output qb;

    state s;
    state next;
    req r;

    assign r.clk_a = clk_a;
    assign r.clk_b = clk_b;
    assign r.d = d;
    assign next = twoclk_comb_inner(Pair#(state, req)::mk (s, r));
    assign qa = next.qa;
    assign qb = next.qb;

    // only change the ff interfaces that are gated on clk_a
    always @(posedge clk_a) begin
        s.o_clk2_qa <= next.o_clk2_qa;
    end
    // only change the ff interfaces that are gated on clk_b
    always @(posedge clk_b) begin
        s.o_clk1_qb <= next.o_clk1_qb;
    end

endmodule
