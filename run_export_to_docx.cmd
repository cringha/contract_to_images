@call .venv\Scripts\activate.bat
chcp 65001

REM 读取用户资料截图
REM 社保截图等，转为word文档

REM 输入的Excel数据，按照格式填写数据
SET INPUT_EXCEL=inputs\users-full-list.xlsx
SET INPUT_EXCEL=user-list.xlsx


REM 输入 社保PDF文件的根目录，每个城市的社保，按照约定的城市命名，例如：“北京.pdf”
SET INPUT_USER_SNAPSHOT_IMAGES_ROOT=.\output

REM 输入，社保截图文件的存放位置
SET INPUT_SS_IMAGE_ROOT=..\ss_images 

REM 输出，社保截图文件的存放位置
SET OUTPUT_IMAGE_ROOT=.\output

REM 输入 
SET INPUT_RESUME_TYPE=X

REM 转换 WORD 模板的
SET INPUT_DOCX_TEMPLATE=data/user_list_cert_resume_template.docx
SET INPUT_DOCX_TEMPLATE2=data/user_list_resume_template-v2.docx
SET INPUT_DOCX_TEMPLATE=data/user_certs_template.docx



 
REM 输出 DOCX 文件名
SET OUTPUT_DOCX_FILENAME=.\user_full_cert_result_list.docx


python export-user-image-to-docx.py -i  %INPUT_EXCEL%   --user-snapshot-root %INPUT_USER_SNAPSHOT_IMAGES_ROOT% -x %INPUT_SS_IMAGE_ROOT%  --user-resume-type %INPUT_RESUME_TYPE%  --docx-template-file  %INPUT_DOCX_TEMPLATE%  -o %OUTPUT_DOCX_FILENAME% --user-snapshot-types 身份证,毕业证,资质证书,合同,社保 --sheet-name-user 人员 --col-user-name 姓名 


@call .venv\Scripts\deactivate.bat