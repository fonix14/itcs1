from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/ui/command-center", response_class=HTMLResponse)
async def command_center():

    html = """
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>ITCS Operations Center</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
body{
font-family:system-ui;
background:#0f172a;
color:white;
margin:0;
}

.header{
padding:20px;
background:#020617;
border-bottom:1px solid #1e293b;
}

.grid{
display:grid;
grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
gap:20px;
padding:30px;
}

.card{
background:#1e293b;
border-radius:14px;
padding:20px;
text-decoration:none;
color:white;
transition:0.2s;
}

.card:hover{
transform:translateY(-4px);
background:#334155;
}

.title{
font-size:20px;
margin-bottom:10px;
}

.desc{
opacity:0.7;
font-size:14px;
}

</style>
</head>

<body>

<div class="header">
<h1>ITCS Operations Center</h1>
</div>

<div class="grid">

<a class="card" href="/ui/tasks">
<div class="title">Задачи</div>
<div class="desc">Контроль всех заявок магазинов</div>
</a>

<a class="card" href="/ui/admin/managers">
<div class="title">Менеджеры</div>
<div class="desc">Назначение магазинов и управление</div>
</a>

<a class="card" href="/ui/director/dashboard">
<div class="title">Операционный обзор</div>
<div class="desc">Состояние сети магазинов</div>
</a>

<a class="card" href="/ui/upload">
<div class="title">Импорт Excel</div>
<div class="desc">Загрузка выгрузки портала</div>
</a>

<a class="card" href="/ui/dashboard">
<div class="title">Health Dashboard</div>
<div class="desc">Состояние системы и SLA</div>
</a>

</div>

</body>
</html>
"""

    return HTMLResponse(html)
