"""
视频管理页面
"""
import streamlit as st
from video_tag_system.models.video import VideoCreate, VideoUpdate
from video_tag_system.models.tag import TagCreate
from video_tag_system.exceptions import VideoNotFoundError, DuplicateVideoError


def show_videos(get_services):
    st.markdown('<h1 class="page-title">🎥 视频管理</h1>', unsafe_allow_html=True)
    
    video_svc, tag_svc, video_tag_svc, session = get_services()
    
    try:
        tab1, tab2 = st.tabs(["📋 视频列表", "➕ 添加视频"])
        
        with tab1:
            col_search, col_filter = st.columns([3, 1])
            
            with col_search:
                search_keyword = st.text_input(
                    "搜索视频",
                    placeholder="输入标题、路径或描述...",
                    label_visibility="collapsed"
                )
            
            with col_filter:
                tag_tree = tag_svc.get_tag_tree()
                all_tags = []
                for parent in tag_tree.items:
                    all_tags.append((parent.id, parent.name, None))
                    for child in parent.children:
                        all_tags.append((child.id, child.name, parent.name))
                
                tag_options = ["全部"] + [f"{t[1]}" + (f" ({t[2]})" if t[2] else "") for t in all_tags]
                selected_filter = st.selectbox("标签筛选", tag_options, label_visibility="collapsed")
            
            if selected_filter != "全部":
                selected_idx = tag_options.index(selected_filter) - 1
                tag_ids = [all_tags[selected_idx][0]]
                videos_data = video_svc.list_videos_by_tags(tag_ids=tag_ids, page_size=100)
                videos = videos_data.items
                total = videos_data.total
            else:
                videos_data = video_svc.list_videos(search=search_keyword if search_keyword else None, page_size=100)
                videos = videos_data.items
                total = videos_data.total
            
            st.markdown(f"<p style='color: #9E9E9E;'>共找到 <strong style='color: #FF4B4B;'>{total}</strong> 个视频</p>", unsafe_allow_html=True)
            
            if videos:
                for video in videos:
                    with st.container():
                        st.markdown(f"""
                            <div class="card fade-in">
                                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                    <div style="flex: 1;">
                                        <h3 style="margin: 0; color: #FAFAFA;">{video.title or '未命名视频'}</h3>
                                        <p style="color: #9E9E9E; font-size: 0.85rem; margin: 0.25rem 0;">
                                            📁 {video.file_path}
                                        </p>
                                    </div>
                                    <div style="text-align: right;">
                                        <span style="color: #FF4B4B; font-weight: 600;">ID: {video.id}</span>
                                    </div>
                                </div>
                        """, unsafe_allow_html=True)
                        
                        col_info, col_tags = st.columns([1, 1])
                        
                        with col_info:
                            info_items = []
                            if video.duration:
                                hours = video.duration // 3600
                                minutes = (video.duration % 3600) // 60
                                seconds = video.duration % 60
                                if hours > 0:
                                    info_items.append(f"⏱️ {hours}:{minutes:02d}:{seconds:02d}")
                                else:
                                    info_items.append(f"⏱️ {minutes}:{seconds:02d}")
                            if video.file_size:
                                size_mb = video.file_size / (1024 * 1024)
                                info_items.append(f"💾 {size_mb:.1f} MB")
                            info_items.append(f"📅 {video.created_at.strftime('%Y-%m-%d %H:%M')}")
                            
                            st.markdown(f"""
                                <div style="color: #9E9E9E; font-size: 0.9rem;">
                                    {' | '.join(info_items)}
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
                        
                        if video.description:
                            st.markdown(f"""
                                <div style="color: #9E9E9E; font-size: 0.85rem; margin-top: 0.5rem; 
                                            padding: 0.5rem; background: rgba(0,0,0,0.2); border-radius: 0.5rem;">
                                    📝 {video.description}
                                </div>
                            """, unsafe_allow_html=True)
                        
                        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
                        
                        with col_btn1:
                            if st.button("✏️ 编辑", key=f"edit_{video.id}", use_container_width=True):
                                st.session_state[f"editing_video_{video.id}"] = True
                        
                        with col_btn2:
                            if st.button("🏷️ 标签", key=f"tags_{video.id}", use_container_width=True):
                                st.session_state[f"managing_tags_{video.id}"] = True
                        
                        with col_btn3:
                            if st.button("📋 复制路径", key=f"copy_{video.id}", use_container_width=True):
                                st.code(video.file_path, language=None)
                        
                        with col_btn4:
                            if st.button("🗑️ 删除", key=f"delete_{video.id}", use_container_width=True):
                                st.session_state[f"confirm_delete_{video.id}"] = True
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        if st.session_state.get(f"editing_video_{video.id}"):
                            with st.form(f"edit_form_{video.id}"):
                                st.markdown("### ✏️ 编辑视频")
                                new_title = st.text_input("标题", value=video.title or "")
                                new_desc = st.text_area("描述", value=video.description or "")
                                new_duration = st.number_input("时长（秒）", value=video.duration or 0, min_value=0)
                                
                                col_save, col_cancel = st.columns(2)
                                with col_save:
                                    if st.form_submit_button("💾 保存", use_container_width=True):
                                        try:
                                            video_svc.update_video(video.id, VideoUpdate(
                                                title=new_title or None,
                                                description=new_desc or None,
                                                duration=new_duration or None
                                            ))
                                            st.success("✅ 更新成功！")
                                            st.session_state[f"editing_video_{video.id}"] = False
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ 更新失败: {str(e)}")
                                
                                with col_cancel:
                                    if st.form_submit_button("❌ 取消", use_container_width=True):
                                        st.session_state[f"editing_video_{video.id}"] = False
                                        st.rerun()
                        
                        if st.session_state.get(f"managing_tags_{video.id}"):
                            st.markdown("### 🏷️ 管理标签")
                            
                            current_tag_ids = {t.id for t in video.tags}
                            
                            available_tags = []
                            for parent in tag_tree.items:
                                available_tags.append((parent.id, parent.name, None))
                                for child in parent.children:
                                    available_tags.append((child.id, child.name, parent.name))
                            
                            tag_selections = {}
                            for tag_id, tag_name, parent_name in available_tags:
                                label = f"{tag_name}" + (f" ({parent_name})" if parent_name else "")
                                tag_selections[tag_id] = st.checkbox(
                                    label,
                                    value=tag_id in current_tag_ids,
                                    key=f"tag_select_{video.id}_{tag_id}"
                                )
                            
                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                if st.button("💾 保存标签", key=f"save_tags_{video.id}", use_container_width=True):
                                    selected_tag_ids = [tid for tid, selected in tag_selections.items() if selected]
                                    try:
                                        video_tag_svc.set_video_tags(video.id, selected_tag_ids)
                                        st.success("✅ 标签更新成功！")
                                        st.session_state[f"managing_tags_{video.id}"] = False
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ 更新失败: {str(e)}")
                            
                            with col_cancel:
                                if st.button("❌ 取消", key=f"cancel_tags_{video.id}", use_container_width=True):
                                    st.session_state[f"managing_tags_{video.id}"] = False
                                    st.rerun()
                        
                        if st.session_state.get(f"confirm_delete_{video.id}"):
                            st.warning(f"⚠️ 确定要删除视频「{video.title or video.file_path}」吗？此操作不可恢复！")
                            col_confirm, col_cancel = st.columns(2)
                            with col_confirm:
                                if st.button("✅ 确认删除", key=f"confirm_del_{video.id}", use_container_width=True):
                                    try:
                                        video_svc.delete_video(video.id)
                                        st.success("✅ 删除成功！")
                                        st.session_state[f"confirm_delete_{video.id}"] = False
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ 删除失败: {str(e)}")
                            with col_cancel:
                                if st.button("❌ 取消", key=f"cancel_del_{video.id}", use_container_width=True):
                                    st.session_state[f"confirm_delete_{video.id}"] = False
                                    st.rerun()
                        
                        st.markdown("---")
            else:
                st.markdown("""
                    <div class="empty-state">
                        <div class="empty-state-icon">🎥</div>
                        <div class="empty-state-text">暂无视频数据</div>
                        <p style="color: #9E9E9E;">点击"添加视频"标签页开始添加</p>
                    </div>
                """, unsafe_allow_html=True)
        
        with tab2:
            st.markdown("### ➕ 添加新视频")
            
            with st.form("add_video_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    file_path = st.text_input("文件路径 *", placeholder="/movies/video.mp4")
                    title = st.text_input("标题", placeholder="视频标题")
                    duration_str = st.text_input("时长", placeholder="格式: 1:30:00 或 90")
                
                with col2:
                    description = st.text_area("描述", placeholder="视频描述...")
                    file_size = st.number_input("文件大小 (MB)", min_value=0, value=0)
                
                if st.form_submit_button("➕ 添加视频", use_container_width=True):
                    if not file_path:
                        st.error("❌ 文件路径不能为空！")
                    else:
                        try:
                            duration = None
                            if duration_str:
                                if ":" in duration_str:
                                    parts = duration_str.split(":")
                                    if len(parts) == 3:
                                        duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                                    elif len(parts) == 2:
                                        duration = int(parts[0]) * 60 + int(parts[1])
                                else:
                                    duration = int(duration_str)
                            
                            video = video_svc.create_video(VideoCreate(
                                file_path=file_path,
                                title=title or None,
                                description=description or None,
                                duration=duration,
                                file_size=int(file_size * 1024 * 1024) if file_size > 0 else None
                            ))
                            st.success(f"✅ 视频添加成功！ID: {video.id}")
                            st.rerun()
                        except DuplicateVideoError:
                            st.error("❌ 该文件路径已存在！")
                        except Exception as e:
                            st.error(f"❌ 添加失败: {str(e)}")
    
    finally:
        session.close()
