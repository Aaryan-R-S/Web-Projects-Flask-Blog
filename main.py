from flask import Flask, render_template, request, session,flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

from datetime import datetime
import json
import math
import os

from werkzeug.utils import secure_filename
from werkzeug.utils import redirect 

import pymysql
pymysql.install_as_MySQLdb()


with open('config.json') as f:
    params = json.load(f)["params"]
    
    
app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['UPLOAD_FOLDER'] = params['upload_location']
app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = '465',
    MAIL_USE_SSL =True,
    MAIL_USERNAME = params['gmail_id'],
    MAIL_PASSWORD = params['gmail_pwd']
)

mail = Mail(app)

local_server = params["local_server"]
    
if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']
    
db = SQLAlchemy(app)

class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(15) , nullable=False)
    message = db.Column(db.String(300), nullable=False)
    date = db.Column(db.String(12), nullable = True)
    
class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(30), nullable=False)
    topic = db.Column(db.String(30), nullable=False)
    author = db.Column(db.String(20), nullable=False)
    slug = db.Column(db.String(30), nullable=False)
    content = db.Column(db.String(1000), nullable=False)
    img_file = db.Column(db.String(30), nullable=False)
    date = db.Column(db.String(12), nullable = True)


@app.route("/")
def home():
    posts_preview = Posts.query.filter_by().all()
    end = math.ceil(len(posts_preview)/int(params['no_of_posts']))
    pg = request.args.get('page')
    if not str(pg).isnumeric():
        pg = 1
    pg = int(pg)
    if pg == 0:
        b = flash("You're at the Beginning of posts!","secondary")
    if pg == end+1:
        e = flash("You've reached to the End of posts!","secondary")
    if pg == 1 or pg==0:
        pg=1
        pre = '/?page=0'
        nex = "/?page="+str(pg+1)
    elif pg == end or pg==end+1:
        pg=end
        pre = "/?page="+str(pg-1)
        nex = '/?page='+str(end+1)
    else:
        pre = "/?page="+str(pg-1)
        nex = "/?page="+str(pg+1)

    posts_preview = posts_preview[(pg-1)*int(params['no_of_posts']) : (pg-1)*int(params['no_of_posts'])+int(params['no_of_posts'])]
    return render_template('index.html', params = params, posts = posts_preview, pre=pre,nex =nex)


@app.route("/about")
def about():
    return render_template('about.html', params = params)


@app.route("/posts", methods=['GET'])
def postsAll():
    p = Posts.query.filter_by().all()
    return render_template('postsAll.html', params = params, post_all = p)


@app.route("/posts/<string:post_slug>", methods=['GET'])
def posts(post_slug):
    p = Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html', params = params, post_no = p)


@app.route("/edit/<string:post_slug>", methods=['GET','POST'])
def edit(post_slug):
    if 'user' in session and session['user'] in params['admins'] :
        if post_slug=='post-new':
            ae = "Add Post"
        else:
            ae="Edit Post"
        if request.method == 'POST':
            ti = request.form.get('ti')
            to = request.form.get('to')
            au = request.form.get('au')
            sl = request.form.get('sl')
            im = request.form.get('im')
            co = request.form.get('co')
            da = datetime.now()
            
            if post_slug=='post-new':
                postNew = Posts(title =ti , topic=to, author=au,slug=sl, content=co,img_file=im, date=da)
                db.session.add(postNew)
                db.session.commit()
                flash("Post Added Successfully!", "success")
                return redirect('/login')
            else:
                post = Posts.query.filter_by(slug=post_slug).first()
                post.title = ti
                post.topic = to
                post.author =au
                post.slug = sl
                post.content = co
                post.img_file = im
                post.date = da
                db.session.commit()
                flash("Post Edited Successfully!", "success")
                return redirect('/login')
        else:
            if post_slug=='post-new':
                post = {
                    "title":"",
                    "topic":"",
                    "author":"",
                    "slug":"",
                    "content":"",
                    "img_file":""
                }
                return render_template('edit.html', params = params, admin = session['user'], ae=ae, post_slug=post_slug,post = post)
            else:
                post = Posts.query.filter_by(slug=post_slug).first()
                return render_template('edit.html', params = params, admin = session['user'], ae=ae, post_slug=post_slug,post=post)
                
    return redirect('/login')


@app.route("/delete/<string:post_slug>", methods=['GET','POST'])
def delete(post_slug):
    if 'user' in session and session['user'] in params['admins'] :
        flash("Post Deleted Successfully!", "danger")
        post = Posts.query.filter_by(slug=post_slug).first()
        db.session.delete(post)
        db.session.commit()
    return redirect('/login')


@app.route("/contact", methods= ['GET', 'POST'])
def contact():
    if request.method == "POST":
        n = request.form.get('name')
        e = request.form.get('email')
        p = request.form.get('phone')
        m = request.form.get('message')
    
        entry = Contacts(name=n, email = e, phone = p, message = m, date=datetime.now())
        db.session.add(entry)
        db.session.commit()
        
        mail.send_message(subject = f"Successfully Submitted your Message to {params['blog_author']}, author of {params['blog_name']}!", 
                          sender=params['gmail_id'], 
                          recipients=[e],
                          body = f"Dear {n},\n\nYour message has been Successfully submitted to {params['blog_author']}, author of {params['blog_name']}!\n\nWe will try to reach you ASAP!\n\nHope you are enjoying our Blog...\nThanks for your Response!\n\nFrom: {params['blog_author']}\nEmail: {params['gmail_id']}"  
                          )
        
        mail.send_message(subject = f"New message! by {n}, from your {params['blog_name']}", 
                          sender=params['gmail_id'], 
                          recipients=[params['gmail_id']],
                          body = f"From: {n}\nMessage : {m}\n\nContact : {p}\nEmail :{e}"
                          )

    return render_template('contact.html', params = params)


@app.route("/login", methods=['GET','POST'])
def login():
    display = "You haven't Signed in yet!"
    if 'user' in session and session['user'] in params['admins'] :
        p = Posts.query.filter_by().all()
        return render_template('admin.html', params = params, posts=p,admin=session['user'])
    
    if request.method == "POST":
        login = False
        u = request.form.get('u')
        p = request.form.get('p')
        a = params['admins']
        for k,i in a.items():
            if k==u and i==p:
                login = True
                session['user'] = u
        if login:
            p = Posts.query.filter_by().all()
            return render_template('admin.html', params = params, posts=p, admin=session['user'])
        else:
            return render_template('login.html', params = params, display="Invalid Username or Incorrect Password!")
            
    return render_template('login.html', params = params, display=display)
    
        
@app.route("/upload", methods=['GET','POST'])
def upload():
    flash("Image Uploaded Successfully!", "success")
    if 'user' in session and session['user'] in params['admins'] :
        if request.method == "POST":
            f = request.files['u']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            
    return redirect('/login')


@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/login')
    

app.run(debug=True)

