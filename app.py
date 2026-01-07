import streamlit as st
import pandas as pd
import random
import itertools

# --- 页面配置 ---
st.set_page_config(page_title="羽毛球大乱斗", page_icon="🏸", layout="centered")

# --- 样式优化 (让它看起来像手机App) ---
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 20px; height: 3em; font-weight: bold; }
    .big-font { font-size: 20px !important; font-weight: bold; }
    .rank-card { background-color: #f0f2f6; padding: 10px; border-radius: 10px; margin-bottom: 5px; }
    .winner { color: #ff4b4b; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 初始化数据 ---
if 'players' not in st.session_state:
    st.session_state.players = [] # 存储玩家名字
if 'matches' not in st.session_state:
    st.session_state.matches = [] # 存储比赛记录
if 'current_match' not in st.session_state:
    st.session_state.current_match = None # 当前正在进行的比赛

# --- 核心函数 ---

def calculate_rankings():
    """计算排名：胜场 -> 净胜分 -> 总得分"""
    stats = {p: {'matches': 0, 'wins': 0, 'losses': 0, 'points': 0, 'diff': 0} for p in st.session_state.players}
    
    for m in st.session_state.matches:
        # m = {'t1': [p1, p2], 't2': [p3, p4], 's1': score1, 's2': score2}
        s1 = m['s1']
        s2 = m['s2']
        
        # 队伍1统计
        for p in m['t1']:
            stats[p]['matches'] += 1
            stats[p]['points'] += s1
            stats[p]['diff'] += (s1 - s2)
            if s1 > s2: stats[p]['wins'] += 1
            else: stats[p]['losses'] += 1
            
        # 队伍2统计
        for p in m['t2']:
            stats[p]['matches'] += 1
            stats[p]['points'] += s2
            stats[p]['diff'] += (s2 - s1)
            if s2 > s1: stats[p]['wins'] += 1
            else: stats[p]['losses'] += 1

    # 转为DataFrame并排序
    df = pd.DataFrame.from_dict(stats, orient='index')
    if not df.empty:
        df = df.sort_values(by=['wins', 'diff', 'points'], ascending=[False, False, False])
        df['胜率'] = df.apply(lambda x: f"{int(x['wins'])}胜-{int(x['losses'])}负", axis=1)
        return df[['胜率', 'diff', 'points']] # 展示列：胜率，净胜分，总分
    return pd.DataFrame()

def generate_match():
    """自动生成对阵：优先选场次少的人"""
    if len(st.session_state.players) < 4:
        st.error("至少需要4人才能开始双打！")
        return

    # 统计每个人打了几场
    match_counts = {p: 0 for p in st.session_state.players}
    for m in st.session_state.matches:
        for p in m['t1'] + m['t2']:
            match_counts[p] += 1
            
    # 按场次从小到大排序，取出场最少的4个人
    sorted_players = sorted(match_counts.items(), key=lambda item: item[1])
    # 为了避免每次都是固定组合，如果有多人场次相同，随机打乱
    candidates = [p[0] for p in sorted_players]
    
    # 取前4个（如果大家场次一样，就随机取4个）
    # 这里做一个加权随机或者简单随机，为了简单且公平，我们取场次最少的N个人，从中随机选4个
    min_count = sorted_players[0][1]
    pool = [p for p, c in sorted_players if c <= min_count + 1] # 选取场次最少和次少的人作为候选池
    
    if len(pool) < 4:
        pool = candidates[:6] # 候选池不够就扩大范围
        
    selected = random.sample(pool, 4)
    random.shuffle(selected)
    
    st.session_state.current_match = {
        't1': [selected[0], selected[1]],
        't2': [selected[2], selected[3]]
    }

# --- 界面 UI ---

st.title("🏸 羽毛球大乱斗助手")

# 1. 选手管理
with st.expander("管理选手 (当前 {} 人)".format(len(st.session_state.players))):
    new_player = st.text_input("输入名字添加", key="add_input")
    if st.button("添加选手"):
        if new_player and new_player not in st.session_state.players:
            st.session_state.players.append(new_player)
            st.rerun()
    
    st.write("参赛名单:", ", ".join(st.session_state.players))
    if st.button("重置所有数据 (慎点)"):
        st.session_state.players = []
        st.session_state.matches = []
        st.session_state.current_match = None
        st.rerun()

# 2. 比赛控制区
st.header("⚔️ 比赛进行中")

if st.session_state.current_match is None:
    if len(st.session_state.players) >= 4:
        if st.button("🎲 生成下一场对阵", type="primary"):
            generate_match()
            st.rerun()
    else:
        st.info("请先添加至少4名选手")
else:
    cm = st.session_state.current_match
    t1_name = f"{cm['t1'][0]} & {cm['t1'][1]}"
    t2_name = f"{cm['t2'][0]} & {cm['t2'][1]}"
    
    st.subheader(f"🔴 {t1_name}  VS  🔵 {t2_name}")
    
    c1, c2 = st.columns(2)
    with c1:
        s1 = st.number_input("🔴 红队得分", min_value=0, step=1, key="s1_in")
    with c2:
        s2 = st.number_input("🔵 蓝队得分", min_value=0, step=1, key="s2_in")
        
    col_submit, col_cancel = st.columns(2)
    with col_submit:
        if st.button("✅ 结束并记录"):
            # 记录比赛
            record = {
                't1': cm['t1'], 't2': cm['t2'],
                's1': int(s1), 's2': int(s2)
            }
            st.session_state.matches.insert(0, record) # 新比赛放前面
            st.session_state.current_match = None # 清空当前比赛
            st.rerun()
            
    with col_cancel:
        if st.button("❌ 取消本场"):
            st.session_state.current_match = None
            st.rerun()

# 3. 实时排行榜
st.header("🏆 实时排名")
df_rank = calculate_rankings()
if not df_rank.empty:
    # 美化显示
    st.dataframe(
        df_rank.style.highlight_max(axis=0, color='lightgreen'), 
        use_container_width=True
    )
else:
    st.write("暂无比赛数据")

# 4. 历史记录
with st.expander("查看历史对阵记录"):
    for i, m in enumerate(st.session_state.matches):
        winner = "红队" if m['s1'] > m['s2'] else "蓝队"
        st.markdown(f"**第 {len(st.session_state.matches)-i} 场**: {m['t1'][0]}+{m['t1'][1]} ({m['s1']}) vs ({m['s2']}) {m['t2'][0]}+{m['t2'][1]}")
