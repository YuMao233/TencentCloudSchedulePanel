import datetime
from apscheduler.schedulers.background import BackgroundScheduler


def job_func(text):
    print("当前时间：", datetime.datetime.utcnow().strftime(
        "%Y-%m-%d %H:%M:%S.%f")[:-3])
    print('参数:' + text)


scheduler = BackgroundScheduler()
scheduler.start()
scheduler.add_job(job_func, 'cron', hour='13',
                  minute='59', id='www', args=['text'])


scheduler.add_job(job_func, 'cron', hour='14',
                  minute='08', id='www2',  day_of_week='0,2,3,4,5,6', args=['text'])

# scheduler.remove_job('www')


if __name__ == "__main__":
    jobs = scheduler.get_jobs()
    for v in jobs:
        print(v.id + "|" + str(v))
        v.args[0] = 'ssss'
        print(v.id + "|" + str(v))
    while True:
        pass
