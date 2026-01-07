import streamlit as st
import pandas as pd
import random
import itertools

# --- 页面配置 ---
st.set_page_config(page_title="羽毛球赛程表", page_icon="🏸", layout="centered")

# --- CSS样式优化 (让它更像App) ---
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
    .big-score { font-size: 24px; font-weight: bold; color: #333; }
</style>
""", unsafe_allow_html=True)

# --- 初始化数据 ---
if 'players' not in st.session_state:
    st.session_state.players = [] 
if 'schedule' not in st.session_state:
    st.session_state.schedule = [] # 存储生成的赛程列表 [{'id':1, 't1':(A,B), 't2':(C,D), 's1':0, 's2':0, 'done':False}]

# --- 核心算法逻辑 ---

def generate_full_schedule():
    """
    生成全赛程逻辑：
    1. 生成所有可能的搭档组合 (Pairs)
    2. 将Pairs两两组合成比赛 (Match)
    3. 尽量保证每个人在相邻场次得到休息（简单打乱）
    """
    players = st.session_state.players
    n = len(players)
    
    if n < 4:
        st.error("至少需要4人才能生成赛程！")
        return

    # 1. 生成所有双打组合 (比如8人会有28对组合)
    all_pairs = list(itertools.combinations(players, 2))
    random.shuffle(all_pairs) # 打乱顺序
    
    schedule = []
    match_id = 1
    
    # 2. 贪心算法：尝试把配对组合成比赛
    # 为了防止死循环（最后剩下两对有人冲突），我们尝试几次
    attempts = 0
    success = False
    
    while attempts < 50 and not success:
        temp_pairs = all_pairs[:]
        temp_schedule = []
        possible = True
        
        while len(temp_pairs) >= 2:
            pair1 = temp_pairs.pop(0) # 取出一对
            
            # 在剩下的对子里找一对，要求4个人互不重复
            found_opponent = False
            for i, pair2 in enumerate(temp_pairs):
                # 检查两对是否有重复的人
                if set(pair1).isdisjoint(set(pair2)):
                    # 找到对手了！
                    temp_pairs.pop(i)
                    temp_schedule.append({
                        'id': 0, # 稍后编号
                        't1': pair1,
                        't2': pair2,
                        's1': 0, 
                        's2': 0,
                        'done': False
                    })
                    found_opponent = True
                    break
            
            if not found_opponent:
                # 如果这对找不到对手（比如剩下的人里都有重叠），这次尝试失败
                possible = False
                break
        
        if possible and len(temp_pairs) == 0:
            success = True
            # 给比赛编号
            for idx, match in enumerate(temp_schedule):
                match['id'] = idx + 1
            schedule = temp_schedule
        else:
            attempts += 1
            random.shuffle(all_pairs) # 重新洗牌再试

    if success:
        st.session_state.schedule = schedule
        st.toast(f"成功生成 {len(schedule)} 场比赛！")
    else:
        st.error("生成失败：人数可能不支持完美循环（如6人），建议增减人数或手动重试。")

def calculate_rankings():
    """计算排名"""
    if not st.session_state.schedule:
        return pd.DataFrame()

    stats = {p: {'matches': 0, 'wins': 0, 'losses': 0, 'points': 0, 'diff': 0} for p in st.session_state.players}
    
    for m in st.session_state.schedule:
        if m['done']: # 只计算已完成的比赛
            s1 = m['s1']
            s2 = m['s2']
            
            # 队伍1
            for p in m['t1']:
                stats[p]['matches'] += 1
                stats[p]['points'] += s1
                stats[p]['diff'] += (s1 - s2)
                if s1 > s2: stats[p]['wins'] += 1
                elif s1 < s2: stats[p]['losses'] += 1
            
            # 队伍2
            for p in m['t2']:
                stats[p]['matches'] += 1
                stats[p]['points'] += s2
                stats[p]['diff'] += (s2 - s1)
                if s2 > s1: stats[p]['wins'] += 1
                elif s2 < s1: stats[p]['losses'] += 1

    df = pd.DataFrame.from_dict(stats, orient='index')
    if not df.empty:
        df = df.sort_values(by=['wins', 'diff', 'points'], ascending=[False, False, False])
        df['胜率'] = df.apply(lambda x: f"{int(x['wins'])}胜 {int(x['losses'])}负", axis=1)
        return df[['胜率', 'diff', 'points', 'matches']]
    return pd.DataFrame()

# --- 界面 UI ---

st.title("🏸 羽毛球排赛神器")

# 顶部导航
tab1, tab2, tab3 = st.tabs(["📅 赛程表 (录分)", "🏆 排行榜", "⚙️ 设置"])

# === Tab 1: 赛程表 ===
with tab1:
    if not st.session_state.schedule:
        st.info("暂无赛程，请去【设置】页生成比赛。")
    else:
        # 显示进度条
        done_count = sum(1 for m in st.session_state.schedule if m['done'])
        total_count = len(st.session_state.schedule)
        st.progress(done_count / total_count if total_count > 0 else 0)
        st.caption(f"进度: {done_count} / {total_count} 场")

        # 遍历显示所有比赛
        for i, match in enumerate(st.session_state.schedule):
            # 样式：已完成的变绿，未完成的默认
            container_class = "match-done" if match['done'] else "match-card"
            status_icon = "✅" if match['done'] else "🔴"
            
            t1_str = f"{match['t1'][0]} & {match['t1'][1]}"
            t2_str = f"{match['t2'][0]} & {match['t2'][1]}"
            
            # 使用 expander 做折叠卡片
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
                        # 更新状态
                        st.session_state.schedule[i]['s1'] = new_s1
                        st.session_state.schedule[i]['s2'] = new_s2
                        st.session_state.schedule[i]['done'] = True
                        st.rerun()
                
                if match['done']:
                    if st.button("撤销/修改", key=f"undo_{match['id']}"):
                        st.session_state.schedule[i]['done'] = False
                        st.rerun()

# === Tab 2: 排行榜 ===
with tab2:
    st.header("实时排名")
    df_rank = calculate_rankings()
    if not df_rank.empty:
        st.dataframe(
            df_rank.style.highlight_max(axis=0, color='lightgreen'), 
            use_container_width=True
        )
    else:
        st.write("比赛还没开始，暂无数据。")

# === Tab 3: 设置与生成 ===
with tab3:
    st.header("管理选手")
    
    # 快速添加
    new_player = st.text_input("输入名字 (回车添加)", key="add_input")
    if st.button("添加"):
        if new_player and new_player not in st.session_state.players:
            st.session_state.players.append(new_player)
            st.success(f"已添加 {new_player}")
            st.rerun()

    st.write(f"当前名单 ({len(st.session_state.players)}人):")
    st.code(", ".join(st.session_state.players))
    
    st.markdown("---")
    st.header("生成操作")
    
    st.info("提示：8人会自动生成14场比赛（每人搭档7次）。")
    
    if st.button("🎲 生成全赛程表 (慎点，会清空旧分)", type="primary"):
        if len(st.session_state.players) >= 4:
            generate_full_schedule()
            st.rerun()
        else:
            st.error("至少需要4人！")

    if st.button("⚠️ 清空所有数据"):
        st.session_state.players = []
        st.session_state.schedule = []
        st.rerun()
