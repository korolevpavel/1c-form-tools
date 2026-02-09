# 1C Form Tools

Инструменты для редактирования модулей **обычных форм** внешних обработок 1С через Git и внешние редакторы (Claude Code, VS Code и др.)

## Проблема

При сохранении обработки из конфигуратора в XML:

| Тип формы | Модуль | Можно редактировать извне? |
|-----------|--------|---------------------------|
| Управляемая | `Module.bsl` (отдельный файл) | Да |
| Обычная | Внутри `Form.bin` (бинарник) | Нет |

## Решение

```
  Конфигуратор                    Git-репозиторий                  Редактор
 ┌───────────┐                   ┌─────────────────┐            ┌───────────┐
 │ Сохранить │  ──── XML ────►  │ Form.bin        │            │           │
 │ как XML   │                   │                 │            │ Claude    │
 └───────────┘                   │  extract ▼      │            │ Code      │
                                 │                 │            │           │
                                 │ Form.bin        │   edit     │ VS Code   │
                                 │ Module.bsl ◄────┼────────────┤           │
                                 │                 │            │ ...       │
                                 │  git commit     │            └───────────┘
                                 │  (auto-pack ▲)  │
 ┌───────────┐                   │                 │
 │ Открыть   │  ◄─── XML ─────  │ Form.bin ✓      │
 │ из XML    │                   └─────────────────┘
 └───────────┘
```

Два Python-скрипта + Git pre-commit hook:

- **extract_form_modules.py** — распаковывает `Form.bin` через v8unpack, извлекает модуль в `Module.bsl`
- **pack_form_modules.py** — упаковывает `Module.bsl` обратно в `Form.bin` через v8unpack
- **pre-commit hook** — автоматически вызывает pack при коммите

## Лицензия

[MIT](LICENSE)

## Требования

- Python 3.10+
- Git

### Зависимости

| Пакет | Назначение | Лицензия |
|-------|-----------|----------|
| [v8unpack](https://github.com/saby-integration/v8unpack) | Распаковка/сборка контейнеров 1С (Form.bin) | MIT |
| [tqdm](https://github.com/tqdm/tqdm) | Прогресс-бары (транзитивная зависимость v8unpack) | MIT/MPL |

Установка:

```
pip install v8unpack
```

## Установка в свой проект

Скопировать скрипты и hook в целевой репозиторий:

```cmd
mkdir <ваш-проект>\.1c-tools
copy extract_form_modules.py <ваш-проект>\.1c-tools\
copy pack_form_modules.py    <ваш-проект>\.1c-tools\
copy pre-commit              <ваш-проект>\.git\hooks\pre-commit
```

Для корректной работы хука с кириллическими путями:

```cmd
cd <ваш-проект>
git config core.quotePath false
```

## Рабочий процесс

### 1. Сохранение из конфигуратора

В конфигураторе: **Файл -> Сохранить как...** -> выбрать формат **Файлы XML** -> сохранить в каталог репозитория (например `src/`)

### 2. Извлечение модулей обычных форм

```cmd
python .1c-tools\extract_form_modules.py src --force
```

Результат — рядом с каждым `Form.bin` появится `Module.bsl`:

```
src/
├── Ext/
│   └── ObjectModule.bsl            <- модуль объекта (уже .bsl)
└── Forms/
    ├── УправляемаяФорма/
    │   └── Ext/Form/Module.bsl     <- уже есть от платформы
    └── ОбычнаяФорма/
        └── Ext/
            ├── Form.bin            <- бинарные данные формы
            └── Module.bsl          <- ИЗВЛЕЧЁННЫЙ модуль
```

### 3. Редактирование

Любым текстовым редактором — VS Code, Claude Code и т.д.

### 4. Коммит

```bash
git add -A
git commit -m "Рефакторинг основной формы"
```

Pre-commit hook автоматически:
1. Обнаружит изменённые `Module.bsl` рядом с `Form.bin`
2. Упакует модуль обратно в `Form.bin`
3. Добавит обновлённый `Form.bin` в коммит

### 5. Загрузка в конфигуратор

В конфигураторе: **Файл -> Открыть...** -> выбрать XML файл из каталога `src/`

## Параметры скриптов

### extract_form_modules.py

```
python extract_form_modules.py <каталог> [--force] [--verbose]

  каталог   Каталог с XML-выгрузкой обработки
  --force   Перезаписать существующие Module.bsl
  --verbose Подробный вывод
```

### pack_form_modules.py

```
python pack_form_modules.py <каталог> [--no-backup] [--verbose]

  каталог     Каталог с XML-выгрузкой обработки
  --no-backup Не создавать Form.bin.bak
  --verbose   Подробный вывод
```

## Интеграция с Claude Code

В каталоге `.claude/skills/` находятся скиллы для Claude Code:

- `/1c-form-extract` — извлечение модулей
- `/1c-form-pack` — упаковка модулей

Для подключения скопируйте каталог `.claude/skills/` в свой проект.

## Технические детали

### Формат Form.bin

`Form.bin` — контейнер 1С, содержащий два файла:
- **form** — бинарные данные разметки формы (элементы, свойства, привязки)
- **module** — текст модуля формы в UTF-8 с BOM

### Как работают скрипты

Оба скрипта используют `v8unpack` (`container_reader` / `container_writer`):

1. **Extract**: `container_reader.extract(Form.bin, temp_dir)` -> находит файл `module` -> сохраняет как `Module.bsl`
2. **Pack**: `container_reader.extract(Form.bin, temp_dir)` -> заменяет `module` содержимым `Module.bsl` -> `container_writer.build(temp_dir, Form.bin)`

Данные внутри контейнера хранятся без сжатия (`deflate=False`, `nested=True`).

## Структура проекта

```
1c-form-tools/
├── extract_form_modules.py       <- извлечение Module.bsl из Form.bin
├── pack_form_modules.py          <- упаковка Module.bsl обратно в Form.bin
├── pre-commit                    <- Git hook (авто-pack при коммите)
├── .claude/skills/               <- скиллы для Claude Code
│   ├── 1c-form-extract/SKILL.md
│   └── 1c-form-pack/SKILL.md
└── README.md
```
