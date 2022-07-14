create table users (
    id int serial primary key,
    email varchar(200) not null unique,
    first_name varchar(200),
    last_name varchar(200),
    password varchar(10) not null,
    status varchar(25) not null,
    created timestamp not null
    -- +25 more columns here (birthday, country, language, middle_name, ...)
);

create table user_post (
    id int serial primary key,
    author_id int references users (id) not null,
    author_first_name varchar(200),
    author_last_name varchar(200),
    author_seen timestamp,
    title varchar(500) not null,
    content varchar(10000) not null,
    created timestamp not null
);
