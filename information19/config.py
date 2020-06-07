from redis import StrictRedis
import logging


class Config(object):
    """项目配置信息 (父类配置)"""
    DEBUG = True

    # mysql数据库配置信息
    # 数据库链接配置
    SQLALCHEMY_DATABASE_URI = "mysql://root:cq@127.0.0.1:3306/information19"
    # 关闭数据库修改跟踪
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    #能替换 db.session.commit()
    # 当数据库会话对象结束的时候自动帮助提交更新数据到数据库
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True

    #redis数据库配置信息
    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379
    REDIS_NUM = 9

    # 加密字符串
    SECRET_KEY = "ASLKDASJDKSAJHDSAKJKJHKJ"
    #通过flask-session拓展，将flask中的sesssion（内存）调整到redis的配置信息
    # 存储数据库的类型：redis
    SESSION_TYPE = "redis"
    # 将redis实例对象进行传入
    SESSION_REDIS = StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_NUM)
    # 对session数据进行加密处理
    SESSION_USE_SIGNER = True
    # 关闭永久存储
    SESSION_PERMANENT = False
    # 过期时长(24小时)
    PERMANENT_SESSION_LIFETIME = 86400


class DevelopmentConfig(Config):
    """开发环境的项目配置信息"""
    DEBUG = True
    # 开发模式的日志级别：DEBUG
    LOG_LEVEL = logging.DEBUG


class ProductionConfig(Config):
    """生产环境的项目配置"""
    DEBUG = False
    # 线上模式的日志级别：WANRING
    LOG_LEVEL = logging.WARNING


# 给外界暴露一个使用配置类的接口
# 使用方法： config_dict['development'] --> DevelopmentConfig 开发环境的配置类
config_dict = {
    "development": DevelopmentConfig,
    "production": ProductionConfig
}