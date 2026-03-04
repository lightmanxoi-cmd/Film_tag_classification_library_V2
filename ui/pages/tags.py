"""
标签管理页面
"""
import streamlit as st
from video_tag_system.models.tag import TagCreate, TagUpdate, TagMergeRequest
from video_tag_system.exceptions import DuplicateTagError, TagNotFoundError, ValidationError, TagMergeError


def show_tags(get_services):
    st.markdown('<h1 class="page-title">🏷️ 标签管理</h1>', unsafe_allow_html=True)
    
    video_svc, tag_svc, video_tag_svc, session = get_services()
    
    try:
        tab1, tab2, tab3 = st.tabs(["🌲 标签树", "➕ 添加标签", "🔗 合并标签"])
        
        with tab1:
            tag_tree = tag_svc.get_tag_tree()
            
            if tag_tree.items:
                st.markdown("### 📊 标签统计概览")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("一级标签", len(tag_tree.items))
                with col2:
                    child_count = sum(len(p.children) for p in tag_tree.items)
                    st.metric("二级标签", child_count)
                with col3:
                    total = len(tag_tree.items) + child_count
                    st.metric("标签总数", total)
                
                st.markdown("---")
                st.markdown("### 🌲 标签树结构")
                
                for parent in tag_tree.items:
                    video_count = video_tag_svc.get_tag_video_count(parent.id)
                    
                    with st.expander(
                        f"📁 {parent.name} ({video_count} 个视频)",
                        expanded=True
                    ):
                        col_info, col_actions = st.columns([3, 1])
                        
                        with col_info:
                            if parent.description:
                                st.markdown(f"📝 {parent.description}")
                            st.caption(f"排序: {parent.sort_order} | 创建于: {parent.created_at.strftime('%Y-%m-%d')}")
                        
                        with col_actions:
                            if st.button("✏️", key=f"edit_parent_{parent.id}", help="编辑"):
                                st.session_state[f"editing_tag_{parent.id}"] = True
                            if st.button("🗑️", key=f"del_parent_{parent.id}", help="删除"):
                                st.session_state[f"deleting_tag_{parent.id}"] = True
                        
                        if st.session_state.get(f"editing_tag_{parent.id}"):
                            with st.form(f"edit_parent_form_{parent.id}"):
                                new_name = st.text_input("名称", value=parent.name)
                                new_desc = st.text_area("描述", value=parent.description or "")
                                new_order = st.number_input("排序", value=parent.sort_order, min_value=0)
                                
                                if st.form_submit_button("保存"):
                                    try:
                                        tag_svc.update_tag(parent.id, TagUpdate(
                                            name=new_name,
                                            description=new_desc or None,
                                            sort_order=new_order
                                        ))
                                        st.success("✅ 更新成功！")
                                        st.session_state[f"editing_tag_{parent.id}"] = False
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ {str(e)}")
                        
                        if st.session_state.get(f"deleting_tag_{parent.id}"):
                            st.warning(f"⚠️ 确定删除标签「{parent.name}」？")
                            if st.button("确认删除", key=f"confirm_del_parent_{parent.id}"):
                                try:
                                    tag_svc.delete_tag(parent.id)
                                    st.success("✅ 删除成功！")
                                    st.rerun()
                                except ValidationError as e:
                                    st.error(f"❌ {str(e)}")
                        
                        if parent.children:
                            for child in parent.children:
                                child_video_count = video_tag_svc.get_tag_video_count(child.id)
                                
                                st.markdown(f"""
                                    <div class="tree-item child">
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <div>
                                                <span style="font-weight: 500;">📂 {child.name}</span>
                                                <span style="color: #9E9E9E; font-size: 0.85rem;">
                                                    ({child_video_count} 个视频)
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                col_edit, col_del = st.columns(2)
                                with col_edit:
                                    if st.button("✏️", key=f"edit_child_{child.id}", help="编辑"):
                                        st.session_state[f"editing_tag_{child.id}"] = True
                                with col_del:
                                    if st.button("🗑️", key=f"del_child_{child.id}", help="删除"):
                                        st.session_state[f"deleting_tag_{child.id}"] = True
                                
                                if st.session_state.get(f"editing_tag_{child.id}"):
                                    with st.form(f"edit_child_form_{child.id}"):
                                        new_name = st.text_input("名称", value=child.name)
                                        new_desc = st.text_area("描述", value=child.description or "")
                                        
                                        if st.form_submit_button("保存"):
                                            try:
                                                tag_svc.update_tag(child.id, TagUpdate(
                                                    name=new_name,
                                                    description=new_desc or None
                                                ))
                                                st.success("✅ 更新成功！")
                                                st.session_state[f"editing_tag_{child.id}"] = False
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"❌ {str(e)}")
                                
                                if st.session_state.get(f"deleting_tag_{child.id}"):
                                    st.warning(f"⚠️ 确定删除标签「{child.name}」？")
                                    if st.button("确认删除", key=f"confirm_del_child_{child.id}"):
                                        try:
                                            tag_svc.delete_tag(child.id)
                                            st.success("✅ 删除成功！")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ {str(e)}")
            else:
                st.markdown("""
                    <div class="empty-state">
                        <div class="empty-state-icon">🏷️</div>
                        <div class="empty-state-text">暂无标签数据</div>
                        <p style="color: #9E9E9E;">点击"添加标签"开始创建</p>
                    </div>
                """, unsafe_allow_html=True)
        
        with tab2:
            st.markdown("### ➕ 添加新标签")
            
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.markdown("#### 添加一级标签")
                with st.form("add_parent_tag"):
                    parent_name = st.text_input("标签名称 *", placeholder="如：动作")
                    parent_desc = st.text_area("描述", placeholder="标签描述...")
                    parent_order = st.number_input("排序", min_value=0, value=0)
                    
                    if st.form_submit_button("➕ 添加一级标签", use_container_width=True):
                        if not parent_name:
                            st.error("❌ 标签名称不能为空！")
                        else:
                            try:
                                tag = tag_svc.create_tag(TagCreate(
                                    name=parent_name,
                                    description=parent_desc or None,
                                    sort_order=parent_order
                                ))
                                st.success(f"✅ 一级标签「{tag.name}」添加成功！")
                                st.rerun()
                            except DuplicateTagError:
                                st.error("❌ 该标签名称已存在！")
                            except Exception as e:
                                st.error(f"❌ 添加失败: {str(e)}")
            
            with col_right:
                st.markdown("#### 添加二级标签")
                tag_tree = tag_svc.get_tag_tree()
                
                if tag_tree.items:
                    parent_options = {f"{p.name} (ID: {p.id})": p.id for p in tag_tree.items}
                    
                    with st.form("add_child_tag"):
                        child_name = st.text_input("标签名称 *", placeholder="如：武侠")
                        selected_parent = st.selectbox("父标签 *", list(parent_options.keys()))
                        child_desc = st.text_area("描述", placeholder="标签描述...")
                        
                        if st.form_submit_button("➕ 添加二级标签", use_container_width=True):
                            if not child_name:
                                st.error("❌ 标签名称不能为空！")
                            else:
                                try:
                                    parent_id = parent_options[selected_parent]
                                    tag = tag_svc.create_tag(TagCreate(
                                        name=child_name,
                                        parent_id=parent_id,
                                        description=child_desc or None
                                    ))
                                    st.success(f"✅ 二级标签「{tag.name}」添加成功！")
                                    st.rerun()
                                except DuplicateTagError:
                                    st.error("❌ 该标签名称在当前父标签下已存在！")
                                except Exception as e:
                                    st.error(f"❌ 添加失败: {str(e)}")
                else:
                    st.info("💡 请先添加一级标签")
        
        with tab3:
            st.markdown("### 🔗 合并标签")
            st.markdown("""
                <div style="background: rgba(255, 152, 0, 0.1); padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
                    <strong>⚠️ 注意：</strong>合并操作将把源标签的所有视频关联转移到目标标签，然后删除源标签。此操作不可恢复！
                </div>
            """, unsafe_allow_html=True)
            
            tag_tree = tag_svc.get_tag_tree()
            
            if tag_tree.items:
                all_tags = []
                for parent in tag_tree.items:
                    all_tags.append((parent.id, parent.name, None))
                    for child in parent.children:
                        all_tags.append((child.id, child.name, parent.name))
                
                tag_options = {f"{t[1]}" + (f" ({t[2]})" if t[2] else "") + f" [ID:{t[0]}]": t[0] for t in all_tags}
                
                col1, col2 = st.columns(2)
                
                with col1:
                    source_selection = st.selectbox("源标签（将被删除）", list(tag_options.keys()), key="source_tag")
                
                with col2:
                    target_selection = st.selectbox("目标标签（将保留）", list(tag_options.keys()), key="target_tag")
                
                if st.button("🔗 执行合并", use_container_width=True):
                    source_id = tag_options[source_selection]
                    target_id = tag_options[target_selection]
                    
                    if source_id == target_id:
                        st.error("❌ 源标签和目标标签不能相同！")
                    else:
                        try:
                            result = tag_svc.merge_tags(TagMergeRequest(
                                source_tag_id=source_id,
                                target_tag_id=target_id
                            ))
                            st.success(f"✅ 合并成功！转移了 {result['transferred_relations']} 个视频关联")
                            st.rerun()
                        except TagMergeError as e:
                            st.error(f"❌ 合并失败: {str(e)}")
                        except Exception as e:
                            st.error(f"❌ 操作失败: {str(e)}")
            else:
                st.info("💡 暂无标签可合并")
    
    finally:
        session.close()
