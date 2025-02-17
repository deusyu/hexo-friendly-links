# hexo-friendly-links

自动提取本仓库 issues 中第一段 `JSON` 代码块并保存到仓库中.

本案例用于添加动态友链。

## 使用方法

1. fork 本仓库，把 `config.yml` 配置改为自己的：

```yaml
# 要抓取的 issues 配置
issues:
  repo: Doradx/hexo-friendly-links # 仓库持有者/仓库名
  groups: [
    {
      name: 'friendly_links_active', # 对应生成的json文件名称
      state: all, # issues状态, all/open/closed
      labels: ['active'] # 本组必须包含的标签列表, 多个标签为and关系
    },
    {
      name: 'friendly_links_404',
      state: all,
      labels: ['404']
    },
    {
      name: 'friendly_links_open_checklist',
      state: open,
      labels: ['checklist']
    }
  ]
  sort: updated-desc # 排序，按最近更新，取消此项则按创建时间排序
  keep_raw: false # 是否需要原始issuses数据字段 (包含大量github用户信息)

```

2. 打开 action 运行权限。

## 测试是否配置成功

1. 新建 issue 并按照模板要求填写提交。
2. 等待 Action 运行完毕，检查 `output` 分支是否有 `/json/all.json` 文件或`/json/<组名>.json`，内容是否正确，如果正确则表示已经配置成功。


## 申请友链
前往GitHub提交[issues](https://github.com/Doradx/hexo-friendly-links/issues)即可, [直达链接](https://github.com/deusyu/hexo-friendly-links/issues/new?assignees=&labels=&template=template_friend_new.yaml)
需要准备的内容:
```json
{
    "title": "博客标题/昵称",
    "url": "博客地址",
    "avatar": "头像地址, 请注意跨域问题",
    "screenshot": "网站截图链接",
    "description": "博客简介/描述"
}
```

## 我的友链
信息如下：
```json
{
    "title": "既往不恋",
    "url": "https://deusyu.app",
    "avatar": "https://deusyu.app/img/avatar-2023.png",
    "screenshot": "无",
    "description": "Beauty will save the world."
}
```

## 定时同步生成的json至私有仓库的静态博客
yaml路径：.github/workflows/sync_json.yml
1. 定义好几个Github Actions secrets  
- GH_PAT: checkout私有仓库需要的token，在Github `Settings -> Developer Settings -> Personal access tokens` 中申请
- PRIVATE_REPO: 私有仓库的名称，比如`deusyu/hexo-blog`
- PRIVATE_PATH: 私有静态博客的JSON目录, 比如`source/link`
- USER_EMAIL: 自己的邮箱地址，比如`daniel@deusyu.app`
- USER_NAME: 自己的用户名，比如`deusyu`
2. 手动调试
