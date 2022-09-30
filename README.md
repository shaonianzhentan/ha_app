# 家庭助理Android应用
Android手机推送通知与GPS持续定位

[![hacs_badge](https://img.shields.io/badge/Home-Assistant-%23049cdb)](https://www.home-assistant.io/)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
![visit](https://visitor-badge.laobi.icu/badge?page_id=shaonianzhentan.ha_app&left_text=visit)

## 安装

安装完成重启HA，刷新一下页面，在集成里搜索`家庭助理Android应用`

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=ha_app)


## 使用说明

> **Android手机权限配置**【下面是我的小米手机需要的权限】

- `通知管理`权限`全部都要`

- `省电策略`设置为`无限制`
- `定位`设置为`始终允许`
- `锁屏显示`设置为`始终允许`
- `后台弹出界面`设置为`始终允许`
- `常驻通知`设置为`始终允许`
- 开启`自启动`权限

> 请严格按流程执行
1. 下载并安装APP，安装成功后最好先别打开
2. 进入此APP的应用信息中，设置以上所需要的权限
3. 手动设置权限非常重要
4. 打开APP扫一扫插件生成的二维码进行关联
5. 关联成功后，自动上报GPS位置信息