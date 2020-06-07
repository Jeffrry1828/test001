import qiniu
access_key = 'W0oGRaBkAhrcppAbz6Nc8-q5EcXfL5vLRashY4SI'
secret_key = 'tsYCBckepW4CqW0uHb9RdfDMXRDOTEpYecJAMItL'
bucket_name = 'python-ihome'

"""
使用方法： 域名+图片名称

oz6itywx9.bkt.clouddn.com/FgiH5A9KFDvjlaKQs7FK8wZIcIQh

"""


def pic_storage(data):
    """借助七牛云上传图片"""
    # 身份鉴定
    q = qiniu.Auth(access_key, secret_key)
    # 上传的图片名称， 如果不指明，七牛云会给你分配一个唯一的图片名称
    # key = 'hello'
    if not data:
        return None
    token = q.upload_token(bucket_name)
    try:
        # 调用七牛云sdk上传二进制图片数据
        ret, info = qiniu.put_data(token, None, data)
    except Exception as e:
        # 自定义工具方法的异常一定要抛出给调用者，不能私自解决
        raise e

    print(ret)
    print("--------")
    print(info)

    if info.status_code != 200:
        # 上传图片到七牛云失败
        raise Exception("上传图片到七牛云失败")

    # 上传图片成功 返回图片名称
    return ret["key"]


if __name__ == '__main__':
    file = input("请输入图片的地址：")
    with open(file, "rb") as f:
        data = f.read()
        pic_storage(data)