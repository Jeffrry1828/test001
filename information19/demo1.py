# class Person(object):
#
#     def __init__(self):
#         self.name = "curry"
#
#     def __eq__(self, other):
#         return True
#
# if __name__ == '__main__':
#
#     p1 = Person()
#     p2 = Person()
#     print(p1 == p2)


# import functools
# # 获取当前登录用户信息的装饰器
# def user_login_data(view_func):
#     # 使用装饰器改变了被装饰的函数的一些特性，函数名称，可以使用functools解决这个问题
#     @functools.wraps(view_func)
#     def wrapper(*args, **kwargs):
#         return view_func(*args, **kwargs)
#     return wrapper
#
#
# @user_login_data
# def index():
#     """index"""
#     print("index")
#
#
# @user_login_data
# def user():
#     """user"""
#     print("user")
#
# if __name__ == '__main__':
#     print(index.__name__)
#     print(user.__name__)
import random
import datetime
from info import db
from info.models import User
from manage import app


def add_test_users():
    """添加测试用户"""
    users = []
    # 获取当前时间
    now = datetime.datetime.now()

    for num in range(0, 10000):
        try:
            user = User()
            user.nick_name = "%011d" % num
            user.mobile = "%011d" % num
            user.password_hash = "pbkdf2:sha256:50000$SgZPAbEj$a253b9220b7a916e03bf27119d401c48ff4a1c81d7e00644e0aaf6f3a8c55829"
            # 2678400，一个月的秒数
            # 当前时间 - 31天 = 9-11
            # 当前时间 - 随机的秒 = 10月11 - 9月11号中，用户随机登录了
            user.last_login = now - datetime.timedelta(seconds=random.randint(0, 2678400))
            users.append(user)
            print(user.mobile)
        except Exception as e:
            print(e)
    # 手动开启应用上下文
    with app.app_context():
        db.session.add_all(users)
        db.session.commit()
    print("OK")

if __name__ == '__main__':
    add_test_users()