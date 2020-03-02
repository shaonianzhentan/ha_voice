
import os
import logging
import uuid
import base64
import json
import string
from aiohttp import web
import voluptuous as vol
from homeassistant.components.weblink import Link
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers import config_validation as cv, intent

from aip import AipSpeech

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'ha_voice'
VERSION = '1.2'
URL = '/ha-voice-api-' + str(uuid.uuid4())
ROOT_PATH = '/' + DOMAIN + '-local/' + VERSION

CONF_APP_ID = 'app_id'
CONF_API_KEY = 'api_key'
CONF_SECRET_KEY = 'secret_key'

def setup(hass, config):
    """ 你的 APPID AK SK """    
    cfg  = config[DOMAIN]
    APP_ID = cfg.get(CONF_APP_ID)
    API_KEY = cfg.get(CONF_API_KEY)
    SECRET_KEY = cfg.get(CONF_SECRET_KEY)
    
    hass.data[DOMAIN] = AipSpeech(APP_ID, API_KEY, SECRET_KEY)    
    
    # 注册静态目录
    local = hass.config.path("custom_components/" + DOMAIN + "/local")
    if os.path.isdir(local):
        hass.http.register_static_path(ROOT_PATH, local, False)    
    Link(hass, "语音小助手", URL, "mdi:microphone")
    
    hass.http.register_view(HassGateView)
    
    async def handle_text(call):
        """这里处理命令."""
        text = call.data.get('text', '')
        _res = await conversation_process(hass, text)
        _LOGGER.info(_res)

    hass.services.register(DOMAIN, 'process', handle_text)
    
    # 加载自定义卡片
    hass.components.frontend.add_extra_js_url(hass, ROOT_PATH + '/ha-voice-panel.js')
    # Return boolean to indicate that initialization was successfully.
        # 显示插件信息
    _LOGGER.info('''
-------------------------------------------------------------------

    语音小助手【作者QQ：635147515】
    
    版本：''' + VERSION + '''    
    
    介绍：在HA里使用的语音小助手
    
    项目地址：https://github.com/shaonianzhentan/ha_voice
    
-------------------------------------------------------------------''')
    return True

def text_start(findText, text):
    return text.find(findText,0,len(findText)) >= 0

# 处理文字内容
async def conversation_process(hass, text):
    if text == '':
        return {'code':1, 'msg': '空文本'}
    # 去掉前后标点符号
    text = text.strip('。，、＇：∶；?‘’“”〝〞ˆˇ﹕︰﹔﹖﹑·¨….¸;！´？！～—ˉ｜‖＂〃｀@﹫¡¿﹏﹋﹌︴々﹟#﹩$﹠&﹪%*﹡﹢﹦﹤‐￣¯―﹨ˆ˜﹍﹎+=<­­＿_-\ˇ~﹉﹊（）〈〉‹›﹛﹜『』〖〗［］《》〔〕{}「」【】︵︷︿︹︽_﹁﹃︻︶︸﹀︺︾ˉ﹂﹄︼')    
    _LOGGER.info(text)
    # 发送事件，共享给其他组件
    hass.bus.fire('ha_voice_text_event', {
        'text': text
    })
    try:
        # 执行自定义脚本
        states = hass.states.async_all()
        for state in states:
            entity_id = state.entity_id
            if entity_id.find('script.') == 0:
                attributes = state.attributes
                friendly_name = attributes.get('friendly_name')
                cmd = friendly_name.split('=')
                if cmd.count(text) > 0:
                    arr = entity_id.split('.')
                    _LOGGER.info('执行脚本：' + entity_id)
                    await hass.services.async_call(arr[0], arr[1])
                    return {'code': 0, 'msg': '正在执行自定义脚本', 'text': text}
        
        # 开关控制
        intent_type = ''
        if text_start('打开',text) or text_start('开启',text) or text_start('启动',text):
            intent_type = 'HassTurnOn'
            if '打开' in text:
                _name = text.split('打开')[1]
            elif '开启' in text:
                _name = text.split('开启')[1]
            elif '启动' in text:
                _name = text.split('启动')[1]
        elif text_start('关闭',text) or text_start('关掉',text) or text_start('关上',text):
            intent_type = 'HassTurnOff'
            if '关闭' in text:
                _name = text.split('关闭')[1]
            elif '关掉' in text:
                _name = text.split('关掉')[1]
            elif '关上' in text:
                _name = text.split('关上')[1]            
        elif text_start('切换', text):
            intent_type = 'HassToggle'
            _name = text.split('切换')[1]
        # 默认的开关操作
        if intent_type != '':
            # 操作所有灯和开关
            if _name == '所有灯' or _name == '所有的灯' or _name == '全部灯' or _name == '全部的灯':
                _name = 'all lights'
            elif _name == '所有开关' or _name == '所有的开关' or _name == '全部开关' or _name == '全部的开关':
                _name = 'all switchs'
            intent_response = await intent.async_handle(hass, DOMAIN, intent_type, {'name': {'value': _name}})
            return {'code':0, 'data': intent_response.speech, 'type': 'intent', 'msg': '正在' + text, 'text': text}
        else:
            # 调用内置的语音服务
            if hass.services.has_service('conversation','process'):
                _log_info("调用内置的语音服务")
                await hass.services.async_call('conversation', 'process', {'text': text})
                return {'code': 0, 'msg': '调用内置的语音服务', 'text': text}
            else:
                return {'code': 0, 'msg': '系统没有开启内置的语音服务', 'text': text}
    except Exception as e:
        print(e)
        return {'code':1, 'msg': '【出现异常】' + str(e), 'text': text}

class HassGateView(HomeAssistantView):

    url = URL
    name = DOMAIN
    requires_auth = False
    cors_allowed = True
    
    async def get(self, request):
        # 这里进行重定向
        hass = request.app["hass"]
        return web.HTTPFound(location=(ROOT_PATH + '/i.htm?base_url=' + hass.config.api.base_url.strip('/')
        +'&api=' + URL))
    
    async def post(self, request):
        hass = request.app["hass"]
        try:
            reader = await request.multipart()
            file = await reader.next()
            # 生成文件
            filename = os.path.dirname(__file__) + '/' + str(uuid.uuid4())+ '.wav'
            size = 0
            with open(filename, 'wb') as f:
                while True:
                    chunk = await file.read_chunk()  # 默认是8192个字节。
                    if not chunk:
                        break
                    size += len(chunk)
                    f.write(chunk)
            # 读取文件
            res = hass.data[DOMAIN].asr(get_file_content(filename), 'wav', 8000, {
                'dev_pid': 1537,
            })
            # 识别结束，删除文件
            os.remove(filename)
            
            if res['err_no'] != 0:
                return self.json({'code':1, 'msg': '百度语音识别错误'})
            _text = res['result'][0]
            _res = await conversation_process(hass, _text)
            return self.json(_res)
            
        except Exception as e:
            print(e)
            # 语音文字处理
            try:
                response = await request.json()
                _text = response['text']
                res = await conversation_process(hass, _text)
                return self.json(res)
            except Exception as e:
                print(e)
                return self.json({'code':1, 'msg': '出现异常'})

def get_file_content(filePath):
    with open(filePath, 'rb') as fp:
        return fp.read()