from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, CreateRegistrationForm, CreateLoginForm, CreateCommentForm
from flask_gravatar import Gravatar
from functools import wraps
from sqlalchemy import ForeignKey


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


##CONFIGURE TABLES
class User(UserMixin,db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)

    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment",back_populates="commenter")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    author_id = db.Column(db.Integer,ForeignKey("user.id"))
    author = relationship("User", back_populates="posts")

    blog_comment = relationship("Comment", back_populates="blog")



# one blogpost(parent) many comments(chilled)
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    commenter = relationship("User", back_populates="comments")
    commenter_id = db.Column(db.Integer, ForeignKey("user.id"))

    blog = relationship("BlogPost", back_populates="blog_comment")
    blog_id = db.Column(db.Integer, ForeignKey("blog_posts.id"))


with app.app_context():
    db.create_all()



def admin_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return func(*args,**kwargs)
    return wrapper

@login_manager.user_loader
def load_user(user_id):
    user = db.session.query(User).filter_by(id=user_id).scalar()
    return user

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=['POST', 'GET'])
def register():
    register_form = CreateRegistrationForm()
    if register_form.validate_on_submit():
        if not db.session.query(User).filter_by(email=register_form.email.data).scalar():
            new_user= User(
                email=register_form.email.data,
                password=generate_password_hash(register_form.password.data,method="pbkdf2",salt_length=8),
                name=register_form.name.data,
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('get_all_posts'))
        flash("EMAIL ALREADY IN USE! LOG IN INSTEAD")
        return redirect(url_for("login"))
    return render_template("register.html",form= register_form)


@app.route('/login', methods=["POST", "GET"])
def login():
    login_form = CreateLoginForm()
    if login_form.validate_on_submit():
        user = db.session.query(User).filter_by(email=login_form.email.data).scalar()
        if user:
            check_pass = check_password_hash(pwhash=user.password, password=login_form.password.data)
            if check_pass:
                login_user(user)
                return redirect(url_for('get_all_posts'))
            flash("PASSWORD INCORRECT!")
        flash("EMAIL DOES NOT EXIST")
    return render_template("login.html", form=login_form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
@login_required
def show_post(post_id):
    requested_post = db.session.query(BlogPost).filter_by(id=post_id).scalar()
    comment_form = CreateCommentForm()
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("YOU MUST LOGIN/REGISTER FIRST TO COMMENT")
            return redirect(url_for("login"))
        else:
            new_comment = Comment(
                text=comment_form.comment.data,
                commenter=current_user,
                blog=requested_post
            )
            db.session.add(new_comment)
            db.session.commit()
            comment_form.comment.data = ""
            return render_template("post.html",post=requested_post,form=comment_form)
    return render_template("post.html", post=requested_post,form=comment_form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["POST","GET"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
