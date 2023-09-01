# -*- coding: utf-8 -*-
# author: https://github.com/BeaCox
import json
import os
import re

import requests
import yaml

version = 'v2.1'  # 版本号，已经存在json文件里面了
output_dir = 'json'  # 输出目录不应该随着版本变化，应该固定.

# load config
with open('config.yml', 'r', encoding='utf-8') as file:
    ystr = file.read()
    cfg = yaml.load(ystr, Loader=yaml.FullLoader)

# get labels list from repo using github api


def get_labels_for_repo(repo):
    response = requests.get('https://api.github.com/repos/%s/labels' % (repo), headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'Mozilla/5.0 (Macintosh;Intel Mac OS X 10_12_6) AppleWebKit/537.36(KHTML, like Gecko) Chrome/67.0.3396.99Safari/537.36',
    })
    if response.status_code != 200:
        print('error:', response.status_code)
        raise Exception('Http Error:', response.status_code)
    labels_list = response.json()
    return labels_list

# get issues list according to the labels and state


def get_issues_list(repo, labels=[], state='all', sort='created'):
    def _query_issues_from_github_api_per_page(repo, labels=[], state='all', sort='created', page=1, per_page=100, timeout=10, ssl=True):
        response = requests.get('https://api.github.com/repos/%s/issues' % (repo), params={
            'state': state,
            'labels': ','.join(labels),
            'per_page': per_page,
            'page': page,
            'sort': sort
        }, headers={
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'Mozilla/5.0 (Macintosh;Intel Mac OS X 10_12_6) AppleWebKit/537.36(KHTML, like Gecko) Chrome/67.0.3396.99Safari/537.36',
        },
            timeout=timeout,
            verify=ssl
        )
        if response.status_code != 200:
            print('error:', response.status_code)
            raise Exception('Http Error:', response.status_code)
        resp_list = response.json()
        issues_list = []
        for item in resp_list:
            def parser_json(item):
                # parser the body
                body_re = re.findall(r'```json([\s\S]+)```', item['body'])
                return dict(
                    json.loads(body_re[0]),
                    **{
                        'raw': item
                    }
                )

            def parser_table(item):
                # 解析body中需要的字段: 
                item_keys = {
                    'title': '博客名称',
                    'url': '博客地址',
                    'avatar': '网站图标',
                    'description': '博客描述',
                    'url-friends': '友链地址',
                    'url-feed': '订阅地址'
                }
                # 采用 ### 将数据分为多个部分, 每个部分的第一行为title, 第二行为value
                items = item['body'].split('###')
                item_dict = {}
                item_dict_new = {}
                for item in items:
                    if len(item.split('\n\n')) < 2:
                        continue
                    key, value = item.split('\n\n')[0], item.split('\n\n')[1]
                    item_dict[key.strip()] = value.strip()
                # 替换 dict 的 key
                for k,v in item_keys.items():
                    item_dict_new[k] = item_dict.pop(
                        v).strip() if v in item_dict else ''
                    item_dict_new[k] = '' if item_dict_new[k] == '_No response_' else item_dict_new[k]
                return item_dict_new
            
            if not len(re.findall(r'```json([\s\S]+)```', item['body'])):
                issues_list.append(parser_json(item))
            else:
                issues_list.append(parser_table(item))
        return issues_list
    total_issues_list = []
    try:
        page = 1
        per_page = 100
        issues_list = _query_issues_from_github_api_per_page(
            repo, labels=labels, state=state, sort=sort, page=page, per_page=per_page)
        total_issues_list += issues_list
        while len(issues_list) == per_page:
            page += 1
            issues_list = _query_issues_from_github_api_per_page(
                repo, labels=labels, state=state, sort=sort, page=page, per_page=per_page)
            total_issues_list += issues_list
        return total_issues_list
    except Exception as e:
        raise Exception('getData Error:', e)


# generate issues dict according to the groups
def generate_json_based_on_issues():
    output_dict = {}
    cfg_issues = cfg['issues']
    labels_list = get_labels_for_repo(cfg_issues["repo"])
    issues_list = get_issues_list(
        repo=cfg_issues["repo"], state='all', sort=cfg_issues["sort"])
    # 生成 all, 包含所有的issues, 不区分state和labels
    output_dict['all'] = issues_list
    # 根据state过滤issues
    # 生成 groups
    if not cfg_issues['groups']:
        return output_dict
    for group in cfg_issues['groups']:
        # 状态过滤
        issues_list_with_state = issues_list
        if group['state'] and group['state'] != 'all':
            issues_list_with_state = list(
                filter(lambda x: x['raw']['state'] == group['state'], issues_list))
        # 根据labels过滤
        issues_list_with_state_and_labels = issues_list_with_state
        if group['labels'] and len(group['labels']):
            issues_list_with_state_and_labels = list(
                filter(lambda item: set(group['labels']).issubset(set([x['name'] for x in item['raw']['labels']])), issues_list_with_state))

        # 生成json
        output_dict[group['name']] = issues_list_with_state_and_labels

    # remove raw data
    if not cfg_issues['keep_raw']:
        for item in issues_list:
            del item['raw']

    return output_dict


output_dict = generate_json_based_on_issues()
os.makedirs(output_dir, exist_ok=True)
for key in output_dict.keys():
    with open(os.path.join(output_dir, key+'.json'), 'w', encoding='utf-8') as file:
        # 生成json文件, 涵盖更多信息, 方便后续处理
        json.dump({
            'version': version,
            'config': cfg,
            'label': key,
            'content': output_dict[key]
        }, file, ensure_ascii=False, indent=2)
    print('generate file:', key+'.json')
print('done')
