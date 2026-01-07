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
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 10px;
    }
    .badge-casual { background-color: #e3f2fd; color: #1565c0; border: 1px solid #1565c0; }
    .badge-pro { background-color: #fff3e0; color: #e65100; border: 1px solid #e65100; }
</style>
""", unsafe_allow_html=True)

# --- 初始化数据 ---
if 'players' not in st.session_state:
    st.session_state.players = [] 
if 'schedule' not in st.session_state:
    st.session_state.schedule = []
if 'match_mode' not in st.session_state:
    st.session_state.match_mode = "casual" # casual 或 pro

# --- 核心算法逻辑 ---

def get_target_match_count(n, mode):
    """
    根据人数和模式，决定总场次
    """
    if n < 4: return 0
    
    # === ☕ 养生/标准模式 (目标：每人~4场) ===
    if mode == "casual":
        if n == 5: return 5  # 每人4场
        if n == 6: return 6  # 每人4场
        if n == 7: return 7  # 每人4场
        if n == 8: return 8  # 每人4场
        # 其他人数：寻找每人至少3-4场的倍数
        return int(n * 4 / 4) # 简单估算，保持n场左右
        
    # === 🔥 激斗/全循环模式 (目标：每人6-7场，或全搭档) ===
    if mode == "pro":
        if n == 5: return 5   # 5人本身就是全循环，无需增加
        if n == 6: return 9   # 🌟 6人9场：每人6场 (完美全互搭)
        if n == 7: return 10  # 🌟 7人10场：每人约5.7场 (高强度)
        if n == 8: return 14  # 🌟 8人14场：每人7场 (完美全互搭)
        
        # 9人以上Pro模式太累，回归到每人5场左右
        return int(n * 5 / 4) + 2 

def generate_full_schedule(mode):
    current_players = [p for p in st.session_state.players if p and str(p).strip()]
    n = len(current_players)
    if n < 4:
        st.error("至少需要4人才能生成赛程！")
        return

    # 1. 获取目标场次
    target_matches = get_target_match_count(n, mode)
    st.session_state.match_mode = mode # 记录当前模式
    
    # 2. 生成所有组合
    all_pairs = list(itertools.combinations(current_players, 2))
    random.shuffle(all_pairs)
    
    # 3. 贪心算法
    best_schedule = []
    
    # 增加尝试次数，确保Pro模式能算出来
    max_attempts = 500
    
    for _ in range(max_attempts):
        random.shuffle(all_pairs)
        temp_pairs = all_pairs[:]
        temp_schedule = []
        player_counts = {p: 0 for p in current_players}
        
        for _ in range(target_matches):
            # 动态排序：优先选出场最少的人
            temp_pairs.sort(key=lambda x: player_counts[x[0]] + player_counts[x[1]])
            
            if not temp_pairs: break
            
            found_match = False
            search_limit = min(len(temp_pairs), 20) # 性能优化
            
            for i in range(search_limit):
                pair1 = temp_pairs[i]
                for j in range(i + 1, search_limit):
                    pair2 = temp_pairs[j]
                    
                    if set(pair1).isdisjoint(set(pair2)):
                        # 检查重复对阵：如果是Pro模式(6人9场)，允许极少量重复？
                        # 这里我们坚持不重复搭档原则 (all_pairs里每种组合只有一个)
                        
                        temp_schedule.append({
                            'id': 0, 't1': pair1, 't2': pair2, 's1': 0, 's2': 0, 'done': False
                        })
                        player_counts[pair1[0]] += 1
                        player_counts[pair1[1]] += 1
                        player_counts[pair2[0]] += 1
                        player_counts[pair2[1]] += 1
                        
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
        msg = f"已生成 {len(best_schedule)} 场比赛！"
        if mode == "pro":
            st.toast("🔥 激斗模式开启！建议改为 15 分制以节省体力。", icon="💡")
        else:
            st.toast(msg)
    else:
        st.error("生成失败，请重试。")

def calculate_rankings():
    if not st.session_state.schedule:
        return pd.DataFrame()

    active_players = set()
    for m in st.session_state.schedule:
        for p in m['t1'] + m['t2']:
            active_players.add(p)
            
    stats = {p: {'wins': 0, 'losses': 0, 'diff': 0, 'points': 0, 'total_score': 0} for p in active_players}
    
    for m in st.session_state.schedule:
        if m['done']:
            s1 = int(m['s1'])
            s2 = int(m['s2'])
            score_diff = abs(s1 - s2)
            
            for p in m['t1']:
                stats[p]['diff'] += (s1 - s2)
                stats[p]['total_score'] += s1
                if s1 > s2:
                    stats[p]['wins'] += 1
                    stats[p]['points'] += 2
                elif s1 < s2:
                    stats[p]['losses'] += 1
                    if score_diff <= 6: stats[p]['points'] += 1
            
            for p in m['t2']:
                stats[p]['diff'] += (s2 - s1)
                stats[p]['total_score'] += s2
                if s2 > s1:
                    stats[p]['wins'] += 1
                    stats[p]['points'] += 2
                elif s2 < s1:
                    stats[p]['losses'] += 1
                    if score_diff <= 6: stats[p]['points'] += 1

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

    df['胜-负'] = df.apply(lambda x: f"{int(x['wins'])} - {int(x['losses'])}", axis=1)
    df.index.name = '选手'
    df = df.reset_index()
    df = df.rename(columns={'points': '积分', 'diff': '净胜分'})
    return df[['名次', '选手', '胜-负', '积分', '净胜分']]

# --- 界面 UI ---

st.title("🏸 羽毛球智能排赛")

tab1, tab2, tab3 = st.tabs(["📅 对阵录分", "🏆 排行榜", "⚙️ 赛制设置"])

# === Tab 1: 对阵表 ===
with tab1:
    if not st.session_state.schedule:
        st.info("暂无赛程，请去【赛制设置】页生成比赛。")
    else:
        # 显示当前模式提示
        if st.session_state.match_mode == "pro":
            st.markdown("""
            <div class="mode-badge badge-pro">🔥 激斗模式 (推荐 15 分制)</div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="mode-badge badge-casual">☕ 养生模式 (推荐 21 分制)</div>
            """, unsafe_allow_html=True)

        done_count = sum(1 for m in st.session_state.schedule if m['done'])
        total_count = len(st.session_state.schedule)
        st.progress(done_count / total_count if total_count > 0 else 0)
        st.caption(f"进度: {done_count} / {total_count}")

        for i, match in enumerate(st.session_state.schedule):
            with st.container(border=True):
                c_p1, c_vs, c_p2 = st.columns([5, 2, 5])
                with c_p1:
                    st.markdown(f"**:red[{match['t1'][0]}]**")
                    st.markdown(f"**:red[{match['t1'][1]}]**")
                with c_vs:
                    if match['done']:
                        st.markdown(f"<h3 style='text-align: center; color: green; margin:0;'>{match['s1']}:{match['s2']}</h3>", unsafe_allow_html=True)
                    else:
                        st.markdown("<h3 style='text-align: center; color: #ddd; margin:0;'>VS</h3>", unsafe_allow_html=True)
                with c_p2:
                    st.markdown(f"<div style='text-align: right; color: #1976d2; font-weight:bold'>{match['t2'][0]}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align: right; color: #1976d2; font-weight:bold'>{match['t2'][1]}</div>", unsafe_allow_html=True)
                
                st.divider()

                if not match['done']:
                    c_in1, c_in2, c_btn = st.columns([3, 3, 2])
                    with c_in1:
                        new_s1 = st.number_input("红分", 0, 30, match['s1'], key=f"s1_{match['id']}", label_visibility="collapsed")
                    with c_in2:
                        new_s2 = st.number_input("蓝分", 0, 30, match['s2'], key=f"s2_{match['id']}", label_visibility="collapsed")
                    with c_btn:
                        if st.button("确认", key=f"btn_{match['id']}", type="primary"):
                            st.session_state.schedule[i]['s1'] = new_s1
                            st.session_state.schedule[i]['s2'] = new_s2
                            st.session_state.schedule[i]['done'] = True
                            st.rerun()
                else:
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
    
    # 1. 模式选择
    st.subheader("1️⃣ 选择模式")
    mode_option = st.radio(
        "赛制强度:",
        ("casual", "pro"),
        format_func=lambda x: "☕ 养生休闲 (每人~4场 / 21分制)" if x == "casual" else "🔥 激斗循环 (全互搭 / 15分制)"
    )

    st.markdown("---")
    
    # 2. 名单编辑
    st.subheader("2️⃣ 编辑名单")
    df_players = pd.DataFrame(st.session_state.players, columns=["选手姓名"])
    edited_df = st.data_editor(df_players, num_rows="dynamic", use_container_width=True, key="player_editor")
    
    raw_list = edited_df["选手姓名"].tolist()
    clean_list = [str(p) for p in raw_list if pd.notna(p) and str(p).strip() != ""]
    st.session_state.players = clean_list

    count = len(st.session_state.players)
    st.write(f"当前人数: **{count}** 人")
    
    # 3. 动态预估文本
    target_match = get_target_match_count(count, mode_option)
    
    btn_disabled = count < 4
    if count < 4:
        btn_label = "🚫 至少需要4人"
    else:
        btn_label = f"🎲 生成赛程 ({target_match}场)"
    
    st.info(f"💡 预计生成 **{target_match}** 场比赛。")
    
    if st.button(btn_label, type="primary", disabled=btn_disabled):
        generate_full_schedule(mode_option)
        st.rerun()
        
    if st.button("⚠️ 清空所有赛程"):
        st.session_state.schedule = []
        st.rerun()
