from flask import Flask,Response, request, render_template
from MySQLdb import cursors, connect
from datetime import datetime
import time
import json
import mysql.connector
from statistics import mean
from flask_cors import CORS, cross_origin
from flask import jsonify


app = Flask("__name__")
cors = CORS(app)
# app.config['CORS_HEADERS'] = 'Content-Type'


@app.route('/')
def main_page():
    #return render_template('form.html')
    sensor, curr_data, bar_data = read_table()
    yesterday = read_yesterday()
    return render_template("dataourfarm.html",sensor=sensor,curr_state=curr_data,bar=bar_data,yesterday=yesterday)

@app.route('/input',methods=["POST"])
def input_data():
    suhu = 0.0
    lembap = 0.0
    sm = 0.0
    rel = 0
# perintah arduino
    try:
        if request.method == "POST":
            suhu = float(request.form["suhu"])
            lembap = float(request.form["lembap"])
            sm = float(request.form["sm"])
            rel = int(request.form["relay"])
        insert_to_table(suhu,lembap,sm,rel)
        return "suhu : {}, kelembapan : {}, soil moisture : {}, relay : {}".format(suhu ,lembap, sm, rel)
    except Exception as e:
        return "error {}".format(e.message)

@app.route('/get',methods=["GET"])
def get_data_api():
    sensor, curr_data, bar_data = read_table()
    yesterday = read_yesterday()
    return jsonify({'sensor':sensor,'curr_data':curr_data,'bar_data':bar_data, 'yesterday':yesterday})

def insert_to_table(suhu,lembap,sm,rel):
    try:
        conn = connect(host='localhost',db='db_sister',
                       user='root',passwd='password')
        cursor = conn.cursor()
        query = "INSERT INTO sensor (suhu, kelembapan, soil_moist, relay) VALUES (%s, %s, %s, %s)"

        tuple = (suhu, lembap, sm, rel)
        try:
            cursor.execute(query,tuple)
            conn.commit()
        except:
            conn.rollback()
        print("Data berhasil dimasukkan")

    except Error as error:
        print("Gagal memasukkan data {}".format(error))

    finally:
        if (conn.is_connected()):
            cursor.close()
            conn.close()
            print("MySql ditutup")

def read_table():
    conn = connect(host = "localhost", user="root", passwd="password", db="db_sister", cursorclass=cursors.DictCursor)
    cur = conn.cursor()
    cur.execute("SELECT * from sensor order by id desc")
    data = cur.fetchall()
    sensor = get_data(data)
    top_data = read_top(sensor)
    curr_data = sensor[0]
    return sensor, curr_data, top_data

#@app.route('/yesterday',methods=["GET"])
def read_yesterday():
    conn = connect(host = "localhost", user="root", passwd="password", db="db_sister", cursorclass=cursors.DictCursor)
    cur = conn.cursor()
    #ini tambahan
    try:
        cur.execute("SELECT * FROM sensor WHERE DATE(time) = DATE(NOW() - INTERVAL 3 DAY) order by id desc")
        data = cur.fetchall()
        sensor = get_data(data)
        y_suhu, y_lembap, y_sm = mean_yesterday(sensor)
    except:
        y_suhu = 0
        y_lembap = 0
        y_sm = 0
    #tambah end
    sensor,curr_data,bar = read_table()
    #tambahan - edit
    if y_suhu != 0:
        suhu_yes=((curr_data['suhu']-y_suhu)/y_suhu)
        suhu_yes = suhu_yes * 100
    else:
        suhu_yes = 0
    if y_lembap != 0:
        lembap_yes=((curr_data['lembap']-y_lembap)/y_lembap)
        lembap_yes = lembap_yes * 100
    else:
        lembap_yes = 0
    if y_sm != 0:
        sm_yes = ((curr_data['sm']-y_sm)/y_sm)
        sm_yes = sm_yes * 100
    else:
        sm_yes = 0
    # tambah -edit end
    sign = lambda x: (1, 0)[x <= 0]
    yesterday = dict()
    yesterday['suhu'] = {'nilai':float(round(suhu_yes,2)),'sign':sign(suhu_yes)}
    yesterday['lembap'] = {'nilai':float(round(lembap_yes,2)), 'sign':sign(lembap_yes)}
    yesterday['sm'] = {'nilai':float(round(sm_yes,2)), 'sign':sign(sm_yes)}
    #return jsonify({'suhu':suhu_yes,'lembap':lembap_yes,'sm':sm_yes})
    return yesterday

def mean_yesterday(sensors):
    list_suhu = []
    list_lembap = []
    list_sm = []
    for sensor in sensors:
        list_suhu.append(sensor['suhu'])
        list_lembap.append(sensor['lembap'])
        list_sm.append(sensor['sm'])
    mean_suhu = mean(list_suhu)
    mean_lembap = mean(list_lembap)
    mean_sm = mean(list_sm)
    return mean_suhu,mean_lembap,mean_sm

def read_top(data):
    top = data[:10]
    top = top[::-1]
    ret = {}
    li_suhu = []
    li_lembap = []
    li_sm = []
    li_relay = []
    li_cahaya = []
    for i in top:
       li_suhu.append(i['suhu'])
       li_lembap.append(i['lembap'])
       li_sm.append(i['sm'])
       li_relay.append(i['relay'])
    ret = {
           'suhu':li_suhu,
           'lembap':li_lembap,
           'sm':li_sm,
           'relay':li_relay
          }
    return ret

def get_data(data):
    li = []
    for dat in data:
        di = {}
        waktu = dat['time']
        tanggal = waktu.strftime("%d/%m/%Y")
        jam = waktu.strftime("%H:%M:%S")
        di['tanggal'] = tanggal
        di['jam'] = jam
        di['suhu'] = dat['suhu']
        di['lembap'] = dat['kelembapan']
        di['sm'] = dat['soil_moist']
        di['relay'] = dat['relay']
        li.append(di)
    return li


if __name__ == "__main__":
    app.run(host='0.0.0.0',port='5001',debug=True, threaded=True)
