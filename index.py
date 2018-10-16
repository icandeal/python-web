from urllib import parse
from wsgiref.simple_server import make_server
import elasticsearch as es
import json

# 创建es client
# client = es.Elasticsearch(["gw1in.aliyun.etiantian.net:12052 "])
client = es.Elasticsearch(["10.1.5.205", "10.1.5.206", "10.1.5.207"])


# 公用方法，用于对返回的对象进行处理
def rtn_data(data):
    return bytes(json.dumps(data), encoding='utf-8')


# 接口方法，获取每个城市的日活用户数量
def get_action_user_city(params):
    data = []       # 返回的数据对象
    # 获取参数
    try:
        date = params['date']
    except KeyError:       # 参数获取失败直接返回
        data['result'] = -1
        data['msg'] = 'params error!'
        print(json.dumps(data))
        return data
    # 查询体
    body = {
        "size": 0,
        "query": {
            "bool": {
                "must": [
                    {
                        "terms": {
                            "c_date": [
                                date
                            ]
                        }
                    },
                    {
                        "exists": {
                            "field": "lng"
                        }
                    },
                    {
                        "exists": {
                            "field": "lat"
                        }
                    }
                ]
            }
        },
        "aggs": {
            "city": {
                "terms": {
                    "script": {
                        "inline": "doc['lng.keyword'].value+','+doc['lat.keyword'].value",
                        "lang": "painless"
                    },
                    "size": 9999,
                    "order": [
                        {
                            "_count": "desc"
                        },
                        {
                            "_term": "asc"
                        }
                    ]
                },
                "aggs": {
                    "sum_tea": {
                        "sum": {
                            "field": "tea_count"
                        }
                    },
                    "sum_stu": {
                        "sum": {
                            "field": "stu_count"
                        }
                    }
                }
            }
        }
    }
    # 查询es
    response = client.search(index='class_year_user_action_count', body=body)
    # 获取查询结果
    aggs = response['aggregations']
    city_aggs = aggs['city']
    city_buckets = city_aggs['buckets']
    # 遍历桶
    for bucket in city_buckets:
        city_data = {}
        key = bucket['key']
        tea_sum = bucket['sum_tea']['value']
        stu_sum = bucket['sum_stu']['value']
        city_data['from'] = '116.46,39.92'
        city_data['to'] = key
        city_data['teaCount'] = tea_sum
        city_data['stuCount'] = stu_sum
        city_data['value'] = tea_sum + stu_sum
        data.append(city_data)

    return data   # 返回结果数据


# 云函数入口类
def handler(environ, start_response):
    # for k, v in environ.items():
    #     print(k, "@@", v)

    # ################# 获取接口名称 #################
    # request_uri = str(environ['fc.request_uri'])
    # inter_name = request_uri[request_uri.rfind("/data") + 6:]  # 接口名称在'/data'后面
    # params_pos = inter_name.find('?')       # url后面可能会带GET的参数
    # print(params_pos)
    # if params_pos > -1:
    #     inter_name = inter_name[0:params_pos]

    # 获取并分离接口名称
    path = str(environ['PATH_INFO'])
    inter_name = path.replace("/", "")
    print("inter_name==============", inter_name)

    params = {}  # 创建参数字典

    # ################ 获取GET参数 ################
    try:
        query_string = environ['QUERY_STRING']
    except KeyError:
        query_string = None
    if query_string is not None:
        get_attr = parse.parse_qs(query_string)
        for key in get_attr.keys():
            value = get_attr.get(key)[0]
            params[str(key)] = str(value)

    # ################ 获取POST参数 ################
    content_length = int(environ['CONTENT_LENGTH'])
    wsgi_input = environ['wsgi.input']
    request_body = wsgi_input.read(content_length)
    content = parse.parse_qs(str(request_body, 'utf-8'))
    for key in content.keys():
        value = content.get(key)[0]
        params[str(key)] = str(value)

    # 查看最终参数列表
    for k, v in params.items():
        print(k, "###", v)
    print(inter_name)       # 查看最终接口名称
    rtn = rtn_data(eval(inter_name)(params))  # 调用对应接口方法, 并使用公用方法rtn_data处理返回的数据

    status = '200 OK'
    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    return [rtn]    # 返回已处理过的


# serv = make_server('localhost', 8088, handler)
# serv.serve_forever()
