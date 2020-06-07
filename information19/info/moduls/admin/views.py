import time

from flask import abort
from flask import current_app
from flask import request, jsonify, redirect, url_for
from flask import session
from info import db
from info.models import User, News, Category
from info.utils.pic_storage import pic_storage
from info.utils.response_code import RET
from . import admin_bp
from flask import render_template
from datetime import datetime, timedelta
from info import constants


@admin_bp.route('/add_category', methods=['POST'])
def add_category():
    """添加、编辑分类"""
    """
    1.获取参数
        1.1 id:分类id，name:分类名称
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.0 有id值表示编辑分类
        3.1 没有id表示新增分类
    4.返回值
    """
    # 1.1 id:分类id，name:分类名称
    id = request.json.get("id")
    name = request.json.get("name")

    if not name:
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    # 3.0 有id值表示编辑分类
    if id:
        # 根据分类id查询分类对象
        try:
            category = Category.query.get(id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询分类对象异常")
        if not category:
            return jsonify(errno=RET.NODATA, errmsg="分类不存在")
        else:
            # 修改分类名称
            category.name = name
    # 3.1 没有id表示新增分类
    else:
        # 创建分类对象
        category = Category()
        category.name = name
        # 添加到数据库
        db.session.add(category)

    # 将分类对象的修改保存回数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存分类对象异常")

    return jsonify(errno=RET.OK, errmsg="OK")


@admin_bp.route('/news_type')
def news_type():
    """新闻分类页面展示"""
    # 获取分类数据
    try:
        categories = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询分类异常")

    # 对象列表转字典列表
    # 模型列表转换字典列表
    category_dict_list = []
    for category in categories if categories else []:
        category_dict = category.to_dict()
        category_dict_list.append(category_dict)

    # 删除最新分类
    category_dict_list.pop(0)

    data = {
        "categories": category_dict_list,
    }
    return render_template("admin/news_type.html", data=data)


# /admin/news_edit_detail?news_id=1
@admin_bp.route('/news_edit_detail', methods=['POST', 'GET'])
def news_edit_detail():
    """新闻编辑详情页面接口"""

    if request.method == 'GET':
        """展示详情页面"""
        # 获取新闻id
        news_id = request.args.get("news_id")
        if not news_id:
            return Exception("参数不足")
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询新闻对象异常")
        # 新闻不存在
        if not news:
            abort(404)
        # 新闻字典
        news_dict = news.to_dict()

        # 获取分类数据
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询分类异常")

        # 对象列表转字典列表
        # 模型列表转换字典列表
        category_dict_list = []
        for category in categories if categories else []:
            category_dict = category.to_dict()
            # 选中当前新闻的分类的标志位
            category_dict["is_selected"] = False
            # 当新闻的分类id和遍历拿到的分类id相等时，将标志位改为True
            if category.id == news.category_id:
                category_dict["is_selected"] = True

            category_dict_list.append(category_dict)

        # 删除最新分类
        category_dict_list.pop(0)

        data = {
            "categories": category_dict_list,
            "news": news_dict
        }
        return render_template("admin/news_edit_detail.html", data=data)

    # POST请求：发布新闻
    """
    1.获取参数
        1.1 title:新闻标题， category_id:新闻分类id，digest:新闻摘要，
            index_image:新闻主图片（非必传） content: 新闻内容，
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.0 将新闻主图片上传到七牛云
        3.1 创建新闻对象，并将其属性赋值
        3.2 保存回数据库
    4.返回值
    """

    # 1.1获取参数
    title = request.form.get("title")
    category_id = request.form.get("category_id")
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image")

    # 获取新闻id
    news_id = request.form.get("news_id")

    # 2.1 非空判断
    if not all([title, category_id, digest, content, news_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    # 只有图片有更改，才需要上传到七牛云
    pic_name = None
    if index_image:
        try:
            pic_data = index_image.read()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.PARAMERR, errmsg="图片数据不能为空")

        # 3.0 将新闻主图片上传到七牛云
        try:
            pic_name = pic_storage(pic_data)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.THIRDERR, errmsg="上传图片到七牛云失败")

    # 3.1 查询新闻对象，并将其属性赋值
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻异常")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻不存在")

    # 编辑新闻属性
    news.title = title
    news.category_id = category_id
    news.digest = digest
    news.content = content
    # 有图片名称才修改
    if pic_name:
        news.index_image_url = constants.QINIU_DOMIN_PREFIX + pic_name

    # 3.2 保存回数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存新闻对象异常")

    # 4.返回值
    return jsonify(errno=RET.OK, errmsg="发布新闻成功")


# /admin/news_edit?p=页码
@admin_bp.route('/news_edit')
def news_edit():
    """新闻编辑页面的展示"""
    # 1.获取参数
    p = request.args.get("p", 1)
    # 2.校验参数
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    news_list = []
    current_page = 1
    total_page = 1
    # 获取查询关键字
    keywords = request.args.get("keywords")
    # 条件列表  默认查询的就是非审核通过的
    filters = []
    if keywords:
        # 新闻标题包含这个关键字
        filters.append(News.title.contains(keywords))
    try:
        paginate = News.query.filter(*filters).order_by(News.create_time.desc())\
            .paginate(p, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)
        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="")

    # 模型列表转换字典列表
    news_dict_list = []
    for news in news_list if news_list else []:
        news_dict_list.append(news.to_review_dict())

    data = {
        "news_list": news_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("admin/news_edit.html", data=data)


# /admin/news_review_detail?news_id=1
@admin_bp.route('/news_review_detail', methods=['POST', 'GET'])
def news_review_detail():
    """新闻审核详情接口"""

    if request.method == 'GET':
        """展示新闻详情页面"""
        news_id = request.args.get("news_id")

        if not news_id:
            return Exception("参数不足")

        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询新闻对象异常")
        if not news:
            abort(404)

        # 对象转字典
        news_dict = news.to_dict() if news else None

        data = {
            "news": news_dict
        }

        return render_template("admin/news_review_detail.html", data=data)

    #POST请求：新闻审核
    """
    1.获取参数
        1.1 news_id:新闻id, action: 审核通过、审核不通过
    2.校验参数
        2.1 非空判断
        2.2 action in ['accept', 'reject']
    3.逻辑处理
        3.0 根据news_id查询出新闻对象
        3.1 通过：news.status = 0
        3.2 拒绝：news.status = -1 , news.reason = 拒绝原因
    4.返回值
    """
    #1.1 用户对象 新闻id comment_id评论的id，action:(点赞、取消点赞)
    params_dict = request.json
    news_id = params_dict.get("news_id")
    action = params_dict.get("action")

    #2.1 非空判断
    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    #2.3 action in ['accept', 'reject']
    if action not in ['accept', 'reject']:
        return jsonify(errno=RET.PARAMERR, errmsg="action参数错误")

    # 3.0 根据news_id查询出新闻对象
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻对象异常")
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻不存在")

    # 3.1 通过：news.status = 0
    if action == "accept":
        news.status = 0
    # 3.2 拒绝：news.status = -1 , news.reason = 拒绝原因
    else:
        # 获取拒绝原因
        reason = request.json.get("reason")
        if reason:
            news.status = -1
            news.reason = reason
        else:
            return jsonify(errno=RET.PARAMERR, errmsg="请填写拒绝原因")
    # 将新闻对象的修改保存回数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存新闻对象异常")

    return jsonify(errno=RET.OK, errmsg="OK")


# /admin/news_review?p=页码
@admin_bp.route('/news_review')
def news_review():
    """新闻审核页面的展示"""
    # 1.获取参数
    p = request.args.get("p", 1)
    # 2.校验参数
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    news_list = []
    current_page = 1
    total_page = 1
    # 获取查询关键字
    keywords = request.args.get("keywords")
    # 条件列表  默认查询的就是非审核通过的
    filters = [News.status != 0]
    if keywords:
        # 新闻标题包含这个关键字
        filters.append(News.title.contains(keywords))
    try:
        paginate = News.query.filter(*filters).order_by(News.create_time.desc())\
            .paginate(p, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)
        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="")

    # 模型列表转换字典列表
    news_dict_list = []
    for news in news_list if news_list else []:
        news_dict_list.append(news.to_review_dict())

    data = {
        "news_list": news_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("admin/news_review.html", data=data)


# /admin/user_list?p=页码
@admin_bp.route('/user_list')
def user_list():
    """查询用户列表数据"""
    # 1.获取参数
    p = request.args.get("p", 1)
    # 2.校验参数
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    user_list = []
    current_page = 1
    total_page = 1
    try:
        paginate = User.query.filter(User.is_admin == False).order_by(User.last_login.desc())\
            .paginate(p, constants.ADMIN_USER_PAGE_MAX_COUNT, False)
        # 获取当前页码的所有数据
        user_list = paginate.items
        # 当前页码
        current_page = paginate.page
        # 总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="")

    # 对象列表转字典列表
    user_dict_list = []
    for user in user_list if user_list else []:
        user_dict_list.append(user.to_admin_dict())

    # 组织响应数据
    data = {
        "users": user_dict_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("admin/user_list.html", data=data)


@admin_bp.route('/user_count')
def user_count():

    # 查询总人数
    total_count = 0
    try:
        # User.is_admin == False查询非管理员用户
        total_count = User.query.filter(User.is_admin == False).count()
    except Exception as e:
        current_app.logger.error(e)

    """
    time.struct_time(tm_year=2018, tm_mon=10, tm_mday=11, tm_hour=18, tm_min=29, tm_sec=46, tm_wday=3, tm_yday=284, tm_isdst=0)
    """
    # 查询月新增数（10-11 <--> 10-01）
    mon_count = 0
    try:
        # 获取当前系统的年月日
        now = time.localtime()
        print(now)
        """
        每一个月的月初时间（字符串）
        mon_begin: 2018-10-01
        mon_begin: 2018-11-01
        mon_begin: 2019-10-01
        """
        mon_begin = '%d-%02d-01' % (now.tm_year, now.tm_mon)
        # strptime： 时间字符串转换成时间格式 %Y-%m-%d: 2018-10-11
        mon_begin_date = datetime.strptime(mon_begin, '%Y-%m-%d')
        # User.create_time >= mon_begin_date表当前用户的创建时间大于每一个月第一天
        mon_count = User.query.filter(User.is_admin == False, User.create_time >= mon_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)

    # 查询日新增数
    day_count = 0
    try:
        """
        每一天的开始时间
        day_begin：2018-10-11:00:00   -- 2018-10-11:23:59
        day_begin：2018-10-12:00:00   -- 2018-10-12:23:59
        """
        day_begin = '%d-%02d-%02d' % (now.tm_year, now.tm_mon, now.tm_mday)
        day_begin_date = datetime.strptime(day_begin, '%Y-%m-%d')
        day_count = User.query.filter(User.is_admin == False, User.create_time > day_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)

    # 查询图表信息
    # 获取到当天00:00:00时间
    now_date = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
    # 定义空数组，保存数据
    active_date = []
    active_count = []

    # 依次添加数据，再反转
    for i in range(0, 31): # 0 1, 2, 3,....30
        """
        now_date: 2018-10-11:00:00 减去0天
        begin_date：2018-10-11:00:00  开始时间
        end_date: 2018-10-11:23:59    结束时间 = 开始时间 + 1天


        now_date: 2018-10-11:00:00 减去1天
        begin_date：2018-10-10:00:00  开始时间
        end_date: 2018-10-10:23:59    结束时间 = 开始时间 + 1天


        now_date: 2018-10-11:00:00 减去2天
        begin_date：2018-10-09:00:00  开始时间
        end_date: 2018-10-09:23:59    结束时间 = 开始时间 + 1天
        .
        .
        .
        now_date: 2018-10-11:00:00 减去30天
        begin_date：2018-09-11:00:00  开始时间
        end_date: 2018-09-1:23:59    结束时间 = 开始时间 + 1天


        """
        # 一天的开始时间
        begin_date = now_date - timedelta(days=i)
        # 一天的结束时间
        end_date = begin_date + timedelta(days=1)
        # end_date = now_date - timedelta(days=(i - 1))

        # 添加时间 10-11 .. 10-09...
        active_date.append(begin_date.strftime('%Y-%m-%d'))
        count = 0
        try:
            # 最后一次登录时间 > 大于今天的开始时间
            # 最后一次登录时间 < 小于今天的结束时间
            count = User.query.filter(User.is_admin == False, User.last_login >= begin_date,
                                      User.last_login < end_date).count()
        except Exception as e:
            current_app.logger.error(e)
        # 添加每一天的活跃人数
        active_count.append(count)

    # 数据反转
    active_date.reverse()
    active_count.reverse()

    data = {"total_count": total_count, "mon_count": mon_count, "day_count": day_count, "active_date": active_date,
            "active_count": active_count}

    return render_template('admin/user_count.html', data=data)

# /admin/index
@admin_bp.route('/index')
def admin_index():
    """后台管理首页"""
    return render_template("admin/index.html")


# /admin/login
@admin_bp.route('/login', methods=['POST', 'GET'])
def admin_login():
    """后台管理登录接口"""
    # get请求：展示登录页
    if request.method == "GET":
        # 判断管理员用户是否有登录，如果管理员有登录直接进入管理首页（提高用户体验）
        user_id = session.get("user_id")
        is_admin = session.get("is_admin", False)
        if user_id and is_admin:
            # 当前用户登录 & is_admin=True表示是管理员
            return redirect(url_for("admin.admin_index"))
        else:
            # 不是管理员用户
            return render_template("admin/login.html")
    # post请求：管理员登录业务逻辑处理
    """
    1.获取参数
        1.1 username: 账号， password:密码
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.0 根据username查询用户
        3.1 name.check_password进行密码校验
        3.2 管理员用户数据保存到session
    4.返回值
        4.1 跳转到管理首页
    """
    # 1.1 username: 账号， password:密码
    username = request.form.get("username")
    password = request.form.get("password")
    # 2.1 非空判断
    if not all([username, password]):
        return render_template("admin/login.html", errmsg="参数不足")

    # 3.0 根据username查询用户
    try:
        admin_user = User.query.filter(User.mobile == username, User.is_admin == True).first()
    except Exception as e:
        current_app.logger.error(e)
        return render_template("admin/login.html", errmsg="查询管理员用户对象异常")
    if not admin_user:
        return render_template("admin/login.html", errmsg="管理员用户不存在")

    # 3.1 user.check_password进行密码校验
    if not admin_user.check_passowrd(password):
        return render_template("admin/login.html", errmsg="密码填写错误")
    # 保存回数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return render_template("admin/login.html", errmsg="保存用户对象异常")

    # 3.2 管理员用户数据保存到session
    session["nick_name"] = username
    session["user_id"] = admin_user.id
    session["mobile"] = username
    session["is_admin"] = True

    #4.重定向到管理首页
    return redirect(url_for("admin.admin_index"))
