import streamlit as st
import pandas as pd
import random
import itertools

# --- 页面配置 ---
st.set_page_config(page_title="羽毛球排赛小助手", page_icon="🏸", layout="centered")

# --- CSS 样式 ---
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; }
    .stNumberInput input { font-size: 18px; font-weight: bold; text-align: center; }
    .stDataFrame td { font-size: 16px !important; }
    
    /* 模式徽章 (图标在右) */
    .mode-badge {
        padding: 6px 12px; border-radius: 15px; font-size: 13px; font-weight: bold;
        display: inline-block; margin-bottom: 10px; width: 100%; text-align: center;
    }
    .badge-casual { background-color: #e3f2fd; color: #1565c0; border: 1px solid #1565c0; }
    .badge-pro { background-color: #fff3e0; color: #e65100; border: 1px solid #e65100; }
    
    /* 名字样式 */
    .player-names {
        font-size: 16px; font-weight: bold; 
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    /* 场次标签 */
    .match-tag {
        font-size: 12px; color: #999; font-weight: bold; margin-bottom: 5px; display: block;
    }
</style>
""", unsafe_allow_html=True)

# --- 初始化数据 ---
if 'players' not in st.session_state:
    # 默认初始化8个空位
    st.session_state.players = [f"选手{i+1}" for i in range(8)]
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
    # 过滤掉空名字
    current_players = [p for p in st.session_state.players if p and str(p).strip()]
    n = len(current_players)
    if n < 4:
        st.error("至少需要4人才能生成赛程！")
        return

    target_matches = get_target_match_count(n, mode)
    st.session_state.match_mode = mode
    
    all_pairs = list(itertools.combinations(current_players, 2))
    best_schedule = []
    
    # 尝试生成算法 (防连打)
    for _ in range(500):
        random.shuffle(all_pairs)
        temp_pairs = all_pairs[:]
        temp_schedule = []
        player_counts = {p: 0 for p in current_players}
        
        for _ in range(target_matches):
            last_match_players = []
            if temp_schedule:
                last_m = temp_schedule[-1]
                last_match_players = list(last_m['t1']) + list(last_m['t2'])

            def sort_key(pair):
                balance_score = player_counts[pair[0]] + player_counts[pair[1]]
                fatigue_penalty = 0
                if pair[0] in last_match_players: fatigue_penalty += 100
                if pair[1] in last_match_players: fatigue_penalty += 100
                return balance_score + fatigue_penalty

            temp_pairs.sort(key=sort_key)
            
            if not temp_pairs: break
            
            found_match = False
            search_limit = min(len(temp_pairs), 20)
            
            for i in range(search_limit):
                pair1 = temp_pairs[i]
                for j in range(i + 1, search_limit):
                    pair2 = temp_pairs[j]
                    if set(pair1).isdisjoint(set(pair2)):
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
        
        if len(temp_schedule) == target_matches:
            best_schedule = temp_schedule
            break
        if len(temp_schedule) > len(best_schedule):
            best_schedule = temp_schedule

    if len(best_schedule) > 0:
        for idx, match in enumerate(best_schedule):
            match['id'] = idx + 1
        st.session_state.schedule = best_schedule
        # 成功提示
        st.toast(f"✅ 赛程已生成！共 {len(best_schedule)} 场", icon="🎉")
        return True # 返回成功状态
    else:
        st.error("生成失败，请重试。")
        return False

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
            for p in m['t1']:
                stats[p]['matches'] += 1
                stats[p]['diff'] += (s1 - s2)
                stats[p]['total_score'] += s1
                if s1 > s2: stats[p]['wins'] += 1; stats[p]['points'] += 2
                else: 
                    stats[p]['losses'] += 1
                    if diff <= 6: stats[p]['points'] += 1
            for p in m['t2']:
                stats[p]['matches'] += 1
                stats[p]['diff'] += (s2 - s1)
                stats[p]['total_score'] += s2
                if s2 > s1: stats[p]['wins'] += 1; stats[p]['points'] += 2
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
    df['场数'] = df['matches']
    df['胜-负'] = df.apply(lambda x: f"{int(x['wins'])} - {int(x['losses'])}", axis=1)
    df.index.name = '选手'
    df = df.reset_index()
    df = df.rename(columns={'points': '积分', 'diff': '净胜分'})
    return df[['名次', '选手', '场数', '胜-负', '积分', '净胜分']]

# --- 界面 UI ---

st.title("🏸 羽毛球智能排赛")

tab1, tab2, tab3 = st.tabs(["📅 对阵录分", "🏆 排行榜", "⚙️ 赛制设置"])

# === Tab 1: 对阵表 ===
with tab1:
    if not st.session_state.schedule:
        st.info("👈 请先点击【赛制设置】生成赛程")
    else:
        # 显示生成完毕的提示框
        st.success("🎉 赛程生成完毕！请按顺序进行比赛。", icon="✅")

        # 模式徽章 (图标在右)
        if st.session_state.match_mode == "pro":
            st.markdown('<div class="mode-badge badge-pro">激斗模式 (15分制) 🔥</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="mode-badge badge-casual">养生模式 (21分制) ☕</div>', unsafe_allow_html=True)

        done_count = sum(1 for m in st.session_state.schedule if m['done'])
        total_count = len(st.session_state.schedule)
        st.progress(done_count / total_count if total_count > 0 else 0)
        st.caption(f"进度: {done_count} / {total_count}")

        for i, match in enumerate(st.session_state.schedule):
            with st.container(border=True):
                # 新增：左上角显示 第X场
                st.markdown(f"<span class='match-tag'>第 {match['id']} 场</span>", unsafe_allow_html=True)
                
                c_p1, c_vs, c_p2 = st.columns([5, 2, 5])
                with c_p1:
                    st.markdown(f"<div class='player-names' style='text-align: center; color: #d32f2f;'>{match['t1'][0]} & {match['t1'][1]}</div>", unsafe_allow_html=True)
                with c_vs:
                    if match['done']:
                        st.markdown(f"<div style='text-align: center; color: green; font-weight:900; font-size: 20px;'>{match['s1']}:{match['s2']}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='text-align: center; color: #ddd; font-weight:bold;'>VS</div>", unsafe_allow_html=True)
                with c_p2:
                    st.markdown(f"<div class='player-names' style='text-align: center; color: #1976d2;'>{match['t2'][0]} & {match['t2'][1]}</div>", unsafe_allow_html=True)
                
                st.divider()

                if not match['done']:
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
                "场数": st.column_config.NumberColumn("场数", width="small"),
                "胜-负": st.column_config.TextColumn("胜-负", width="small"),
                "积分": st.column_config.NumberColumn("积分", format="%d"),
                "净胜分": st.column_config.NumberColumn("净胜分", format="%d"),
            }
        )
    else:
        st.info("暂无数据")

# === Tab 3: 赛制设置 ===
with tab3:
    st.header("📋 赛前设置")
    
    # 1. 模式选择
    st.subheader("1️⃣ 选择模式")
    mode_option = st.radio(
        "赛制强度:",
        ("casual", "pro"),
        format_func=lambda x: "养生休闲 (标准 21分) ☕" if x == "casual" else "激斗循环 (高强度 15分) 🔥"
    )

    st.markdown("---")
    
    # 2. 名单编辑 (新逻辑：先定人数，再填名字)
    st.subheader("2️⃣ 确认名单")
    
    col_num, col_info = st.columns([1, 2])
    with col_num:
        # 输入人数，动态调整列表长度
        target_num = st.number_input("参加人数", min_value=4, max_value=20, value=len(st.session_state.players), step=1)
    
    # 逻辑：调整列表长度但保留已有名字
    current_len = len(st.session_state.players)
    if target_num > current_len:
        # 补坑
        for i in range(current_len, target_num):
            st.session_state.players.append(f"选手{i+1}")
    elif target_num < current_len:
        # 裁剪
        st.session_state.players = st.session_state.players[:target_num]

    # 显示表格供编辑
    df_players = pd.DataFrame(st.session_state.players, columns=["点击下方名字修改"])
    edited_df = st.data_editor(df_players, use_container_width=True, key="player_editor", hide_index=True)
    
    # 实时同步名字
    st.session_state.players = edited_df["点击下方名字修改"].tolist()

    st.markdown("---")
    
    # 3. 确认生成
    count = len(st.session_state.players)
    target_match = get_target_match_count(count, mode_option)
    avg_games = (target_match * 4) / count if count > 0 else 0
    avg_str = f"{int(avg_games)}" if avg_games.is_integer() else f"{avg_games:.1f}"
    
    st.info(f"💡 确认名单后，将生成 **{target_match}** 场比赛，每人约 **{avg_str}** 场。")
    
    # 这个按钮现在是“确认名单 + 生成”
    if st.button(f"✅ 确认名单并生成赛程", type="primary"):
        if generate_full_schedule(mode_option):
            st.rerun()

    if st.button("⚠️ 重置/清空所有数据"):
        st.session_state.schedule = []
        st.session_state.players = [f"选手{i+1}" for i in range(8)] # 重置为8人模板
        st.rerun()
