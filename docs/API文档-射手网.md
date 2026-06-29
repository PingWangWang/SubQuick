---
created: 2026-06-29T15:21:25 (UTC +08:00)
tags: []
source: https://secure.assrt.net/api/doc
author: 
---

# API文档 - 射手网

> ## Excerpt
> 本文档给出ASSRT API的使用方法。

---
本文档给出ASSRT API的使用方法。

我们承诺为个人用户提供免费的API服务，商业合作请洽![img](api%E6%96%87%E6%A1%A3-%E5%B0%84%E6%89%8B%E7%BD%91/email.jpg)。

使用ASSRT API完全免费，但请在合适的位置添加来源说明及本站链接。例如：

> 字幕服务由[assrt.net](https://assrt.net/)提供

## 概述

本API使用HTTP协议进行通信，回复数据采用JSON封装。

API服务器的域名为`api.assrt.net`。一个典型的API终结点(endpoint)形如`/v1/foo/bar?{args}`。可以使用HTTP或者HTTPS方式访问API服务，对应的url为`http://api.assrt.net`和`https://api.assrt.net`

由于网络原因，也可以使用以下替代域名访问：`api.makedie.me`

不限使用GET或者POST，例如以下的请求是等价的：

```
GET /v1/foo/bar?arg1=a&arg2=b HTTP/1.1
```

```
POST /v1/foo/bar HTTP/1.1
Content-Type: application/x-www-form-urlencoded

arg1=a&arg2=b
```

但请注意，POST请求中的url参数会被忽略。如：

```
POST /v1/foo/bar&arg1=c HTTP/1.1
Content-Type: application/x-www-form-urlencoded

arg1=a&arg2=b
```

以上请求中的arg1会被认为是_a_而不是_c_

### 使用Token

Token为32位随机数字和大小写字母组合。用户[注册](https://secure.assrt.net/user/register.xml)后即可在[用户面板](https://secure.assrt.net/usercp.php)中查看自己的API密钥(Token)，并可以重置Token。

所有API请求如无特别说明均需带上Token。使用的方法有两种：

方法一：

```
GET /v1/foo/bar?token=TOKEN HTTP/1.1
Host: api.assrt.net
User-Agent: curl/7.43.0
Accept: */*
```

方法二：

```
GET /v1/sub/detail HTTP/1.1
Host: api.assrt.net
User-Agent: curl/7.43.0
Accept: */*
Authorization: Bearer TOKEN
```

请将请求中的TOKEN替换成你自己的密钥。

**在下文中如无特别说明，所有API请求均需带上Token。**

### API配额

为了公平使用的原则，API初始配额为 **20次每分钟**。注意每个token以及每个IP共享同一个配额，如A用户和B用户使用不同的token，但是IP相同，则ta们一共可以使用20次每分钟的配额；同理不同IP的用户使用同一token也只能合计使用20次每分钟的API请求。

如果你需要更高的请求速率，请将您的应用场景以及所需的配额发送邮件至[![img](api%E6%96%87%E6%A1%A3-%E5%B0%84%E6%89%8B%E7%BD%91/email.1.jpg)](https://secure.assrt.net/images/email.jpg)，我们将在审核后为你开通。

对于非商业应用场景，我们会优先审核发布更多高质量字幕的个人用户。

另外你可以在[用户面板](https://secure.assrt.net/usercp.php)或[使用api](https://secure.assrt.net/api/doc#userquota)查询当前可用配额。

## Endpoints

以下列举了API服务的所有终结点

### sub

字幕相关服务

#### sub/search

搜索字幕

|参数|是否可选|含义|
|---|---|---|
|q|搜索字符串，至少长度为3|
|pos|可选|分页时的起始位置|
|cnt|可选|返回的结果数量，最多一次返回15个结果，默认为15|
|is\_file|可选|值为1时指定搜索字符串为（不包含扩展名的）视频文件名|
|no\_muxer|可选|值为1时指定忽略搜索字符串中的压制组和视频参数信息|
|filelist|可选|值为1时同时返回压缩包内的文件列表，但不返回文件的下载链接|

典型请求举例:

```shell
curl "https://api.assrt.net/v1/sub/search?token=TOKEN&q=big&cnt=1&pos=0"
```

典型响应举例:

```json
{
    "status": 0,
    "sub": {
        "subs": [{
            "native_name": "老大哥（美版） 第17季第26集\/Big Brother US S17E26",
            "videoname": "big.brother.us.s17e26.720p.hdtv.x264-bajskorv",
            "revision": 0,
            "subtype": "VobSub",
            "upload_time": "2015-08-21 22:11:00",
            "vote_score": 0,
            "id": 594897,
            "release_site": "人人影视YYeTs",
            "lang": {
                "langlist": {
                    "langdou": true,
                    "langkor": true
                },
                "desc": "韩  双语"
            }
        },
        {
            "native_name": "老大哥（美版） 第17季第24集\/Big Brother US S14E24",
            "videoname": "big.brother.us.s17e24.720p.hdtv.x264-bajskorv",
            "revision": 0,
            "subtype": "Subrip(srt)",
            "upload_time": "2015-08-18 10:02:00",
            "vote_score": 0,
            "id": 594867,
            "release_site": "人人影视YYeTs",
            "lang": {
                "langlist": {
                    "langdou": true,
                    "langkor": true
                },
                "desc": "韩 双语"
            }
        }],
        "action": "search",
        "keyword": "big",
        "result": "succeed"
    }
}
```

如果可以确定搜索字符串为视频文件名，则可以使用_is\_file=1_，除了压制组和视频参数以外的内容将被忽略。或者使用_no\_muxer=1_，这样搜索字符串中的压制组也会被忽略；使用_no\_muxer=1_将默认_is\_file=1_。建议仅在结果太多时使用_is\_file=1_。

对于`q=Gone.with.the.Wind.1939.1080p.BluRay.x264-WiKi`

|额外参数|实际搜索字符串|
|---|---|
|Gone.with.the.Wind.1939.1080p.BluRay.x264-WiKi|
|&is\_file=1|Gone with the Wind 1939 -WiKi|
|&no\_muxer=1|Gone with the Wind 1939|

关于返回的字幕信息的结构，见[subs](https://secure.assrt.net/api/doc#subs)

#### sub/detail

获取字幕详细信息

|参数|是否可选|含义|
|---|---|---|
|id|字幕ID，为6位整数|

典型请求举例:

```shell
curl "https://api.assrt.net/v1/sub/detail?token=TOKEN&id=602333"
```

典型响应举例:

```json
{
    "status": 0,
    "sub": {
        "result": "succeed",
        "action": "detail",
        "subs": [{
            "filename": "洛东江大决战.Does the Nak-Dong River Flow.1976.DVD.X264.AAC.HALFCDi.rar",
            "native_name": "洛东江大决战\/Commando on the Nakdong River\/Does the Nak-Dong River Flow\/洛東江大決戦",
            "id": 602333,
            "down_count": 14,
            "revision": 0,
            "upload_time": "2015-07-03 11:28:53",
            "url": "http:\/\/file0.assrt.net\/download\/602333\/洛东江大决战.Does the Nak-Dong River Flow.1976.DVD.X264.AAC.HALFCDi.rar?_=1450914208&-=f281c84ea1a1d01280bd105e5f4a0baf&api=1",
            "size": 20180,
            "producer": {
                "producer": "chenchun8219",
                "verifier": "谢里登大道",
                "source": "校订翻译",
                "uploader": "谢里登大道"
            },
            "filelist": [{
                "url": "http:\/\/file0.assrt.net\/onthefly\/602333\/-\/1\/洛东江大决战.Does the Nak-Dong River Flow.1976.DVD.X264.AAC.HALFCDi.srt?_=1450914208&-=af6b1e5c372713868f36e3c4f3864458&api=1",
                "f": "洛东江大决战.Does the Nak-Dong River Flow.1976.DVD.X264.AAC.HALFCDi.srt",
                "s": "52KB"
            }],
            "subtype": "VobSub",
            "title": "洛东江大决战\/Commando on the Nakdong River\/Does the Nak-Dong River Flow\/洛東江大決戦\/洛东江大决战.Does the Nak-Dong River Flow.1976.DVD.X264.AAC.HALFCDi",
            "vote_score": 0,
            "release_site": "个人",
            "videoname": "낙동강은 흐르는가",
            "view_count": 289,
            "lang": {
                "desc": "双语",
                "langlist": {
                    "langdou": true
                }
            }
        }]
    }
}
```

关于返回的字幕信息的结构，见[subs](https://secure.assrt.net/api/doc#subs)

#### sub/similar

获取与某个字幕类似的其他5个字幕

|参数|是否可选|含义|
|---|---|---|
|id|字幕ID，为6位整数|

典型请求举例:

```shell
curl "https://api.assrt.net/v1/sub/similar?token=TOKEN&id=603765"
```

典型响应举例:

```json
{
    "status": 0,
    "sub": {
        "result": "succeed",
        "action": "similar",
        "subs": [{
            "native_name": "无限斯托拉托斯\/BD 两季+OVA1\/2全\/IS",
            "videoname": "Infinite Stratos",
            "revision": 0,
            "subtype": "Subrip(srt)",
            "upload_time": "2015-08-22 18:37:08",
            "vote_score": 50,
            "id": 602887,
            "release_site": "个人",
            "lang": {
                "desc": "双语",
                "langlist": {
                    "langdou": true
                }
            }
        },
        "此处省略其余4个结果",
        ]
    }
}
```

这个请求的响应格式与[sub/search](https://secure.assrt.net/api/doc#subsearch)相同

### user

用户信息相关服务

#### user/quota

获取当前用户可用配额

|参数|是否可选|含义|
|---|---|---|
|无|

典型请求举例:

```shell
curl "https://api.assrt.net/v1/user/quota?token=TOKEN"
```

典型响应举例:

```json
{
    "status": 0,
    "user": {
        "result": "succeed",
        "action": "quota",
        "quota": 20
    }
}
```

## 数据类型

### subs

字幕基本信息由以下键构成：

-   **id** 字幕ID
-   **native\_name** 影片原始名称
-   **revision** 字幕的修订版本ID，如不存在则为0
-   **upload\_time** 上传时间
-   **subtype** 字幕格式
-   **vote\_score** 用户评分，如果没有人评分则为0
-   **release\_site** 发行的字幕组名称 (可选)
-   **videoname** 字幕匹配的视频文件名 (可选)
-   **vote\_machine\_translate** 用户评价此字幕为机器翻译字幕 (可选)
-   **lang** 字幕语言 (可选)
    -   **langlist** 字幕语言列表
    -   **desc** 字幕语言描述

以下仅为[字幕详细信息](https://secure.assrt.net/api/doc#subdetail)才可见的键：

-   **filename** 字幕文件名
-   **size** 字幕文件大小
-   **url** 字幕下载地址
-   **view\_count** 浏览次数
-   **down\_count** 下载次数
-   **title** 标题
-   **filelist** 字幕压缩包内含的文件列表 (可选)
    -   **s** 文件大小
    -   **f** 文件名
    -   **url**该文件下载地址
-   **producer** 发布人 (可选)
    -   **uploader** 上传者
    -   **verifier** 校订者
    -   **producer** 制作者
    -   **source** 字幕来源

## 错误值

开发者应判断回复信息中的status值，如果不为零，说明发生了错误。需要注意的是，错误有时会影响HTTP状态码，其中APIError为200，ClientFail和ServerFail分别为4xx和5xx。

请不要保存下载地址，因为每次生成的下载地址都是唯一的而且具有一定的有效时间。

### APIError

|错误代码|错误信息|说明|
|---|---|---|
|1|no such user|用户不存在|
|101|length of keyword must be longer than 3|搜索关键词长度必须大于3|

### ClientFail

|错误代码|错误信息|说明|
|---|---|---|
|20000|your request is missing essential arguments|请求缺少参数|
|20001|invalid token|Token不存在|
|20400|API endpoint not found|API终结点不存在|
|20900|subtitle not found|字幕不存在|

### ServerFail

|错误代码|错误信息|说明|
|---|---|---|
|30000|server is encounting errors|服务器抽风了|
|30001|database is unavailable|数据库挂了|
|30002|search engine is unavailable|搜索引擎挂了|
|30300|API is temporarily unavailable|站长改代码少打了一个分号|
|30900|you are exceeding request limits|配额超限|

最后修改：2020/04/27
