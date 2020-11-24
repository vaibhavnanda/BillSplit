import os
import sqlite3
import json

from flask import Flask,request,url_for,redirect, render_template, flash
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from oauthlib.oauth2 import WebApplicationClient
import requests

from db import init_db_command,get_db,close_db
from user import User
import sys
import datetime
from pytz import timezone


# To secure confidential info while pushing on github
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID",None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET",None)
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

# Managing user sessions
login_manager = LoginManager()
login_manager.init_app(app)

# Database setup
try:
    init_db_command()
except sqlite3.OperationalError:
    pass # Assuming db has already been created

#oAuth2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)

india = timezone('Asia/Kolkata')


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


# Homepage
@app.route("/")
def index():
    if current_user.is_authenticated:
        if request.method == "GET":
            curemail = current_user.email
            db = get_db()
            cur = db.cursor()
            data = {'name' : current_user.name , 'email' : current_user.email , 'pic' : current_user.profile_pic}
            payTemp = cur.execute("SELECT sum(amount) FROM borrower WHERE email=? and done=?",(curemail,"0"))
            for i in payTemp:
                pay = i["sum(amount)"]
            if pay == None or int(pay) == 0:
                pay = 0
            recTemp = cur.execute("SELECT sum(amount) FROM borrower WHERE payto=? and done=?",(curemail,"0"))
            for i in recTemp:
                rec = i["sum(amount)"]
            if rec == None or int(rec) == 0:
                rec = 0

            return render_template("home.html" , data = data , pay = pay , rec = rec)
    else:
        return render_template('login.html')


def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

@app.route("/login")
def login():
    # URL to hit for google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@app.route("/login/callback")
def callback():
    code = request.args.get("code")

    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send a request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    # You want to make sure their email is verified.
    # The user authenticated with Google, authorized your
    # app, and now you've verified their email through Google!
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400

    # Create a user in your db with the information provided
    # by Google
    user = User(
        id_=unique_id, name=users_name, email=users_email, profile_pic=picture
    )

    # Doesn't exist? Add it to the database.
    if not User.get(unique_id):
        User.create(unique_id, users_name, users_email, picture)

    # Begin user session by logging the user in
    login_user(user)

    # Send user back to homepage
    return redirect(url_for("index"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))










@app.route("/friends" , methods = ['GET' , 'POST'])
def friends():
    curemail = current_user.email
    db = get_db()
    cur = db.cursor()
    if request.method == 'GET':       
        data = cur.execute("SELECT * FROM friends WHERE youremail=?" , (curemail,)).fetchall()
        return render_template('friends.html' , data = data)
    else:
        if ('add' not in request.form) or (request.form['add'] == ''):
            flash('Please Specify Mail')
            return redirect('/friends')
        fremail = request.form['add']
        if fremail == curemail:
            flash('This is your email')
            return redirect('/friends')
        check = cur.execute("SELECT * FROM members WHERE email=?" , (fremail,)).fetchone()

        print(check, file=sys.stderr)
        if check:
            check2 = cur.execute("SELECT * FROM friends WHERE youremail=? and friendemail=?" , (curemail,fremail,)).fetchone()
            if check2:
                flash("Already friends")
                redirect('/friends')
            else:
                cur.execute("INSERT INTO friends(youremail,friendemail,pay,rec) VALUES (?,?,?,?)" , (curemail,fremail,0,0))
                cur.execute("INSERT INTO friends(youremail,friendemail,pay,rec) VALUES (?,?,?,?)" , (fremail,curemail,0,0))
                db.commit()
            return redirect('/friends')            
        else:    
            flash('User doesn\'t exist')
            return redirect('/friends')









@app.route('/split' , methods = ['GET' , 'POST'])
def split():
    curemail = current_user.email
    db = get_db()
    cur = db.cursor()
    data = cur.execute("SELECT name,email,profile_pic FROM members where email IN (SELECT friendemail FROM friends where youremail=?)" , (curemail,)).fetchall()

    return render_template('split.html' , data = data)





@app.route('/split2' , methods = ['POST' , 'GET'])
def split2():
    curemail = current_user.email
    db = get_db()
    cur = db.cursor()
    if request.method == 'GET':
        return redirect('/split')
    else:
        candidates = request.form.getlist('cb')
        candidates.append(curemail)
        data = cur.execute("SELECT profile_pic,email,name FROM members WHERE email IN ("+",".join(["?"]*len(candidates))+")",(candidates)).fetchall()
        name = request.form['name']
        if name == '':
            return redirect('/split')
        amount = request.form['amount']
        if amount == '':
            return redirect('/split')
        return render_template('split2.html' , data = data , name = name , amount = amount)






@app.route('/split3' , methods = ['POST' , 'GET'])
def split3():
    curemail = current_user.email
    db = get_db()
    cur = db.cursor()
    if request.method == 'GET':
        return redirect('/split')
    else:
        formData = request.form
        data = []
        sum = 0
        for i in formData:
            if i == "name":
                name = formData[i]
            elif i == "amount":
                amount = formData[i]
            elif i == "submit":
                submit = formData[i]
            else:
                profilePicTemp = cur.execute("SELECT profile_pic FROM members WHERE email=?",(i,))
                for j in profilePicTemp:
                    profilePic = j["profile_pic"]
                temp = {
                    "email" : i ,
                    "share" : formData[i] ,
                    "profile_pic" : profilePic
                }
                data.append(temp)
                sum += int(formData[i])
        # Here share is string
        transactionId = str(datetime.datetime.now(india)) + name + curemail

        if sum != int(amount):
            # print("Sum Not equal to amt")
            flash("Paid amount was not equal to the specified amount.")
            return redirect('/split')
        
        if submit == "Split equally":
            cur.execute("INSERT INTO transactions(transaction_id,name,amount) VALUES (?,?,?)",(transactionId,name,amount))    
            db.commit()
            perPerson = int(int(amount)/len(data))
            receivers = []
            senders = []
            neutrals = []
            curDate = str(datetime.datetime.now(india))[0:10]
            curTime = str(datetime.datetime.now(india))[11:19]
            for i in data:
                tempEmail = i["email"]
                tempShare = int(i["share"])

                cur.execute("INSERT INTO notifications(youremail,friendemail,transaction_id,date,time,type) VALUES (?,?,?,?,?,?)" , (curemail,tempEmail,transactionId,curDate,curTime,"1"))
                db.commit()

                if tempShare > 0:
                    cur.execute("INSERT INTO spender(email,transaction_id,amount) VALUES (?,?,?)",(tempEmail,transactionId,tempShare))
                if tempShare == perPerson:
                    tempDict = {
                        "email" : tempEmail ,
                        "share" : "0"
                    }
                    neutrals.append(tempDict)
                elif tempShare > perPerson:
                    tempShare -= perPerson
                    tempDict = {
                        "email" : tempEmail ,
                        "share" : tempShare
                    }
                    receivers.append(tempDict)
                else:
                    tempShare = perPerson - tempShare
                    tempDict = {
                        "email" : tempEmail ,
                        "share" : tempShare
                    }
                    senders.append(tempDict)
            db.commit()
             
            # Here share is int
            receivers = sorted(receivers , key= lambda i : i["share"] , reverse = True)
            senders = sorted(senders , key= lambda i : i["share"] , reverse = True)
            senTempShare = -1
            recTempShare = -1
            while len(receivers) > 0 or len(senders) > 0:
                if recTempShare == -1:
                    recTempData = receivers.pop()
                    recTempEmail = recTempData["email"]
                    recTempShare = recTempData["share"]
                if senTempShare == -1:
                    senTempData = senders.pop()
                    senTempEmail = senTempData["email"]
                    senTempShare = senTempData["share"]

                senToRecInfo = db.execute("SELECT pay,rec FROM friends WHERE youremail=? AND friendemail=?",(senTempEmail,recTempEmail))
                for i in senToRecInfo:
                    senToRecPay = i["pay"]
                    # senToRecRev = i["rec"]
                if senTempShare == recTempShare:
                    # insert in db
                    cur.execute("INSERT INTO borrower(email,transaction_id,amount,payto,done) VALUES (?,?,?,?,?)",(senTempEmail,transactionId,senTempShare,recTempEmail,"0"))
                    check = cur.execute("SELECT * FROM friends WHERE youremail=? AND friendemail=?",(senTempEmail,recTempEmail)).fetchone()
                    if check:
                        cur.execute("UPDATE friends SET pay=? WHERE youremail=? AND friendemail=?",(int(senToRecPay)+senTempShare,senTempEmail,recTempEmail))
                        cur.execute("UPDATE friends SET rec=? WHERE youremail=? AND friendemail=?",(int(senToRecPay)+senTempShare,recTempEmail,senTempEmail))
                    else:
                        cur.execute("INSERT INTO friends(youremail,friendemail,pay,rec) VALUES (?,?,?,?)",(senTempEmail,recTempEmail,int(senTempShare),0))
                        cur.execute("INSERT INTO friends(youremail,friendemail,pay,rec) VALUES (?,?,?,?)",(recTempEmail,senTempEmail,0,int(senTempShare)))
                    db.commit()
                    senTempShare = -1
                    recTempShare = -1
                elif senTempShare > recTempShare:
                    # insert in db
                    cur.execute("INSERT INTO borrower(email,transaction_id,amount,payto,done) VALUES (?,?,?,?,?)",(senTempEmail,transactionId,recTempShare,recTempEmail,"0"))
                    check = cur.execute("SELECT * FROM friends WHERE youremail=? AND friendemail=?",(senTempEmail,recTempEmail)).fetchone()
                    if check:
                        cur.execute("UPDATE friends SET pay=? WHERE youremail=? AND friendemail=?",(int(senToRecPay)+recTempShare,senTempEmail,recTempEmail))
                        cur.execute("UPDATE friends SET rec=? WHERE youremail=? AND friendemail=?",(int(senToRecPay)+recTempShare,recTempEmail,senTempEmail))
                    else:
                        cur.execute("INSERT INTO friends(youremail,friendemail,pay,rec) VALUES (?,?,?,?)",(senTempEmail,recTempEmail,int(recTempShare),0))
                        cur.execute("INSERT INTO friends(youremail,friendemail,pay,rec) VALUES (?,?,?,?)",(recTempEmail,senTempEmail,0,int(recTempShare)))
                    db.commit()
                    senTempShare = senTempShare - recTempShare
                    recTempShare = -1
                elif senTempShare < recTempShare:
                    # insert in db
                    cur.execute("INSERT INTO borrower(email,transaction_id,amount,payto,done) VALUES (?,?,?,?,?)",(senTempEmail,transactionId,senTempShare,recTempEmail,"0"))
                    check = cur.execute("SELECT * FROM friends WHERE youremail=? AND friendemail=?",(senTempEmail,recTempEmail)).fetchone()
                    if check:
                        cur.execute("UPDATE friends SET pay=? WHERE youremail=? AND friendemail=?",(int(senToRecPay)+senTempShare,senTempEmail,recTempEmail))
                        cur.execute("UPDATE friends SET rec=? WHERE youremail=? AND friendemail=?",(int(senToRecPay)+senTempShare,recTempEmail,senTempEmail))
                    else:
                        cur.execute("INSERT INTO friends(youremail,friendemail,pay,rec) VALUES (?,?,?,?)",(senTempEmail,recTempEmail,int(senTempShare),0))
                        cur.execute("INSERT INTO friends(youremail,friendemail,pay,rec) VALUES (?,?,?,?)",(recTempEmail,senTempEmail,0,int(senTempShare)))
                    db.commit()
                    recTempShare = recTempShare - senTempShare
                    senTempShare = -1

            return render_template('splitdone.html')


        if submit == "Split manually":
            return render_template('splitmanually.html' , data = data , name = name , amount = amount)
        
        return redirect('/split')





@app.route('/splitmanually' , methods = ['POST' , 'GET'])
def splitmanually():
    curemail = current_user.email
    db = get_db()
    cur = db.cursor()
    curDate = str(datetime.datetime.now(india))[0:10]
    curTime = str(datetime.datetime.now(india))[11:19]
    if request.method == "GET":
        redirect('/')
    
    else:
        formData = request.form
        spender = []
        borrower = []
        listForNot = []
        sum1 = 0
        sum2 = 0
        for i in formData:
            if i == "name":
                name = formData[i]
            elif i == "amount":
                amount = formData[i]
            elif i == "submit":
                continue
            else:
                tempStr = i[-4:]
                # print(tempStr)
                if tempStr == "paid":
                    temp = {
                        "email" : i[:-4] ,
                        "share" : int(formData[i])
                    }
                    listForNot.append(temp["email"])
                    spender.append(temp)
                    sum1 += int(formData[i])
                
                if tempStr == "owes":
                    temp = {
                        "email" : i[:-4] ,
                        "share" : int(formData[i])
                    }
                    listForNot.append(temp["email"])
                    borrower.append(temp)
                    sum2 += int(formData[i])
        
        if sum1 != int(amount):
            # print("Spending amount not equal to event amount")
            flash("Spending amount was not equal to the specified amount.")
            return redirect('/split')
        if sum2 != int(amount):
            # print("Borrowing amount not equal to event amount")
            flash("Borrowing amount was not equal to the specified amount.")
            return redirect('/split')

        transactionId = str(datetime.datetime.now(india)) + name + curemail
        cur.execute("INSERT INTO transactions(transaction_id,name,amount) VALUES (?,?,?)",(transactionId,name,amount))    
        db.commit()

        borrower = sorted(borrower , key= lambda i : i["email"])
        spender = sorted(spender , key= lambda i : i["email"])

        uniqueList = set(listForNot)
        for x in uniqueList:
            cur.execute("INSERT INTO notifications(youremail,friendemail,transaction_id,date,time,type) VALUES (?,?,?,?,?,?)" , (curemail,x,transactionId,curDate,curTime,"1"))
            db.commit()

        for i in range(len(spender)):
            cur.execute("INSERT INTO spender(email,transaction_id,amount) VALUES (?,?,?)" , (spender[i]["email"] , transactionId , spender[i]["share"]))
            # print(i)
            # print('A')
            if spender[i]["share"] == borrower[i]["share"]:
                spender[i]["share"] = 0
                borrower[i]["share"] = 0

            elif spender[i]["share"] > borrower[i]["share"]:
                spender[i]["share"] -= borrower[i]["share"] 
                borrower[i]["share"] = 0

            elif spender[i]["share"] < borrower[i]["share"]:
                borrower[i]["share"] -= spender[i]["share"] 
                spender[i]["share"] = 0

        receivers = sorted(spender , key= lambda i : i["share"])
        senders = sorted(borrower , key= lambda i : i["share"])

        senTempShare = -1
        recTempShare = -1
        while len(receivers) > 0 and len(senders) > 0:
            if recTempShare == -1:
                recTempData = receivers.pop()
                recTempEmail = recTempData["email"]
                recTempShare = int(recTempData["share"])
            if senTempShare == -1:
                senTempData = senders.pop()
                senTempEmail = senTempData["email"]
                senTempShare = int(senTempData["share"])

            if int(recTempShare) == 0:
                recTempShare = -1
                continue

            if int(senTempShare) == 0:
                senTempShare = -1
                continue

            senToRecInfo = db.execute("SELECT pay,rec FROM friends WHERE youremail=? AND friendemail=?",(senTempEmail,recTempEmail))
            for i in senToRecInfo:
                senToRecPay = i["pay"]
                # senToRecRev = i["rec"]
            if senTempShare == recTempShare:
                # insert in db
                cur.execute("INSERT INTO borrower(email,transaction_id,amount,payto,done) VALUES (?,?,?,?,?)",(senTempEmail,transactionId,senTempShare,recTempEmail,"0"))
                check = cur.execute("SELECT * FROM friends WHERE youremail=? AND friendemail=?",(senTempEmail,recTempEmail)).fetchone()
                if check:
                    cur.execute("UPDATE friends SET pay=? WHERE youremail=? AND friendemail=?",(int(senToRecPay)+senTempShare,senTempEmail,recTempEmail))
                    cur.execute("UPDATE friends SET rec=? WHERE youremail=? AND friendemail=?",(int(senToRecPay)+senTempShare,recTempEmail,senTempEmail))
                else:
                    cur.execute("INSERT INTO friends(youremail,friendemail,pay,rec) VALUES (?,?,?,?)",(senTempEmail,recTempEmail,int(senTempShare),0))
                    cur.execute("INSERT INTO friends(youremail,friendemail,pay,rec) VALUES (?,?,?,?)",(recTempEmail,senTempEmail,0,int(senTempShare)))
                db.commit()
                senTempShare = -1
                recTempShare = -1
            elif senTempShare > recTempShare:
                # insert in db
                cur.execute("INSERT INTO borrower(email,transaction_id,amount,payto,done) VALUES (?,?,?,?,?)",(senTempEmail,transactionId,recTempShare,recTempEmail,"0"))
                check = cur.execute("SELECT * FROM friends WHERE youremail=? AND friendemail=?",(senTempEmail,recTempEmail)).fetchone()
                if check:
                    cur.execute("UPDATE friends SET pay=? WHERE youremail=? AND friendemail=?",(int(senToRecPay)+recTempShare,senTempEmail,recTempEmail))
                    cur.execute("UPDATE friends SET rec=? WHERE youremail=? AND friendemail=?",(int(senToRecPay)+recTempShare,recTempEmail,senTempEmail))
                else:
                    cur.execute("INSERT INTO friends(youremail,friendemail,pay,rec) VALUES (?,?,?,?)",(senTempEmail,recTempEmail,int(recTempShare),0))
                    cur.execute("INSERT INTO friends(youremail,friendemail,pay,rec) VALUES (?,?,?,?)",(recTempEmail,senTempEmail,0,int(recTempShare)))
                db.commit()
                senTempShare = senTempShare - recTempShare
                recTempShare = -1
            elif senTempShare < recTempShare:
                # insert in db
                cur.execute("INSERT INTO borrower(email,transaction_id,amount,payto,done) VALUES (?,?,?,?,?)",(senTempEmail,transactionId,senTempShare,recTempEmail,"0"))
                check = cur.execute("SELECT * FROM friends WHERE youremail=? AND friendemail=?",(senTempEmail,recTempEmail)).fetchone()
                if check:
                    cur.execute("UPDATE friends SET pay=? WHERE youremail=? AND friendemail=?",(int(senToRecPay)+senTempShare,senTempEmail,recTempEmail))
                    cur.execute("UPDATE friends SET rec=? WHERE youremail=? AND friendemail=?",(int(senToRecPay)+senTempShare,recTempEmail,senTempEmail))
                else:
                    cur.execute("INSERT INTO friends(youremail,friendemail,pay,rec) VALUES (?,?,?,?)",(senTempEmail,recTempEmail,int(senTempShare),0))
                    cur.execute("INSERT INTO friends(youremail,friendemail,pay,rec) VALUES (?,?,?,?)",(recTempEmail,senTempEmail,0,int(senTempShare)))
                db.commit()
                recTempShare = recTempShare - senTempShare
                senTempShare = -1

        return render_template('splitdone.html')
              









@app.route('/events' , methods = ['GET' , 'POST'])
def events():
    curemail = current_user.email
    db = get_db()
    cur = db.cursor()
    cur2 = db.cursor()
    if request.method == 'GET':       
        data = []
        tempSpenderData = cur.execute("SELECT transaction_id,name FROM transactions WHERE transaction_id IN (SELECT transaction_id FROM spender WHERE email=?)",(curemail,))
        if tempSpenderData:
            for i in tempSpenderData:
                tempDict = {
                    "transaction_id" : i["transaction_id"] ,
                    "name" : i["name"]
                }
                data.append(tempDict)
        tempBorrowerData = cur.execute("SELECT transaction_id,name FROM transactions WHERE transaction_id IN (SELECT transaction_id FROM borrower WHERE email=?)",(curemail,))
        if tempBorrowerData:
            for i in tempBorrowerData:
                tempDict = {
                    "transaction_id" : i["transaction_id"] ,
                    "name" : i["name"]
                }
                data.append(tempDict)
        
        sortedData = sorted(data, key = lambda i: i['transaction_id'],reverse=True) # Sorting on the basis of date and time

        uniqueData = list({v['transaction_id']:v for v in sortedData}.values()) # For unique entries in the list

        return render_template('events.html' , data = uniqueData)
    
    else:
        dataFromHTML = request.form
        for i in dataFromHTML:
            transactionId = i

        # print(transactionId)
        transactionData = cur.execute("SELECT * FROM transactions WHERE transaction_id=?" , (transactionId,))
        
        for i in transactionData:
            transactionName = i["name"]
            transactionAmount = i["amount"]

        date = transactionId[:10]
        time = transactionId[11:19]

        spenderData = cur.execute("SELECT email,amount FROM spender WHERE transaction_id=?" , (transactionId,))
        
        spenderList = []
        for i in spenderData:
            tempEmail = i["email"]
            tempPaid = i["amount"]
            tempNameFromDB = cur2.execute("SELECT name,profile_pic FROM members WHERE email=?" , (tempEmail,))
            for j in tempNameFromDB:
                tempName = j["name"]
                tempProfilePic = j["profile_pic"]
            tempData = {
                "email" : tempEmail ,
                "paid" : tempPaid , 
                "name" : tempName ,
                "profile_pic" : tempProfilePic
            }
            spenderList.append(tempData)

        borrowerData = cur.execute("SELECT email,amount,payto,done FROM borrower WHERE transaction_id=?" , (transactionId,))
        
        borrowerList = []
        
        for i in borrowerData:
            tempEmail = i["email"]
            tempPaid = i["amount"]
            tempPayTo = i["payto"]
            tempDone = i["done"]
            tempPayOrRec = "x"
            
            if tempDone == "0":
                if tempEmail == curemail:
                    tempPayOrRec = "paid"  # Have you paid the amount?
                elif tempPayTo == curemail:
                    tempPayOrRec = "recd"  # Have you received the amount?

            # print(tempPayOrRec)

            tempNameFromDB = cur2.execute("SELECT name,profile_pic FROM members WHERE email=?" , (tempEmail,))
            for j in tempNameFromDB:
                tempName1 = j["name"]
                tempProfilePic1 = j["profile_pic"]

            tempNameFromDB2 = cur2.execute("SELECT name,profile_pic FROM members WHERE email=?" , (tempPayTo,))
            for j in tempNameFromDB2:
                tempName2 = j["name"]
                tempProfilePic2 = j["profile_pic"]

            tempData = {
                "email1" : tempEmail ,
                "email2" : tempPayTo ,
                "name1" : tempName1 ,
                "name2" : tempName2 ,
                "profile_pic1" : tempProfilePic1 ,
                "profile_pic2" : tempProfilePic2 ,
                "paid" : tempPaid , 
                "payOrRec" : tempPayOrRec ,
                "done" : tempDone
            }
            borrowerList.append(tempData)
        
        # print(spenderList)
        # print(borrowerList)
        return render_template('eventinfo.html' , spenderList = spenderList , borrowerList = borrowerList , name = transactionName , tid = transactionId , amount = transactionAmount , date = date , time = time )





@app.route('/payorrec' , methods = ['GET' , 'POST'])
def payorrec():
    if request.method == "GET":
        return redirect('/')
    if request.method == "POST":
        data = request.form
        for i in data:
            tempData = i.split(' ')
        tid=""
        # print(tempData)
        email1 = tempData[0]
        email2 = tempData[1]
        for j in range(2,len(tempData)):
            tid = tid + tempData[j] + " "
        
        tid = tid[:-1]
        
        return render_template('payorrec.html' , email1 = email1 , email2 = email2 , tid = tid)


@app.route('/confirm' , methods = ['POST' , 'GET'])
def confirm():
    # curemail = current_user.email
    db = get_db()
    cur = db.cursor()
    if request.method == "GET":
        return redirect('/')

    else:
        data = request.form
        for i in data:
            tempData = i.split(' ')
        tid=""
        email1 = tempData[0]
        email2 = tempData[1]
        for j in range(2,len(tempData)):
            tid += tempData[j] + " "
        
        tid = tid[:-1]

        tempamount = cur.execute("SELECT amount FROM borrower WHERE email=? AND payto=? AND transaction_id=?" , (email1,email2,tid))
        for i in tempamount:
            amount = i["amount"]

        cur.execute("UPDATE borrower SET done=? WHERE email=? AND payto=? AND transaction_id=?" , ("1",email1,email2,tid))
        db.commit()
        senToRecInfo = db.execute("SELECT pay,rec FROM friends WHERE youremail=? AND friendemail=?",(email1,email2))
        for i in senToRecInfo:
            senToRecPay = i["pay"]
        
        cur.execute("UPDATE friends SET pay=? WHERE youremail=? AND friendemail=?",(int(senToRecPay)-int(amount),email1,email2))
        cur.execute("UPDATE friends SET rec=? WHERE youremail=? AND friendemail=?",(int(senToRecPay)-int(amount),email2,email1))
        db.commit()

        curDate = str(datetime.datetime.now(india))[0:10]
        curTime = str(datetime.datetime.now(india))[11:19]

        cur.execute("INSERT INTO notifications(youremail,friendemail,transaction_id,date,time,type) VALUES (?,?,?,?,?,?)",(email1,email2,tid,curDate,curTime,"2"))
        db.commit()
        return redirect('/events')










@app.route('/notifications')
def notifications():
    curemail = current_user.email
    db = get_db()
    cur = db.cursor()
    cur2 = db.cursor()
    userInfo = cur.execute("SELECT name,profile_pic FROM members WHERE email=?",(curemail,))
    for i in userInfo:
        name1 = i["name"]
        profile_pic1 = i["profile_pic"]

    sentTemp = cur.execute("SELECT * FROM notifications WHERE youremail=?",(curemail,))
    sentList = []
    for i in sentTemp:
        email2 = i["friendemail"]
        tid = i["transaction_id"]
        date = i["date"]
        time = i["time"]
        typeOfNot = i["type"]

        userInfo2 = cur2.execute("SELECT name,profile_pic FROM members WHERE email=?",(email2,))
        for j in userInfo2:
            name2 = j["name"]
            profile_pic2 = j["profile_pic"]

        tNameTemp = cur2.execute("SELECT name FROM transactions WHERE transaction_id=?",(tid,))
        for j in tNameTemp:
            tName = j["name"]


        tempData = {
            "email1" : curemail ,
            "email2" : email2 ,
            "name1" : name1 ,
            "name2" : name2 ,
            "profile_pic1" : profile_pic1 ,
            "profile_pic2" : profile_pic2 ,
            "tid" : tid ,
            "tName" : tName ,
            "date" : date ,
            "time" : time ,
            "typeOfNot" : typeOfNot
            
        }
        sentList.append(tempData)

    recdTemp = cur.execute("SELECT * FROM notifications WHERE friendemail=?",(curemail,))
    recdList = []
    for i in recdTemp:
        email2 = i["youremail"]
        tid = i["transaction_id"]
        date = i["date"]
        time = i["time"]
        typeOfNot = i["type"]

        userInfo2 = cur2.execute("SELECT name,profile_pic FROM members WHERE email=?",(email2,))
        for j in userInfo2:
            name2 = j["name"]
            profile_pic2 = j["profile_pic"]

        tNameTemp = cur2.execute("SELECT name FROM transactions WHERE transaction_id=?",(tid,))
        for j in tNameTemp:
            tName = j["name"]


        tempData = {
            "email2" : curemail ,
            "email1" : email2 ,
            "name2" : name1 ,
            "name1" : name2 ,
            "profile_pic2" : profile_pic1 ,
            "profile_pic1" : profile_pic2 ,
            "tid" : tid ,
            "tName" : tName ,
            "date" : date ,
            "time" : time ,
            "typeOfNot" : typeOfNot
            
        }
        recdList.append(tempData)

    newList = sentList + recdList

    newList = sorted(newList, key = lambda i: (i['date'], i['time']), reverse = True)

    return render_template('notifications.html' , newList = newList , curemail = curemail)










@app.route('/userinfo/<id>')
def userinfo(id):
    # curemail = current_user.email
    db = get_db()
    cur = db.cursor()
    dataTemp = id.split(' ')
    data = cur.execute("SELECT name,email,profile_pic FROM members WHERE email=?",(dataTemp[1],))
    return render_template('userinfo.html' , data = data , back = dataTemp[0])


if __name__ == "__main__":
    app.run(ssl_context="adhoc" )


