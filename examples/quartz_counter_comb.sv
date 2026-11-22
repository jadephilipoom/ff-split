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
typedef struct packed { bit[0:0] resetn; bit[0:0] en; } req__1B_1B_2S;

function automatic state__1B_1B_1B_1B_3A_4S counter_comb_inner_specialization_1 (
  input Pair#(state__1B_1B_1B_1B_3A_4S, req__1B_1B_2S)::t p);
  begin state__1B_1B_1B_1B_3A_4S _st_0 = Pair#(state__1B_1B_1B_1B_3A_4S, req__1B_1B_2S)::fst(p);
  begin req__1B_1B_2S _d_1 = Pair#(state__1B_1B_1B_1B_3A_4S, req__1B_1B_2S)::snd(p);
  begin bit[0:0] g_2 = (_d_1.en & _d_1.resetn);
  begin bit[0:0] n_1_3 = (_st_0.o_clk1_q_1 ^ (_st_0.o_clk1_q_0 & g_2));
  begin bit[0:0] i_clk1_q_1_4 = (_d_1.resetn ? n_1_3 : 1'd0);
  begin bit[0:0] n_2_5 = (_st_0.o_clk1_q_2 ^ ((_st_0.o_clk1_q_1 & _st_0.o_clk1_q_0) & g_2));
  begin bit[0:0] n_0_6 = (_st_0.o_clk1_q_0 ^ g_2);
  begin bit[0:0] i_clk1_q_2_7 = (_d_1.resetn ? n_2_5 : 1'd0);
  begin bit[0:0] i_clk1_q_0_8 = (_d_1.resetn ? n_0_6 : 1'd0);
  begin state__1B_1B_1B_1B_3A_4S _new_st_9 = _st_0;
  begin bit[3-1:0][0:0] count_upd_10 = _new_st_9.count;
  begin bit[3-1:0][0:0] count_upd_11;
  count_upd_11 = count_upd_10;
  count_upd_11[Pair#(bit[1:0], unit)::mk(2'd0, tt).fst] = _st_0.o_clk1_q_0;
  begin bit[3-1:0][0:0] count_upd_12;
  count_upd_12 = count_upd_11;
  count_upd_12[Pair#(bit[1:0], unit)::mk(2'd1, tt).fst] = _st_0.o_clk1_q_1;
  begin bit[3-1:0][0:0] count_upd_13;
  count_upd_13 = count_upd_12;
  count_upd_13[Pair#(bit[1:0], unit)::mk(2'd2, tt).fst] = _st_0.o_clk1_q_2;
  begin state__1B_1B_1B_1B_3A_4S _new_st_14;
  _new_st_14 = _new_st_9;
  _new_st_14.count = count_upd_13;
  begin state__1B_1B_1B_1B_3A_4S _new_st_15;
  _new_st_15 = _new_st_14;
  _new_st_15.o_clk1_q_2 = i_clk1_q_2_7;
  begin state__1B_1B_1B_1B_3A_4S _new_st_16;
  _new_st_16 = _new_st_15;
  _new_st_16.o_clk1_q_1 = i_clk1_q_1_4;
  begin state__1B_1B_1B_1B_3A_4S _new_st_17;
  _new_st_17 = _new_st_16;
  _new_st_17.o_clk1_q_0 = i_clk1_q_0_8;
  counter_comb_inner_specialization_1 = _new_st_17; end end end end end end end end end end end end end end end end end end
endfunction

function automatic state__1B_1B_1B_1B_3A_4S counter_comb_inner (
  input Pair#(state__1B_1B_1B_1B_3A_4S, req__1B_1B_2S)::t x);
  counter_comb_inner = counter_comb_inner_specialization_1(x);
endfunction

