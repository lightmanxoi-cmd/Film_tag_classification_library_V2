"""
视频-标签关联管理页面
"""
import streamlit as st
from video_tag_system.models.video_tag import BatchTagOperation


def show_associations(get_services):
    st.markdown('<h1 class="page-title">🔗 标签关联管理</h1>', unsafe_allow_html=True)
    
    video_svc, tag_svc, video_tag_svc, session = get_services()
    
    try:
        tab1, tab2, tab3 = st.tabs(["📊 关联概览", "⚡ 批量操作", "🔍 按标签筛选"])
        
        with tab1:
            st.markdown("### 📊 视频-标签关联统计")
            
            videos_data = video_svc.list_videos(page_size=100)
            tag_tree = tag_svc.get_tag_tree()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_relations = sum(len(v.tags) for v in videos_data.items)
                st.metric("总关联数", total_relations)
            
            with col2:
                avg_tags = total_relations / len(videos_data.items) if videos_data.items else 0
                st.metric("平均标签数/视频", f"{avg_tags:.1f}")
            
            with col3:
                untagged = sum(1 for v in videos_data.items if not v.tags)
                st.metric("未标签视频", untagged)
            
            st.markdown("---")
            
            if videos_data.items:
                st.markdown("### 📋 视频标签详情")
                
                for video in videos_data.items:
                    with st.container():
                        col_name, col_tags, col_actions = st.columns([2, 3, 1])
                        
                        with col_name:
                            st.markdown(f"""
                                <div>
                                    <strong>{video.title or '未命名'}</strong>
                                    <br><small style="color: #9E9E9E;">ID: {video.id}</small>
                                </div>
                            """, unsafe_allow_html=True)
                        
                        with col_tags:
                            if video.tags:
                                tags_html = " ".join([
                                    f'<span class="tag-badge {"parent" if t.level == 1 else "child"}">{t.name}</span>'
                                    for t in video.tags
                                ])
                                st.markdown(f"<div>{tags_html}</div>", unsafe_allow_html=True)
                            else:
                                st.markdown("<span style='color: #9E9E9E;'>暂无标签</span>", unsafe_allow_html=True)
                        
                        with col_actions:
                            if st.button("🏷️ 管理", key=f"manage_{video.id}", use_container_width=True):
                                st.session_state[f"editing_tags_{video.id}"] = True
                        
                        if st.session_state.get(f"editing_tags_{video.id}"):
                            current_tag_ids = {t.id for t in video.tags}
                            
                            available_tags = []
                            for parent in tag_tree.items:
                                available_tags.append((parent.id, parent.name, None))
                                for child in parent.children:
                                    available_tags.append((child.id, child.name, parent.name))
                            
                            selected_tags = st.multiselect(
                                "选择标签",
                                options=[t[0] for t in available_tags],
                                default=list(current_tag_ids),
                                format_func=lambda x: next(
                                    (f"{t[1]}" + (f" ({t[2]})" if t[2] else "") for t in available_tags if t[0] == x),
                                    str(x)
                                ),
                                key=f"multiselect_{video.id}"
                            )
                            
                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                if st.button("💾 保存", key=f"save_multi_{video.id}", use_container_width=True):
                                    try:
                                        video_tag_svc.set_video_tags(video.id, selected_tags)
                                        st.success("✅ 更新成功！")
                                        st.session_state[f"editing_tags_{video.id}"] = False
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ {str(e)}")
                            
                            with col_cancel:
                                if st.button("❌ 取消", key=f"cancel_multi_{video.id}", use_container_width=True):
                                    st.session_state[f"editing_tags_{video.id}"] = False
                                    st.rerun()
                        
                        st.markdown("---")
            else:
                st.info("暂无视频数据")
        
        with tab2:
            st.markdown("### ⚡ 批量标签操作")
            
            videos_data = video_svc.list_videos(page_size=100)
            tag_tree = tag_svc.get_tag_tree()
            
            if not videos_data.items:
                st.info("暂无视频可操作")
            elif not tag_tree.items:
                st.info("暂无标签可使用")
            else:
                col_left, col_right = st.columns(2)
                
                with col_left:
                    st.markdown("#### 批量添加标签")
                    
                    video_options = {
                        f"{v.title or '未命名'} (ID: {v.id})": v.id 
                        for v in videos_data.items
                    }
                    tag_options = {}
                    for parent in tag_tree.items:
                        tag_options[f"{parent.name}"] = parent.id
                        for child in parent.children:
                            tag_options[f"  └─ {child.name}"] = child.id
                    
                    selected_videos_add = st.multiselect(
                        "选择视频",
                        list(video_options.keys()),
                        key="batch_add_videos"
                    )
                    selected_tags_add = st.multiselect(
                        "选择要添加的标签",
                        list(tag_options.keys()),
                        key="batch_add_tags"
                    )
                    
                    if st.button("➕ 批量添加", use_container_width=True):
                        if not selected_videos_add or not selected_tags_add:
                            st.warning("请选择视频和标签")
                        else:
                            video_ids = [video_options[v] for v in selected_videos_add]
                            tag_ids = [tag_options[t] for t in selected_tags_add]
                            
                            try:
                                result = video_tag_svc.batch_add_tags(BatchTagOperation(
                                    video_ids=video_ids,
                                    tag_ids=tag_ids
                                ))
                                st.success(f"✅ {result['message']}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 操作失败: {str(e)}")
                
                with col_right:
                    st.markdown("#### 批量移除标签")
                    
                    selected_videos_remove = st.multiselect(
                        "选择视频",
                        list(video_options.keys()),
                        key="batch_remove_videos"
                    )
                    selected_tags_remove = st.multiselect(
                        "选择要移除的标签",
                        list(tag_options.keys()),
                        key="batch_remove_tags"
                    )
                    
                    if st.button("➖ 批量移除", use_container_width=True):
                        if not selected_videos_remove or not selected_tags_remove:
                            st.warning("请选择视频和标签")
                        else:
                            video_ids = [video_options[v] for v in selected_videos_remove]
                            tag_ids = [tag_options[t] for t in selected_tags_remove]
                            
                            try:
                                result = video_tag_svc.batch_remove_tags(BatchTagOperation(
                                    video_ids=video_ids,
                                    tag_ids=tag_ids
                                ))
                                st.success(f"✅ {result['message']}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 操作失败: {str(e)}")
        
        with tab3:
            st.markdown("### 🔍 按标签筛选视频")
            
            tag_tree = tag_svc.get_tag_tree()
            
            if tag_tree.items:
                all_tags = []
                for parent in tag_tree.items:
                    all_tags.append((parent.id, parent.name, None))
                    for child in parent.children:
                        all_tags.append((child.id, child.name, parent.name))
                
                tag_options = {
                    f"{t[1]}" + (f" ({t[2]})" if t[2] else ""): t[0] 
                    for t in all_tags
                }
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    selected_filter_tags = st.multiselect(
                        "选择标签进行筛选",
                        list(tag_options.keys())
                    )
                
                with col2:
                    match_mode = st.radio(
                        "匹配模式",
                        ["任意标签", "全部标签"],
                        horizontal=True
                    )
                
                if selected_filter_tags:
                    tag_ids = [tag_options[t] for t in selected_filter_tags]
                    match_all = match_mode == "全部标签"
                    
                    videos = video_svc.list_videos_by_tags(tag_ids=tag_ids, match_all=match_all, page_size=100)
                    
                    st.markdown(f"<p style='color: #9E9E9E;'>找到 <strong style='color: #FF4B4B;'>{videos.total}</strong> 个匹配的视频</p>", unsafe_allow_html=True)
                    
                    if videos.items:
                        for video in videos.items:
                            st.markdown(f"""
                                <div class="card fade-in">
                                    <div style="display: flex; justify-content: space-between;">
                                        <div>
                                            <strong style="font-size: 1.1rem;">{video.title or '未命名'}</strong>
                                            <br><small style="color: #9E9E9E;">{video.file_path}</small>
                                        </div>
                                        <div style="text-align: right;">
                                            <span style="color: #FF4B4B;">ID: {video.id}</span>
                                        </div>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("没有找到匹配的视频")
            else:
                st.info("暂无标签可筛选")
    
    finally:
        session.close()
