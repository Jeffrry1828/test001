import logging
from flask import current_app, jsonify
from flask import g
from flask import request
from flask import session

from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import index_bp
from info import redis_store
from info.models import User, News, Category
from flask import render_template
from info import constants


# 127.0.0.1:5000/news_list?cid=x&page=1&per_page=10
@index_bp.route('/news_list')
def get_news_list():
    """获取新闻列表数据后端接口 （get）"""
    """
    1.获取参数
        1.1 cid:分类id， page:当前页码(默认值：第一页)， per_page:每一页多少条数据（默认值：10条） （数据类型json）
    2.参数校验
        2.1 非空判断
        2.2 整型强制类型转换
    3.逻辑处理
        3.1 分页查询
        3.2 对象列表转换成字典列表
    4.返回值
    """
    # 1.1 cid:分类id， page:当前页码(默认值：第一页)， per_page:每一页多少条数据（默认值：10条） （数据类型json）
    param_dict = request.args
    cid = param_dict.get('cid')
    page = param_dict.get('page', "1")
    per_page = param_dict.get('per_page', "10")

    # 2.1 非空判断
    if not cid:
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    # 2.2 整型强制类型转换
    try:
        # 进行数据向整型转换
        cid = int(cid)
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数内容格式错误")

    """
    # 2 3 4 5 6
    if cid != 1:
        paginate = News.query.filter(News.category_id == cid).order_by(News.create_time.desc()) \
            .paginate(page, per_page, False)
    else:
        # cid == 1 查询最新数据
        paginate = News.query.filter().order_by(News.create_time.desc()) \
            .paginate(page, per_page, False)
    """
    # 条件列表 默认条件：新闻必须审核通过
    filters = [News.status == 0]
    if cid != 1:
        # == 在sqlalchemy底层有重写__eq__方法，改变了该返回值，返回是一个查询条件
        filters.append(News.category_id == cid)

    # 3.1 分页查询 *filters拆包
    try:
        paginate = News.query.filter(*filters).order_by(News.create_time.desc())\
            .paginate(page, per_page, False)
        # 获取当前页码的所有数据
        news_list = paginate.items
        # 当前页码
        current_page = paginate.page
        # 总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻列表数据异常")
    # 3.2 对象列表转换成字典列表
    news_dict_list = []
    for news in news_list if news_list else []:
        news_dict_list.append(news.to_dict())

    data = {
        "news_list": news_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }
    # 4.返回值
    return jsonify(errno=RET.OK, errmsg="查询新闻列表数据成功", data=data)


#2.使用蓝图
@index_bp.route('/')
@user_login_data
def index():
    """新闻首页"""
    #------------------获取用户登录信息------------------
    #1.获取当前登录用户的id
    # user_id = session.get("user_id")
    # user = None # type:User
    # #2.查询用户对象
    # if user_id:
    #     try:
    #         # 获取到用户对象
    #         user = User.query.get(user_id)
    #     except Exception as e:
    #         current_app.logger.error(e)
    #         return jsonify(errno=RET.DBERR, errmsg="查询用户对象异常")
    # #3.将对象转成字典

    """
    基本格式：
    if user:
        user_info = user.to_dict()

    数据格式：
        "data": {
                "user_info": {"id": self.id}
            }
    使用方式：data.user_info.id
    """

    # 通过装饰器的g对象中获取当前登录的用户
    user = g.user

    # ------------------获取新闻点击排行数据------------------
    try:
        news_rank_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS).all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻排行数据异常")

    """
    # news_rank_list 对象列表===》 [news1, news2, ...新闻对象 ]
    # news_rank_dict_list 字典列表===> [{新闻字典}, {}, {}]
    """
    # 字典列表初始化
    news_rank_dict_list = []
    # 将新闻对象列表转换成字典列表
    for news_obj in news_rank_list if news_rank_list else []:
        # 将新闻对象转成字典
        news_dict = news_obj.to_dict()
        # 构建字典列表
        news_rank_dict_list.append(news_dict)

    # ------------------获取新闻分类数据------------------
    try:
        categories = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻分类数据异常")

    # 对象列表转换成字典列表
    category_dict_list = []
    for category in categories if categories else []:
        category_dict_list.append(category.to_dict())

    # 组织响应数据字典
    data = {
        "user_info": user.to_dict() if user else None,
        "news_rank_list": news_rank_dict_list,
        "categories": category_dict_list
    }

    # 返回模板
    return render_template("news/index.html",data=data)


@index_bp.route('/favicon.ico')
def favicon():
    """返回网页的图标"""
    """
    Function used internally to send static files from the static
        folder to the browser
    这个方法是被内部用来发送静态文件到浏览器的
    """
    return current_app.send_static_file("news/favicon.ico")




