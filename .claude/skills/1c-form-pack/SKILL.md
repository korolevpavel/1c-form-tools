---
name: 1c-form-pack
description: Упаковка модулей Module.bsl обратно в Form.bin обычных форм 1С
---

## О навыке

Упаковывает отредактированные модули Module.bsl обратно в бинарные контейнеры Form.bin обычных форм.

Использует `container_reader` / `container_writer` из библиотеки **v8unpack** для корректной работы с контейнерами 1С.

## Когда использовать

После редактирования `Module.bsl` файлов, извлечённых через `/1c-form-extract`, перед загрузкой обработки в конфигуратор.

**При коммите упаковка происходит автоматически** через pre-commit hook.

## Команда

```cmd
bash .1c-tools/run-python .1c-tools/pack_form_modules.py <каталог> [--no-backup] [--verbose]
```

**Параметры:**
- `каталог` — каталог с XML-выгрузкой (например `src`)
- `--no-backup` — не создавать Form.bin.bak
- `--verbose`, `-v` — подробный вывод

## Примеры

```cmd
# Упаковать (с backup)
bash .1c-tools/run-python .1c-tools/pack_form_modules.py src

# Упаковать без backup
bash .1c-tools/run-python .1c-tools/pack_form_modules.py src --no-backup

# Подробный вывод
bash .1c-tools/run-python .1c-tools/pack_form_modules.py src --verbose
```

## Что происходит

1. Скрипт ищет пары `Form.bin` + `Module.bsl`
2. Распаковывает контейнер Form.bin через `container_reader.extract`
3. Заменяет файл `module` содержимым Module.bsl
4. Собирает контейнер обратно через `container_writer.build`
5. Создаёт backup (`Form.bin.bak`) если не указан `--no-backup`

## Рабочий процесс

1. Извлечь модули: `/1c-form-extract`
2. Редактировать `Module.bsl` файлы
3. **Упаковать: `bash .1c-tools/run-python .1c-tools/pack_form_modules.py src`**
4. Загрузить в конфигуратор: **Файл → Открыть...**

## Требования

```cmd
bash .1c-tools/run-python -c "import v8unpack"
```

## Backup

По умолчанию создаётся `Form.bin.bak` перед перезаписью. Если упаковка не удалась, можно восстановить:

```cmd
cp Form.bin.bak Form.bin
```

## Окружение проекта

Команды выполняются из корня целевого проекта через Bash (Git Bash на Windows).
Скрипты, `run-python` и зависимости должны быть установлены по README репозитория.
Launcher и pre-commit используют одинаковый Python: явный `PYTHON`, проектный
`.1c-tools/.venv` (bin/python или Scripts/python.exe), затем Python >= 3.10 из PATH.
Активация venv не нужна. Если зависимости отсутствуют, выполните команду установки,
указанную launcher, через выбранный интерпретатор. Не устанавливайте их в другой Python.
Замените `src` фактическим каталогом XML-выгрузки; для одной формы используйте её каталог.

Хук должен быть установлен отдельно. Он блокирует частично добавленные в индекс пары Module.bsl / Form.bin.
