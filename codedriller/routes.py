import os
import secrets
import sqlite3
from datetime import datetime
from random import choice
from PIL import Image
from pathlib import Path
from flask import render_template, url_for, flash, redirect, request, abort
from codedriller import app, db, bcrypt, mail
from codedriller.forms import (RegistrationForm, LoginForm, UpdateAccountForm,
                             PostForm, FlagForm, RequestResetForm, ResetPasswordForm)
from codedriller.models import User, PythonCards
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message

card_num = int()
cards_tot = int()
table = PythonCards
table_name = 'python_cards'
language = 'Python'
recently_viewed = []
non_auth_note = 'Use Code Driller to study Python learning flashcards. Study as a guest or login to create, archive, rate, and flag content.'


def get_paths(path):
    if os.path.exists(path):
        file_path = Path.cwd() / path
    else:
        file_path = None
    return file_path

def get_cards_tot(table_name):
    conn = sqlite3.connect(get_paths('codedriller\\site.db'))
    cursor = conn.cursor()
    cursor.execute(f'SELECT max(rowid) from {table_name}')
    total = cursor.fetchall()[0][0]
    if total is None:
        total = '0'
    else:
    # Find the number of flagged cards to subtract from the total.
        flags = db.session.execute(f'SELECT flagged FROM {table_name}')
        flags = [e for e, in flags]
        total -= flags.count(1)
    return total


def find_card_ids():
    card_ids = db.session.execute(f'SELECT id FROM {table_name}')
    card_ids = [e for e, in card_ids]
    flags = db.session.execute(f'SELECT flagged FROM {table_name}')
    flags = [e for e, in flags]
    for i in range(0, len(card_ids)):
        if flags[i] == 1:
            card_ids[i] = 0
    return card_ids

def archive_card():
    user = User.query.get(current_user.id) 
    if user.archived != '':
        user.archived = user.archived + ',' + str(card_num)
    else:
        user.archived = str(card_num)
    db.session.commit()


@app.route("/")
@app.route("/home")
def home():    
    global card_num, cards_tot, cards, recently_viewed, card_ids, num_archived, card_num_formatted

    card_subject = (PythonCards, 'python_cards',  'Python')
    table, table_name, language = card_subject
    
    card_ids = []
 
    page = request.args.get('page', 1, type=int)
    cards = table.query.order_by(table.id).paginate(page=page, per_page=10000)
    rows_tot = get_cards_tot(table_name)
    if rows_tot is not None:
        cards_tot = int(rows_tot)
    else:
        cards_tot = 0

    if not current_user.is_authenticated:
        flash(non_auth_note, 'info')

    if cards_tot == 0 and not current_user.is_authenticated:
        flash('There are no cards in this deck. Please register, login, and add some!', 'warning')
        sidebar = False
    else:
        sidebar = True    

    # THIS IS TEMPORARY FOR TEST...
    user_archived = [] 
    elgible_ids = []  

    if current_user.is_authenticated:
        if cards_tot > 0:
            user = User.query.get(current_user.id) 
            user_archived_temp = (user.archived).split(',')
            
            user_archived = []
            if len(user_archived_temp) > 0:
                for i in range(0, len(user_archived_temp)):
                    if user_archived_temp[i] != '':
                        user_archived.append(int(user_archived_temp[i]))
    
                elgible_ids = set(find_card_ids()).difference(set(user_archived))
                if len(recently_viewed) > 0:
                    elgible_ids = elgible_ids.difference(set(recently_viewed))
                
                if 0 in elgible_ids:
                    elgible_ids.remove(0)

                # If there is nothing to study, reset the archived cards.
                if len(elgible_ids) < 2:
                    flash('There are no cards eligible for viewing. Resetting archive...', 'warning')
                    user.archived = ''
                    db.session.commit()
                    elgible_ids = set(card_ids).difference(set(recently_viewed))
        
        else:
            flash(f'There are no cards in this deck. Add cards to study {language}.', 'warning')
            sidebar = False
    else:
        if cards_tot > 0:
            elgible_ids = set(find_card_ids())

    if 0 in elgible_ids:
        elgible_ids.remove(0)

    if len(elgible_ids) > 0:
        elgible_ids = elgible_ids.difference(set(recently_viewed))
        card_num = choice(tuple(elgible_ids))

        # If the card is not well rated, choose another card 60% of the time.
        if choice([0, 1]):
            table_query = table.query.get(card_num)
            if table_query.upvoted > 0 and table_query.downvoted > 0:
                rating_ratio = table_query.upvoted / table_query.downvoted
                if rating_ratio <= 0.6:
                    card_num = choice(tuple(elgible_ids))
            else:
                if table_query.upvoted == 0 and table_query.downvoted > 0:
                    card_num = choice(tuple(elgible_ids))


    card_ids = find_card_ids()
    recently_viewed_max = int(0.2 * len(card_ids))
    x = len(card_ids)
    if len(recently_viewed) <= recently_viewed_max:
        recently_viewed.append(card_num)
    else:
        recently_viewed.pop(0)
        recently_viewed.append(card_num)

    num_archived = len(user_archived)

    card_num_formatted = ('000' + str(card_num))[-4:]
    show_next_btn = False
    

    table_query = table.query.get(card_num) 
    card_submitter_id = table_query.user_id
    user = User.query.get(card_submitter_id) 
    card_submitter = user.username
    image_file = url_for('static', filename='profile_pics/' + user.image_file)
    
    return render_template('home.html', image_file=image_file, card_submitter=card_submitter, show_next_btn=show_next_btn, num_archived=num_archived, language=language, card_num_formatted=card_num_formatted, card_num=card_num, cards_tot=cards_tot, cards=cards, sidebar=sidebar, card_ids=card_ids, user_archived=user_archived, elgible_ids=elgible_ids, recently_viewed=recently_viewed)


def show_voting_btns_check():
    """ Determine whether to show voting buttons based on if the user has voted on the card. """
    user = User.query.get(current_user.id)
    if str(card_num) in (user.upvoted).split(',') or str(card_num) in (user.downvoted).split(','):
        return False
    return True


@app.route("/study_answer")
def study_answer():
    if current_user.is_authenticated:
        show_voting_btns = show_voting_btns_check()
    else:
        show_voting_btns = False
        flash(non_auth_note, 'info')

    table_query = table.query.get(card_num)
    card_submitter_id = table_query.user_id
    user = User.query.get(card_submitter_id) 
    card_submitter = user.username
    image_file = url_for('static', filename='profile_pics/' + user.image_file)

    return render_template('study_answer.html', image_file=image_file, card_submitter=card_submitter, show_voting_btns=show_voting_btns, show_next_btn=True, num_archived=num_archived, language=language, card_num=card_num, card_num_formatted=card_num_formatted, cards_tot=cards_tot, cards=cards, sidebar=True)



@app.route("/upvote", methods=['GET', 'POST'])
@app.route("/upvote")
def upvote():
    user = User.query.get(current_user.id) 
    if user.upvoted != '':
        user.upvoted = user.upvoted + ',' + str(card_num)
        user.upvoted = set(list(eval(user.upvoted)))

        # Convert the set of integers to a comma-delimited strings
        lst_temp = []
        for e in user.upvoted:
            lst_temp.append(str(e))
        user.upvoted = ','.join(lst_temp)   

    else:
        user.upvoted = str(card_num)
    
    # Update the language table.
    table_query = table.query.get(card_num)
    table_query.upvoted = table_query.upvoted + 1
    db.session.commit()
    return home()
   

@app.route("/downvote", methods=['GET', 'POST'])
@app.route("/downvote")
def downvote():
    user = User.query.get(current_user.id) 
    if user.downvoted != '':
        user.downvoted = user.downvoted + ',' + str(card_num)
        user.downvoted = set(list(eval(user.downvoted)))

        # Convert the set of integers to a comma-delimited strings
        lst_temp = []
        for e in user.downvoted:
            lst_temp.append(str(e))
        user.downvoted = ','.join(lst_temp)   

    else:
        user.downvoted = str(card_num)
    
    # Update the language table.
    table_query = table.query.get(card_num)
    table_query.downvoted = table_query.downvoted + 1
    db.session.commit()

    # Downvoted cards are archived.
    archive_card()

    return home()


@app.route("/flag", methods=['GET', 'POST'])
@app.route("/flag")
def flag():
    global table_name
    conn = sqlite3.connect(get_paths('codedriller\\site.db'))
    cursor = conn.cursor()
    # table_name = lang_tab[language]
    cursor.execute(f'Update {table_name} set flagged = 1 where id = {str(card_num)}')
    conn.commit()

    user = User.query.get(current_user.id)
    # Reset the user flagged quantity, if the user has flagged three times and more than one month has elapsed since the last time.
    duration = datetime.utcnow() - user.date_flagged
    days = duration.days
    if days > 30:
        user.flagged = 0
    # Update the user table to increment the total of flagged cards. 
    if user.flagged < 4:
        user.flagged = user.flagged + 1
        user.date_flagged = datetime.utcnow()
        db.session.commit()
    else:
        flash('You reached the maximum number of cards that can be flagged within a 30 day period.', 'warning')

    form = FlagForm()
    if form.validate_on_submit():
        card_table = table.query.get(card_num)
        card_table.flag_reason = form.reason.data
        db.session.commit()
        flash('Thank you for identifying content that needs to be flagged.', 'success')
        return redirect(url_for('home'))
    return render_template('flag_reason.html', title='Flag Reason', language=language, card_num=card_num, form=form)


@app.route("/archive", methods=['GET', 'POST'])
@app.route("/archive")
def archive():
    archive_card()
    return home()


@app.route("/about")
def about():
    page = request.args.get('page', 1, type=int)
    cards = table.query.order_by(table.id).paginate(page=page, per_page=10000)
    return render_template('about.html', title='About', cards=cards)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        cards = table(question=form.content.data, answer=form.content2.data, author=current_user, flag_reason='')
        db.session.add(cards)
        db.session.commit()
        flash('Your flashcard has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', form=form, legend=f'New {language} Flashcard')


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Code Driller Password Reset Request',
                  sender=os.environ.get('EMAIL_USER'),
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)
