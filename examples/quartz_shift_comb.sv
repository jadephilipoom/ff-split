// Generated from Rocq by Quartz (experimental prototype version)
typedef enum bit { tt } unit; // no zero-size types in SystemVerilog :/

class Pair #(parameter type A, parameter type B);
  typedef struct packed { A fst; B snd; } t;
  static function A fst (t p); return p.fst; endfunction
  static function B snd (t p); return p.snd; endfunction
  static function t mk (A a, B b); return t'{a, b}; endfunction
endclass

class Either #(parameter type A, parameter type B);
  typedef union tagged packed { A left; B right; } t;
  static function t left(A a); return tagged left a; endfunction
  static function t right(B b); return tagged right b; endfunction
endclass

typedef struct packed { bit[0:0] o_clk1_q_2; bit[0:0] o_clk1_q_1; bit[0:0] o_clk1_q_0; bit[3-1:0][0:0] q; } state__1B_1B_1B_1B_3A_4S;
typedef struct packed { bit[0:0] d; } req__1B_1S;

function automatic state__1B_1B_1B_1B_3A_4S shift_comb_inner_specialization_1 (
  input Pair#(state__1B_1B_1B_1B_3A_4S, req__1B_1S)::t p);
  begin state__1B_1B_1B_1B_3A_4S _st_0 = Pair#(state__1B_1B_1B_1B_3A_4S, req__1B_1S)::fst(p);
  begin req__1B_1S _d_1 = Pair#(state__1B_1B_1B_1B_3A_4S, req__1B_1S)::snd(p);
  begin bit[0:0] i_clk1_q_2_2 = _st_0.o_clk1_q_1;
  begin bit[0:0] i_clk1_q_1_3 = _st_0.o_clk1_q_0;
  begin state__1B_1B_1B_1B_3A_4S _new_st_4 = _st_0;
  begin bit[3-1:0][0:0] q_upd_5 = _new_st_4.q;
  begin bit[3-1:0][0:0] q_upd_6;
  q_upd_6 = q_upd_5;
  q_upd_6[Pair#(bit[1:0], unit)::mk(2'd0, tt).fst] = _st_0.o_clk1_q_0;
  begin bit[3-1:0][0:0] q_upd_7;
  q_upd_7 = q_upd_6;
  q_upd_7[Pair#(bit[1:0], unit)::mk(2'd1, tt).fst] = _st_0.o_clk1_q_1;
  begin bit[3-1:0][0:0] q_upd_8;
  q_upd_8 = q_upd_7;
  q_upd_8[Pair#(bit[1:0], unit)::mk(2'd2, tt).fst] = _st_0.o_clk1_q_2;
  begin state__1B_1B_1B_1B_3A_4S _new_st_9;
  _new_st_9 = _new_st_4;
  _new_st_9.q = q_upd_8;
  begin state__1B_1B_1B_1B_3A_4S _new_st_10;
  _new_st_10 = _new_st_9;
  _new_st_10.o_clk1_q_2 = i_clk1_q_2_2;
  begin state__1B_1B_1B_1B_3A_4S _new_st_11;
  _new_st_11 = _new_st_10;
  _new_st_11.o_clk1_q_1 = i_clk1_q_1_3;
  begin state__1B_1B_1B_1B_3A_4S _new_st_12;
  _new_st_12 = _new_st_11;
  _new_st_12.o_clk1_q_0 = _d_1.d;
  shift_comb_inner_specialization_1 = _new_st_12; end end end end end end end end end end end end end
endfunction

function automatic state__1B_1B_1B_1B_3A_4S shift_comb_inner (
  input Pair#(state__1B_1B_1B_1B_3A_4S, req__1B_1S)::t x);
  shift_comb_inner = shift_comb_inner_specialization_1(x);
endfunction

