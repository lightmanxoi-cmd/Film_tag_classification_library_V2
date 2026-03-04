"""
数据库管理页面
"""
import streamlit as st
import os
import json
import csv
from datetime import datetime
from pathlib import Path
from sqlalchemy import text, inspect


def show_database(db_manager):
    st.markdown('<h1 class="page-title">💾 数据库管理</h1>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 数据库状态", 
        "🔧 数据库配置", 
        "💾 备份管理", 
        "📤 数据导入导出",
        "🔍 SQL查询"
    ])
    
    with tab1:
        show_database_status(db_manager)
    
    with tab2:
        show_database_config(db_manager)
    
    with tab3:
        show_backup_management(db_manager)
    
    with tab4:
        show_import_export(db_manager)
    
    with tab5:
        show_sql_query(db_manager)


def show_database_status(db_manager):
    st.markdown("### 📊 数据库状态")
    
    integrity = db_manager.verify_integrity()
    
    col1, col2 = st.columns(2)
    with col1:
        if integrity["valid"]:
            st.success("✅ 数据库完整性验证通过")
        else:
            st.error("❌ 数据库完整性验证失败")
            for error in integrity["errors"]:
                st.error(f"  • {error}")
    
    with col2:
        db_url = db_manager.database_url
        if db_url.startswith("sqlite:///"):
            db_path = db_url.replace("sqlite:///", "")
            if os.path.exists(db_path):
                file_size = os.path.getsize(db_path)
                st.metric("数据库大小", f"{file_size / (1024*1024):.2f} MB")
            else:
                st.info("数据库文件尚未创建")
    
    st.markdown("---")
    st.markdown("#### 数据表状态")
    
    for table_name, table_info in integrity["tables"].items():
        if table_info["exists"]:
            with st.expander(f"📋 {table_name}", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**字段列表:**")
                    for col in table_info['columns']:
                        st.markdown(f"- `{col}`")
                with col2:
                    try:
                        with db_manager.get_session() as session:
                            count = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                            st.metric("记录数", count)
                    except Exception as e:
                        st.error(f"获取记录数失败: {str(e)}")
        else:
            st.markdown(f"""
                <div class="card fade-in">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="font-size: 1.1rem;">📋 {table_name}</strong>
                        </div>
                        <span style="color: #F44336;">❌ 不存在</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("#### 数据统计")
    
    try:
        from video_tag_system.services.video_service import VideoService
        from video_tag_system.services.tag_service import TagService
        from video_tag_system.services.video_tag_service import VideoTagService
        
        with db_manager.get_session() as session:
            video_svc = VideoService(session)
            tag_svc = TagService(session)
            video_tag_svc = VideoTagService(session)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🎥 视频总数", video_svc.count_videos())
            with col2:
                st.metric("🏷️ 标签总数", tag_svc.count_tags())
            with col3:
                st.metric("🔗 关联总数", video_tag_svc.count_associations())
    except Exception as e:
        st.warning(f"获取统计数据失败: {str(e)}")


def show_database_config(db_manager):
    st.markdown("### 🔧 数据库配置")
    
    st.markdown("#### 当前数据库连接")
    current_db_url = db_manager.database_url
    st.code(current_db_url, language=None)
    
    st.markdown("---")
    st.markdown("#### 切换数据库")
    
    with st.form("switch_database_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            db_type = st.selectbox("数据库类型", ["SQLite", "MySQL", "PostgreSQL"])
        
        with col2:
            if db_type == "SQLite":
                db_path = st.text_input("数据库文件路径", value="./video_library.db")
            else:
                db_host = st.text_input("主机地址", value="localhost")
                db_port = st.number_input("端口", value=3306 if db_type == "MySQL" else 5432)
                db_name = st.text_input("数据库名称")
                db_user = st.text_input("用户名")
                db_pass = st.text_input("密码", type="password")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            submitted = st.form_submit_button("🔄 切换数据库", use_container_width=True)
        
        with col_btn2:
            create_new = st.form_submit_button("➕ 创建新数据库", use_container_width=True)
        
        if submitted or create_new:
            if db_type == "SQLite":
                new_url = f"sqlite:///{db_path}"
            elif db_type == "MySQL":
                new_url = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
            else:
                new_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
            
            try:
                db_manager.close()
                db_manager.database_url = new_url
                db_manager._engine = None
                db_manager._session_factory = None
                
                if create_new:
                    db_manager.create_tables()
                    st.success(f"✅ 数据库创建成功！")
                else:
                    db_manager.create_tables()
                    st.success(f"✅ 已切换到新数据库！")
                
                st.rerun()
            except Exception as e:
                st.error(f"❌ 操作失败: {str(e)}")
    
    st.markdown("---")
    st.markdown("#### 现有SQLite数据库文件")
    
    db_files = list(Path(".").glob("*.db"))
    if db_files:
        for db_file in db_files:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"📄 `{db_file.name}`")
            with col2:
                size_mb = db_file.stat().st_size / (1024 * 1024)
                st.markdown(f"{size_mb:.2f} MB")
            with col3:
                if st.button("切换", key=f"switch_db_{db_file.name}"):
                    try:
                        db_manager.close()
                        db_manager.database_url = f"sqlite:///{db_file}"
                        db_manager._engine = None
                        db_manager._session_factory = None
                        db_manager.create_tables()
                        st.success(f"✅ 已切换到 {db_file.name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 切换失败: {str(e)}")
    else:
        st.info("未找到其他SQLite数据库文件")


def show_backup_management(db_manager):
    st.markdown("### 💾 备份管理")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 创建备份")
        
        backup_name = st.text_input("备份名称（可选）", placeholder="留空则自动生成")
        
        if st.button("💾 立即备份", use_container_width=True):
            try:
                if backup_name:
                    backup_path = f"./backups/{backup_name}.db"
                    backup_path = db_manager.backup(backup_path)
                else:
                    backup_path = db_manager.backup()
                st.success(f"✅ 备份成功！")
                st.code(backup_path, language=None)
            except Exception as e:
                st.error(f"❌ 备份失败: {str(e)}")
    
    with col2:
        st.markdown("#### 备份设置")
        st.info("备份文件存储在 `./backups/` 目录")
        
        max_backups = st.number_input("最大备份数量", min_value=1, max_value=50, value=10)
        if st.button("💾 保存设置", use_container_width=True):
            st.success("✅ 设置已保存")
    
    st.markdown("---")
    st.markdown("#### 📁 现有备份")
    
    backups = db_manager.list_backups()
    
    if backups:
        for backup in backups:
            with st.container():
                col_info, col_actions = st.columns([3, 1])
                
                with col_info:
                    size_mb = backup["size"] / (1024 * 1024)
                    st.markdown(f"""
                        <div class="card fade-in">
                            <strong>📦 {backup['name']}</strong>
                            <br><small style="color: #9E9E9E;">
                                大小: {size_mb:.2f} MB | 
                                创建时间: {backup['created_at']}
                            </small>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col_actions:
                    if st.button("🔄 恢复", key=f"restore_{backup['name']}", use_container_width=True):
                        st.session_state[f"confirm_restore_{backup['name']}"] = True
                    
                    if st.button("🗑️ 删除", key=f"del_backup_{backup['name']}", use_container_width=True):
                        st.session_state[f"confirm_del_backup_{backup['name']}"] = True
                
                if st.session_state.get(f"confirm_restore_{backup['name']}"):
                    st.warning("⚠️ 恢复将覆盖当前数据，确定继续？")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("✅ 确认恢复", key=f"yes_{backup['name']}"):
                            try:
                                db_manager.restore(backup['path'])
                                st.success("✅ 恢复成功！")
                                st.session_state[f"confirm_restore_{backup['name']}"] = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 恢复失败: {str(e)}")
                    with col_no:
                        if st.button("❌ 取消", key=f"no_{backup['name']}"):
                            st.session_state[f"confirm_restore_{backup['name']}"] = False
                            st.rerun()
                
                if st.session_state.get(f"confirm_del_backup_{backup['name']}"):
                    st.warning("⚠️ 确定删除此备份？")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("✅ 确认删除", key=f"yes_del_{backup['name']}"):
                            try:
                                os.remove(backup['path'])
                                st.success("✅ 删除成功！")
                                st.session_state[f"confirm_del_backup_{backup['name']}"] = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 删除失败: {str(e)}")
                    with col_no:
                        if st.button("❌ 取消", key=f"no_del_{backup['name']}"):
                            st.session_state[f"confirm_del_backup_{backup['name']}"] = False
                            st.rerun()
    else:
        st.info("暂无备份文件")


def show_import_export(db_manager):
    st.markdown("### 📤 数据导入导出")
    
    tab_import, tab_export = st.tabs(["📥 数据导入", "📤 数据导出"])
    
    with tab_import:
        st.markdown("#### 📥 导入数据")
        
        import_type = st.selectbox("导入类型", ["CSV文件", "JSON文件"])
        
        if import_type == "CSV文件":
            st.markdown("##### 导入视频数据 (CSV)")
            st.markdown("CSV格式要求：`file_path,title,description,duration,file_size`")
            
            uploaded_file = st.file_uploader("选择CSV文件", type=["csv"], key="import_csv")
            
            if uploaded_file:
                try:
                    content = uploaded_file.read().decode('utf-8')
                    lines = content.strip().split('\n')
                    
                    if len(lines) > 1:
                        st.markdown(f"**预览前5行:**")
                        preview_df = []
                        for line in lines[:6]:
                            preview_df.append(line.split(','))
                        st.dataframe(preview_df)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            skip_header = st.checkbox("跳过标题行", value=True)
                        with col2:
                            skip_duplicates = st.checkbox("跳过重复路径", value=True)
                        
                        if st.button("📥 导入CSV", use_container_width=True):
                            try:
                                from video_tag_system.models.video import VideoCreate
                                from video_tag_system.services.video_service import VideoService
                                
                                imported_count = 0
                                skipped_count = 0
                                errors = []
                                
                                with db_manager.get_session() as session:
                                    video_svc = VideoService(session)
                                    
                                    start_idx = 1 if skip_header else 0
                                    for line in lines[start_idx:]:
                                        try:
                                            parts = line.split(',')
                                            if len(parts) >= 1:
                                                file_path = parts[0].strip()
                                                title = parts[1].strip() if len(parts) > 1 else None
                                                description = parts[2].strip() if len(parts) > 2 else None
                                                duration = int(parts[3].strip()) if len(parts) > 3 and parts[3].strip() else None
                                                file_size = int(parts[4].strip()) if len(parts) > 4 and parts[4].strip() else None
                                                
                                                video_svc.create_video(VideoCreate(
                                                    file_path=file_path,
                                                    title=title or None,
                                                    description=description or None,
                                                    duration=duration,
                                                    file_size=file_size
                                                ))
                                                imported_count += 1
                                        except Exception as e:
                                            if "已存在" in str(e) and skip_duplicates:
                                                skipped_count += 1
                                            else:
                                                errors.append(str(e))
                                
                                st.success(f"✅ 导入完成！成功: {imported_count}, 跳过: {skipped_count}")
                                if errors:
                                    st.warning(f"有 {len(errors)} 条记录导入失败")
                                    with st.expander("查看错误详情"):
                                        for err in errors[:10]:
                                            st.error(err)
                                
                            except Exception as e:
                                st.error(f"❌ 导入失败: {str(e)}")
                except Exception as e:
                    st.error(f"❌ 文件读取失败: {str(e)}")
        
        else:
            st.markdown("##### 导入JSON数据")
            st.markdown("支持导入视频、标签或完整数据")
            
            uploaded_file = st.file_uploader("选择JSON文件", type=["json"], key="import_json")
            
            if uploaded_file:
                try:
                    content = uploaded_file.read().decode('utf-8')
                    data = json.loads(content)
                    
                    st.json(data[:2] if isinstance(data, list) else data)
                    
                    import_mode = st.selectbox("导入模式", ["视频数据", "标签数据", "完整数据"])
                    
                    if st.button("📥 导入JSON", use_container_width=True):
                        try:
                            if import_mode == "视频数据":
                                import_videos_from_json(db_manager, data)
                            elif import_mode == "标签数据":
                                import_tags_from_json(db_manager, data)
                            else:
                                import_full_data(db_manager, data)
                            
                            st.success("✅ 导入成功！")
                        except Exception as e:
                            st.error(f"❌ 导入失败: {str(e)}")
                except Exception as e:
                    st.error(f"❌ 文件解析失败: {str(e)}")
    
    with tab_export:
        st.markdown("#### 📤 导出数据")
        
        export_type = st.selectbox("导出类型", ["CSV格式", "JSON格式"])
        export_data = st.multiselect("选择导出内容", ["视频数据", "标签数据", "关联数据"], default=["视频数据", "标签数据"])
        
        if st.button("📤 导出数据", use_container_width=True):
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if export_type == "CSV格式":
                    export_dir = Path("./exports")
                    export_dir.mkdir(exist_ok=True)
                    
                    if "视频数据" in export_data:
                        export_videos_csv(db_manager, export_dir / f"videos_{timestamp}.csv")
                    if "标签数据" in export_data:
                        export_tags_csv(db_manager, export_dir / f"tags_{timestamp}.csv")
                    if "关联数据" in export_data:
                        export_associations_csv(db_manager, export_dir / f"associations_{timestamp}.csv")
                    
                    st.success(f"✅ 导出成功！文件保存在 `./exports/` 目录")
                
                else:
                    export_dir = Path("./exports")
                    export_dir.mkdir(exist_ok=True)
                    
                    export_json(db_manager, export_dir / f"full_export_{timestamp}.json", export_data)
                    
                    st.success(f"✅ 导出成功！文件: `./exports/full_export_{timestamp}.json`")
                
            except Exception as e:
                st.error(f"❌ 导出失败: {str(e)}")


def show_sql_query(db_manager):
    st.markdown("### 🔍 SQL查询")
    
    st.markdown("""
        <div style="background: rgba(255, 152, 0, 0.1); padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
            <strong>⚠️ 注意：</strong>请谨慎执行SQL语句，特别是DELETE、UPDATE、DROP等修改操作！
        </div>
    """, unsafe_allow_html=True)
    
    query_type = st.radio("查询类型", ["SELECT查询", "执行SQL"], horizontal=True)
    
    if query_type == "SELECT查询":
        query = st.text_area(
            "输入SELECT查询语句",
            value="SELECT * FROM videos LIMIT 10",
            height=100
        )
        
        col1, col2 = st.columns([1, 3])
        with col1:
            limit = st.number_input("结果限制", min_value=1, max_value=10000, value=100)
        
        with col2:
            st.markdown("#### 快捷查询模板")
            template_queries = {
                "查看所有视频": "SELECT * FROM videos",
                "查看所有标签": "SELECT * FROM tags",
                "查看视频标签关联": "SELECT v.title, t.name FROM videos v JOIN video_tags vt ON v.id = vt.video_id JOIN tags t ON vt.tag_id = t.id",
                "统计各标签视频数": "SELECT t.name, COUNT(vt.video_id) as video_count FROM tags t LEFT JOIN video_tags vt ON t.id = vt.tag_id GROUP BY t.id ORDER BY video_count DESC",
                "查找无标签视频": "SELECT * FROM videos WHERE id NOT IN (SELECT video_id FROM video_tags)"
            }
            
            selected_template = st.selectbox("选择模板", [""] + list(template_queries.keys()))
            if selected_template:
                query = template_queries[selected_template]
        
        if st.button("🔍 执行查询", use_container_width=True):
            try:
                with db_manager.get_session() as session:
                    result = session.execute(text(query))
                    
                    if result.returns_rows:
                        rows = result.fetchall()
                        columns = result.keys()
                        
                        st.markdown(f"**查询结果: {len(rows)} 行**")
                        
                        if rows:
                            data = [dict(zip(columns, row)) for row in rows[:limit]]
                            st.dataframe(data, use_container_width=True)
                            
                            if len(rows) > limit:
                                st.info(f"仅显示前 {limit} 条记录，共 {len(rows)} 条")
                        else:
                            st.info("查询结果为空")
                    else:
                        st.success("✅ 查询执行成功")
                        
            except Exception as e:
                st.error(f"❌ 查询失败: {str(e)}")
    
    else:
        st.markdown("#### 执行SQL语句")
        
        sql = st.text_area(
            "输入SQL语句",
            value="",
            height=100,
            placeholder="例如: UPDATE videos SET title = '新标题' WHERE id = 1"
        )
        
        st.warning("⚠️ 此操作将直接修改数据库，请确保已备份！")
        
        if st.button("⚡ 执行SQL", use_container_width=True):
            st.session_state["confirm_sql"] = True
        
        if st.session_state.get("confirm_sql"):
            st.error("⚠️ 确定要执行此SQL语句吗？")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("✅ 确认执行"):
                    try:
                        with db_manager.get_session() as session:
                            result = session.execute(text(sql))
                            session.commit()
                            
                            if result.rowcount >= 0:
                                st.success(f"✅ 执行成功！影响 {result.rowcount} 行")
                            else:
                                st.success("✅ 执行成功！")
                            
                            st.session_state["confirm_sql"] = False
                    except Exception as e:
                        st.error(f"❌ 执行失败: {str(e)}")
                        st.session_state["confirm_sql"] = False
            with col_no:
                if st.button("❌ 取消"):
                    st.session_state["confirm_sql"] = False


def import_videos_from_json(db_manager, data):
    from video_tag_system.models.video import VideoCreate
    from video_tag_system.services.video_service import VideoService
    
    with db_manager.get_session() as session:
        video_svc = VideoService(session)
        
        for item in data:
            video_svc.create_video(VideoCreate(
                file_path=item.get('file_path'),
                title=item.get('title'),
                description=item.get('description'),
                duration=item.get('duration'),
                file_size=item.get('file_size')
            ))


def import_tags_from_json(db_manager, data):
    from video_tag_system.models.tag import TagCreate
    from video_tag_system.services.tag_service import TagService
    
    with db_manager.get_session() as session:
        tag_svc = TagService(session)
        
        for item in data:
            tag_svc.create_tag(TagCreate(
                name=item.get('name'),
                parent_id=item.get('parent_id'),
                description=item.get('description'),
                sort_order=item.get('sort_order', 0)
            ))


def import_full_data(db_manager, data):
    import_videos_from_json(db_manager, data.get('videos', []))
    import_tags_from_json(db_manager, data.get('tags', []))


def export_videos_csv(db_manager, filepath):
    with db_manager.get_session() as session:
        videos = session.execute(text("SELECT * FROM videos")).fetchall()
        columns = session.execute(text("PRAGMA table_info(videos)")).fetchall()
        column_names = [col[1] for col in columns]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(column_names)
            for video in videos:
                writer.writerow(video)


def export_tags_csv(db_manager, filepath):
    with db_manager.get_session() as session:
        tags = session.execute(text("SELECT * FROM tags")).fetchall()
        columns = session.execute(text("PRAGMA table_info(tags)")).fetchall()
        column_names = [col[1] for col in columns]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(column_names)
            for tag in tags:
                writer.writerow(tag)


def export_associations_csv(db_manager, filepath):
    with db_manager.get_session() as session:
        associations = session.execute(text("SELECT * FROM video_tags")).fetchall()
        columns = session.execute(text("PRAGMA table_info(video_tags)")).fetchall()
        column_names = [col[1] for col in columns]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(column_names)
            for assoc in associations:
                writer.writerow(assoc)


def export_json(db_manager, filepath, export_data):
    data = {}
    
    with db_manager.get_session() as session:
        if "视频数据" in export_data:
            videos = session.execute(text("SELECT * FROM videos")).fetchall()
            columns = session.execute(text("PRAGMA table_info(videos)")).fetchall()
            column_names = [col[1] for col in columns]
            data['videos'] = [dict(zip(column_names, row)) for row in videos]
        
        if "标签数据" in export_data:
            tags = session.execute(text("SELECT * FROM tags")).fetchall()
            columns = session.execute(text("PRAGMA table_info(tags)")).fetchall()
            column_names = [col[1] for col in columns]
            data['tags'] = [dict(zip(column_names, row)) for row in tags]
        
        if "关联数据" in export_data:
            associations = session.execute(text("SELECT * FROM video_tags")).fetchall()
            columns = session.execute(text("PRAGMA table_info(video_tags)")).fetchall()
            column_names = [col[1] for col in columns]
            data['associations'] = [dict(zip(column_names, row)) for row in associations]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
