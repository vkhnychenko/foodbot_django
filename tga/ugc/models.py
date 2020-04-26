from django.db import models


class Users(models.Model):
    user_id = models.PositiveIntegerField(verbose_name='ID пользователя', unique=True)
    name = models.CharField(verbose_name='Имя пользователя', max_length=50)
    username = models.CharField(verbose_name='Никнейм пользователя', max_length=50)

    def __str__(self):
        return f'{self.user_id} {self.name} {self.username}'

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'


# class Category(models.Model):
#     name = models.CharField('Название категории', max_length=50)
#
#     def __str__(self):
#         return f'{self.name}'
#
#     class Meta:
#         verbose_name = 'Категория'
#         verbose_name_plural = 'Категории'


class Items(models.Model):
    CATEGORIES = [
        ('Шаверма', 'Шаверма'),
        ('Добавки', 'Добавки'),
        ('Закуски', 'Закуски'),
        ('Соусы', 'Соусы'),
        ('Напитки', 'Напитки'),
    ]
    category = models.CharField('Категории',  choices=CATEGORIES,db_index=True, max_length=100)
    name = models.CharField('Наименование товара', max_length=50)
    photo_url = models.URLField(unique=True)
    price = models.PositiveIntegerField(verbose_name='Цена')
    price1 = models.PositiveIntegerField(verbose_name='Цена', default=0)
    description = models.CharField(max_length=50)
    caption = models.TextField('Описание или состав продукта', default='Описание')
    size = models.CharField('Размер товара', max_length=50, default='None')

    def __str__(self):
        return f'{self.name}'

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'


class Cart(models.Model):
    user_id = models.PositiveIntegerField(verbose_name='ID пользователя')
    product = models.ForeignKey(Items, verbose_name='Продукт', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    size = models.CharField('Размер товара', max_length=50)
    price = models.PositiveIntegerField(verbose_name='Цена')

    class Meta:
        verbose_name = 'Корзина товаров'


class Orders(models.Model):
    user_id = models.PositiveIntegerField(verbose_name='ID пользователя')
    product = models.ForeignKey(Items, verbose_name='Продукт', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    size = models.CharField('Размер товара', max_length=50)
    price = models.PositiveIntegerField(verbose_name='Цена')

    class Meta:
        verbose_name = 'Заказы'


