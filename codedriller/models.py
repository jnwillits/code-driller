from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from codedriller import db, login_manager, app
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin): 
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    date_registered = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    java_cards = db.relationship('JavaCards', backref='author', lazy=True)
    javascript_cards = db.relationship('JavascriptCards', backref='author', lazy=True)
    python_cards = db.relationship('PythonCards', backref='author', lazy=True)
    studying = db.Column(db.String, nullable=False, default='')
    upvoted = db.Column(db.String, nullable=False, default='')
    downvoted = db.Column(db.String, nullable=False, default='')
    archived = db.Column(db.String, nullable=False, default='')
    date_flagged = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    flagged = db.Column(db.Integer, nullable=False, default=0)

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"


class JavaCards(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, default='')
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    upvoted = db.Column(db.Integer, nullable=False, default=0)
    downvoted = db.Column(db.Integer, nullable=False, default=0)
    flagged = db.Column(db.Integer, nullable=False, default=0)
    flag_reason = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"JavaCards('{self.id}', '{self.question}')"



class JavascriptCards(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, default='')
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    upvoted = db.Column(db.Integer, nullable=False, default=0)
    downvoted = db.Column(db.Integer, nullable=False, default=0)
    flagged = db.Column(db.Integer, nullable=False, default=0)
    flag_reason = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"JavascriptCards('{self.id}', '{self.question}')"



class PythonCards(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, default='')
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    upvoted = db.Column(db.Integer, nullable=False, default=0)
    downvoted = db.Column(db.Integer, nullable=False, default=0)
    flagged = db.Column(db.Integer, nullable=False, default=0)
    flag_reason = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"PythonCards('{self.id}', '{self.question}')"
