CREATE TABLE members (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    profile_pic TEXT NOT NULL

);

CREATE TABLE transactions (
    transaction_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    amount TEXT NOT NULL
);

CREATE TABLE spender (
    email TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    amount TEXT NOT NULL
);

CREATE TABLE borrower (
    email TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    amount TEXT NOT NULL,
    payto TEXT NOT NULL ,
    done TEXT NOT NULL
);

CREATE TABLE friends (
    youremail TEXT NOT NULL,
    friendemail TEXT NOT NULL,
    pay TEXT NOT NULL,
    rec TEXT NOT NULL 
);

CREATE TABLE notifications (
    youremail TEXT NOT NULL,
    friendemail TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    date TEXT NOT NULL ,
    time TEXT NOT NULL ,
    type TEXT NOT NULL
);