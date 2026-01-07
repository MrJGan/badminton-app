import streamlit as st
import pandas as pd
import random
import itertools

# --- 页面配置 ---
st.set_page_config(page_title="羽毛球赛程表", page_icon="🏸", layout="centered")

# --- CSS 样式重构 (核心修改点) ---
st.markdown("""
<style>
    /* 全局按钮样式 */
    .stButton>button { width: 100%; border-radius: 20px; font-weight: bold; }
    
    /* 对阵卡片容器 */
    .match-card-container {
        background-color: white;
        border-radius: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
        margin-bottom: 12px;
        padding: 12px;
    }
    
    /* 已完成的卡片样式 */
    .match-card-done {
        background-color: #f0f9f0; /* 淡淡的绿色背景 */
        border: 1px solid #c3e6cb;
    }

    /* 队名样式 */
    .team-name { font-size: 16px; font-weight: 600; line-height: 1.4; }
    .team-red { color: #d32f2f; }
    .team-blue { color: #1976d2; }
    
    /* 中间VS和比分样式 */
    .vs-score { 
        font-size: 20px; 
        font-weight: 900; 
        text-align: center; 
        color: #333;
        font-family: 'Arial', sans-serif;
    }
    .score-display {
        font-size: 24px;
        color: #2e7d32; /* 绿色比分 */
    }
    
    /* 场次标签 */
    .match-tag {
        font-size: 12px;
        color: #888;
        margin-bottom: 4px;
        display: block;
    }
    
    /* 去掉Streamlit原生Expander的边框，让它融入卡片 */
    .streamlit-expanderHeader {
        background-color: transparent !important;
        font-size: 14px !important;
        color: #555 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 初始化数据 ---
if 'players' not in st.session_state:
    st.session_state.players = [] 
if 'schedule' not in st.session_state:
    st.session_state.schedule = [] 

# --- 核心算法逻辑 (保持不变) ---
def generate_full_schedule():
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
    if not st.session_state.schedule:
        return pd.DataFrame()

    stats = {p: {'wins': 0, 'losses': 0, 'diff': 0, 'points': 0, 'total_score': 0} for p in st.session_state.players}
    
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

tab1, tab2, tab3 = st.tabs(["📅 对阵表", "🏆 排行榜", "⚙️ 设置"])

# === Tab 1: 对阵表 (UI大改版) ===
with tab1:
    if not st.session_state.schedule:
        st.info("暂无赛程，请去【设置】页生成比赛。")
    else:
        # 进度条
        done_count = sum(1 for m in st.session_state.schedule if m['done'])
        total_count = len(st.session_state.schedule)
        st.caption(f"比赛进度: {done_count} / {total_count}")
        st.progress(done_count / total_count if total_count > 0 else 0)

        for i, match in enumerate(st.session_state.schedule):
            # 准备数据
            t1_names = f"{match['t1'][0]}<br>{match['t1'][1]}" # 使用HTML换行
            t2_names = f"{match['t2'][0]}<br>{match['t2'][1]}"
            
            # 判断状态，决定样式
            if match['done']:
                card_class = "match-card-container match-card-done"
                center_content = f"<div class='vs-score score-display'>{match['s1']} : {match['s2']}</div>"
                status_text = "✅ 已结束 (点击修改)"
            else:
                card_class = "match-card-container"
                center_content = "<div class='vs-score' style='color:#ccc;'>VS</div>"
                status_text = "📝 录入比分"

            # --- 渲染自定义 HTML 卡片 ---
            st.markdown(f"""
            <div class="{card_class}">
                <span class="match-tag">第 {match['id']} 场</span>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="text-align: left; width: 35%;" class="team-name team-red">
                        {t1_names}
                    </div>
                    
                    <div style="width: 30%;">
                        {center_content}
                    </div>
                    
                    <div style="text-align: right; width: 35%;" class="team-name team-blue">
                        {t2_names}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # --- 录入区域 (使用 Expander 隐藏) ---
            # 我们把 Expander 放在卡片下面，或者视觉上看起来像是在卡片里
            with st.expander(status_text):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    new_s1 = st.number_input("🔴红分", 0, 30, match['s1'], key=f"s1_{match['id']}")
                with c2:
                    new_s2 = st.number_input("🔵蓝分", 0, 30, match['s2'], key=f"s2_{match['id']}")
                with c3:
                    st.write("") # 占位
                    st.write("") 
                    if st.button("确认", key=f"btn_{match['id']}"):
                        st.session_state.schedule[i]['s1'] = new_s1
                        st.session_state.schedule[i]['s2'] = new_s2
                        st.session_state.schedule[i]['done'] = True
                        st.rerun()
                
                if match['done']:
                    if st.button("撤销重录", key=f"undo_{match['id']}"):
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

# === Tab 3: 设置 ===
with tab3:
    st.header("管理选手")
    new_player = st.text_input("输入名字 (回车)", key="add_input")
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
