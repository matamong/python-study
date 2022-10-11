from django.db import models


class Album(models.Model):
    title = models.CharField(max_length=200)
    desc = models.TextField()


class Track(models.Model):
    album = models.ForeignKey(Album, on_delete=models.DO_NOTHING)
    title = models.CharField(max_length=200)
    desc = models.TextField()

