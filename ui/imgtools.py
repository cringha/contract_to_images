import base64

def save_image_as_py(image_path, py_file_path, variable_name):
    with open(image_path, 'rb') as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

    with open(py_file_path, 'w') as py_file:
        py_file.write(f"{variable_name} = '{encoded_image}'")

# 调用保存图片为Base64编码的函数
image_path = './stamp.png'
py_file_path = './stamp_pn.py'
variable_name = 'image_base64'

save_image_as_py(image_path, py_file_path, variable_name)