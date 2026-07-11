INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Generating static SQL
INFO  [alembic.runtime.migration] Will assume transactional DDL.
BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

INFO  [alembic.runtime.migration] Running upgrade  -> 2f0652c6fde1, initial schema
-- Running upgrade  -> 2f0652c6fde1

CREATE TABLE universities (
    name VARCHAR(255) NOT NULL, 
    initials VARCHAR(10) NOT NULL, 
    coords geography(POINT,4326), 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX idx_universities_coords ON universities USING gist (coords);

CREATE TABLE users (
    full_name VARCHAR(255) NOT NULL, 
    phone VARCHAR(20) NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    password_hash VARCHAR(255) NOT NULL, 
    role VARCHAR(20) NOT NULL, 
    is_verified BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE UNIQUE INDEX ix_users_phone ON users (phone);

CREATE TABLE houses (
    landlord_id VARCHAR(36) NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    location VARCHAR(255) NOT NULL, 
    coords geography(POINT,4326), 
    university_id VARCHAR(36), 
    price INTEGER NOT NULL, 
    walk_time VARCHAR(50), 
    drive_distance VARCHAR(50), 
    rating FLOAT NOT NULL, 
    available_spaces INTEGER NOT NULL, 
    accent VARCHAR(9) NOT NULL, 
    payment_methods JSON NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(landlord_id) REFERENCES users (id), 
    FOREIGN KEY(university_id) REFERENCES universities (id)
);

CREATE INDEX idx_houses_coords ON houses USING gist (coords);

CREATE TABLE landlord_payment_details (
    landlord_id VARCHAR(36) NOT NULL, 
    bank_name VARCHAR(100), 
    account_name VARCHAR(255), 
    account_number VARCHAR(50), 
    mobile_money_provider VARCHAR(50), 
    mobile_money_number VARCHAR(20), 
    is_default BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(landlord_id) REFERENCES users (id), 
    UNIQUE (landlord_id)
);

CREATE TABLE notifications (
    user_id VARCHAR(36) NOT NULL, 
    title VARCHAR(255) NOT NULL, 
    body TEXT NOT NULL, 
    is_read BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE favorites (
    user_id VARCHAR(36) NOT NULL, 
    house_id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(house_id) REFERENCES houses (id), 
    FOREIGN KEY(user_id) REFERENCES users (id), 
    CONSTRAINT uq_favorites_user_house UNIQUE (user_id, house_id)
);

CREATE TABLE house_amenities (
    house_id VARCHAR(36) NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(house_id) REFERENCES houses (id) ON DELETE CASCADE
);

CREATE TABLE house_images (
    house_id VARCHAR(36) NOT NULL, 
    url VARCHAR(500) NOT NULL, 
    "order" INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(house_id) REFERENCES houses (id) ON DELETE CASCADE
);

CREATE TABLE nearby_universities (
    house_id VARCHAR(36) NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    distance VARCHAR(50) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(house_id) REFERENCES houses (id) ON DELETE CASCADE
);

CREATE TABLE rooms (
    house_id VARCHAR(36) NOT NULL, 
    type VARCHAR(50) NOT NULL, 
    rent INTEGER NOT NULL, 
    deposit INTEGER, 
    available INTEGER NOT NULL, 
    features JSON NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(house_id) REFERENCES houses (id)
);

CREATE TABLE bookings (
    student_id VARCHAR(36) NOT NULL, 
    house_id VARCHAR(36) NOT NULL, 
    room_id VARCHAR(36) NOT NULL, 
    move_in_date DATE NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    note VARCHAR(500), 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(house_id) REFERENCES houses (id), 
    FOREIGN KEY(room_id) REFERENCES rooms (id), 
    FOREIGN KEY(student_id) REFERENCES users (id)
);

CREATE TABLE payments (
    reference VARCHAR(64) NOT NULL, 
    lenco_reference VARCHAR(128), 
    booking_id VARCHAR(36), 
    amount NUMERIC(12, 2) NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    operator VARCHAR(50) NOT NULL, 
    phone VARCHAR(20) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    payload JSON NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(booking_id) REFERENCES bookings (id)
);

CREATE UNIQUE INDEX ix_payments_reference ON payments (reference);

INSERT INTO alembic_version (version_num) VALUES ('2f0652c6fde1') RETURNING alembic_version.version_num;

INFO  [alembic.runtime.migration] Running upgrade 2f0652c6fde1 -> 6b380577949e, add otps table
-- Running upgrade 2f0652c6fde1 -> 6b380577949e

CREATE TABLE otps (
    user_id VARCHAR(36) NOT NULL, 
    code VARCHAR(10) NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    used BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_otps_user_id ON otps (user_id);

UPDATE alembic_version SET version_num='6b380577949e' WHERE alembic_version.version_num = '2f0652c6fde1';

INFO  [alembic.runtime.migration] Running upgrade 6b380577949e -> 9f8c7b6d5e4a, add payment_type to payments
-- Running upgrade 6b380577949e -> 9f8c7b6d5e4a

ALTER TABLE payments ADD COLUMN payment_type VARCHAR(20) DEFAULT 'mobile-money' NOT NULL;

UPDATE alembic_version SET version_num='9f8c7b6d5e4a' WHERE alembic_version.version_num = '6b380577949e';

INFO  [alembic.runtime.migration] Running upgrade 9f8c7b6d5e4a -> 3a1b2c4d5e6f, geo module schema
-- Running upgrade 9f8c7b6d5e4a -> 3a1b2c4d5e6f

ALTER TABLE houses ADD COLUMN formatted_address TEXT;

ALTER TABLE houses ALTER COLUMN coords SET NOT NULL;

CREATE TABLE eta_cache (
    house_id VARCHAR(36) NOT NULL, 
    university_id VARCHAR(36) NOT NULL, 
    mode VARCHAR(10) NOT NULL, 
    duration_s INTEGER NOT NULL, 
    distance_m INTEGER NOT NULL, 
    computed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(house_id) REFERENCES houses (id), 
    FOREIGN KEY(university_id) REFERENCES universities (id), 
    CONSTRAINT uix_eta_cache UNIQUE (house_id, university_id, mode)
);

UPDATE alembic_version SET version_num='3a1b2c4d5e6f' WHERE alembic_version.version_num = '9f8c7b6d5e4a';

INFO  [alembic.runtime.migration] Running upgrade 3a1b2c4d5e6f -> 332247adf24d, add email_verified
-- Running upgrade 3a1b2c4d5e6f -> 332247adf24d

ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT false NOT NULL;

UPDATE alembic_version SET version_num='332247adf24d' WHERE alembic_version.version_num = '3a1b2c4d5e6f';

COMMIT;

