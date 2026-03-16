INSERT INTO users (id, full_name, email, role, is_active)
VALUES
('22222222-2222-2222-2222-222222222222', 'Manager 1', 'manager1@local', 'manager', true),
('33333333-3333-3333-3333-333333333333', 'Manager 2', 'manager2@local', 'manager', true),
('44444444-4444-4444-4444-444444444444', 'Manager 3', 'manager3@local', 'manager', true)
ON CONFLICT (email) DO NOTHING;

INSERT INTO stores (store_no, name, address, assigned_user_id, is_active)
VALUES
('1001', 'Store 1001', 'Address 1001', '22222222-2222-2222-2222-222222222222', true),
('1002', 'Store 1002', 'Address 1002', '33333333-3333-3333-3333-333333333333', true),
('1003', 'Store 1003', 'Address 1003', '44444444-4444-4444-4444-444444444444', true)
ON CONFLICT (store_no) DO UPDATE
SET
    name = EXCLUDED.name,
    address = EXCLUDED.address,
    assigned_user_id = EXCLUDED.assigned_user_id,
    is_active = EXCLUDED.is_active;
