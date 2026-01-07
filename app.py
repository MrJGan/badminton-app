import streamlit as st
import pandas as pd
import random
import itertools

# --- 页面配置 ---
st.set_page_config(page_title="羽毛球赛程表", page_icon="🏸", layout="centered")

# --- CSS 微调 (仅保留最安全的样式) ---
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; }
    /* 让分数的输入框稍微大一点 */
    .stNumberInput input { font-size: 18px; font-weight: bold; text-align: center; }
    /* 调整表格字体 */
    .stDataFrame td { font-size: 16px !important; }
</style>
""", unsafe_allow_html=True)

# --- 初始化数据 ---
if 'players' not in st.session_state:
    st.session_state.players = [] 
if 'schedule' not in st.session_state:
    st.session_state.schedule = [] 

# --- 核心算法逻辑 (保持不变) ---
def generate_full_schedule():
    # 从 session_state 获取最新的 player 列表 (去重且去空)
    current_players = [p for p in st.session_state.players if p.strip()]
    n = len(current_players)
    if n < 4:
        st.error("至少需要4人才能生成赛程！")
        return

    all_pairs = list(itertools.combinations(current_players, 2))
    random.shuffle(all_pairs)
    
    schedule = []
    attempts = 0
    success = False
    
    while attempts < 100 and not success:
        temp_pairs = all_pairs[:]
        temp_schedule = []
        possible = True
        
        while len(temp_pairs) >= 2:
            pair1 = temp_pairs.pop(0)
            found_opponent = False
            for i, pair2 in enumerate(temp_pairs):
                if set(pair1).isdisjoint(set(pair2)):
                    temp_pairs.pop(i)
                    temp_schedule.append({
                        'id': 0, 't1': pair1, 't2': pair2, 's1': 0, 's2': 0, 'done': False
                    })
                    found_opponent = True
                    break
            if not found_opponent:
                possible = False
                break
        
        if possible and len(temp_pairs) == 0:
            success = True
            for idx, match in enumerate(temp_schedule):
                match['id'] = idx + 1
            schedule = temp_schedule
        else:
            attempts += 1
            random.shuffle(all_pairs)

    if success:
        st.session_state.schedule = schedule
        st.toast(f"成功生成 {len(schedule)} 场比赛！")
    else:
        st.error("生成失败，请重试或增减人数。")

def calculate_rankings():
    if not st.session_state.schedule:
        return pd.DataFrame()

    # 重新初始化统计，确保用的是最新名单
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

st.title("🏸 羽毛球赛程表")

tab1, tab2, tab3 = st.tabs(["📅 对阵录分", "🏆 排行榜", "⚙️ 名单设置"])

# === Tab 1: 对阵表 (原生组件重构版) ===
with tab1:
    if not st.session_state.schedule:
        st.info("暂无赛程，请去【名单设置】页生成比赛。")
    else:
        # 进度条
        done_count = sum(1 for m in st.session_state.schedule if m['done'])
        total_count = len(st.session_state.schedule)
        st.progress(done_count / total_count if total_count > 0 else 0)
        st.caption(f"进度: {done_count} / {total_count}")

        for i, match in enumerate(st.session_state.schedule):
            # 使用 container(border=True) 创建原生卡片，这是最稳定的方法
            with st.container(border=True):
                # 第一行：显示对阵双方名字
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
                
                st.divider() # 分割线

                # 第二行：录入/修改区域 (直接在同一个卡片里)
                if not match['done']:
                    # --- 录分模式 ---
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
                    # --- 已结束模式 (仅显示修改按钮) ---
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

# === Tab 3: 名单设置 (换成了表格编辑器) ===
with tab3:
    st.header("📋 选手名单管理")
    st.info("💡 在下方表格中直接修改、添加或删除名字。")

    # 1. 准备数据：把 list 转成 DataFrame
    df_players = pd.DataFrame(st.session_state.players, columns=["选手姓名"])

    # 2. 显示编辑器 (允许增删改)
    edited_df = st.data_editor(
        df_players,
        num_rows="dynamic", # 允许添加和删除行
        use_container_width=True,
        key="player_editor"
    )

    # 3. 实时同步回 session_state
    # 注意：这里我们只要非空的名字
    new_player_list = edited_df["选手姓名"].dropna().astype(str).tolist()
    st.session_state.players = new_player_list

    st.markdown("---")
    st.write(f"当前人数: **{len(st.session_state.players)}** 人")
    
    # 生成按钮
    btn_disabled = len(st.session_state.players) < 4
    if st.button("🎲 生成新赛程 (8人=14场)", type="primary", disabled=btn_disabled):
        generate_full_schedule()
        st.rerun()
        
    if st.button("⚠️ 清空所有赛程"):
        st.session_state.schedule = []
        st.rerun()
