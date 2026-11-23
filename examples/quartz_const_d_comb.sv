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

typedef struct packed { bit[0:0] o_clk1_q1; bit[0:0] o_clk1_q0; bit[0:0] q0; bit[0:0] q1; } state__1B_1B_1B_1B_4S;
typedef struct packed { bit[0:0] clk; bit[0:0] d; } req__1B_1B_2S;

function automatic state__1B_1B_1B_1B_4S const_d_comb_inner_specialization_1 (
  input Pair#(state__1B_1B_1B_1B_4S, req__1B_1B_2S)::t p);
  begin state__1B_1B_1B_1B_4S _st_0 = Pair#(state__1B_1B_1B_1B_4S, req__1B_1B_2S)::fst(p);
  begin req__1B_1B_2S _d_1 = Pair#(state__1B_1B_1B_1B_4S, req__1B_1B_2S)::snd(p);
  begin bit[0:0] _st_o_clk1_q1_2 = _st_0.o_clk1_q1;
  begin bit[0:0] _st_o_clk1_q0_3 = _st_0.o_clk1_q0;
  begin bit[0:0] _d_clk_4 = _d_1.clk;
  begin bit[0:0] _d_d_5 = _d_1.d;
  begin bit[0:0] i_clk1_q1_6 = 1'd1;
  begin state__1B_1B_1B_1B_4S _new_st_7 = _st_0;
  begin state__1B_1B_1B_1B_4S _new_st_8;
  _new_st_8 = _new_st_7;
  _new_st_8.q0 = _st_o_clk1_q0_3;
  begin state__1B_1B_1B_1B_4S _new_st_9;
  _new_st_9 = _new_st_8;
  _new_st_9.q1 = _st_o_clk1_q1_2;
  begin state__1B_1B_1B_1B_4S _new_st_10;
  _new_st_10 = _new_st_9;
  _new_st_10.o_clk1_q1 = i_clk1_q1_6;
  begin state__1B_1B_1B_1B_4S _new_st_11;
  _new_st_11 = _new_st_10;
  _new_st_11.o_clk1_q0 = _d_d_5;
  const_d_comb_inner_specialization_1 = _new_st_11; end end end end end end end end end end end end
endfunction

function automatic state__1B_1B_1B_1B_4S const_d_comb_inner (
  input Pair#(state__1B_1B_1B_1B_4S, req__1B_1B_2S)::t x);
  const_d_comb_inner = const_d_comb_inner_specialization_1(x);
endfunction

