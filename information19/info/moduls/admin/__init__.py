from flask import Blueprint
#1.创建蓝图对象
admin_bp = Blueprint("admin", __name__, url_prefix='/admin')

#3.导入views文件中的视图函数
from .views import *


@admin_bp.before_request
def is_admin_user():
    """每次请求之前判断该用户是否是管理员用户"""

    print(request.url)
    # 如果是访问管理员登录页面，正常引导
    if request.url.endswith('/admin/login'):
        # 不拦截
        pass
    else:
        # 获取用户id
        user_id = session.get("user_id")
        # 获取is_admin
        is_admin = session.get("is_admin", False)

        """
         1. 用户不存在，引导到新闻首页(/)
         2. is_admin==False:不是管理员，引导到新闻首页
        """
        if not user_id or not is_admin:
            return redirect('/')

