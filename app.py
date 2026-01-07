import streamlit as st
import pandas as pd
import random
import itertools

# --- 页面配置 ---
st.set_page_config(page_title="羽毛球智能排赛", page_icon="🏸", layout="centered")

# --- CSS 样式 ---
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; }
    .stNumberInput input { font-size: 18px; font-weight: bold; text-align: center; }
    .stDataFrame td { font-size: 16px !important; }
    
    /* 模式徽章 */
    .mode-badge {
        padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;
        display: inline-block; margin-bottom: 10px;
    }
    .badge-casual { background-color: #e3f2fd; color: #1565c0; border: 1px solid #1565c0; }
    .badge-pro { background-color: #fff3e0; color: #e65100; border: 1px solid #e65100; }
    
    /* 名字样式优化 */
    .player-names {
        font-size: 16px; font-weight: bold; 
        white-space: nowrap; /* 不换行 */
        overflow: hidden; text-overflow: ellipsis;
    }
</style>
""", unsafe_allow_html=True)

# --- 初始化数据 ---
if 'players' not in st.session_state:
    st.session_state.players = [] 
if 'schedule' not in st.session_state:
    st.session_state.schedule = []
if 'match_mode' not in st.session_state:
    st.session_state.match_mode = "casual"

# --- 核心算法逻辑 ---

def get_target_match_count(n, mode):
    if n < 4: return 0
    if mode == "casual":
        if n == 5: return 5
        if n == 6: return 6
        if n == 7: return 7
        if n == 8: return 8
        return int(n * 4 / 4)
    if mode == "pro":
        if n == 5: return 5
        if n == 6: return 9
        if n == 7: return 10
        if n == 8: return 14
        return int(n * 5 / 4) + 2 

def generate_full_schedule(mode):
    current_players = [p for p in st.session_state.players if p and str(p).strip()]
    n = len(current_players)
    if n < 4:
        st.error("至少需要4人才能生成赛程！")
        return

    target_matches = get_target_match_count(n, mode)
    st.session_state.match_mode = mode
    
    all_pairs = list(itertools.combinations(current_players, 2))
    
    # === 核心优化：防连续上场算法 ===
    best_schedule = []
    
    # 尝试多次寻找最优解
    for _ in range(500):
        random.shuffle(all_pairs)
        temp_pairs = all_pairs[:]
        temp_schedule = []
        player_counts = {p: 0 for p in current_players}
        
        for _ in range(target_matches):
            # 获取上一场比赛的人（如果存在）
            last_match_players = []
            if temp_schedule:
                last_m = temp_schedule[-1]
                last_match_players = list(last_m['t1']) + list(last_m['t2'])

            # --- 智能排序逻辑 ---
            # 权重1：总场次越少越优先 (balance_score)
            # 权重2：上一场打过的人，权重加超级大 (fatigue_penalty)，让他排到后面去
            
            def sort_key(pair):
                # 均衡分：这两人目前打的总场次之和
                balance_score = player_counts[pair[0]] + player_counts[pair[1]]
                
                # 疲劳分：如果这两人里有人上一场刚打完，加 100 分惩罚
                fatigue_penalty = 0
                if pair[0] in last_match_players: fatigue_penalty += 100
                if pair[1] in last_match_players: fatigue_penalty += 100
                
                return balance_score + fatigue_penalty

            # 按计算出的权重排序，分数越低越优先
            temp_pairs.sort(key=sort_key)
            
            if not temp_pairs: break
            
            # 寻找下一场不冲突的对局
            found_match = False
            search_limit = min(len(temp_pairs), 20)
            
            for i in range(search_limit):
                pair1 = temp_pairs[i]
                for j in range(i + 1, search_limit):
                    pair2 = temp_pairs[j]
                    
                    if set(pair1).isdisjoint(set(pair2)):
                        # 找到了！
                        temp_schedule.append({
                            'id': 0, 't1': pair1, 't2': pair2, 's1': 0, 's2': 0, 'done': False
                        })
                        player_counts[pair1[0]] += 1; player_counts[pair1[1]] += 1
                        player_counts[pair2[0]] += 1; player_counts[pair2[1]] += 1
                        
                        temp_pairs.remove(pair1)
                        temp_pairs.remove(pair2)
                        found_match = True
                        break
                if found_match: break
            
            if not found_match: break
        
        # 评估这次生成的质量
        if len(temp_schedule) == target_matches:
            best_schedule = temp_schedule
            break # 找到完美解，直接退出
        
        if len(temp_schedule) > len(best_schedule):
            best_schedule = temp_schedule

    if len(best_schedule) > 0:
        for idx, match in enumerate(best_schedule):
            match['id'] = idx + 1
        st.session_state.schedule = best_schedule
        st.toast(f"已生成 {len(best_schedule)} 场比赛！(已启用防连打机制)")
    else:
        st.error("生成失败，请重试。")

def calculate_rankings():
    if not st.session_state.schedule: return pd.DataFrame()
    
    active_players = set()
    for m in st.session_state.schedule:
        for p in m['t1'] + m['t2']: active_players.add(p)
            
    stats = {p: {'wins': 0, 'losses': 0, 'diff': 0, 'points': 0, 'total_score': 0, 'matches': 0} for p in active_players}
    
    for m in st.session_state.schedule:
        if m['done']:
            s1, s2 = int(m['s1']), int(m['s2'])
            diff = abs(s1 - s2)
            
            # 更新 t1
            for p in m['t1']:
                stats[p]['matches'] += 1
                stats[p]['diff'] += (s1 - s2)
                stats[p]['total_score'] += s1
                if s1 > s2: 
                    stats[p]['wins'] += 1; stats[p]['points'] += 2
                else: 
                    stats[p]['losses'] += 1
                    if diff <= 6: stats[p]['points'] += 1
            
            # 更新 t2
            for p in m['t2']:
                stats[p]['matches'] += 1
                stats[p]['diff'] += (s2 - s1)
                stats[p]['total_score'] += s2
                if s2 > s1: 
                    stats[p]['wins'] += 1; stats[p]['points'] += 2
                else: 
                    stats[p]['losses'] += 1
                    if diff <= 6: stats[p]['points'] += 1

    df = pd.DataFrame.from_dict(stats, orient='index')
    if df.empty: return pd.DataFrame()

    df = df.sort_values(by=['points', 'diff', 'total_score'], ascending=[False, False, False])

    ranks = []
    for i in range(len(df)):
        if i == 0: ranks.append('🥇')
        elif i == 1: ranks.append('🥈')
        elif i == 2: ranks.append('🥉')
        else: ranks.append(str(i + 1))
    df.insert(0, '名次', ranks)
    
    # 增加一列显示场次
    df['场数'] = df['matches']

    df['胜-负'] = df.apply(lambda x: f"{int(x['wins'])} - {int(x['losses'])}", axis=1)
    df.index.name = '选手'
    df = df.reset_index()
    df = df.rename(columns={'points': '积分', 'diff': '净胜分'})
    return df[['名次', '选手', '场数', '胜-负', '积分', '净胜分']]

# --- 界面 UI ---

st.title("🏸 羽毛球智能排赛")

tab1, tab2, tab3 = st.tabs(["📅 对阵录分", "🏆 排行榜", "⚙️ 赛制设置"])

# === Tab 1: 对阵表 (UI 优化版) ===
with tab1:
    if not st.session_state.schedule:
        st.info("暂无赛程，请去【赛制设置】页生成比赛。")
    else:
        if st.session_state.match_mode == "pro":
            st.markdown('<div class="mode-badge badge-pro">🔥 激斗模式 (15分制)</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="mode-badge badge-casual">☕ 养生模式 (21分制)</div>', unsafe_allow_html=True)

        done_count = sum(1 for m in st.session_state.schedule if m['done'])
        total_count = len(st.session_state.schedule)
        st.progress(done_count / total_count if total_count > 0 else 0)
        st.caption(f"进度: {done_count} / {total_count}")

        for i, match in enumerate(st.session_state.schedule):
            with st.container(border=True):
                # UI 修改 1: 名字同行显示，且居中
                c_p1, c_vs, c_p2 = st.columns([5, 2, 5])
                
                with c_p1:
                    # 使用 text-align: center 实现名字居中
                    st.markdown(f"<div class='player-names' style='text-align: center; color: #d32f2f;'>{match['t1'][0]} & {match['t1'][1]}</div>", unsafe_allow_html=True)
                
                with c_vs:
                    if match['done']:
                        st.markdown(f"<div style='text-align: center; color: green; font-weight:900; font-size: 20px;'>{match['s1']}:{match['s2']}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='text-align: center; color: #ddd; font-weight:bold;'>VS</div>", unsafe_allow_html=True)

                with c_p2:
                    st.markdown(f"<div class='player-names' style='text-align: center; color: #1976d2;'>{match['t2'][0]} & {match['t2'][1]}</div>", unsafe_allow_html=True)
                
                st.divider()

                # UI 修改 2: 录分区域居中，使用 Spacer 挤压中间区域
                if not match['done']:
                    # 比例调整：两边 1.5 的空白，中间紧凑
                    c_sp1, c_in1, c_in2, c_btn, c_sp2 = st.columns([1.5, 2, 2, 2, 1.5])
                    
                    with c_in1:
                        new_s1 = st.number_input("红", 0, 30, match['s1'], key=f"s1_{match['id']}", label_visibility="collapsed")
                    with c_in2:
                        new_s2 = st.number_input("蓝", 0, 30, match['s2'], key=f"s2_{match['id']}", label_visibility="collapsed")
                    with c_btn:
                        if st.button("确认", key=f"btn_{match['id']}", type="primary"):
                            st.session_state.schedule[i]['s1'] = new_s1
                            st.session_state.schedule[i]['s2'] = new_s2
                            st.session_state.schedule[i]['done'] = True
                            st.rerun()
                else:
                    # 修改按钮也居中
                    c_sp1, c_btn, c_sp2 = st.columns([3, 4, 3])
                    with c_btn:
                        if st.button("🔄 修改比分", key=f"undo_{match['id']}"):
                            st.session_state.schedule[i]['done'] = False
                            st.rerun()

# === Tab 2: 排行榜 ===
with tab2:
    st.header("实时排名")
    st.caption("ℹ️ 积分规则：胜+2，负(分差≤6)+1，负(分差>6)+0")
    df_rank = calculate_rankings()
    if not df_rank.empty:
        st.dataframe(
            df_rank,
            hide_index=True,
            use_container_width=True,
            column_config={
                "名次": st.column_config.TextColumn("名次", width="small"),
                "选手": st.column_config.TextColumn("选手", width="medium"),
                "场数": st.column_config.NumberColumn("场数", width="small"), # 新增列
                "胜-负": st.column_config.TextColumn("胜-负", width="small"),
                "积分": st.column_config.NumberColumn("积分", format="%d"),
                "净胜分": st.column_config.NumberColumn("净胜分", format="%d"),
            }
        )
    else:
        st.info("暂无数据")

# === Tab 3: 赛制设置 ===
with tab3:
    st.header("📋 选手与模式")
    
    st.subheader("1️⃣ 选择模式")
    mode_option = st.radio(
        "赛制强度:",
        ("casual", "pro"),
        format_func=lambda x: "☕ 养生休闲 (标准)" if x == "casual" else "🔥 激斗循环 (高强度/全互搭)"
    )

    st.markdown("---")
    
    st.subheader("2️⃣ 编辑名单")
    df_players = pd.DataFrame(st.session_state.players, columns=["选手姓名"])
    edited_df = st.data_editor(df_players, num_rows="dynamic", use_container_width=True, key="player_editor")
    
    raw_list = edited_df["选手姓名"].tolist()
    clean_list = [str(p) for p in raw_list if pd.notna(p) and str(p).strip() != ""]
    st.session_state.players = clean_list

    count = len(st.session_state.players)
    target_match = get_target_match_count(count, mode_option)
    
    # 计算人均场次
    avg_games = 0
    if count > 0:
        avg_games = (target_match * 4) / count
        # 如果是整数就显示整数，否则保留一位小数
        avg_games_str = f"{int(avg_games)}" if avg_games.is_integer() else f"{avg_games:.1f}"

    st.write(f"当前人数: **{count}** 人")
    
    btn_disabled = count < 4
    if count < 4:
        btn_label = "🚫 至少需要4人"
    else:
        # 按钮上显示人均场次
        btn_label = f"🎲 生成赛程 (共{target_match}场 | 人均{avg_games_str}场)"
    
    st.info(f"💡 预计生成 **{target_match}** 场，每人打 **{avg_games_str}** 场，已启用**防连续上场**算法。")
    
    if st.button(btn_label, type="primary", disabled=btn_disabled):
        generate_full_schedule(mode_option)
        st.rerun()
        
    if st.button("⚠️ 清空所有赛程"):
        st.session_state.schedule = []
        st.rerun()
