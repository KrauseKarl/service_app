from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models.signals import post_delete

from .receivers import delete_cache_total_sum
from .tasks import set_price, set_comment
from clients.models import Client


class Service(models.Model):
    name = models.CharField(max_length=50)
    full_price = models.PositiveIntegerField()

    def __init__(self, *args, **kwargs):
        super(Service, self).__init__(*args, **kwargs)
        self.__full_price = self.full_price

    def save(self, *args, **kwargs):
        if self.full_price != self.__full_price:
            for subscription in self.subscriptions.all():
                set_price.delay(subscription.id)
                set_comment.delay(subscription.id)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name}'


class Plan(models.Model):
    PLAN_TYPE = (
        ('full', 'Full'),
        ('student', 'Student'),
        ('discount', 'Discount'),
    )
    plan_type = models.CharField(choices=PLAN_TYPE, max_length=10)
    discount_percent = models.PositiveIntegerField(default=0,
                                                   validators=[MaxValueValidator(100)])

    def __init__(self, *args, **kwargs):
        super(Plan, self).__init__(*args, **kwargs)
        self.__discount_percent = self.discount_percent

    def save(self, *args, **kwargs):
        if self.discount_percent != self.__discount_percent:
            for subscription in self.subscriptions.all():
                set_price.delay(subscription.id)
                set_comment.delay(subscription.id)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.plan_type} ({self.discount_percent}%)'


class Subscription(models.Model):
    client = models.ForeignKey(Client, related_name='subscriptions', on_delete=models.PROTECT)
    service = models.ForeignKey(Service, related_name='subscriptions', on_delete=models.PROTECT)
    plan = models.ForeignKey(Plan, related_name='subscriptions', on_delete=models.PROTECT)
    price = models.PositiveIntegerField(default=0)
    comment = models.CharField(max_length=50, default='', db_index=True)
    field_a = models.CharField(max_length=50, default='')
    field_b = models.CharField(max_length=50, default='')
    objects = models.Manager()

    class Meta:
        indexes = [
            models.Index(fields=['field_a', 'field_b'])
        ]

    def __str__(self):
        return f'{self.client} - {self.service} - {self.plan}'

    def save(self, *args, **kwargs):
        creating = not bool(self.id)
        result = super().save(*args, **kwargs)
        # if creating:
        #     set_price.delay(self.id)
        return result


post_delete.connect(delete_cache_total_sum, sender=Subscription)
