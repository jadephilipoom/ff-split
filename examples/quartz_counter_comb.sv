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

typedef struct packed { bit[0:0] o_clk1_q_2; bit[0:0] o_clk1_q_1; bit[0:0] o_clk1_q_0; bit[3-1:0][0:0] count; } state__1B_1B_1B_1B_3A_4S;
typedef struct packed { bit[0:0] clk; bit[0:0] resetn; bit[0:0] en; } req__1B_1B_1B_3S;

function automatic state__1B_1B_1B_1B_3A_4S counter_comb_inner_specialization_1 (
  input Pair#(state__1B_1B_1B_1B_3A_4S, req__1B_1B_1B_3S)::t p);
  begin state__1B_1B_1B_1B_3A_4S _st_0 = Pair#(state__1B_1B_1B_1B_3A_4S, req__1B_1B_1B_3S)::fst(p);
  begin req__1B_1B_1B_3S _d_1 = Pair#(state__1B_1B_1B_1B_3A_4S, req__1B_1B_1B_3S)::snd(p);
  begin bit[0:0] _st_o_clk1_q_2_2 = _st_0.o_clk1_q_2;
  begin bit[0:0] _st_o_clk1_q_1_3 = _st_0.o_clk1_q_1;
  begin bit[0:0] _st_o_clk1_q_0_4 = _st_0.o_clk1_q_0;
  begin bit[0:0] _d_clk_5 = _d_1.clk;
  begin bit[0:0] _d_resetn_6 = _d_1.resetn;
  begin bit[0:0] _d_en_7 = _d_1.en;
  begin bit[0:0] g_8 = (_d_en_7 & _d_resetn_6);
  begin bit[0:0] n_0_9 = (_st_o_clk1_q_0_4 ^ g_8);
  begin bit[0:0] i_clk1_q_0_10 = (_d_resetn_6 ? n_0_9 : 1'd0);
  begin bit[0:0] n_1_11 = (_st_o_clk1_q_1_3 ^ (_st_o_clk1_q_0_4 & g_8));
  begin bit[0:0] n_2_12 = (_st_o_clk1_q_2_2 ^ ((_st_o_clk1_q_1_3 & _st_o_clk1_q_0_4) & g_8));
  begin bit[0:0] i_clk1_q_2_13 = (_d_resetn_6 ? n_2_12 : 1'd0);
  begin bit[0:0] i_clk1_q_1_14 = (_d_resetn_6 ? n_1_11 : 1'd0);
  begin state__1B_1B_1B_1B_3A_4S _new_st_15 = _st_0;
  begin bit[3-1:0][0:0] count_upd_16 = _new_st_15.count;
  begin bit[3-1:0][0:0] count_upd_17;
  count_upd_17 = count_upd_16;
  count_upd_17[Pair#(bit[1:0], unit)::mk(2'd0, tt).fst] = _st_o_clk1_q_0_4;
  begin bit[3-1:0][0:0] count_upd_18;
  count_upd_18 = count_upd_17;
  count_upd_18[Pair#(bit[1:0], unit)::mk(2'd1, tt).fst] = _st_o_clk1_q_1_3;
  begin bit[3-1:0][0:0] count_upd_19;
  count_upd_19 = count_upd_18;
  count_upd_19[Pair#(bit[1:0], unit)::mk(2'd2, tt).fst] = _st_o_clk1_q_2_2;
  begin state__1B_1B_1B_1B_3A_4S _new_st_20;
  _new_st_20 = _new_st_15;
  _new_st_20.count = count_upd_19;
  begin state__1B_1B_1B_1B_3A_4S _new_st_21;
  _new_st_21 = _new_st_20;
  _new_st_21.o_clk1_q_2 = i_clk1_q_2_13;
  begin state__1B_1B_1B_1B_3A_4S _new_st_22;
  _new_st_22 = _new_st_21;
  _new_st_22.o_clk1_q_1 = i_clk1_q_1_14;
  begin state__1B_1B_1B_1B_3A_4S _new_st_23;
  _new_st_23 = _new_st_22;
  _new_st_23.o_clk1_q_0 = i_clk1_q_0_10;
  counter_comb_inner_specialization_1 = _new_st_23; end end end end end end end end end end end end end end end end end end end end end end end end
endfunction

function automatic state__1B_1B_1B_1B_3A_4S counter_comb_inner (
  input Pair#(state__1B_1B_1B_1B_3A_4S, req__1B_1B_1B_3S)::t x);
  counter_comb_inner = counter_comb_inner_specialization_1(x);
endfunction

