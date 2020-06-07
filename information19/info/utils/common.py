# 自定义过滤器函数
from flask import current_app, jsonify
from flask import g
from flask import session
from info.utils.response_code import RET


def do_index_class(index):
    """根据index下标返回对应的class值"""
    if index == 1:
        return "first"
    elif index == 2:
        return "second"
    elif index == 3:
        return "third"
    else:
        return ""

import functools


# 获取当前登录用户信息的装饰器
def user_login_data(view_func):
    # 使用装饰器改变了被装饰的函数的一些特性，函数名称，可以使用functools解决这个问题(记忆)
    @functools.wraps(view_func)
    def wrapper(*args, **kwargs):
        #一：实现装饰器应该完成的功能（新添加的功能）
        #1.获取用户id
        user_id = session.get("user_id")
        user = None  # type:User
        # 进行延迟导入，解决循环导入db的问题
        from info.models import User
        # 2.查询用户对象
        if user_id:
            try:
                # 获取到用户对象
                user = User.query.get(user_id)
            except Exception as e:
                current_app.logger.error(e)
                return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")
        #3. 将用户对象保存到g对象中
        g.user = user
        #二：实现原有函数的基本功能
        result = view_func(*args, **kwargs)
        return result
    return wrapper
