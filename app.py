import streamlit as st
import pandas as pd
import random
import itertools

# --- 页面配置 ---
st.set_page_config(page_title="羽毛球赛程表", page_icon="🏸", layout="centered")

# --- CSS样式优化 ---
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-weight: bold; }
    .match-card { 
        background-color: #f0f2f6; 
        padding: 15px; 
        border-radius: 10px; 
        margin-bottom: 10px; 
        border-left: 5px solid #ff4b4b;
    }
    .match-done {
        background-color: #e8f5e9;
        border-left: 5px solid #4caf50;
        opacity: 0.8;
    }
    /* 表格字体优化 */
    .stDataFrame td { font-size: 16px !important; vertical-align: middle !important; }
</style>
""", unsafe_allow_html=True)

# --- 初始化数据 ---
if 'players' not in st.session_state:
    st.session_state.players = [] 
if 'schedule' not in st.session_state:
    st.session_state.schedule = [] 

# --- 核心算法逻辑 ---

def generate_full_schedule():
    """ 生成赛程 (保持不变) """
    players = st.session_state.players
    n = len(players)
    if n < 4:
        st.error("至少需要4人才能生成赛程！")
        return

    all_pairs = list(itertools.combinations(players, 2))
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
    """
    计算排名
    规则更新：
    1. 胜方 +2分
    2. 负方分差 <= 6，+1分 (惜败)
    3. 负方分差 > 6，+0分
    """
    if not st.session_state.schedule:
        return pd.DataFrame()

    stats = {p: {'wins': 0, 'losses': 0, 'diff': 0, 'points': 0, 'total_score': 0} for p in st.session_state.players}
    
    for m in st.session_state.schedule:
        if m['done']:
            s1 = int(m['s1'])
            s2 = int(m['s2'])
            score_diff = abs(s1 - s2) # 计算分差
            
            # --- 队伍1 (t1) ---
            for p in m['t1']:
                stats[p]['diff'] += (s1 - s2)
                stats[p]['total_score'] += s1
                if s1 > s2:
                    stats[p]['wins'] += 1
                    stats[p]['points'] += 2 # 胜
                elif s1 < s2:
                    stats[p]['losses'] += 1
                    # 输了，检查是否是惜败
                    if score_diff <= 6:
                        stats[p]['points'] += 1
            
            # --- 队伍2 (t2) ---
            for p in m['t2']:
                stats[p]['diff'] += (s2 - s1)
                stats[p]['total_score'] += s2
                if s2 > s1:
                    stats[p]['wins'] += 1
                    stats[p]['points'] += 2 # 胜
                elif s2 < s1:
                    stats[p]['losses'] += 1
                    # 输了，检查是否是惜败
                    if score_diff <= 6:
                        stats[p]['points'] += 1

    # 转为 DataFrame
    df = pd.DataFrame.from_dict(stats, orient='index')
    
    if df.empty:
        return pd.DataFrame()

    # 1. 排序：积分 > 净胜分 > 总得分
    df = df.sort_values(by=['points', 'diff', 'total_score'], ascending=[False, False, False])

    # 2. 生成【名次】列（金银铜牌）
    ranks = []
    for i in range(len(df)):
        if i == 0: ranks.append('🥇')
        elif i == 1: ranks.append('🥈')
        elif i == 2: ranks.append('🥉')
        else: ranks.append(str(i + 1))
    df.insert(0, '名次', ranks)

    # 3. 生成【胜-负】列
    df['胜-负'] = df.apply(lambda x: f"{int(x['wins'])} - {int(x['losses'])}", axis=1)

    # 4. 整理列名
    df.index.name = '选手'
    df = df.reset_index()
    df = df.rename(columns={'points': '积分', 'diff': '净胜分'})

    return df[['名次', '选手', '胜-负', '积分', '净胜分']]

# --- 界面 UI ---

st.title("🏸 羽毛球赛程表")

# 顶部导航
tab1, tab2, tab3 = st.tabs(["📅 赛程表", "🏆 排行榜", "⚙️ 设置"])

# === Tab 1: 赛程表 ===
with tab1:
    if not st.session_state.schedule:
        st.info("暂无赛程，请去【设置】页生成比赛。")
    else:
        done_count = sum(1 for m in st.session_state.schedule if m['done'])
        total_count = len(st.session_state.schedule)
        st.caption(f"进度: {done_count} / {total_count} 场")
        st.progress(done_count / total_count if total_count > 0 else 0)

        for i, match in enumerate(st.session_state.schedule):
            status_icon = "✅" if match['done'] else "🔴"
            t1_str = f"{match['t1'][0]} & {match['t1'][1]}"
            t2_str = f"{match['t2'][0]} & {match['t2'][1]}"
            
            with st.expander(f"{status_icon} 第 {match['id']} 场: {t1_str} VS {t2_str} ({match['s1']}:{match['s2']})", expanded=not match['done']):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    new_s1 = st.number_input("红队得分", min_value=0, value=match['s1'], key=f"s1_{match['id']}")
                with c2:
                    new_s2 = st.number_input("蓝队得分", min_value=0, value=match['s2'], key=f"s2_{match['id']}")
                with c3:
                    st.write(" ")
                    st.write(" ")
                    if st.button("确认", key=f"btn_{match['id']}"):
                        st.session_state.schedule[i]['s1'] = new_s1
                        st.session_state.schedule[i]['s2'] = new_s2
                        st.session_state.schedule[i]['done'] = True
                        st.rerun()
                
                if match['done']:
                    if st.button("撤销", key=f"undo_{match['id']}"):
                        st.session_state.schedule[i]['done'] = False
                        st.rerun()

# === Tab 2: 排行榜 ===
with tab2:
    st.header("实时排名")
    st.caption("ℹ️ 积分规则：胜得2分，分差≤6得1分(惜败)，分差>6得0分")
    
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
        st.info("比赛尚未开始或暂无数据。")

# === Tab 3: 设置 ===
with tab3:
    st.header("管理选手")
    new_player = st.text_input("输入名字 (回车添加)", key="add_input")
    if st.button("添加"):
        if new_player and new_player not in st.session_state.players:
            st.session_state.players.append(new_player)
            st.success(f"已添加 {new_player}")
            st.rerun()

    st.write(f"当前名单 ({len(st.session_state.players)}人):")
    st.code(", ".join(st.session_state.players))
    
    st.markdown("---")
    
    if st.button("🎲 生成全赛程表 (8人=14场)", type="primary"):
        generate_full_schedule()
        st.rerun()

    if st.button("🗑️ 清空所有数据"):
        st.session_state.players = []
        st.session_state.schedule = []
        st.rerun()
