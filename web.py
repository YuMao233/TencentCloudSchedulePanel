#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   web.py
@Time    :   2019/04/15
@Author  :   Suwings
@Version :   1.0
@Contact :   Suwings@outlook.com
@Desc    :   Main
'''

import os
from datetime import timedelta

import taskend
import tencent_api
import config

from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from flask import Flask, redirect, render_template, request, session
from tencentcloud.common import credential

G_USERNAME = config.G_USERNAME
G_PASSWORD = config.G_PASSWORD
G_CRED = credential.Credential(
    config.G_API_ID,
    config.G_API_KEY
)

app = Flask(__name__)

app.config['SECRET_KEY'] = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

jobstores = {
    'redis': RedisJobStore(port=6379, password=config.G_REDIS_PASSWORD),
}
executors = {
    'default': ThreadPoolExecutor(10),
    'processpool': ProcessPoolExecutor(3)
}
G_scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors)
G_scheduler.start()


def check_user_premission(session):
    if 'username' in session and session['username'] is not None:
        if session['username'] == G_USERNAME and session['login'] is True:
            return True
    return False


@app.route('/index/')
@app.route('/')
def index():
    if check_user_premission(session):
        session.permanent = True
        return render_template('index.html')
    return redirect('/login/')


@app.route('/login/')
def login():
    return render_template('login.html')


@app.route('/logging/', methods=['POST'])
def logging():
    username = request.form['username']
    password = request.form['password']
    if username == G_USERNAME and password == G_PASSWORD:
        session['username'] = username
        session['login'] = True
        return redirect('/')
    else:
        return 'Username or password Error!!!'


@app.route('/logout/')
def delete():
    session['username'] = None
    session['login'] = False
    session.clear()
    return render_template('login.html')


@app.route('/console/<region>')
def console(region=None):
    if region is None:
        return '[Access denied] 请求格式错误.'
    if not check_user_premission(session):
        return '[Access denied] 权限不足.'
    jobs = G_scheduler.get_jobs()
    jobs_list = []
    for job in jobs:
        job_info = str(job).replace('next run at:', '下次执行时间:').replace('trigger: cron', '时间:').replace(
            'start_tencent_instance', '开启实例').replace('stop_tencent_instance', '关闭实例').replace('del_task_instance', '删除计划任务')

        if job.next_run_time is None:
            G_scheduler.remove_job(job.id, jobstore='redis')
            continue
        jobs_list.append([job.id, job_info])

    instances = tencent_api.client_instance_status(G_CRED, region)
    if instances is None:
        instances = []
    return render_template('console.html',
                           region=region,
                           instances=instances,
                           jobs_list=jobs_list
                           )


@app.route('/control/open/', methods=['POST'])
def control_open():
    if not check_user_premission(session):
        return '[Access denied] 权限不足.'
    id = request.form['id']
    region = request.form['region']
    try:
        tencent_api.client_start_instance(G_CRED, region, id)
        return 'OK'
    except Exception:
        return 'NO'


@app.route('/control/stop/', methods=['POST'])
def control_stop():
    if not check_user_premission(session):
        return '[Access denied] 权限不足.'
    id = request.form['id']
    region = request.form['region']
    try:
        tencent_api.client_stop_instance(G_CRED, region, id)
        return 'OK'
    except Exception:
        return 'NO'


@app.route('/mask/index/<region>')
def mask_index(region=None):
    if not check_user_premission(session):
        return '[Access denied] 权限不足.'
    instances = tencent_api.client_instance_status(G_CRED, region)
    if instances is None:
        instances = []
    return render_template('new_mask.html', region=region, instances=instances)


@app.route('/mask/delete/<id>')
def mask_delete(id=None):
    if not check_user_premission(session):
        return '[Access denied] 权限不足.'
    print("删除计划任务:" + id)
    G_scheduler.remove_job(id, jobstore='redis')
    return 'OK'


def start_tencent_instance(G_CRED, region, ext_value, mask_id):
    count = taskend.get_count(mask_id)
    if count == -999 or count > 0:
        tencent_api.client_start_instance(G_CRED, region, ext_value)
        taskend.decr_count(mask_id)
        print("[定时任务] 任务:" + mask_id + "已执行, 开启实例:" + ext_value)


def stop_tencent_instance(G_CRED, region, ext_value, mask_id):
    count = taskend.get_count(mask_id)
    if count == -999 or count > 0:
        tencent_api.client_stop_instance(G_CRED, region, ext_value)
        taskend.decr_count(mask_id)
        print("[定时任务] 任务:" + mask_id + "已执行, 关闭实例:" + ext_value)


def del_task_instance(G_CRED, region, ext_value, mask_id):
    try:
        instance_job = G_scheduler.get_job(ext_value)
        instance_id = instance_job.args[2]
        print("[删除任务] 触发,正在寻找名称为 %s 的实例" % instance_id)
        instances = tencent_api.client_instance_status(G_CRED, region)
        if instances is None:
            return
        for instance in instances:
            if instance[0] == instance_id:
                print("[删除任务] 已找到 %s 实例，已停止实例." % instance_id)
                tencent_api.client_stop_instance(G_CRED, region, instance_id)
    except Exception as err:
        print(err)
    G_scheduler.remove_job(ext_value, jobstore='redis')
    # G_scheduler.remove_job(mask_id)
    print("[定时任务] 删除任务: " + mask_id + " 已执行,此为一次性任务\n删除的目标任务是:" + ext_value)


@app.route('/mask/new/', methods=['POST'])
def mask_new(region=None):
    if not check_user_premission(session):
        return '[Access denied] 权限不足.'
    try:
        mask_a = request.form['mask_a']
        monday_list = ""
        if 'mask_date_1' in request.form:
            monday_list += "0,"
        if 'mask_date_2' in request.form:
            monday_list += "1,"
        if 'mask_date_3' in request.form:
            monday_list += "2,"
        if 'mask_date_4' in request.form:
            monday_list += "3,"
        if 'mask_date_5' in request.form:
            monday_list += "4,"
        if 'mask_date_6' in request.form:
            monday_list += "5,"
        if 'mask_date_7' in request.form:
            monday_list += "6,"
        exectime = request.form['exectime']
        endtime = request.form['endtime']
        if endtime == "":
            endtime = "2099-12-31 23:59:59"
        else:
            endtime += ":00"
        mask_c = request.form['mask_c']
        mask_id = request.form['mask_id']
        region = request.form['region']
        ext_value = request.form['ext_value']
        monday_list = monday_list[:len(monday_list) - 1]
        print("创建计划任务:")
        print("表单:" + str(request.form))
        print("星期:" + str(monday_list))
        print("执行时间:"+str(exectime))

        # 指定时间模式
        if mask_a == 'order':
            taskend.set_count(mask_id, 1)
            if mask_c == 'open':
                G_scheduler.add_job(start_tencent_instance, 'date',  id=mask_id, args=[
                                    G_CRED, region, ext_value, mask_id], run_date=exectime, jobstore='redis', replace_existing=True)
            if mask_c == 'stop':
                G_scheduler.add_job(stop_tencent_instance, 'date',  id=mask_id,
                                    args=[G_CRED, region, ext_value, mask_id], run_date=exectime, jobstore='redis', replace_existing=True)
            if mask_c == 'del':
                G_scheduler.add_job(del_task_instance, 'date',   id=mask_id,
                                    args=[G_CRED, region, ext_value, mask_id], run_date=exectime, jobstore='redis', replace_existing=True)
            return ('<a href="/console/%s">创建成功，单击此处返回到控制台.</a>' % region)
        # 循环执行模式
        exectime_arr = exectime.split(":")
        taskend.set_count(mask_id, -999)
        if mask_c == 'open':
            G_scheduler.add_job(start_tencent_instance, 'cron', hour=exectime_arr[0],
                                minute=exectime_arr[1], id=mask_id, day_of_week=monday_list, args=[G_CRED, region, ext_value, mask_id], end_date=str(endtime), jobstore='redis', replace_existing=True)
        if mask_c == 'stop':
            G_scheduler.add_job(stop_tencent_instance, 'cron', hour=exectime_arr[0],
                                minute=exectime_arr[1], id=mask_id, day_of_week=monday_list, args=[G_CRED, region, ext_value, mask_id], end_date=endtime, jobstore='redis', replace_existing=True)
        if mask_c == 'del':
            G_scheduler.add_job(del_task_instance, 'cron', hour=exectime_arr[0],
                                minute=exectime_arr[1], id=mask_id,  day_of_week=monday_list, args=[G_CRED, region, ext_value, mask_id], end_date=endtime, jobstore='redis', replace_existing=True)
        return '<a href="/console/%s">创建成功，单击此处返回到控制台</a>' % region
    except Exception:
        return '[请求异常] 输入数据格式不正确或某些值输入非法，也有可能您的连续误操作导致出现此异常。<br>请检查重试，如果依然出现此现象，请反馈给开发者.<a href="/console/%s">单击此处返回到控制台</a>' % region


if __name__ == '__main__':
    print("[程序] 程序运行..")
    app.run(debug=False)
