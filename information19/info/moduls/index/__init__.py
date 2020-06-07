from flask import Blueprint

#1.创建蓝图对象
index_bp = Blueprint("index", __name__)

#3.导入views文件中的视图函数
from .views import *