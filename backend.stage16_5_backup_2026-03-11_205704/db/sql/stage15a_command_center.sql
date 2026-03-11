create table if not exists platform_modules (
    id bigserial primary key,
    code text not null unique,
    name text not null,
    description text,
    route_path text not null,
    icon text,
    sort_order int not null default 100,
    is_enabled boolean not null default true,
    created_at timestamptz not null default now()
);

create table if not exists platform_quick_actions (
    id bigserial primary key,
    code text not null unique,
    title text not null,
    route_path text not null,
    icon text,
    sort_order int not null default 100,
    is_enabled boolean not null default true,
    roles text[] not null default '{}',
    created_at timestamptz not null default now()
);

insert into platform_modules (code, name, description, route_path, icon, sort_order)
values
    ('supplier_tasks', 'Заявки поставщика', 'Импорт Excel, задачи, SLA и контроль статусов.', '/ui/tasks', '📋', 10),
    ('imports', 'Импорт Excel', 'Загрузка файлов и контроль качества данных.', '/ui/upload', '📥', 20),
    ('health', 'Health & Anomalies', 'Trust level, аномалии и состояние системы.', '/ui/dashboard', '🩺', 30),
    ('cleaning_journal', 'Cleaning Journal', 'Каркас второго модуля для объектов и журналов.', '/ui/command-center#roadmap', '🧹', 40),
    ('ai_assistant', 'AI Assistant', 'Управленческие сводки и будущий слой аналитики.', '/ui/command-center#ai', '🤖', 50)
on conflict (code) do update
set
    name = excluded.name,
    description = excluded.description,
    route_path = excluded.route_path,
    icon = excluded.icon,
    sort_order = excluded.sort_order,
    is_enabled = true;

insert into platform_quick_actions (code, title, route_path, icon, sort_order, roles)
values
    ('open_upload', 'Загрузить Excel', '/ui/upload', '⬆️', 10, array['dispatcher']),
    ('open_tasks', 'Открыть задачи', '/ui/tasks', '📋', 20, array['dispatcher']),
    ('open_dashboard', 'Открыть dashboard', '/ui/dashboard', '📊', 30, array['dispatcher']),
    ('open_mobile', 'Mobile view', '/m/tasks', '📱', 40, array['dispatcher']),
    ('open_health_api', 'Health API', '/api/dashboard/health', '🩺', 50, array['dispatcher'])
on conflict (code) do update
set
    title = excluded.title,
    route_path = excluded.route_path,
    icon = excluded.icon,
    sort_order = excluded.sort_order,
    roles = excluded.roles,
    is_enabled = true;
