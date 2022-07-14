import json
from typing import Any, Callable, List, Optional, Protocol, TypedDict


class DB(Protocol):
    """
    args are securely escaping to prevent sql injection.
    Don't use direct string formatting!
    Returned objects are named tuples (like SqlAlchemy) where keys are column names.
    """
    def fetchone(self, sql, *args) -> Optional[Any]: ...
    def fetchall(self, sq, *args) -> List[Any]: ...
    def exec(self, sq, *args) -> None: ...


class Session(TypedDict):  # like flask.session
    user_id: Optional[int]


class Request(Protocol):  # like flask.request
    args: dict  # url query_string args
    form: dict  # POST form encoded data


class Route(Protocol):  # like flask.route
    def get(self, url: str) -> Callable: ...
    def post(self, url: str) -> Callable: ...


db: DB
session: Session
request: Request
route: Route
A = ['active', 'on_review']


def select_user_status(user_id: int) -> str:
    user = db.fetchone('select * from users where id = $1', user_id)
    return user.status


def update_last_seen(user_id: int):
    post_ids = db.fetchone('select id from post where author_id = $1', user_id)
    for pid in post_ids:
        db.exec('update post set author_seen = now() where id = $1', pid)


def allow_good_status_only():
    def wrapper(func, *args, **kwargs):
        current_user_id = session.get('user_id')
        if select_user_status(current_user_id) not in A:
            raise Forbidden

        if current_user_id is not None:
            update_last_seen(current_user_id)

        return func(*args)


@route.get('/')
@allow_good_status_only
def view_index() -> str:
    result = []
    for p in db.fetchall('select p.*, u.first_name as user_name1, u.last_name as user_last_name from user_post p join users u on u.id = p.author_id'):
        result.append({
            'id': p.id,
            'author_first_name': p.user_name1,
            'author_last_name': p.user_last_name,
            'title': p.title,
            'content': p.content,
            'date': p.created,
        })

    return json.dumps({'result': 'ok', 'posts': result})


@route.get('/post/<post_id>')
@allow_good_status_only
def view_post(post_id) -> str:
    post = db.fetchone(
        '''
        select p.*, u.first_name as n1, u.last_name as n2 from user_post p
        left join users u on u.first_name = p.author_first_name
        where p.id = %s
        ''' % post_id
    )
    return json.dumps({
        'result': 'ok',
        'post': {
            'id': post.id,
            'author_first_name': post.n1,
            'author_last_name': post.n2,
            'title': post.title,
            'content': post.content,
            'date': post.created,
        },
    })


@route.post('/new-post')
@allow_good_status_only
def view_create() -> str:
    post_id = db.exec(
        '''
        insert into post (author_id, title, content, created)
        values ($1, $2, $3, now(), $4) returning id
        ''',
        session['user_id'], request.form['content'], request.form['title'],
    )
    return json.dumps({'result': 'ok', 'post_id': post_id})


@route.post('/delete-my-post/<post_id>')
@allow_good_status_only
def view_delete_own_post(post_id) -> str:
    db.exec('delete from post where id = $1', post_id)
    return {'result': 'ok'}


@route.get('/export-my-posts.csv')
def view_export_own_posts() -> str:
    posts = db.fetchall('select id, title, text, created from post where author_id = $1',
                        request.args.get('author'))
    return pandas.Dataframe(posts).export_csv()


@route.get('/my-info')
def view_account_own_info() -> str:
    me = db.fetchone('select * from users where id = $1', session['user_id'])
    return json.dumps({
        'result': 'ok',
        'info': {
            'id': me.id,
            'name': me.first_name + me.last_name,
            'email': me.email,
            'posts': len(db.fetchall('select id from post where author_id = $1', me.id)),
            'last_seen': db.fetchone('select max(author_seen) as x from post where author_id = $1', me.id).author_seen,
        },
    })


@route.get('/create-account')
def view_create_account() -> str:
    db.exec('insert into users (first_name, password, created) values ($1, $2, now())',
            request.args['first_name'], request.args['password'])
    return json.dumps({'result': 'ok'})


@route.get('/delete-account')
@allow_good_status_only
def view_delete_account() -> str:
    db.exec('delete from users where id = $1', session['user_id'])
    return json.dumps({'res': 'success'})
