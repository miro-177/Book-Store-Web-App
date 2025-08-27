INSERT INTO User (name, phone_number, email, password, user_status, promos)
VALUES 
('Avery Thompson', '404-555-1278', 'avery.t@example.com', SHA2('password1', 256), 'Active', 1),
('Jordan Lee', '770-555-4321', 'jordan.lee@example.com', SHA2('password2', 256), 'Active', 0),
('John Doe', '452-555-4321', 'john.Doe@example.com', SHA2('password3', 256), 'Active', 0),
('Morgan Patel', '345-555-9988', 'morgan.p@example.com', SHA2('password4', 256), 'Inactive', 0),
('Admin', '678-555-9988', 'Admin@email.com', SHA2('Adm1n', 256), 'Admin', 1)
;
