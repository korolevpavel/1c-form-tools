---
name: 1c-form-extract
description: Извлечение модулей обычных форм 1С из Form.bin в Module.bsl
---

## О навыке

Извлекает модули **обычных форм** из бинарных контейнеров Form.bin в отдельные файлы Module.bsl для редактирования во внешних редакторах.

Использует `container_reader` из библиотеки **v8unpack** для распаковки контейнеров 1С.

## Проблема

При сохранении обработки в XML:
- Управляемые формы → `Module.bsl` (отдельный файл) ✓
- Обычные формы → код внутри `Form.bin` (контейнер) ✗

## Команда

```cmd
bash .1c-tools/run-python .1c-tools/extract_form_modules.py <каталог> [--force] [--verbose]
```

**Параметры:**
- `каталог` — каталог с XML-выгрузкой (например `src`)
- `--force`, `-f` — перезаписать существующие Module.bsl
- `--verbose`, `-v` — подробный вывод

## Примеры

```cmd
# Извлечь модули (пропустить существующие)
bash .1c-tools/run-python .1c-tools/extract_form_modules.py src

# Извлечь с перезаписью
bash .1c-tools/run-python .1c-tools/extract_form_modules.py src --force

# Подробный вывод
bash .1c-tools/run-python .1c-tools/extract_form_modules.py src --force --verbose
```

## Результат

```
src/
└── Forms/
    └── ОбычнаяФорма/
        └── Ext/
            ├── Form.bin        ← контейнер (не трогаем)
            └── Module.bsl      ← ИЗВЛЕЧЁННЫЙ модуль
```

## Рабочий процесс

1. Сохранить обработку из конфигуратора: **Файл → Сохранить как... → Файлы XML**
2. Запустить извлечение: `bash .1c-tools/run-python .1c-tools/extract_form_modules.py src --force`
3. Редактировать `Module.bsl` файлы
4. Упаковать обратно: `/1c-form-pack`
5. Загрузить в конфигуратор: **Файл → Открыть...**

## Требования

```cmd
bash .1c-tools/run-python -c "import v8unpack"
```

## Окружение проекта

Команды выполняются из корня целевого проекта через Bash (Git Bash на Windows).
Скрипты, `run-python` и зависимости должны быть установлены по README репозитория.
Launcher и pre-commit используют одинаковый Python: явный `PYTHON`, проектный
`.1c-tools/.venv` (bin/python или Scripts/python.exe), затем Python >= 3.10 из PATH.
Активация venv не нужна. Если зависимости отсутствуют, выполните команду установки,
указанную launcher, через выбранный интерпретатор. Не устанавливайте их в другой Python.
Замените `src` фактическим каталогом XML-выгрузки; для одной формы используйте её каталог.

Результат нормализуется в UTF-8 BOM и CRLF без удвоения CR. `--force` перезаписывает существующие модули; используйте только когда это нужно задаче.
