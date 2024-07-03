# 家庭助理Android应用
Android手机推送通知与GPS持续定位

[![hacs_badge](https://img.shields.io/badge/Home-Assistant-%23049cdb)](https://www.home-assistant.io/)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
![visit](https://visitor-badge.laobi.icu/badge?page_id=shaonianzhentan.ha_app&left_text=visit)

[![badge](https://img.shields.io/badge/Conversation-语音小助手-049cdb?logo=homeassistant&style=for-the-badge)](https://github.com/shaonianzhentan/conversation)
[![badge](https://img.shields.io/badge/Windows-家庭助理-blue?logo=windows&style=for-the-badge)](https://www.microsoft.com/zh-cn/store/productId/9n2jp5z9rxx2)
[![badge](https://img.shields.io/badge/wechat-微信控制-6cae6a?logo=wechat&style=for-the-badge)](https://github.com/shaonianzhentan/ha_wechat)
[![badge](https://img.shields.io/badge/android-家庭助理-purple?logo=android&style=for-the-badge)](https://github.com/shaonianzhentan/ha_app)

## 安装

安装完成重启HA，刷新一下页面，在集成里搜索`家庭助理Android应用`

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=ha_app)

## 蓝图

应用通知消息

[![导入蓝图](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fshaonianzhentan%2Fha_app%2Fblob%2Fmain%2Fblueprints%2Fha_app_notify.yaml)

短信通知消息

[![导入蓝图](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fshaonianzhentan%2Fha_app%2Fblob%2Fmain%2Fblueprints%2Fha_app_sms.yaml)

按钮事件

[![导入蓝图](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fshaonianzhentan%2Fha_app%2Fblob%2Fmain%2Fblueprints%2Fha_app_button.yaml)

NFC标签

[![导入蓝图](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fshaonianzhentan%2Fha_app%2Fblob%2Fmain%2Fblueprints%2Fha_app_nfc.yaml)

## [使用说明](https://mp.weixin.qq.com/s/t5xaet2Kj5zbgKrasNTAyQ)


### 通知服务

按钮通知
```yaml
service: notify.mobile_app_android_设备名
data:
  message: 内容
  title: 标题
  data:
    actions:
      - action: action_1
        title: 普通按钮
      - action: action_2
        title: 链接按钮
        uri: https://github.com/shaonianzhentan/ha_app
```
图片通知
```yaml
service: notify.mobile_app_android_设备名
data:
  message: 内容
  title: 标题
  data:
    image: https://www.home-assistant.io/images/favicon-192x192.png
```

### 控制服务（测试中）

**媒体控制**
```yaml
service: notify.mobile_app_android_设备名
data:
  message: ha_app_control
  data:
    type: media_play_pause
```
- media_next_track: 下一曲
- media_previous_track: 上一曲
- media_play_pause: 播放/暂停
- media_pause: 暂停
- media_play: 播放


**TTS语音播放**
```yaml
service: notify.mobile_app_android_设备名
data:
  message: ha_app_control
  data:
    type: tts
    data: 播报的文本内容
```

> **Android手机权限配置**【下面是我的小米手机需要的权限】

- `省电策略`设置为`无限制`
- `定位`设置为`始终允许`
- `锁屏显示`设置为`始终允许`
- `后台弹出界面`设置为`始终允许`
- `常驻通知`设置为`始终允许`
- 开启`自启动`权限
- `通知管理`权限`全部都要`

**核心功能**

- [x] 文本控制
- [x] 位置上报
    - 省电策略`无限制`
    - 定位`始终允许`
    - 自启动`打开`
- [x] 消息推送
    - 应用需要开启`常驻通知` `锁屏显示`
    - `通知管理`所有权限
- [x] 通知转发
    - 系统需授权`通知使用权`
- [x] 短信通知
    - 应用需开启`通知类短信`权限
- [x] 来电通知
- [x] 家庭传音
- [x] NFC扫描
- [x] 桌面小组件
    - 应用需开启`悬浮窗`权限
- [x] 小米手环控制
    - 应用需开启`蓝牙`相关权限

**运行轨迹**

使用百度地图鹰眼轨迹服务，24小时监控设备位置

https://lbsyun.baidu.com/trace/admin/service

**应用下载**

> 点击加入QQ群下载更多APK文件

[![badge](https://img.shields.io/badge/QQ群-64185969-76beff?logo=tencentqq&style=for-the-badge)](https://qm.qq.com/cgi-bin/qm/qr?k=m4uDQuuAJCnCll6PuQZUnnJ0zEy7zuk2&jump_from=webapi&authKey=WTxRChNkBUDdVsTcYHeO8yb98Uu8WGJC3hxw53Il4PB7RgBTQ6StHa43MwZJtN5w)


> 关注公众号了解更多相关信息

<img src="https://ha.jiluxinqing.com/img/wechat-channel.png" height="160" alt="HomeAssistant家庭助理" title="HomeAssistant家庭助理"> 

## 答疑解惑

以下情况不会上报位置信息

- 连接WiFi时
- 低功耗节能模式
- 设备未登录
- 没有定位权限
- 5分钟之内偏移超过0.3千米
- 前后两次经纬度相同