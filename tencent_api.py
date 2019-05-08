#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Time    :   2019/04/13
@Author  :   Suwings
@Version :   1.0
@Contact :   Suwings@outlook.com
@Desc    :   腾讯接口
'''

# from tencentcloud.common import credential
# from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cvm.v20170312 import cvm_client, models
import json


def client_instance_status(cred, region):
    client = cvm_client.CvmClient(cred, region)
    req = models.DescribeZonesRequest()
    resp = client.DescribeInstances(req)
    result = resp.to_json_string()
    result = json.loads(result)
    tlen = int(result['TotalCount'])
    if tlen <= 0:
        return None
    instance_set = result['InstanceSet']
    tmp = []
    for instance in instance_set:
        id = instance['InstanceId']
        status = instance['InstanceState']
        name = instance['InstanceName']
        tmp.append([id, status, name])
    return tmp


def client_start_instance(cred, region, id):
    try:
        client = cvm_client.CvmClient(cred, region)
        req = models.DescribeZonesRequest()
        req.InstanceIds = [id]
        resp = client.StartInstances(req)
        result = resp.to_json_string()
        print(result)
    except Exception as err:
        print(err)


def client_stop_instance(cred, region, id):
    try:
        client = cvm_client.CvmClient(cred, region)
        req = models.DescribeZonesRequest()
        req.InstanceIds = [id]
        resp = client.StopInstances(req)
        result = resp.to_json_string()
        print(result)
    except Exception as err:
        print(err)
