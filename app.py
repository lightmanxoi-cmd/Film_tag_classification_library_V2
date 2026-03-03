"""
视频标签分类库管理系统 - Streamlit Web界面
"""
import streamlit as st
from video_tag_system import DatabaseManager
from video_tag_system.services.video_service import VideoService
from video_tag_system.services.tag_service import TagService
from video_tag_system.services.video_tag_service import VideoTagService

st.set_page_config(
    page_title="视频标签分类库管理系统",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

with open("ui/styles.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

@st.cache_resource
def get_db_manager():
    return DatabaseManager(database_url="sqlite:///./video_library.db", echo=False)

db_manager = get_db_manager()
db_manager.create_tables()

def get_services():
    session = db_manager.session_factory()
    return (
        VideoService(session),
        TagService(session),
        VideoTagService(session),
        session
    )

st.sidebar.markdown("""
    <div class="sidebar-header">
        <h1>🎬 视频标签管理</h1>
    </div>
""", unsafe_allow_html=True)

page = st.sidebar.radio(
    "导航菜单",
    ["📊 仪表盘", "🎥 视频管理", "🏷️ 标签管理", "🔗 标签关联", "💾 数据库管理"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
    <div class="sidebar-footer">
        <p>版本 1.0.0</p>
    </div>
""", unsafe_allow_html=True)

if page == "📊 仪表盘":
    from ui.pages.dashboard import show_dashboard
    show_dashboard(get_services)
elif page == "🎥 视频管理":
    from ui.pages.videos import show_videos
    show_videos(get_services)
elif page == "🏷️ 标签管理":
    from ui.pages.tags import show_tags
    show_tags(get_services)
elif page == "🔗 标签关联":
    from ui.pages.associations import show_associations
    show_associations(get_services)
elif page == "💾 数据库管理":
    from ui.pages.database import show_database
    show_database(db_manager)
