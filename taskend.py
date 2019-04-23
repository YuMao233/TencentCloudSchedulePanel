#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   taskend.py
@Time    :   2019/04/16
@Author  :   Suwings
@Contact :   Suwings@outlook.com
@Desc    :   计划任务结束管理器
'''


global G_MAN
G_MAN = {}


def decr_count(name):
    if name in G_MAN:
        if G_MAN[name] == -999:
            return
        G_MAN[name] -= 1
        if G_MAN[name] < 0:
            G_MAN[name] = 0
    else:
        G_MAN[name] = 0


def set_count(name, v):
    G_MAN[name] = int(v)


def get_count(name):
    if name in G_MAN:
        return int(G_MAN[name])
    return -999
