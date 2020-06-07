from flask import current_app, jsonify
from flask import g
from flask import request
from flask import session
from info import constants, db
from info.models import User, News, Comment, CommentLike
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import news_bp
from flask import render_template


# /news/followed_user
@news_bp.route('/followed_user', methods=['POST'])
@user_login_data
def followed_user():
    """关注、取消关注"""
    """
    1.获取参数
        1.1 author_id:作者id，action:关注、取消关注的行为
    2.校验参数
        2.1 非空判断
        2.2 action in ['follow', 'unfollow']
    3.逻辑处理
        3.0 author_id查询被关注的这个作者对象
        3.1 关注：将作者对象添加偶像列表
        3.2 取消关注：将作者从用户的偶像列表移除
    4.返回值
    """

    # 1.1 author_id:作者id，action:关注、取消关注的行为
    #1.1 用户对象 新闻id comment_id评论的id，action:(点赞、取消点赞)
    params_dict = request.json
    author_id = request.json.get('user_id')
    action = params_dict.get("action")
    user = g.user

    #2.1 非空判断
    if not all([author_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    #2.2 用户是否登录判断
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    #2.3 action in ['follow', 'unfollow']
    if action not in ['follow', 'unfollow']:
        return jsonify(errno=RET.PARAMERR, errmsg="action参数错误")

    # 3.0 author_id查询被关注的这个作者对象
    try:
        author = User.query.get(author_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询作者异常")
    if not author:
        return jsonify(errno=RET.NODATA, errmsg="作者不存在")


    """
    if user in author.followers:
    # 用户关注过该作者
    """
    # 3.1 关注：将作者对象添加偶像列表
    if action == "follow":
        if author in user.followed:
            return jsonify(errno=RET.DATAEXIST, errmsg="不能重复关注")
        else:
            # 将作者添加到当前用户的偶像列表，关注
            user.followed.append(author)
    # 3.2 取消关注：将作者从用户的偶像列表移除
    else:
        if author in user.followed:
            # 将作者从用户偶像列表移除，取关
            user.followed.remove(author)

    # 保存回数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="")

    return jsonify(errno=RET.OK, errmsg="OK")






# 127.0.0.1:5000/news/comment_like
@news_bp.route('/comment_like', methods=['POST'])
@user_login_data
def comment_like():
    """点赞、取消点赞接口"""
    """
    1.获取参数
        1.1 comment_id:评论id，user:当前登录用户，action: 点赞/取消点赞的行为
    2.校验参数
        2.1 非空判断
        2.2 action in ['add', 'remove']
    3.逻辑处理
        3.0 根据comment_id查询当前评论对象
        3.1 action等于add表示点赞：先查询commentlike模型对象是否存在，不存在，再创建commentlike该对象并赋值
        3.2 action等于remove表示取消点赞：先查询commentlike模型对象是否存在，存在，才能去删除commentlike对象
        3.3 将commentlike对象的修改保存回数据库
    4.返回值
    """
    #1.1 用户对象 新闻id comment_id评论的id，action:(点赞、取消点赞)
    params_dict = request.json
    comment_id = params_dict.get("comment_id")
    action = params_dict.get("action")
    # 获取当前登录用户对象
    user = g.user

    #2.1 非空判断
    if not all([comment_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    #2.2 用户是否登录判断
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    #2.3 action in ["add", "remove"]
    if action not in ["add", "remove"]:
        return jsonify(errno=RET.PARAMERR, errmsg="action参数错误")

    # 3.0 根据comment_id查询当前评论对象
    try:
        comment = Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询评论对象异常")
    if not comment:
        return jsonify(errno=RET.NODATA, errmsg="评论不存在")

    # 3.1 action等于add表示点赞：先查询commentlike模型对象是否存在，不存在，再创建commentlike该对象并赋值
    if action == "add":
        # 点赞
        try:
            commentlike = CommentLike.query.filter(CommentLike.comment_id == comment_id,
                                                   CommentLike.user_id == user.id).first()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询评论点赞对象异常")
        # 当前用户并未对当前评论点过赞
        if not commentlike:
            # 创建评论点赞模型对象
            commentlike_obj = CommentLike()
            commentlike_obj.user_id = user.id
            commentlike_obj.comment_id = comment_id

            # 添加到数据库
            db.session.add(commentlike_obj)
            # 评论对象上的总评论条数累加
            comment.like_count += 1
    # 3.2 action等于remove表示取消点赞：先查询commentlike模型对象是否存在，存在，才能去删除commentlike对象
    else:
        try:
            commentlike = CommentLike.query.filter(CommentLike.comment_id == comment_id,
                                                   CommentLike.user_id == user.id).first()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询评论点赞对象异常")

        # 当前用户已经对该评论点过赞，再次点击，表取消点赞
        if commentlike:
            # 将维护用户和评论之前的第三张表的对象删除，即表示取消点赞
            db.session.delete(commentlike)
            # 评论对象上的总评论条数减一
            comment.like_count -= 1

    # 3.3 将commentlike对象的修改保存回数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        # 回滚
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="点赞/取消点赞失败")
    # 4.返回值
    return jsonify(errno=RET.OK, errmsg="OK")


# 127.0.0.1:5000/news/news_comment
@news_bp.route('/news_comment', methods=['POST'])
@user_login_data
def news_comment():
    """发布新闻评论接口(主,子评论)"""
    """
    1.获取参数
        1.1 news_id:新闻id，comment_str:评论的内容， parent_id:子评论的父评论id（非必传）
    2.校验参数
        2.1 非空判断
    3.逻辑处理
        3.0 根据news_id查询当前新闻
        3.1 parent_id没有值：创建主评论模型对象，并赋值
        3.2 parent_id有值： 创建子评论模型对象，并赋值
        3.3 将评论模型对象保存到数据库
    4.返回值
    """

    #1.1 news_id:新闻id，comment_str:评论的内容， parent_id:子评论的父评论id（非必传）
    params_dict = request.json
    news_id = params_dict.get("news_id")
    comment_str = params_dict.get("comment")
    parent_id = params_dict.get("parent_id")
    # 获取用户登录信息

    user = g.user

    #2.1 非空判断
    if not all([news_id, comment_str]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    #2.2 用户是否登录判断
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 3.0 根据news_id查询当前新闻
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻对象异常")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻不存在")

    # 3.1 parent_id没有值：创建主评论模型对象，并赋值
    comment_obj = Comment()
    comment_obj.user_id = user.id
    comment_obj.news_id = news_id
    comment_obj.content = comment_str
    # 3.2 parent_id有值： 创建子评论模型对象，并赋值
    if parent_id:
        comment_obj.parent_id = parent_id

    # 3.3 将评论模型对象保存到数据库
    try:
        db.session.add(comment_obj)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="保存评论对象异常")
    # 4.返回值
    return jsonify(errno=RET.OK, errmsg="发布评论成功", data=comment_obj.to_dict())


# 127.0.0.1:5000/news/news_collect
@news_bp.route('/news_collect', methods=['POST'])
@user_login_data
def news_collect():
    """点击收藏/取消收藏的后端接口实现"""
    """
    1.获取参数
        1.1 news_id:当前新闻id，action:收藏or取消收藏的行为（'collect','cancel_collect'）
    2.校验参数
        2.1 非空判断
        2.2 action必须是在['collect','cancel_collect']列表内
    3.逻辑处理
        3.0 根据新闻id查询新闻对象
        3.1 收藏：将当前新闻添加到user.collection_news列中
        3.2 取消收藏：将当前新闻从user.collection_news列中移除
    4.返回值
    """
    # 1.1 news_id:当前新闻id，action:收藏or取消收藏的行为（'collect','cancel_collect'）
    param_dict = request.json
    news_id = param_dict.get('news_id')
    action = param_dict.get('action')
    # 获取当前登录的用户对象
    user = g.user

    # 2.1 非空判断
    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    # 判断用户是否有登录
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    # 2.2 action必须是在['collect','cancel_collect']列表内
    if action not in ["collect", "cancel_collect"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数的内容错误")

    # 3.0 根据新闻id查询新闻对象
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻数据异常")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻不存在")

    # 3.1 收藏：将当前新闻添加到user.collection_news列中
    if action == "collect":
        # 收藏
        user.collection_news.append(news)
    # 3.2 取消收藏：将当前新闻从user.collection_news列中移除
    else:
        # 只有新闻在用户新闻收藏列表中才去移除
        if news in user.collection_news:
            user.collection_news.remove(news)

    # 将用户收藏列表的修改操作保存回数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        # 回滚
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存新闻收藏列表数据异常")

    # 4.返回值
    return jsonify(errno=RET.OK, errmsg="OK!")


# 127.0.0.1:5000/news/127
@news_bp.route('/<int:news_id>')
@user_login_data
def news_detail(news_id):
    """展示新闻详情页面"""
    # ------------------获取用户登录信息------------------

    # 从装饰器的g对象中获取到当前登录的用户
    user = g.user

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

    # ------------------获取新闻详情数据------------------
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询新闻详情数据异常")
    # 新闻详情对象转换成字典
    news_dict = news.to_dict() if news else None

    # 用户浏览量累加
    news.clicks += 1

    # -----------------查询当前用户是否收藏当前新闻------------------
    # is_collected = True表示当前用户收藏过该新闻 反之
    is_collected = False
    # 标示当前登录用户是否对该新闻的作者有关注
    is_followed = False

    # 当前用户已经登录
    if user:
        if news in user.collection_news:
            # 当前新闻在用户的新闻收藏列表内，表示已经收藏
            is_collected = True

    # 判断当前登录用户是否对该新闻的作者有关注

    try:
        author = User.query.filter(User.id == news.user_id).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询作者对象异常")

    # 当前用户处于登录状态，当前新闻有作者
    if user and author:
        """
        当前用户：user
        作者：author

        用户在作者的粉丝列表中,表示当前用户关注过作者
        user in author.followers

        当前作者在用户的偶像列表中，表示当前用户关注过作者
        author in user.followed
        """
        if author in user.followed:
            is_followed = True


    #-----------------查询新闻评论列表数据------------------
    try:
        comments = Comment.query.filter(Comment.news_id == news_id)\
            .order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询评论列表数据异常")

    # -----------------查询当前用户在当前新闻的评论里边具体点赞了那几条评论------------
    commentlike_id_list = []
    if user:
        """
            comments: [评论对象1，评论对象2,....]
            """
        # 1. 查询出当前新闻的所有评论，取得所有评论的id —>  list[1,2,3,4,5,6]
        comment_id_list = [comment.id for comment in comments]

        # 2.再通过评论点赞模型(CommentLike)查询当前用户点赞了那几条评论  —>[模型1,模型2...]
        try:
            commentlike_model_list = CommentLike.query.filter(CommentLike.comment_id.in_(comment_id_list),
                                                              CommentLike.user_id == user.id).all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询评论点赞列表数据异常")

        # 3. 遍历上一步的评论点赞模型列表，获取所以点赞过的评论id（comment_like.comment_id）
        commentlike_id_list = [commentlike_model.comment_id for commentlike_model in commentlike_model_list]

    """
        当前用户点赞过赞的评论id列表：commentlike_id_list = [1, 3, 5]
        comment.id ==> if 1 in [1, 3, 5] ==> comment_dict["is_like"] = True
        comment.id ==> if 2 in [1, 3, 5] ==> comment_dict["is_like"] = False
    """
    # 对象列表转字典列表
    comment_dict_list = []
    for comment in comments if comments else []:
        # 评论对象转字典
        comment_dict = comment.to_dict()
        # 借助评论字典帮助携带一个is_like键值对信息，is_like标志位为True:点过赞，反之
        comment_dict["is_like"] = False

        # 当前评论的id在点过赞的的评论id列表中，将标志位修改成True
        if comment.id in commentlike_id_list:
            comment_dict["is_like"] = True

        comment_dict_list.append(comment_dict)


    # 组织响应数据字典
    data = {
        "user_info": user.to_dict() if user else None,
        "news_rank_list": news_rank_dict_list,
        "news": news_dict,
        "is_collected": is_collected,
        "is_followed": is_followed,
        "comments": comment_dict_list
    }

    return render_template("news/detail.html", data=data)
