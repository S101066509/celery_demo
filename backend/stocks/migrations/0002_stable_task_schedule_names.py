import json

from django.db import migrations
from django.utils import timezone


TASK = "stocks.tasks.data_tasks.run_data_task"


def rename_schedules(apps, schema_editor, reverse=False):
    StockTask = apps.get_model("stocks", "StockTask")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    Changes = apps.get_model("django_celery_beat", "PeriodicTasks")
    db = schema_editor.connection.alias
    schedules = PeriodicTask.objects.using(db)
    tasks = StockTask.objects.using(db).in_bulk()
    prefix = "Run Stock Task (ID:" if reverse else "Run Stock Task: "
    managed = schedules.filter(task=TASK, name__startswith=prefix)
    for entry in managed.only("pk", "name", "args").iterator():
        try:
            args = json.loads(entry.args)
        except (ValueError, TypeError):
            continue
        if not isinstance(args, list) or len(args) != 1 or type(args[0]) is not int:
            continue
        task_id = args[0]
        if not entry.name.endswith(f"(ID:{task_id})"):
            continue
        task = tasks.get(task_id)
        if task is None or not task.is_active or task.schedule_time is None:
            entry.delete(using=db)
            continue
        stable = f"Run Stock Task (ID:{task_id})"
        legacy = f"Run Stock Task: {task.name} (ID:{task_id})"
        expected, target = (stable, legacy) if reverse else (legacy, stable)
        if entry.name == expected:
            schedules.filter(pk=entry.pk).update(name=target)
        else:
            entry.delete(using=db)
    Changes.objects.using(db).update_or_create(ident=1, defaults={"last_update": timezone.now()})


def restore_names(apps, schema_editor):
    rename_schedules(apps, schema_editor, reverse=True)


class Migration(migrations.Migration):
    dependencies = [
        ("stocks", "0001_initial"),
        ("django_celery_beat", "0001_initial"),
    ]
    operations = [migrations.RunPython(rename_schedules, restore_names)]
