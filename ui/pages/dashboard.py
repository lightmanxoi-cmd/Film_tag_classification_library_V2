"""
仪表盘页面
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def show_dashboard(get_services):
    st.markdown('<h1 class="page-title">📊 系统仪表盘</h1>', unsafe_allow_html=True)
    
    video_svc, tag_svc, video_tag_svc, session = get_services()
    
    try:
        total_videos = video_svc.count_videos()
        total_tags = tag_svc.count_tags()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
                <div class="card stat-card fade-in">
                    <div class="stat-icon">🎥</div>
                    <div class="card-value">{total_videos}</div>
                    <div class="card-title">视频总数</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
                <div class="card stat-card fade-in">
                    <div class="stat-icon">🏷️</div>
                    <div class="card-value">{total_tags}</div>
                    <div class="card-title">标签总数</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            tag_tree = tag_svc.get_tag_tree()
            parent_count = len(tag_tree.items)
            st.markdown(f"""
                <div class="card stat-card fade-in">
                    <div class="stat-icon">📁</div>
                    <div class="card-value">{parent_count}</div>
                    <div class="card-title">一级标签</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col4:
            child_count = total_tags - parent_count
            st.markdown(f"""
                <div class="card stat-card fade-in">
                    <div class="stat-icon">📂</div>
                    <div class="card-value">{child_count}</div>
                    <div class="card-title">二级标签</div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("### 🏷️ 标签分布")
            
            tag_tree = tag_svc.get_tag_tree()
            if tag_tree.items:
                tag_data = []
                for parent in tag_tree.items:
                    video_count = video_tag_svc.get_tag_video_count(parent.id)
                    tag_data.append({
                        "name": parent.name,
                        "count": video_count,
                        "type": "一级标签"
                    })
                    for child in parent.children:
                        child_count = video_tag_svc.get_tag_video_count(child.id)
                        tag_data.append({
                            "name": f"  └─ {child.name}",
                            "count": child_count,
                            "type": "二级标签"
                        })
                
                if tag_data:
                    df = pd.DataFrame(tag_data)
                    fig = px.bar(
                        df, 
                        x="count", 
                        y="name",
                        orientation='h',
                        color="type",
                        color_discrete_map={"一级标签": "#FF4B4B", "二级标签": "#1E88E5"},
                        title="各标签关联视频数量"
                    )
                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#FAFAFA'),
                        title_font=dict(color='#FAFAFA'),
                        xaxis=dict(gridcolor='#2D3748', color='#FAFAFA'),
                        yaxis=dict(gridcolor='#2D3748', color='#FAFAFA'),
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("暂无标签数据")
            else:
                st.info("暂无标签数据，请先添加标签")
        
        with col_right:
            st.markdown("### 📈 最近添加的视频")
            
            recent_videos = video_svc.list_videos(page=1, page_size=5)
            if recent_videos.items:
                for video in recent_videos.items:
                    st.markdown(f"""
                        <div class="card fade-in">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <div class="card-title">{video.title or '未命名'}</div>
                                    <div style="color: #9E9E9E; font-size: 0.85rem;">
                                        {video.file_path}
                                    </div>
                                </div>
                                <div style="text-align: right;">
                                    <div style="color: #FF4B4B; font-weight: 600;">
                                        {len(video.tags)} 个标签
                                    </div>
                                    <div style="color: #9E9E9E; font-size: 0.85rem;">
                                        {video.created_at.strftime('%Y-%m-%d')}
                                    </div>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div class="empty-state">
                        <div class="empty-state-icon">🎥</div>
                        <div class="empty-state-text">暂无视频，点击"视频管理"添加</div>
                    </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 🎯 快速操作")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("➕ 添加视频", use_container_width=True):
                st.session_state["nav_to"] = "videos"
                st.rerun()
        
        with col2:
            if st.button("🏷️ 添加标签", use_container_width=True):
                st.session_state["nav_to"] = "tags"
                st.rerun()
        
        with col3:
            if st.button("💾 备份数据库", use_container_width=True):
                st.session_state["nav_to"] = "database"
                st.rerun()
    
    finally:
        session.close()
