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
python .1c-tools/extract_form_modules.py <каталог> [--force] [--verbose]
```

**Параметры:**
- `каталог` — каталог с XML-выгрузкой (например `src`)
- `--force`, `-f` — перезаписать существующие Module.bsl
- `--verbose`, `-v` — подробный вывод

## Примеры

```cmd
# Извлечь модули (пропустить существующие)
python .1c-tools/extract_form_modules.py src

# Извлечь с перезаписью
python .1c-tools/extract_form_modules.py src --force

# Подробный вывод
python .1c-tools/extract_form_modules.py src --force --verbose
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
2. Запустить извлечение: `python .1c-tools/extract_form_modules.py src --force`
3. Редактировать `Module.bsl` файлы
4. Упаковать обратно: `/1c-form-pack`
5. Загрузить в конфигуратор: **Файл → Открыть...**

## Требования

```cmd
pip install v8unpack
```
