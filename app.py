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
    
    .mode-badge {
        padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;
        display: inline-block; margin-bottom: 10px; width: 100%; text-align: center;
    }
    .badge-casual { background-color: #e3f2fd; color: #1565c0; border: 1px solid #1565c0; }
    .badge-pro { background-color: #fff3e0; color: #e65100; border: 1px solid #e65100; }
    
    .player-names {
        font-size: 16px; font-weight: bold; 
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .round-header {
        background-color: #f0f2f6; padding: 5px 10px; border-radius: 5px;
        font-weight: bold; color: #555; margin-bottom: 10px; display: flex; justify-content: space-between;
    }
    .court-label {
        font-size: 12px; color: #888; text-transform: uppercase; font-weight: bold; margin-bottom: 2px;
    }
    .lock-tip {
        color: #666; font-style: italic; font-size: 12px; text-align: center; margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 初始化数据 ---
if 'players' not in st.session_state:
    st.session_state.players = [f"选手{i+1}" for i in range(8)]
if 'schedule' not in st.session_state:
    st.session_state.schedule = []
if 'match_mode' not in st.session_state:
    st.session_state.match_mode = "casual"
if 'court_num' not in st.session_state:
    st.session_state.court_num = 1 # 默认1块场地

# --- 核心算法 ---

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

def generate_full_schedule(mode, court_num):
    current_players = [p for p in st.session_state.players if p and str(p).strip()]
    n = len(current_players)
    if n < 4:
        st.error("至少需要4人才能生成赛程！")
        return False

    target_matches = get_target_match_count(n, mode)
    st.session_state.match_mode = mode
    st.session_state.court_num = court_num
    
    all_pairs = list(itertools.combinations(current_players, 2))
    best_schedule = []
    
    # 增加尝试次数
    for _ in range(500):
        random.shuffle(all_pairs)
        temp_schedule = []
        # 复制一份用于消耗
        # 注意：为了更灵活，我们不真正remove，而是标记使用次数
        # 这里简化处理：每轮重新评估权重
        
        player_matches_count = {p: 0 for p in current_players}
        
        schedule_success = True
        
        # 我们按“批次”生成。
        # 如果是单场地，一批 1 场。
        # 如果是双场地，一批 2 场（且这2场人不能冲突）。
        
        matches_generated = 0
        while matches_generated < target_matches:
            batch_size = court_num
            # 如果剩下的场次不够一批，就剩几场排几场
            if target_matches - matches_generated < batch_size:
                batch_size = target_matches - matches_generated
            
            # 这一批次选出的比赛
            batch_matches = []
            batch_players = set() # 这一批次已上场的人
            
            # 尝试在这个批次里填入 batch_size 场比赛
            for _ in range(batch_size):
                # 寻找一场最佳比赛
                # 1. 过滤掉：包含已经在 batch_players 里的人的 pair
                # 2. 排序：优先选打得少的人
                
                valid_pairs = []
                for pair in all_pairs:
                    # 规则1：当前批次不能冲突
                    if pair[0] in batch_players or pair[1] in batch_players:
                        continue
                    
                    valid_pairs.append(pair)
                
                if not valid_pairs:
                    schedule_success = False; break
                
                # 智能排序
                # 寻找对手：我们需要为 valid_pair 找一个 valid_opponent
                # 这里的逻辑稍微复杂，我们简化为：直接在 all_pairs 里找两对不冲突的
                
                # 重构逻辑：直接找 best match (p1 vs p2)
                # 遍历 valid_pairs 作为 p1，再在剩下的里面找 p2
                
                best_match = None
                best_score = 9999
                
                # 为了性能，打乱 valid_pairs 取前 30 个尝试
                random.shuffle(valid_pairs)
                candidates_p1 = valid_pairs[:30]
                
                for p1 in candidates_p1:
                    # p2 必须也不能在 batch_players 里，且不能和 p1 冲突
                    candidates_p2 = [p for p in all_pairs if set(p).isdisjoint(set(p1)) and p[0] not in batch_players and p[1] not in batch_players]
                    
                    if not candidates_p2: continue
                    
                    # 在 candidates_p2 里找一个权重最低的（平衡场次）
                    # 权重 = p1和p2四个人已打场次之和
                    # 额外规则：避免连续上场（检查上一批次）
                    
                    # 获取上一批次的玩家
                    last_batch_players = []
                    if len(temp_schedule) >= court_num:
                        # 取最后 court_num 场比赛的玩家
                        start_idx = len(temp_schedule) - ((len(temp_schedule)-1) % court_num + 1)
                        # 这里简单点：只要是在 temp_schedule 最后的比赛里出现过
                        # 其实对于双场地，上一轮就是上一次的 batch
                        # 逻辑太复杂容易出错，简化：
                        pass
                        
                    for p2 in candidates_p2:
                        score = 0
                        for p in p1 + p2:
                            score += player_matches_count[p]
                            # 简单的防连打：如果这个人刚打完上一场(id最大那个)，加分
                            if temp_schedule:
                                last_m = temp_schedule[-1]
                                if p in [last_m['t1'][0], last_m['t1'][1], last_m['t2'][0], last_m['t2'][1]]:
                                    score += 50
                        
                        if score < best_score:
                            best_score = score
                            best_match = {'t1': p1, 't2': p2}
                
                if best_match:
                    # 记录这一场
                    batch_matches.append({
                        'id': 0, 't1': best_match['t1'], 't2': best_match['t2'], 
                        's1': 0, 's2': 0, 'done': False
                    })
                    # 标记人被占用了
                    batch_players.update(best_match['t1'])
                    batch_players.update(best_match['t2'])
                else:
                    schedule_success = False; break
            
            if not schedule_success: break
            
            # 批次成功，加入总表
            for m in batch_matches:
                # 更新计数
                for p in m['t1'] + m['t2']:
                    player_matches_count[p] += 1
                temp_schedule.append(m)
                matches_generated += 1
        
        if schedule_success and len(temp_schedule) == target_matches:
            best_schedule = temp_schedule
            break # 成功找到
        
        if len(temp_schedule) > len(best_schedule):
            best_schedule = temp_schedule

    if len(best_schedule) > 0:
        for idx, match in enumerate(best_schedule):
            match['id'] = idx + 1
        st.session_state.schedule = best_schedule
        st.toast(f"✅ 双场地赛程生成！共 {len(best_schedule)} 场", icon="🎉")
        return True
    else:
        st.error("生成失败，人员冲突无法调和（可能是人数太少无法撑起双场地），请重试。")
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

# --- 侧边栏：安全锁 ---
with st.sidebar:
    st.header("🏸 赛事控制台")
    admin_pwd = st.text_input("🔑 管理员密码", type="password")
    is_admin = (admin_pwd == "1234")
    if is_admin:
        st.success("已解锁：管理员模式")
    else:
        st.info("当前：游客/只读模式")

# --- 界面 UI ---

st.title("🏸 羽毛球智能排赛")

tab1, tab2, tab3 = st.tabs(["📅 对阵录分", "🏆 排行榜", "⚙️ 赛制设置"])

# === Tab 1: 对阵表 ===
with tab1:
    if not st.session_state.schedule:
        st.info("👈 请先点击【赛制设置】生成赛程")
    else:
        st.success("🎉 赛程生成完毕！", icon="✅")
        
        # 显示模式和场地信息
        mode_text = "激斗模式 🔥" if st.session_state.match_mode == "pro" else "养生模式 ☕"
        court_text = " | 双场地并行 🏟️x2" if st.session_state.court_num == 2 else " | 单场地 🏟️x1"
        st.info(f"当前赛制：{mode_text}{court_text}")

        done_count = sum(1 for m in st.session_state.schedule if m['done'])
        total_count = len(st.session_state.schedule)
        st.progress(done_count / total_count if total_count > 0 else 0)
        
        # 获取当前场地数
        c_num = st.session_state.get('court_num', 1)
        
        # 遍历比赛，如果是双场地，按2个一组显示
        schedule = st.session_state.schedule
        
        # 辅助函数：渲染单场比赛卡片
        def render_match_card(match, court_name=""):
            with st.container(border=True):
                # 标题栏
                title_col, tag_col = st.columns([3, 1])
                with title_col:
                    if court_name:
                        st.markdown(f"<div class='court-label'>{court_name}</div>", unsafe_allow_html=True)
                with tag_col:
                    st.markdown(f"<div style='text-align:right; font-size:12px; color:#999'>#{match['id']}</div>", unsafe_allow_html=True)
                
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
                    if is_admin:
                        c_sp1, c_in1, c_in2, c_btn, c_sp2 = st.columns([0.5, 2, 2, 2, 0.5])
                        with c_in1:
                            new_s1 = st.number_input("红", 0, 30, match['s1'], key=f"s1_{match['id']}", label_visibility="collapsed")
                        with c_in2:
                            new_s2 = st.number_input("蓝", 0, 30, match['s2'], key=f"s2_{match['id']}", label_visibility="collapsed")
                        with c_btn:
                            if st.button("确认", key=f"btn_{match['id']}", type="primary"):
                                idx = match['id'] - 1
                                st.session_state.schedule[idx]['s1'] = new_s1
                                st.session_state.schedule[idx]['s2'] = new_s2
                                st.session_state.schedule[idx]['done'] = True
                                st.rerun()
                    else:
                        st.caption("🔒 等待录入...")
                else:
                    if is_admin:
                        if st.button("修改", key=f"undo_{match['id']}"):
                            idx = match['id'] - 1
                            st.session_state.schedule[idx]['done'] = False
                            st.rerun()

        # 分组渲染逻辑
        if c_num == 2:
            # 双场地逻辑：每2场一个Block
            for i in range(0, len(schedule), 2):
                round_num = i // 2 + 1
                st.markdown(f"<div class='round-header'>第 {round_num} 轮次 (同时开打)</div>", unsafe_allow_html=True)
                
                col_a, col_b = st.columns(2)
                
                # 场地 A
                if i < len(schedule):
                    with col_a:
                        render_match_card(schedule[i], "🏟️ 场地 A")
                
                # 场地 B
                if i + 1 < len(schedule):
                    with col_b:
                        render_match_card(schedule[i+1], "🏟️ 场地 B")
        else:
            # 单场地逻辑：垂直排
            for match in schedule:
                render_match_card(match)

# === Tab 2: 排行榜 ===
with tab2:
    st.header("实时排名")
    df_rank = calculate_rankings()
    if not df_rank.empty:
        st.dataframe(df_rank, hide_index=True, use_container_width=True)
    else:
        st.info("暂无数据")

# === Tab 3: 赛制设置 ===
with tab3:
    st.header("📋 赛前设置")
    
    if is_admin:
        # 1. 场地与模式
        c1, c2 = st.columns(2)
        with c1:
            court_opt = st.radio("场地数量", (1, 2), format_func=lambda x: f"{x} 块场地")
        with c2:
            mode_opt = st.radio("强度模式", ("casual", "pro"), format_func=lambda x: "养生" if x=="casual" else "激斗")

        st.markdown("---")
        
        # 2. 名单
        col_num, _ = st.columns([1, 2])
        with col_num:
            target_num = st.number_input("人数", 4, 20, len(st.session_state.players))
        
        if target_num > len(st.session_state.players):
            for i in range(len(st.session_state.players), target_num):
                st.session_state.players.append(f"选手{i+1}")
        elif target_num < len(st.session_state.players):
            st.session_state.players = st.session_state.players[:target_num]

        df_p = pd.DataFrame(st.session_state.players, columns=["名字"])
        edited = st.data_editor(df_p, use_container_width=True, hide_index=True)
        st.session_state.players = edited["名字"].tolist()
        
        # 3. 校验与生成
        if court_opt == 2 and target_num < 8:
            st.warning("⚠️ 警告：人数少于8人，很难支持双场地并行（人不够分）。建议切回单场地。")
        
        target_match = get_target_match_count(target_num, mode_opt)
        
        if st.button(f"生成赛程 ({target_match}场)", type="primary"):
            if generate_full_schedule(mode_opt, court_opt):
                st.rerun()

        if st.button("重置数据"):
            st.session_state.schedule = []
            st.rerun()
    else:
        st.warning("🔒 请输入密码解锁设置")
