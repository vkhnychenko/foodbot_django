# Generated by Django 3.0.5 on 2020-04-26 20:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Items',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('Шаверма', 'Шаверма'), ('Добавки', 'Добавки'), ('Закуски', 'Закуски'), ('Соусы', 'Соусы'), ('Напитки', 'Напитки')], db_index=True, max_length=100, verbose_name='Категории')),
                ('name', models.CharField(max_length=50, verbose_name='Наименование товара')),
                ('photo_url', models.URLField(unique=True)),
                ('price', models.PositiveSmallIntegerField(verbose_name='Цена')),
                ('price1', models.PositiveSmallIntegerField(default=0, verbose_name='Цена')),
                ('description', models.CharField(max_length=50)),
                ('caption', models.TextField(default='Описание', verbose_name='Описание или состав продукта')),
                ('size', models.CharField(default='None', max_length=50, verbose_name='Размер товара')),
            ],
            options={
                'verbose_name': 'Товар',
                'verbose_name_plural': 'Товары',
            },
        ),
        migrations.CreateModel(
            name='Users',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.PositiveSmallIntegerField(unique=True, verbose_name='ID пользователя')),
                ('name', models.CharField(max_length=50, verbose_name='Имя пользователя')),
                ('username', models.CharField(max_length=50, verbose_name='Никнейм пользователя')),
            ],
            options={
                'verbose_name': 'Профиль',
                'verbose_name_plural': 'Профили',
            },
        ),
        migrations.CreateModel(
            name='Orders',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.PositiveSmallIntegerField(verbose_name='ID пользователя')),
                ('quantity', models.PositiveSmallIntegerField(verbose_name='Количество')),
                ('size', models.CharField(max_length=50, verbose_name='Размер товара')),
                ('price', models.PositiveSmallIntegerField(verbose_name='Цена')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ugc.Items', verbose_name='Продукт')),
            ],
            options={
                'verbose_name': 'Заказы',
            },
        ),
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.PositiveSmallIntegerField(verbose_name='ID пользователя')),
                ('quantity', models.PositiveSmallIntegerField(verbose_name='Количество')),
                ('size', models.CharField(max_length=50, verbose_name='Размер товара')),
                ('price', models.PositiveSmallIntegerField(verbose_name='Цена')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ugc.Items', verbose_name='Продукт')),
            ],
            options={
                'verbose_name': 'Корзина товаров',
            },
        ),
    ]