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

typedef struct packed { bit[0:0] o_clk1_qb; bit[0:0] o_clk2_qa; bit[0:0] qa; bit[0:0] qb; } state__1B_1B_1B_1B_4S;
typedef struct packed { bit[0:0] clk_a; bit[0:0] clk_b; bit[0:0] d; } req__1B_1B_1B_3S;

function automatic state__1B_1B_1B_1B_4S twoclk_comb_inner_specialization_1 (
  input Pair#(state__1B_1B_1B_1B_4S, req__1B_1B_1B_3S)::t p);
  begin state__1B_1B_1B_1B_4S _st_0 = Pair#(state__1B_1B_1B_1B_4S, req__1B_1B_1B_3S)::fst(p);
  begin req__1B_1B_1B_3S _d_1 = Pair#(state__1B_1B_1B_1B_4S, req__1B_1B_1B_3S)::snd(p);
  begin bit[0:0] _st_o_clk1_qb_2 = _st_0.o_clk1_qb;
  begin bit[0:0] _st_o_clk2_qa_3 = _st_0.o_clk2_qa;
  begin bit[0:0] _d_clk_a_4 = _d_1.clk_a;
  begin bit[0:0] _d_clk_b_5 = _d_1.clk_b;
  begin bit[0:0] _d_d_6 = _d_1.d;
  begin state__1B_1B_1B_1B_4S _new_st_7 = _st_0;
  begin state__1B_1B_1B_1B_4S _new_st_8;
  _new_st_8 = _new_st_7;
  _new_st_8.qa = _st_o_clk2_qa_3;
  begin state__1B_1B_1B_1B_4S _new_st_9;
  _new_st_9 = _new_st_8;
  _new_st_9.qb = _st_o_clk1_qb_2;
  begin state__1B_1B_1B_1B_4S _new_st_10;
  _new_st_10 = _new_st_9;
  _new_st_10.o_clk1_qb = _d_d_6;
  begin state__1B_1B_1B_1B_4S _new_st_11;
  _new_st_11 = _new_st_10;
  _new_st_11.o_clk2_qa = _d_d_6;
  twoclk_comb_inner_specialization_1 = _new_st_11; end end end end end end end end end end end end
endfunction

function automatic state__1B_1B_1B_1B_4S twoclk_comb_inner (
  input Pair#(state__1B_1B_1B_1B_4S, req__1B_1B_1B_3S)::t x);
  twoclk_comb_inner = twoclk_comb_inner_specialization_1(x);
endfunction

