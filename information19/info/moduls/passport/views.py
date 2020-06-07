from flask import abort, make_response, jsonify, session
from flask import json
from flask import request, current_app
from . import passport_bp
from info.utils.captcha.captcha import captcha
from info import redis_store, constants, db
from info.utils.response_code import RET
import re, random
from info.models import User
from info.lib.yuntongxun.sms import CCP
from datetime import datetime




@passport_bp.route('/login_out', methods=['POST'])
def login_out():
    """退出登录后端接口"""
    # 将用户登录信息清除
    session.pop("user_id", None)
    session.pop("mobile", None)
    session.pop("nick_name", None)
    session.pop("is_admin", None)
    return jsonify(errno=RET.OK, errmsg="退出登录成功")


@passport_bp.route('/login', methods=['POST'])
def login():
    """用户登录后端接口 POST"""
    """
        1.获取参数
            1.1 mobile:手机号码  password:未加密的密码
        2.参数校验
            2.1 非空判断
            2.2 手机号码格式判断
        3.逻辑处理
            3.1 根据mobile查询用户是否存在
            3.2 不存在：提示账号不存在
            3.3 存在：判断密码是否填写正确
            3.4 保存用户登录信息（更新用户最后一次登录时间）
        4.返回值
            4.1 登录成功
        """

    # 1.1 mobile:手机号码， password:未加密的密码
    param_dict = request.json
    mobile = param_dict.get("mobile", "")
    password = param_dict.get("password", "")
    # 2.1 非空判断
    if not all([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    # 2.2 手机号码格式判断
    if not re.match('1[35789][0-9]{9}', mobile):
        current_app.logger.error("手机格式错误")
        return jsonify(errno=RET.PARAMERR, errmsg="手机格式错误")

    #3.1 根据mobile查询用户是否存在
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户异常")
    #3.2 不存在：提示账号不存在
    if not user:
        return jsonify(errno=RET.NODATA, errmsg="用户不存在")

    #3.3 存在：判断密码是否填写正确
    # 参数1：未加密的密码
    if not user.check_passowrd(password):
        # 密码错误：
        return jsonify(errno=RET.DATAERR, errmsg="密码填写错误")

    #3.4 保存用户登录信息（更新用户最后一次登录时间）
    session["user_id"] = user.id
    session["nick_name"] = user.mobile
    session["mobile"] = user.mobile

    # 更新最后一次登录时间
    user.last_login = datetime.now()

    # 修改了user对象的数据，需要使用commit将数据保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存用户数据异常")

    #4.登录成功
    return jsonify(errno=RET.OK, errmsg="登录成功")


# 127.0.0.1:5000/passport/register
@passport_bp.route('/register', methods=['post'])
def register():
    """注册的后端接口"""
    """
    1.获取参数
        1.1 mobile:手机号码， smscode:短信验证码， password:未加密的密码
    2.参数校验
        2.1 非空判断
        2.2 手机号码格式判断
    3.逻辑处理
        3.1 根据"SMS_CODE_mobile"作为key去redis中获取真实的短信验证码值
        3.2 对比用户填写的短信验证码和真实的短信验证值
        3.3 不相等： 提示短信验证码填写错误
        3.4 相等： 根据User类创建用户对象，并给其属性赋值
        3.5 存储到数据库
        3.6 一般需求：注册成功，一般自动登录，记录用户登录信息
    4.返回值
        4.1 注册成功
    """
    # 1.1 mobile:手机号码， smscode:短信验证码， password:未加密的密码
    param_dict = request.json
    mobile = param_dict.get("mobile", "")
    smscode = param_dict.get("smscode", "")
    password = param_dict.get("password", "")
    #2.1 非空判断
    if not all([mobile, smscode, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    #2.2 手机号码格式判断
    if not re.match('1[35789][0-9]{9}', mobile):
        current_app.logger.error("手机格式错误")
        return jsonify(errno=RET.PARAMERR, errmsg="手机格式错误")

    #3.1 根据"SMS_CODE_mobile"作为key去redis中获取真实的短信验证码值
    try:
        real_smscode = redis_store.get("SMS_CODE_%s" %mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询真实短信验证码异常")

    # 从redis数据库删除短信验证码
    if real_smscode:
        redis_store.delete("SMS_CODE_%s" %mobile)
    else:
        return jsonify(errno=RET.NODATA, errmsg="短信验证码过期")

    #3.2 对比用户填写的短信验证码和真实的短信验证值
    if smscode != real_smscode:
        # 3.3 不相等： 提示短信验证码填写错误
        return jsonify(errno=RET.DATAERR, errmsg="短信验证码填写错误")

    #3.4 相等： 根据User类创建用户对象，并给其属性赋值
    user = User()
    user.mobile = mobile
    user.nick_name = mobile
    # 当前时间作为最后一次登录时间
    user.last_login = datetime.now()
    #TODO: 密码加密处理
    # 一般的套路
    # user.set_password_hash(password)
    # 将属性赋值的底层实现（复习）
    user.password = password

    #3.5 存储到数据库
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        # 数据库回滚
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="添加用户数据异常")

    #3.6 一般需求：注册成功，一般自动登录，记录用户登录信息
    session["user_id"] = user.id
    session["nick_name"] = user.mobile
    session["mobile"] = user.mobile

    #4.返回注册成功
    return jsonify(errno=RET.OK, errmsg="注册成功")




# 127.0.0.1:5000/passport/image_code?code_id=uuid编码
@passport_bp.route('/image_code')
def get_image_code():
    """获取验证码图片的后端接口 （GET）"""

    """
    1.获取参数
        1.1 获取code_id，全球唯一的编码（uuid）
    2.校验参数
        2.1 非空判断，判断code_id是否有值
    3.逻辑处理
        3.1 生成验证码图片 & 生成验证码图片的真实值（文字）
        3.2 以code_id作为key 将生成验证码图片的真实值（文字）存储到redis数据库
    4.返回值
        4.1 返回验证码图片
    """

    #1.1 获取code_id，全球唯一的编码（uuid）
    code_id = request.args.get('code_id', '')

    #2.1 非空判断，判断code_id是否有值
    if not code_id:
        current_app.logger.error("参数不足")
        # 参数不存在404错误
        abort(404)

    #3.1 生成验证码图片 & 生成验证码图片的真实值（文字）
    image_name, real_image_code, image_data = captcha.generate_captcha()
    #3.2 以code_id作为key 将生成验证码图片的真实值（文字）存储到redis数据库
    try:
        redis_store.setex("imageCodeId_%s" % code_id, constants.IMAGE_CODE_REDIS_EXPIRES, real_image_code)
    except Exception as e:
        current_app.logger.error(e)
        abort(500)

    #4.1返回验证码图片(二进制图片数据，不能兼容所有浏览器)
    # 创建响应对象
    response = make_response(image_data)
    # 设置响应数据的内容类型 Content-Type："image/JPEG"
    response.headers["Content-Type"] = "image/JPEG"
    return response


#127.0.0.1:5000/passport/sms_code
@passport_bp.route('/sms_code', methods=['POST'])
def send_sms_code():
    """点击发送短信验证码后端接口"""
    """
    1.获取参数
        1.1 用户账号手机号码mobile, 用户填写的图片验证码值：image_code， 编号UUID:image_code_id

    2.校验参数
        2.1 非空判断 mobile,image_code，image_code_id 是否有空
        2.2 手机号码格式的正则判断

    3.逻辑处理
        3.1 根据编号去redis数据库获取图片验证码的真实值（正确值）
             3.1.1 真实值有值: 将这个值从redis中删除（防止他人多次拿着同一个验证码值来验证）
             3.1.2 真实值没有值： 图片验证码真实值过期了

        3.2 拿用户填写的图片验证码值和Redis中获取的真实值进行比较

        3.3 不相等 告诉前端图片验证码填写错误

        TODO: 判断用户是否注册过,如果注册过，就不在发送短信验证码引导到登录页（提高用户体验）

        3.4 相等， 生成6位随机短信验证码，发送短信验证码

        3.4 将 生成6位随机短信验证码存储到redis数据库

    4.返回值
        4.1 发送短信验证码成功
    """
    # 上传数据是json类型
    #1.1 用户账号手机号码mobile, 用户填写的图片验证码值：image_code， 编号UUID:image_code_id
    #json.loads(request.data)
    # 可以接受前端上传的json格式数据，json字符串转换成python对象
    param_dict = request.json
    # 手机号码
    mobile = param_dict.get("mobile", "")
    # 用户填写的图片验证码值
    image_code = param_dict.get("image_code", "")
    # uuid编号
    image_code_id = param_dict.get("image_code_id", "")
    # 2.1 非空判断 mobile,image_code，image_code_id 是否有空
    if not all([mobile, image_code, image_code_id]):
        # 记录日志
        current_app.logger.error("参数不足")
        # 给调用者返回json格式的错误信息
        return jsonify({"errno":RET.PARAMERR, "errmsg": '参数不足'})

    # 2.2 手机号码格式的正则判断
    if not re.match('1[35789][0-9]{9}', mobile):
        current_app.logger.error("手机格式错误")
        return jsonify(errno=RET.PARAMERR, errmsg="手机格式错误")

    #3.1 根据编号去redis数据库获取图片验证码的真实值（正确值）
    try:
        real_image_code = redis_store.get("imageCodeId_%s" % image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="从redis中获取图片真实值异常")
    #3.1.1 真实值有值: 将这个值从redis中删除（防止他人多次拿着同一个验证码值来验证）
    if real_image_code:
        redis_store.delete("imageCodeId_%s" % image_code_id)
    # 3.1.2 真实值没有值： 图片验证码真实值过期了
    else:
        return jsonify(errno=RET.NODATA, errmsg="图片验证码过期")

    #3.2 拿用户填写的图片验证码值和Redis中获取的真实值进行比较
    # 细节1：全部按照小写格式进行比较（忽略大小写）
    # 细节2：redis对象创建的时候设置decode_responses=True
    if real_image_code.lower() != image_code.lower():
        #3.3 不相等 告诉前端图片验证码填写错误
        return jsonify(errno=RET.DATAERR, errmsg="填写图片验证码错误")

    #TODO: 判断用户是否注册过,如果注册过，就不在发送短信验证码引导到登录页（提高用户体验）
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="从mysql中查询用户异常")
    # 注册过就不在发送短信验证码引导到登录页
    if user:
        return jsonify(errno=RET.DATAEXIST, errmsg="手机号码已经注册")

    #3.4 相等， 生成6位随机短信验证码，发送短信验证码
    # 生成6位随机短信验证码
    sms_code = random.randint(0, 999999)
    # 补足6位前面补0
    sms_code = "%06d" % sms_code

    current_app.logger.debug(sms_code)

    try:
        result = CCP().send_template_sms(mobile, {sms_code, constants.SMS_CODE_REDIS_EXPIRES/60}, 1)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="云通讯发送短信失败")

    if result != 0:
        return jsonify(errno=RET.THIRDERR, errmsg="云通讯发送短信失败")

    #3.4 将 生成6位随机短信验证码存储到redis数据库
    try:
        # SMS_CODE_18520340804 每个用户这个key都不一样
        redis_store.setex("SMS_CODE_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="存储短信验证码异常")

    #4.返回值
    return jsonify(errno=RET.OK, errmsg="发送短信验证码成功，注意查收")






